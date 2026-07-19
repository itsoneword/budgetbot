"""
AI-access paywall via Telegram Stars (T-023).

Flow: denial site or menu button -> send_ai_offer (inline Buy button) ->
send_invoice (currency XTR, no provider token — digital goods) ->
PreCheckoutQueryHandler (validation only, NO DB writes, must answer <10s) ->
successful_payment message — the ONLY place a purchase grants access:
payments.record() first (UNIQUE charge_id makes Telegram redeliveries
no-ops), then entitlements.grant(source='purchase').

Everything here is STATELESS (no context.user_data): a bot restart between
invoice and payment must not lose the flow. The invoice_payload encodes the
terms as sold ('ai:30'/'ai:perp', domain/payments.py) so a stale invoice
paid after a config change grants exactly what it advertised.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import CallbackContext

from domain.payments import encode_ai_payload, parse_ai_payload
from shared.di import get_repos
from src.config import AI_ACCESS_DAYS, AI_ACCESS_PRICE_STARS, is_admin
from src.language_util import check_language
from src.logger import log_user_interaction

STARS_CURRENCY = "XTR"


def _sold_duration_days():
    """Terms currently on sale: AI_ACCESS_DAYS, 0 -> None (perpetual)."""
    return AI_ACCESS_DAYS if AI_ACCESS_DAYS > 0 else None


def _offer_text(texts) -> str:
    days = _sold_duration_days()
    if days is None:
        return texts.BUY_AI_OFFER_PERPETUAL.format(price=AI_ACCESS_PRICE_STARS)
    return texts.BUY_AI_OFFER.format(days=days, price=AI_ACCESS_PRICE_STARS)


def build_ai_offer(texts, include_back: bool = False):
    """(offer text, inline keyboard) for the paywall offer.

    include_back appends a Back row (back_to_main_menu) — used by the
    menu_ask_ai edit-in-place path (T-044); message contexts (/ask, voice
    denial) keep the plain Buy-only keyboard.
    """
    rows = [[InlineKeyboardButton(texts.BUY_AI_BUTTON, callback_data="buy_ai")]]
    if include_back:
        rows.append(
            [InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_main_menu")]
        )
    return _offer_text(texts), InlineKeyboardMarkup(rows)


async def send_ai_offer(update: Update, context: CallbackContext) -> None:
    """Show the paywall offer with a Buy button.

    Contract (plan amendment): replies via update.effective_message so it
    works from message contexts (/ask and voice denial) AND from callback
    contexts, where update.message is None.
    """
    texts = check_language(update, context)
    text, keyboard = build_ai_offer(texts)
    await update.effective_message.reply_text(text, reply_markup=keyboard)


async def _send_invoice(update: Update, context: CallbackContext) -> None:
    """Send the Stars invoice. Payload encodes the terms as sold."""
    texts = check_language(update, context)
    days = _sold_duration_days()
    description = (
        texts.BUY_AI_DESCRIPTION_PERPETUAL if days is None
        else texts.BUY_AI_DESCRIPTION.format(days=days)
    )
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=texts.BUY_AI_TITLE,
        description=description,
        payload=encode_ai_payload(days),
        currency=STARS_CURRENCY,
        # Stars invoices take NO provider_token and exactly one price item.
        prices=[LabeledPrice(texts.BUY_AI_TITLE, AI_ACCESS_PRICE_STARS)],
    )


async def buy_ai(update: Update, context: CallbackContext) -> None:
    """/buy_ai — send the invoice. Already-entitled users are told a repeat
    purchase extends their access (GREATEST semantics in the repo) and get
    the invoice anyway."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    try:
        repos = get_repos(context)
        if await repos.entitlements.has_ai_access(user_id):
            await update.effective_message.reply_text(texts.BUY_AI_ALREADY)
    except Exception:
        # Informational check only — never block a purchase on a DB hiccup.
        logging.exception("buy_ai entitlement pre-check failed for user %s", user_id)
    await _send_invoice(update, context)


async def buy_ai_callback(update: Update, context: CallbackContext) -> None:
    """Buy button on the offer message -> invoice. The button itself never
    grants anything; the purchase still flows invoice -> successful_payment."""
    await update.callback_query.answer()
    await _send_invoice(update, context)


async def precheckout(update: Update, context: CallbackContext) -> None:
    """Answer the pre-checkout query. Validation only — NO DB access, the
    10-second answer deadline must never be at the mercy of a slow pool."""
    query = update.pre_checkout_query
    texts = check_language(update, context)
    ok = (
        query.currency == STARS_CURRENCY
        and parse_ai_payload(query.invoice_payload) is not None
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=texts.PAY_PRECHECKOUT_FAILED)


async def successful_payment(update: Update, context: CallbackContext) -> None:
    """THE only handler that turns money into access.

    Order matters: payments.record() first — its UNIQUE charge_id makes a
    Telegram redelivery return False, in which case the entitlement is NOT
    re-granted (a second grant would wrongly extend expiry again).
    """
    message = update.effective_message
    user_id = update.effective_user.id
    texts = check_language(update, context)
    sp = message.successful_payment
    charge_id = sp.telegram_payment_charge_id
    terms = parse_ai_payload(sp.invoice_payload)

    try:
        repos = get_repos(context)
        inserted = await repos.payments.record(
            user_id=user_id,
            telegram_payment_charge_id=charge_id,
            invoice_payload=sp.invoice_payload,
            currency=sp.currency,
            amount=sp.total_amount,
            duration_days=terms.duration_days if terms else None,
        )
        if inserted and terms is not None:
            entitlement = await repos.entitlements.grant(
                user_id,
                granted_by=user_id,
                source="purchase",
                duration_days=terms.duration_days,
                notes=f"stars charge {charge_id}",
            )
            await _send_receipt(message, texts, entitlement.expires_at)
        elif inserted:
            # Unreachable in practice (precheckout validates the payload) —
            # but money was taken, so make it findable for a manual /grant_ai.
            logging.critical(
                "Stars payment %s from user %s recorded with UNPARSEABLE payload %r "
                "— NO entitlement granted, run /grant_ai %s manually.",
                charge_id, user_id, sp.invoice_payload, user_id,
            )
            await message.reply_text(texts.ERROR_PROCESSING_REQUEST)
        else:
            # Redelivery of an already-recorded payment: receipt only, no re-grant.
            logging.warning(
                "Duplicate successful_payment delivery for charge %s (user %s) — "
                "skipping re-grant.", charge_id, user_id,
            )
            entitlement = await repos.entitlements.get(user_id)
            await _send_receipt(
                message, texts, entitlement.expires_at if entitlement else None
            )
    except Exception:
        # Money is taken; the grant state is unknown. CRITICAL with the
        # charge_id so the owner can audit and /grant_ai (or /refund_ai) manually.
        logging.critical(
            "Stars payment processing FAILED after payment: charge_id=%s user=%s "
            "payload=%r amount=%s — verify ai_payments/ai_entitlements, "
            "then /grant_ai %s or /refund_ai %s.",
            charge_id, user_id, sp.invoice_payload, sp.total_amount, user_id, user_id,
            exc_info=True,
        )
        await message.reply_text(texts.ERROR_PROCESSING_REQUEST)


async def _send_receipt(message, texts, expires_at) -> None:
    """Localized receipt: expiry date for timed passes, perpetual otherwise."""
    if expires_at is None:
        await message.reply_text(texts.BUY_AI_RECEIPT_PERPETUAL)
    else:
        await message.reply_text(
            texts.BUY_AI_RECEIPT_DAYS.format(expiry=expires_at.strftime("%Y-%m-%d %H:%M"))
        )


async def refund_ai(update: Update, context: CallbackContext) -> None:
    """Admin-only: /refund_ai USER_ID [charge_id] — refund a Stars payment
    (default: the user's latest paid one) and revoke ALL AI access (owner
    decision 2026-07-11: blunt revoke; re-grant remainders manually in
    stacked cases)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is restricted to the bot owner.")
        return

    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /refund_ai USER_ID [charge_id]")
        return
    target_id = int(args[0])

    repos = get_repos(context)
    if len(args) > 1:
        payment = await repos.payments.get_by_charge_id(args[1])
        if payment is None or payment.user_id != target_id:
            await update.message.reply_text(
                f"No payment with that charge id for user {target_id}."
            )
            return
        if payment.status != "paid":
            await update.message.reply_text(
                f"Payment {payment.telegram_payment_charge_id} is already refunded."
            )
            return
    else:
        payment = await repos.payments.get_latest_paid(target_id)
        if payment is None:
            await update.message.reply_text(f"User {target_id} has no refundable payment.")
            return

    charge_id = payment.telegram_payment_charge_id
    try:
        await context.bot.refund_star_payment(
            user_id=target_id, telegram_payment_charge_id=charge_id
        )
    except Exception as exc:
        logging.exception("refund_star_payment failed for charge %s", charge_id)
        await update.message.reply_text(
            f"Telegram refused the refund for {charge_id}: {exc}"
        )
        return

    marked = await repos.payments.mark_refunded(
        charge_id, refunded_by=update.effective_user.id
    )
    revoked = await repos.entitlements.revoke(
        target_id, revoked_by=update.effective_user.id
    )
    await update.message.reply_text(
        f"Refunded {payment.amount} XTR to {target_id} (charge {charge_id}).\n"
        f"Payment marked refunded: {'yes' if marked else 'NO — check ai_payments'}. "
        f"AI access revoked: {'yes' if revoked else 'no active entitlement'}.\n"
        "Note: a refund revokes ALL access — re-grant any remainder from other "
        "purchases manually with /grant_ai."
    )
