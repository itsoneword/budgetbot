"""
Menu handlers for main menu navigation and routing.

Handles: menu display, menu callbacks, submenu navigation.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from src.language_util import check_language, format_monthly_limit
from shared.di import get_repos
from src.commands import build_help_text
from src.config import ADMIN_USER_ID, VERSION, VERSION_DATE
from src.logger import log_debug, log_function_call, log_state_transition, log_user_interaction
from src.keyboards import (
    create_main_menu_keyboard,
    create_show_transactions_keyboard,
    create_settings_keyboard_menu,
    create_settings_language_keyboard,
    create_settings_currency_keyboard,
    create_tx_categories_keyboard,
    create_add_transaction_keyboard,
)
from src.states import (
    TRANSACTION,
    SELECT_TRANSACTION_CATEGORY,
    SETTINGS_LANGUAGE,
    SETTINGS_CURRENCY,
    SETTINGS_LIMIT,
    ADD_CATEGORY,
    PROCESS_INCOME,
    ASK_INPUT,
)

# Import handlers used by menu_call
from src.handlers.recurring import build_rules_view, list_rules
from src.handlers.reminders import build_reminder_view, build_tz_keyboard, get_reminder
from src.handlers.records import build_records_report, build_last_month_report
from src.handlers.charts import send_chart, send_yearly_piechart
from src.handlers.categories import show_categories
from src.handlers.transactions import show_recent_entries
from src.detailed_transactions import start_detailed_transactions

# Telegram hard limit for message text length.
TELEGRAM_MESSAGE_LIMIT = 4096


async def _safe_edit(query, text, **kwargs):
    """edit_message_text that swallows the 'Message is not modified' error.

    Double-tapping a button re-issues the same edit; Telegram rejects it with
    BadRequest and without this guard every second tap would trip the global
    error handler. Everything else re-raises.
    """
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


def _back_kb(texts, cb: str = "back_to_main_menu") -> InlineKeyboardMarkup:
    """One-row keyboard with a single Back button."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(texts.BACK_BUTTON, callback_data=cb)]]
    )


async def _edit_to_main_menu(query, texts):
    """Edit the tapped (anchor) message back into the main menu."""
    await _safe_edit(
        query,
        texts.MAIN_MENU_TEXT,
        reply_markup=create_main_menu_keyboard(texts),
        parse_mode=ParseMode.HTML,
    )
    log_state_transition(TRANSACTION)
    return TRANSACTION


def _split_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT):
    """Split text into <=limit chunks on line boundaries (hard-cut fallback)."""
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # pathological single line — hard cut
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


async def _edit_report(query, texts, text, reply_markup, parse_mode=None):
    """Edit the anchor into a report + Back button, in place.

    Reports longer than one Telegram message can't be an edit: fall back to
    sending the chunks and restoring the anchor to the main menu, so exactly
    one menu keyboard exists — never a duplicate menu message.
    """
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        await _safe_edit(query, text, reply_markup=reply_markup, parse_mode=parse_mode)
        log_state_transition(TRANSACTION)
        return TRANSACTION
    for chunk in _split_text(text):
        await query.message.reply_text(chunk, parse_mode=parse_mode)
    return await _edit_to_main_menu(query, texts)


async def show_menu(update: Update, context: CallbackContext):
    """Display the main menu."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    # Clear user_data cache when returning to main menu
    # Keep only essential data like language settings
    language = context.user_data.get('language', None)
    context.user_data.clear()
    log_debug(f"context.user_data is {context.user_data}")
    if language:
        context.user_data['language'] = language

    reply_markup = create_main_menu_keyboard(texts)
    await update.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    log_state_transition(TRANSACTION)
    return TRANSACTION


async def menu_call(update: Update, context: CallbackContext):
    """Handle menu callbacks using dispatch pattern.

    Edit-in-place navigation (T-044): every branch either edits the tapped
    message (the navigation anchor) into the requested view — with a Back
    button where the view isn't itself a menu — or, for flows that must send
    new content (media groups, invoices, typed input), sends it and edits
    the anchor back to the main menu. No branch re-sends the menu as a new
    message.
    """
    query = update.callback_query
    log_function_call()

    # Single ack for every branch; stale queries (e.g. after a restart) are
    # already expired at Telegram — never let that kill the navigation.
    try:
        await query.answer()
    except BadRequest:
        pass

    user_id = update.effective_user.id
    texts = check_language(update, context)
    action = query.data

    # Ask-AI typed-question mode (T-045): any menu tap cancels a pending
    # question prompt — only the menu_ask_ai branch below re-arms the flag.
    # Prevents a stale flag from swallowing a later typed transaction.
    context.user_data.pop("awaiting_ask", None)

    # Import here to avoid circular imports
    from src.core import build_detailed_report

    # =========================================================================
    # Show transactions actions
    # =========================================================================
    if action == "show_monthly_summary":
        report = await build_records_report(update, context, tx_type='spending')
        return await _edit_report(
            query, texts, report or texts.RECORDS_NOT_FOUND_TEXT,
            reply_markup=_back_kb(texts), parse_mode=ParseMode.HTML,
        )

    if action == "show_last_month_summary":
        report = await build_last_month_report(update, context, tx_type='spending')
        return await _edit_report(
            query, texts, report or texts.RECORDS_NOT_FOUND_TEXT,
            reply_markup=_back_kb(texts), parse_mode=ParseMode.HTML,
        )

    if action == "show_last_transactions":
        return await start_detailed_transactions(update, context)

    if action == "show_monthly_charts":
        await _safe_edit(query, texts.GENERATING_MONTHLY_CHARTS)
        if await send_chart(update, context):
            # Media went out as new messages — restore the anchor to the menu
            # so exactly one menu keyboard exists.
            return await _edit_to_main_menu(query, texts)
        return await _edit_report(
            query, texts, texts.NO_DATA, reply_markup=_back_kb(texts)
        )

    if action == "show_extended_stats":
        report = await build_detailed_report(update, context)
        return await _edit_report(
            query, texts, report, reply_markup=_back_kb(texts)
        )

    if action == "show_last_month_extended_stats":
        report = await build_detailed_report(update, context, period='last_month')
        return await _edit_report(
            query, texts, report, reply_markup=_back_kb(texts)
        )

    if action == "show_yearly_charts":
        await _safe_edit(query, texts.GENERATING_YEARLY_CHARTS)
        if await send_yearly_piechart(update, context):
            return await _edit_to_main_menu(query, texts)
        return await _edit_report(
            query, texts, texts.NO_YEARLY_DATA, reply_markup=_back_kb(texts)
        )

    if action == "show_income_stats":
        # PTB Message objects are immutable — pass the type, don't mutate .text
        report = await build_records_report(update, context, tx_type='income')
        return await _edit_report(
            query, texts, report or texts.RECORDS_NOT_FOUND_TEXT,
            reply_markup=_back_kb(texts), parse_mode=ParseMode.HTML,
        )

    # =========================================================================
    # Category management actions
    # =========================================================================
    if action == "edit_show_categories":
        return await show_categories(update, context)

    if action == "menu_edit_transactions":
        return await show_recent_entries(update, context)

    if action == "menu_edit_categories":
        context.user_data["current_page"] = 0
        return await show_categories(update, context)

    # =========================================================================
    # Main menu navigation
    # =========================================================================
    if action == "menu_add_transaction":
        # Add-transaction section (T-035/T-036): spending / income / recurring
        reply_markup = create_add_transaction_keyboard(texts)
        await _safe_edit(
            query,
            texts.ADD_TX_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_add_income":
        # Prompt for income input; the PROCESS_INCOME state of the main
        # conversation catches the next message (save_income_text path).
        # Back is served by the conversation fallback (menu_callback).
        await _safe_edit(
            query, texts.INCOME_HELP,
            reply_markup=_back_kb(texts), parse_mode=ParseMode.HTML,
        )
        log_state_transition(PROCESS_INCOME)
        return PROCESS_INCOME

    if action in ("menu_add_spending", "back_to_categories"):
        log_function_call()
        repos = get_repos(context)
        language = context.user_data.get('language', 'en')
        categories = await repos.categories.get_all_categories(user_id, language)

        context.user_data["tx_categories"] = categories
        context.user_data["tx_page"] = 0

        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await _safe_edit(
            query,
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SELECT_TRANSACTION_CATEGORY)
        return SELECT_TRANSACTION_CATEGORY

    if action == "menu_show_transactions":
        reply_markup = create_show_transactions_keyboard(texts)
        await _safe_edit(
            query,
            texts.SHOW_TRANSACTIONS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_recurring":
        # Recurring rules (T-026). Rendered without parse_mode: rule names are
        # user text. Button presses are handled by the standalone ^rr
        # CallbackQueryHandler registered before spendings_handler in core.py.
        repos = get_repos(context)
        rules = await list_rules(repos, user_id)
        text, reply_markup = build_rules_view(
            rules, texts, back_cb="back_to_main_menu"
        )
        await _safe_edit(query, text, reply_markup=reply_markup)
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_reminder":
        # Daily reminder (T-034). Button presses (rem_*/tzpick_*) are handled
        # by standalone CallbackQueryHandlers registered before
        # spendings_handler in core.py, like ^rr.
        repos = get_repos(context)
        reminder = await get_reminder(repos, user_id)
        text, reply_markup = build_reminder_view(
            reminder, texts, back_cb="back_to_main_menu"
        )
        await _safe_edit(query, text, reply_markup=reply_markup)
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_settings":
        reply_markup = create_settings_keyboard_menu(texts)
        await _safe_edit(
            query,
            texts.SETTINGS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_ask_ai":
        # Ask-AI funnel (T-023): entitled users get the typed-question prompt
        # (T-045) and the conversation moves to ASK_INPUT (T-046) — inside the
        # conversation the TRANSACTION state would route typed text to the
        # amount handler, so the question needs its own state. The
        # awaiting_ask flag stays as the out-of-conversation backup (stale
        # prompt after a restart -> top-level handle_text intercept); Back or
        # any other menu tap clears it (pop at the top of menu_call).
        # Everyone else gets the Stars offer — both as edits of the anchor
        # (T-044). The button never grants anything — purchases flow
        # exclusively invoice -> successful_payment (handlers/payments.py).
        # A Buy tap still sends the invoice as a new message (unavoidable);
        # the anchor keeps its Back button.
        from src.ai_access import check_ai_access
        from src.handlers.payments import build_ai_offer
        if await check_ai_access(user_id, context):
            context.user_data["awaiting_ask"] = True
            await _safe_edit(query, texts.ASK_AI_PROMPT, reply_markup=_back_kb(texts))
            log_state_transition(ASK_INPUT)
            return ASK_INPUT
        offer_text, offer_kb = build_ai_offer(texts, include_back=True)
        await _safe_edit(query, offer_text, reply_markup=offer_kb)
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_help":
        await _safe_edit(
            query,
            build_help_text(texts, is_admin=query.from_user.id == ADMIN_USER_ID),
            reply_markup=_back_kb(texts),
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "back_to_main_menu":
        # Leaving an input prompt via Back must also drop the
        # out-of-conversation limit marker (see settings_change_limit).
        context.user_data.pop('awaiting_limit', None)
        return await _edit_to_main_menu(query, texts)

    # =========================================================================
    # Settings submenu
    # =========================================================================
    if action == "settings_change_language":
        reply_markup = create_settings_language_keyboard()
        await _safe_edit(
            query,
            texts.SELECT_LANGUAGE,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SETTINGS_LANGUAGE)
        return SETTINGS_LANGUAGE

    if action == "settings_change_currency":
        reply_markup = create_settings_currency_keyboard()
        await _safe_edit(
            query,
            texts.CHOOSE_CURRENCY_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SETTINGS_CURRENCY)
        return SETTINGS_CURRENCY

    if action == "settings_change_limit":
        context.user_data['awaiting_limit'] = True
        # Back leads home (and clears awaiting_limit in the branch above).
        await _safe_edit(query, texts.CHOOSE_LIMIT_TEXT, reply_markup=_back_kb(texts))
        log_state_transition(SETTINGS_LIMIT)
        return SETTINGS_LIMIT

    if action == "settings_timezone":
        # One-tap timezone picker (T-034); tzpick_ taps are handled by the
        # standalone handler registered before spendings_handler in core.py.
        # Back returns to the Settings submenu.
        await _safe_edit(
            query, texts.TZ_PICK_PROMPT,
            reply_markup=build_tz_keyboard(back_cb="menu_settings", texts=texts),
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "settings_about":
        repos = get_repos(context)
        config = await repos.users.get_config(int(user_id))
        name = (config.name if config else None) or query.from_user.first_name
        currency = config.currency if config else 'EUR'
        language = config.language if config else 'en'
        limit = float(config.monthly_limit) if config else 99999999

        # Back returns to the Settings submenu this view came from.
        await _safe_edit(
            query,
            texts.ABOUT.format(
                name, currency, language,
                format_monthly_limit(limit, texts), VERSION, VERSION_DATE,
            ),
            reply_markup=_back_kb(texts, cb="menu_settings"),
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    # =========================================================================
    # Transaction actions
    # =========================================================================
    if action == "cancel_transaction":
        log_function_call()
        # Single edit: cancellation notice + main menu in one message — no
        # sleep, no extra menu message (T-044).
        await _safe_edit(
            query,
            texts.TRANSACTION_CANCELED + "\n\n" + texts.MAIN_MENU_TEXT,
            reply_markup=create_main_menu_keyboard(texts),
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "edit_add_remove_category":
        await _safe_edit(
            query,
            texts.ADD_CAT_PROMPT,
            reply_markup=_back_kb(texts),
            parse_mode="MarkdownV2"
        )
        log_state_transition(ADD_CATEGORY)
        return ADD_CATEGORY

    # Default fallback
    log_state_transition(TRANSACTION)
    return TRANSACTION


async def menu_callback(update: Update, context: CallbackContext) -> int:
    """Fallback callback handler that routes to menu_call."""
    query = update.callback_query
    user_id = update.effective_user.id
    log_debug("menu_callback called")
    return await menu_call(update, context)
