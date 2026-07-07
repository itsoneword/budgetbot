"""
Onboarding handlers for new user registration flow.

Handles: start, language selection, currency selection, spending limit setup.
"""

from decimal import Decimal

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from language_util import check_language
from shared.di import get_repos
from src.logger import log_function_call, log_state_transition, log_user_interaction
from keyboards import (
    create_language_keyboard,
    create_skip_keyboard,
    create_settings_currency_keyboard,
)
from src.states import LANGUAGE, CURRENCY, LIMIT, TRANSACTION


async def start(update: Update, context: CallbackContext):
    """Initial bot command - creates user and starts onboarding flow."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Create or update user in database
    repos = get_repos(context)
    await repos.users.create_user(
        user_id,
        username=update.effective_user.first_name,
        telegram_username=update.effective_user.username,
    )

    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )

    reply_markup = create_language_keyboard()

    await update.message.reply_text(texts.SELECT_LANGUAGE, reply_markup=reply_markup)

    log_state_transition(LANGUAGE)
    return LANGUAGE


async def save_language(update: Update, context: CallbackContext):
    """Save user's language selection and proceed to currency selection."""
    log_function_call()
    query = update.callback_query
    user_language = query.data
    user_id = update.effective_user.id
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )

    # Save language to database
    repos = get_repos(context)
    await repos.users.get_or_create_config(user_id)  # Ensure config exists
    await repos.users.update_language(user_id, user_language)

    # Update language cache
    context.user_data['cached_language'] = user_language

    texts = check_language(update, context)

    reply_markup = create_settings_currency_keyboard()

    await query.edit_message_text(texts.LANGUAGE_REPLY.format(user_language))
    await update.effective_message.reply_text(
        texts.CHOOSE_CURRENCY_TEXT, reply_markup=reply_markup
    )

    log_state_transition(CURRENCY)
    return CURRENCY


async def save_currency(update: Update, context: CallbackContext):
    """Save user's currency selection and proceed to limit setup."""
    log_function_call()
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )
    user_currency = query.data.split('_')[1]

    # Save currency to database
    repos = get_repos(context)
    await repos.users.update_currency(user_id, user_currency)

    reply_markup = create_skip_keyboard(texts)

    await query.edit_message_text(texts.CURRENCY_REPLY.format(user_currency))
    await update.effective_message.reply_text(
        texts.CHOOSE_LIMIT_TEXT, reply_markup=reply_markup
    )

    log_state_transition(LIMIT)
    return LIMIT


async def save_limit(update: Update, context: CallbackContext):
    """Save user's monthly spending limit."""
    log_function_call()
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )
    try:
        # Try to convert the entered data to a float
        limit = float(update.effective_message.text)
    except ValueError:
        # If the conversion fails, send an error message and skip the step
        await update.effective_message.reply_text(
            "Invalid limit. Please enter a number."
        )
        log_state_transition(LIMIT)
        return LIMIT

    # Save limit to database
    repos = get_repos(context)
    await repos.users.update_limit(user_id, Decimal(str(limit)))

    await update.effective_message.reply_text(texts.LIMIT_SET)
    await update.effective_message.reply_text(texts.TRANSACTION_START_TEXT, parse_mode=ParseMode.HTML)
    log_state_transition(TRANSACTION)
    return TRANSACTION


async def skip_limit(update: Update, context: CallbackContext):
    """Skip limit setup - sets a very high default limit."""
    log_function_call()
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )
    await context.bot.edit_message_reply_markup(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        reply_markup=None,
    )
    # Save "no limit" as very high value to PostgreSQL
    repos = get_repos(context)
    await repos.users.update_limit(user_id, Decimal('99999999'))

    await update.effective_message.reply_text(texts.NO_LIMIT)
    await update.effective_message.reply_text(texts.TRANSACTION_START_TEXT, parse_mode=ParseMode.HTML)
    log_state_transition(TRANSACTION)
    return TRANSACTION
