"""
Admin and informational handlers.

Handles: help command, about/profile info, archive profile, usage charts.
"""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from src.language_util import check_language
from shared.di import get_repos
from src.config import ADMIN_USER_ID
from src.logger import log_user_interaction
from src.keyboards import create_settings_keyboard
from src.charts import generate_usage_summary_chart
from src.states import TRANSACTION, DELETE_PROFILE


async def help(update: Update, context: CallbackContext):
    """Display help text with available commands."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    await update.message.reply_text(texts.HELP_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION


async def about(update: Update, context: CallbackContext):
    """Display user profile information and settings."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Get user config from PostgreSQL
    repos = get_repos(context)
    config = await repos.users.get_config(user_id)
    name = config.name if config else update.effective_user.first_name
    currency = config.currency if config else 'EUR'
    language = config.language if config else 'en'
    limit = float(config.monthly_limit) if config else 99999999

    reply_markup = create_settings_keyboard(texts)

    await update.message.reply_text(
        texts.ABOUT.format(name, currency, language, limit),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION


async def archive_profile(update: Update, context: CallbackContext):
    """Handle profile deletion request with confirmation."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    # Check if this is a confirmation or initial request
    if update.message and (update.message.text == "Delete profile" or update.message.text == "Удалить профиль"):
        # User confirmed deletion
        # result = await archive_user_data(user_id)
        # await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        return ConversationHandler.END
    else:
        # Initial request - ask for confirmation
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.DELETE_PROFILE_CONFIRMATION,
            parse_mode=ParseMode.HTML
        )
        return DELETE_PROFILE


async def show_log_chart(update: Update, context: CallbackContext) -> int:
    """Admin-only: Display usage statistics charts."""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("This command is restricted to the bot owner.")
        return TRANSACTION

    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )

    try:
        chart_paths = [
            generate_usage_summary_chart(),
            generate_usage_summary_chart(days=365, label="1y"),
        ]
    except FileNotFoundError:
        await update.message.reply_text("Log file not found.")
        return TRANSACTION
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return TRANSACTION
    except Exception as exc:
        await update.message.reply_text(f"Failed to build usage chart: {exc}")
        return TRANSACTION

    captions = ["Usage summary (last 30 days)", "Usage summary (last year)"]
    for path, caption in zip(chart_paths, captions):
        with open(path, "rb") as chart_file:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=chart_file,
                caption=caption,
            )

    return TRANSACTION
