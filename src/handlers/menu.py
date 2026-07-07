"""
Menu handlers for main menu navigation and routing.

Handles: menu display, menu callbacks, submenu navigation.
"""

import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from language_util import check_language
from shared.di import get_repos
from src.logger import log_debug, log_function_call, log_state_transition, log_user_interaction
from keyboards import (
    create_main_menu_keyboard,
    create_show_transactions_keyboard,
    create_settings_keyboard_menu,
    create_settings_language_keyboard,
    create_settings_currency_keyboard,
    create_tx_categories_keyboard,
)
from src.states import (
    TRANSACTION,
    SELECT_TRANSACTION_CATEGORY,
    SETTINGS_LANGUAGE,
    SETTINGS_CURRENCY,
    SETTINGS_LIMIT,
    ADD_CATEGORY,
)

# Import handlers used by menu_call
from src.handlers.records import show_records, show_last_month_records
from src.handlers.charts import send_chart, send_yearly_piechart
from src.handlers.categories import show_categories
from src.handlers.transactions import show_recent_entries
from src.detailed_transactions import start_detailed_transactions


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
    """Handle menu callbacks using dispatch pattern."""
    query = update.callback_query
    log_function_call()

    user_id = update.effective_user.id
    texts = check_language(update, context)
    action = query.data

    # Import show_detailed here to avoid circular imports
    from src.core import show_detailed

    # =========================================================================
    # Show transactions actions
    # =========================================================================
    if action == "show_monthly_summary":
        await query.answer()
        await query.edit_message_text(texts.LOADING_MONTHLY_SUMMARY)
        await show_records(update, context)
        return await _return_to_main_menu(query, texts)

    if action == "show_last_month_summary":
        await query.answer()
        await query.edit_message_text(texts.LOADING_LAST_MONTH_SUMMARY)
        await show_last_month_records(update, context)
        return await _return_to_main_menu(query, texts)

    if action == "show_last_transactions":
        await query.answer()
        return await start_detailed_transactions(update, context)

    if action == "show_monthly_charts":
        await query.answer()
        await query.edit_message_text(texts.GENERATING_MONTHLY_CHARTS)
        await send_chart(update, context)
        return await _return_to_main_menu(query, texts)

    if action == "show_extended_stats":
        await query.answer()
        await query.edit_message_text(texts.LOADING_EXTENDED_STATS)
        await show_detailed(update, context)
        return await _return_to_main_menu(query, texts)

    if action == "show_last_month_extended_stats":
        await query.answer()
        await query.edit_message_text(texts.LOADING_LAST_MONTH_EXTENDED_STATS)
        await show_detailed(update, context, period='last_month')
        return await _return_to_main_menu(query, texts)

    if action == "show_yearly_charts":
        await query.answer()
        await query.edit_message_text(texts.GENERATING_YEARLY_CHARTS)
        await send_yearly_piechart(update, context)
        return await _return_to_main_menu(query, texts)

    if action == "show_income_stats":
        await query.answer()
        await query.edit_message_text(texts.LOADING_INCOME_STATS)
        update.effective_message.text = "/show_income"
        await show_records(update, context)
        return await _return_to_main_menu(query, texts)

    # =========================================================================
    # Category management actions
    # =========================================================================
    if action == "edit_show_categories":
        await query.answer()
        return await show_categories(update, context)

    if action == "menu_edit_transactions":
        await query.answer()
        return await show_recent_entries(update, context)

    if action == "menu_edit_categories":
        await query.answer()
        context.user_data["current_page"] = 0
        return await show_categories(update, context)

    # =========================================================================
    # Main menu navigation
    # =========================================================================
    if action in ("menu_add_transaction", "back_to_categories"):
        log_function_call()
        repos = get_repos(context)
        language = context.user_data.get('language', 'en')
        categories = await repos.categories.get_all_categories(user_id, language)

        context.user_data["tx_categories"] = categories
        context.user_data["tx_page"] = 0

        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await query.edit_message_text(
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SELECT_TRANSACTION_CATEGORY)
        return SELECT_TRANSACTION_CATEGORY

    if action == "menu_show_transactions":
        reply_markup = create_show_transactions_keyboard(texts)
        await query.edit_message_text(
            texts.SHOW_TRANSACTIONS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_settings":
        reply_markup = create_settings_keyboard_menu(texts)
        await query.edit_message_text(
            texts.SETTINGS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "menu_help":
        await query.edit_message_text(texts.HELP_TEXT)
        return await _return_to_main_menu(query, texts)

    if action == "back_to_main_menu":
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    # =========================================================================
    # Settings submenu
    # =========================================================================
    if action == "settings_change_language":
        reply_markup = create_settings_language_keyboard()
        await query.edit_message_text(
            texts.SELECT_LANGUAGE,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SETTINGS_LANGUAGE)
        return SETTINGS_LANGUAGE

    if action == "settings_change_currency":
        reply_markup = create_settings_currency_keyboard()
        await query.edit_message_text(
            texts.CHOOSE_CURRENCY_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(SETTINGS_CURRENCY)
        return SETTINGS_CURRENCY

    if action == "settings_change_limit":
        context.user_data['awaiting_limit'] = True
        await query.edit_message_text(texts.CHOOSE_LIMIT_TEXT)
        log_state_transition(SETTINGS_LIMIT)
        return SETTINGS_LIMIT

    if action == "settings_about":
        repos = get_repos(context)
        config = await repos.users.get_config(int(user_id))
        currency = config.currency if config else 'EUR'
        language = config.language if config else 'en'
        limit = float(config.monthly_limit) if config else 99999999

        await query.edit_message_text(
            texts.ABOUT.format(query.from_user.first_name, currency, language, limit),
            parse_mode=ParseMode.HTML
        )
        return await _return_to_main_menu(query, texts)

    # =========================================================================
    # Transaction actions
    # =========================================================================
    if action == "cancel_transaction":
        log_function_call()
        await query.edit_message_text(
            texts.TRANSACTION_CANCELED,
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(1)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log_state_transition(TRANSACTION)
        return TRANSACTION

    if action == "edit_add_remove_category":
        await query.edit_message_text(
            texts.ADD_CAT_PROMPT,
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


async def _return_to_main_menu(query, texts):
    """Helper: Return to main menu after an action."""
    reply_markup = create_main_menu_keyboard(texts)
    await query.message.reply_text(
        texts.BACK_TO_MAIN_MENU,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    log_state_transition(TRANSACTION)
    return TRANSACTION
