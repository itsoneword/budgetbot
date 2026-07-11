"""
/recurring — manage recurring transaction rules (T-026).

Write path = the internal action API (create_rule / list_rules /
set_rule_active / delete_rule): handler-independent, so T-027's AI channel
calls the same validated functions and the LLM never gets its own write path.

Add is args-only (`/recurring add <name> <amount> <day>`): a free-text add
flow would be hijacked by the quick-add regex entry point in core.py.
Rule names are user text — all views render without parse_mode so names
can't inject HTML.
"""
import logging
from typing import List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from domain.recurring import format_rules_list, validate_rule_input
from infrastructure.repositories import RecurringRule
from shared.di import get_repos
from src.language_util import check_language, ensure_user_config_cached

logger = logging.getLogger(__name__)


# =========================================================================
# Internal action API (also the T-027 AI-channel surface)
# =========================================================================

async def create_rule(
    repos, user_id: int, name: str, amount: float, day: int,
    currency: str, language: str,
) -> RecurringRule:
    """Create an active spending rule; inputs must be pre-validated
    (domain.recurring.validate_rule_input). The category is resolved from the
    user's dictionary like the quick-add flow — 'other' when unknown."""
    categories = await repos.categories.find_category_by_subcategory(user_id, name, language)
    category = categories[0] if categories else "other"
    return await repos.recurring.add(
        user_id=user_id,
        category_name=category,
        subcategory_name=name,
        amount=amount,
        currency=currency,
        day_of_month=day,
    )


async def list_rules(repos, user_id: int) -> List[RecurringRule]:
    return await repos.recurring.list_for_user(user_id)


async def set_rule_active(repos, user_id: int, rule_id: int, active: bool) -> bool:
    return await repos.recurring.set_active(rule_id, user_id, active)


async def delete_rule(repos, user_id: int, rule_id: int) -> bool:
    return await repos.recurring.delete(rule_id, user_id)


# =========================================================================
# Rendering
# =========================================================================

def build_rules_view(rules: List[RecurringRule], texts) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """(message text, inline keyboard) for the rules list."""
    if not rules:
        return texts.RECURRING_LIST_EMPTY, None
    text = texts.RECURRING_LIST_HEADER + "\n\n" + format_rules_list(
        rules,
        paused_label=texts.RECURRING_PAUSED_LABEL,
        day_label=texts.RECURRING_DAY_WORD,
    ) + "\n\n" + texts.RECURRING_USAGE
    keyboard = []
    for rule in rules:
        if rule.active:
            toggle = InlineKeyboardButton(
                texts.RECURRING_PAUSE_BTN.format(rule.subcategory_name),
                callback_data=f"rr_pause_{rule.id}",
            )
        else:
            toggle = InlineKeyboardButton(
                texts.RECURRING_RESUME_BTN.format(rule.subcategory_name),
                callback_data=f"rr_resume_{rule.id}",
            )
        keyboard.append([
            toggle,
            InlineKeyboardButton(texts.RECURRING_DELETE_BTN, callback_data=f"rr_del_{rule.id}"),
        ])
    return text, InlineKeyboardMarkup(keyboard)


async def _render_rules(query, repos, user_id: int, texts) -> None:
    rules = await list_rules(repos, user_id)
    text, markup = build_rules_view(rules, texts)
    await query.edit_message_text(text, reply_markup=markup)


# =========================================================================
# Handlers
# =========================================================================

async def recurring_command(update: Update, context: CallbackContext) -> None:
    """/recurring — list rules; /recurring add <name> <amount> <day> — create."""
    user_id = update.effective_user.id
    repos = get_repos(context)
    config = await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    args = context.args or []

    if not args:
        rules = await list_rules(repos, user_id)
        text, markup = build_rules_view(rules, texts)
        await update.message.reply_text(text, reply_markup=markup)
        return

    if args[0].lower() != "add" or len(args) < 4:
        await update.message.reply_text(texts.RECURRING_USAGE)
        return

    name = " ".join(args[1:-2])
    payload, error = validate_rule_input(name, args[-2], args[-1])
    if error is not None:
        error_text = {
            "name": texts.RECURRING_INVALID_NAME,
            "amount": texts.RECURRING_INVALID_AMOUNT,
            "day": texts.RECURRING_INVALID_DAY,
        }[error]
        await update.message.reply_text(error_text + "\n\n" + texts.RECURRING_USAGE)
        return

    rule = await create_rule(
        repos, user_id,
        name=payload["name"], amount=payload["amount"], day=payload["day"],
        currency=config["currency"], language=config["language"],
    )
    message = texts.RECURRING_ADDED.format(
        name=rule.subcategory_name,
        amount=rule.amount,
        currency=rule.currency,
        day=rule.day_of_month,
    )
    if rule.day_of_month >= 29:
        message += "\n" + texts.RECURRING_DAY_CLAMP_NOTE
    await update.message.reply_text(message)


async def handle_recurring_callback(update: Update, context: CallbackContext) -> None:
    """rr_pause_/rr_resume_/rr_del_/rr_delc_/rr_back inline actions.

    Registered as a standalone CallbackQueryHandler (pattern '^rr') BEFORE
    spendings_handler in core.py, so its pattern-less menu_callback fallback
    can't swallow these while a conversation is active.
    """
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    data = query.data

    if data == "rr_back":
        await _render_rules(query, repos, user_id, texts)
        return

    try:
        action, rule_id = data.rsplit("_", 1)
        rule_id = int(rule_id)
    except ValueError:
        logger.warning("Bad recurring callback data: %r", data)
        return

    if action == "rr_pause":
        await set_rule_active(repos, user_id, rule_id, False)
        await _render_rules(query, repos, user_id, texts)
    elif action == "rr_resume":
        await set_rule_active(repos, user_id, rule_id, True)
        await _render_rules(query, repos, user_id, texts)
    elif action == "rr_del":
        rule = await repos.recurring.get_by_id(rule_id, user_id)
        if rule is None:
            await _render_rules(query, repos, user_id, texts)
            return
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                texts.RECURRING_CONFIRM_DELETE_BTN, callback_data=f"rr_delc_{rule_id}"
            ),
            InlineKeyboardButton(texts.RECURRING_BACK_BTN, callback_data="rr_back"),
        ]])
        await query.edit_message_text(
            texts.RECURRING_CONFIRM_DELETE.format(name=rule.subcategory_name),
            reply_markup=keyboard,
        )
    elif action == "rr_delc":
        deleted = await delete_rule(repos, user_id, rule_id)
        if not deleted:
            logger.warning("Recurring delete: rule %s not found for user %s", rule_id, user_id)
        await _render_rules(query, repos, user_id, texts)
    else:
        logger.warning("Unknown recurring callback action: %r", data)
