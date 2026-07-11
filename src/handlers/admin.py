"""
Admin and informational handlers.

Handles: help command, about/profile info, archive profile, usage charts.
"""

import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from src.language_util import check_language
from shared.di import get_repos
from src.commands import build_help_text
from src.config import ADMIN_USER_ID, LLM_ALLOWED_USERS, is_admin
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
    help_text = build_help_text(
        texts, is_admin=update.effective_user.id == ADMIN_USER_ID
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
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


def _format_expiry(expires_at) -> str:
    """Human string for an entitlement expiry (None = perpetual)."""
    if expires_at is None:
        return "perpetual"
    return f"until {expires_at.strftime('%Y-%m-%d %H:%M')} UTC"


async def grant_ai(update: Update, context: CallbackContext) -> int:
    """Admin-only: /grant_ai <user_id> [days] — grant AI access (T-022).

    Without days the grant is perpetual. With days, a repeat grant extends
    the current expiry (GREATEST semantics in EntitlementRepository.grant).
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is restricted to the bot owner.")
        return TRANSACTION

    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /grant_ai <user_id> [days]")
        return TRANSACTION
    target_id = int(args[0])

    duration_days = None
    if len(args) > 1:
        if not args[1].isdigit() or int(args[1]) <= 0:
            await update.message.reply_text("Days must be a positive integer. Usage: /grant_ai <user_id> [days]")
            return TRANSACTION
        duration_days = int(args[1])

    repos = get_repos(context)
    if not await repos.users.user_exists(target_id):
        await update.message.reply_text(
            f"User {target_id} is unknown — they must /start the bot first."
        )
        return TRANSACTION

    entitlement = await repos.entitlements.grant(
        target_id,
        granted_by=update.effective_user.id,
        source="admin",
        duration_days=duration_days,
    )
    await update.message.reply_text(
        f"AI access granted to {target_id}: {_format_expiry(entitlement.expires_at)}."
    )
    return TRANSACTION


async def revoke_ai(update: Update, context: CallbackContext) -> int:
    """Admin-only: /revoke_ai <user_id> — revoke AI access (T-022)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is restricted to the bot owner.")
        return TRANSACTION

    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /revoke_ai <user_id>")
        return TRANSACTION
    target_id = int(args[0])

    repos = get_repos(context)
    if await repos.entitlements.revoke(target_id, revoked_by=update.effective_user.id):
        await update.message.reply_text(f"AI access revoked for {target_id}.")
    else:
        await update.message.reply_text(f"User {target_id} has no active AI entitlement.")
    return TRANSACTION


async def list_ai(update: Update, context: CallbackContext) -> int:
    """Admin-only: /list_ai — list active AI entitlements (T-022)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is restricted to the bot owner.")
        return TRANSACTION

    repos = get_repos(context)
    entitlements = await repos.entitlements.list_active()

    lines = [f"Active AI entitlements: {len(entitlements)}"]
    for ent in entitlements:
        username = f" @{ent.telegram_username}" if ent.telegram_username else ""
        lines.append(
            f"{ent.user_id}{username} — {ent.source}, {_format_expiry(ent.expires_at)}"
        )
    if LLM_ALLOWED_USERS:
        env_ids = ", ".join(str(uid) for uid in sorted(LLM_ALLOWED_USERS))
        lines.append(f"Env allowlist (LLM_ALLOWED_USERS, legacy): {env_ids}")

    await update.message.reply_text("\n".join(lines))
    return TRANSACTION


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
            await asyncio.to_thread(generate_usage_summary_chart),
            await asyncio.to_thread(generate_usage_summary_chart, days=365, label="1y"),
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
