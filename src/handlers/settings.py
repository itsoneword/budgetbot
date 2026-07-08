"""
Settings handlers for modifying user preferences.

Handles: language change, currency change, spending limit modification.
"""

from decimal import Decimal

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from src.language_util import check_language
from shared.di import get_repos
from src.logger import log_debug, log_state_transition
from src.keyboards import create_main_menu_keyboard
from src.states import TRANSACTION, SETTINGS_LIMIT


async def handle_settings_language(update: Update, context: CallbackContext):
    """Handle language change from settings menu."""
    query = update.callback_query
    user_id = update.effective_user.id
    new_lang = query.data.split('_')[1]

    # Save to database
    repos = get_repos(context)
    await repos.users.update_language(user_id, new_lang)

    # Update language cache
    context.user_data['cached_language'] = new_lang

    texts = check_language(update, context)

    await query.edit_message_text(texts.LANGUAGE_REPLY.format(new_lang))

    # Send a new message with the main menu keyboard to continue interaction
    reply_markup = create_main_menu_keyboard(texts)
    await query.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    log_state_transition(TRANSACTION)
    return TRANSACTION


async def handle_settings_currency(update: Update, context: CallbackContext):
    """Handle currency change from settings menu."""
    query = update.callback_query
    user_id = update.effective_user.id
    texts = check_language(update, context)

    new_currency = query.data.split('_')[1]
    log_debug(f"new_currency is {new_currency}")

    # Save to database
    repos = get_repos(context)
    await repos.users.update_currency(user_id, new_currency)

    await query.edit_message_text(texts.CURRENCY_REPLY.format(new_currency))

    # Send a new message with the main menu keyboard to continue interaction
    reply_markup = create_main_menu_keyboard(texts)
    await query.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    log_state_transition(TRANSACTION)
    return TRANSACTION


async def handle_settings_limit(update: Update, context: CallbackContext):
    """Handle spending limit change from settings menu."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    try:
        new_limit = float(update.message.text)

        # Save to database
        repos = get_repos(context)
        await repos.users.update_limit(user_id, Decimal(str(new_limit)))

        await update.message.reply_text(texts.LIMIT_SET)

        # Show main menu after setting the limit
        reply_markup = create_main_menu_keyboard(texts)
        await update.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except ValueError:
        await update.message.reply_text("Invalid limit. Please enter a number.")
        return SETTINGS_LIMIT

    log_state_transition(TRANSACTION)
    return TRANSACTION
