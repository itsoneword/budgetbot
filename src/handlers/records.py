"""
Records handlers for displaying transaction summaries and income processing.

Handles: current month records, last month records, income entry.
"""

from datetime import datetime, timedelta

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from src.language_util import check_language, cache_user_language, get_cached_currency, ensure_user_config_cached
from shared.di import get_repos
from src.logger import log_debug, log_user_interaction
from domain.session_loader import load_user_session
from domain.filters import get_records_summary, get_last_month_summary, calculate_limit_usage
from src.save_transaction import process_income_input
from src.states import TRANSACTION, PROCESS_INCOME


def _command_from_update(update: Update) -> str:
    """First word of the triggering command, '' when the update has no text
    (callback queries carry the edited message text, not a command)."""
    message = update.effective_message
    if message and message.text and message.text.startswith("/"):
        return message.text.split()[0][1:]
    return ""


def _format_records_text(records: dict, texts, currency: str,
                         record_type: str, record_type2: str) -> str:
    """Render a records summary dict into the RECORDS_TEMPLATE text."""
    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in records['sum_per_cat'].items()
    )
    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in records['av_per_day'].items()
    )
    av_per_day_sum = round(sum(records['av_per_day'].values()))

    return texts.RECORDS_TEMPLATE.format(
        total=records['total'],
        sum_per_cat=sum_per_cat_text,
        av_per_day_sum=av_per_day_sum,
        av_per_day=av_per_day_text,
        total_av_per_day=records['total_av_per_day'],
        predicted_total=records['prediction'],
        comparison=records['comparison'],
        currency=currency,
        record_type=record_type,
        record_type2=record_type2,
    )


async def build_records_report(update: Update, context: CallbackContext,
                               tx_type: str = None) -> str | None:
    """Build the current-month summary text (HTML), or None when no records.

    Shared by the /show command path (show_records sends it) and the menu
    path (menu_call edits the tapped message with it — T-044). The
    limit-exceeded warning is appended when applicable.
    """
    user_id = update.effective_user.id

    # Get repos and cache language from DB
    repos = get_repos(context)
    await cache_user_language(context, repos, user_id)

    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )

    transaction_type = tx_type or (
        'income' if "income" in _command_from_update(update) else 'spending'
    )
    record_type, record_type2 = (
        (texts.INCOME_TYPE1, texts.INCOME_TYPE2)
        if transaction_type == 'income'
        else (texts.SPENDINGS_TYPE1, texts.SPENDINGS_TYPE2)
    )

    # Load user session (batch fetch from DB)
    session = await load_user_session(user_id, repos, transactions_months=2)
    currency = session.currency

    # Get records summary using pure Python filters
    records = get_records_summary(session.transactions, transaction_type)
    if records is None:
        return None

    output_text = _format_records_text(
        records, texts, currency, record_type, record_type2
    )

    # Append limit usage (only for spendings, only when exceeded)
    if transaction_type == 'spending' and session.monthly_limit:
        try:
            limit_data = calculate_limit_usage(
                session.transactions, session.monthly_limit
            )

            if limit_data['exceeded']:
                output_text += "\n\n" + texts.LIMIT_EXCEEDED.format(
                    percent_difference=limit_data['percent_difference'],
                    current_daily_average=limit_data['current_daily_average'],
                    daily_limit=limit_data['daily_limit'],
                    days_zero_spending=limit_data['days_zero_spending'],
                    new_daily_limit=limit_data['new_daily_limit'],
                    currency=currency,
                )
        except Exception as e:
            log_debug(f"Exception in build_records_report when calculating limit: {e}")

    return output_text


async def show_records(update: Update, context: CallbackContext, tx_type: str = None):
    """Show monthly spending/income summary (from PostgreSQL via domain layer).

    tx_type: 'spending' | 'income'; derived from the command text when not
    given. Command path only — the menu edits the tapped message instead
    via build_records_report (T-044).
    """
    output_text = await build_records_report(update, context, tx_type)
    texts = check_language(update, context)
    if output_text is None:
        # effective_message: update.message is None for callback queries
        await update.effective_message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return TRANSACTION

    await update.effective_message.reply_text(output_text, parse_mode=ParseMode.HTML)
    return TRANSACTION


async def build_last_month_report(update: Update, context: CallbackContext,
                                  tx_type: str = None) -> str | None:
    """Build last month's summary text (HTML), or None when no records.

    Shared by the /show_last_month command path and the menu edit path (T-044).
    """
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    # Ensure user config is cached (for get_cached_currency)
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, int(user_id))

    if tx_type is None:
        tx_type = 'income' if "income" in _command_from_update(update) else 'spending'
    record_type, record_type2 = (
        (texts.INCOME_TYPE1, texts.INCOME_TYPE2)
        if tx_type == 'income'
        else (texts.SPENDINGS_TYPE1, texts.SPENDINGS_TYPE2)
    )

    # Get last month name for display
    current_date = datetime.now()
    last_month_date = current_date.replace(day=1) - timedelta(days=1)
    last_month_name = last_month_date.strftime("%B %Y")

    currency = get_cached_currency(context)

    # Load transactions from PostgreSQL (need enough months for last month + comparison)
    session = await load_user_session(
        int(user_id), repos,
        load_transactions=True,
        transactions_months=3,  # Current + last + previous for comparison
        transaction_type=tx_type
    )

    # Get last month summary
    records = get_last_month_summary(session.transactions, tx_type)
    if records is None:
        return None

    # Add last month name to the output
    return f"<b>{last_month_name} {record_type}</b>\n\n" + _format_records_text(
        records, texts, currency, record_type, record_type2
    )


async def show_last_month_records(update: Update, context: CallbackContext, tx_type: str = None):
    """Show last month's spending/income summary (from PostgreSQL)."""
    output_text = await build_last_month_report(update, context, tx_type)
    texts = check_language(update, context)
    if output_text is None:
        # effective_message: update.message is None for callback queries
        await update.effective_message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return TRANSACTION

    await update.effective_message.reply_text(output_text, parse_mode=ParseMode.HTML)
    return TRANSACTION


async def save_income_text(update: Update, context: CallbackContext, text: str) -> bool:
    """Parse and save one income entry ("[dd.mm] [category] amount").

    The single income write path — used by the /income conversation, /income
    inline args and the voice/free-text add_income intent (T-035). Replies
    with the specific error itself (invalid amount or invalid date, dv-5465);
    returns False when nothing was saved — callers control only conversation
    state. Replies with the saved confirmation on success.
    """
    user_id = update.effective_user.id
    texts = check_language(update, context)

    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, int(user_id))
    currency = get_cached_currency(context)

    parts = text.lower().split()
    try:
        amount = float(parts[-1])
    except (ValueError, IndexError):
        await update.effective_message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        return False

    try:
        timestamp, category = process_income_input(user_id, parts)
    except ValueError:
        # Date-shaped garbage ('99.99', '29.02' in a non-leap year) — explicit
        # error, nothing saved: silently treating it as a category would both
        # pollute the category set and drop the user's date intent (dv-5465).
        await update.effective_message.reply_text(
            texts.INCOME_INVALID_DATE.format(token=parts[0])
        )
        return False

    await repos.transactions.save_income(
        user_id=int(user_id),
        category=category,
        subcategory="",  # Income doesn't use subcategory
        amount=amount,
        currency=currency,
        timestamp=timestamp,
    )

    await update.effective_message.reply_text(
        texts.INCOME_SAVED.format(
            category=category,
            amount=amount,
            currency=currency,
            date=timestamp.strftime("%Y-%m-%d"),
        ),
        parse_mode=ParseMode.HTML,
    )
    return True


async def start_income(update: Update, context: CallbackContext):
    """/income entry: save inline args directly, else prompt for input."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)

    # "/income trading 300" — save immediately, no conversation (T-035).
    # On failure save_income_text already replied the specific error (dv-5465).
    if context.args:
        if await save_income_text(update, context, " ".join(context.args)):
            return ConversationHandler.END

    await update.effective_message.reply_text(
        texts.INCOME_HELP, parse_mode=ParseMode.HTML
    )
    return PROCESS_INCOME


async def process_income(update: Update, context: CallbackContext):
    """Process and save income entry (conversation step after /income)."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)

    if not await save_income_text(update, context, update.effective_message.text):
        # Error already replied inside save_income_text (dv-5465)
        return PROCESS_INCOME
    return ConversationHandler.END


async def process_income_menu(update: Update, context: CallbackContext):
    """PROCESS_INCOME step of the main-menu conversation (Add income button).

    Same write path as /income but returns to the menu instead of ending the
    conversation — ending would kill the menu's callback routing (T-035)."""
    from src.keyboards import create_main_menu_keyboard

    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)

    if not await save_income_text(update, context, update.effective_message.text):
        # Error already replied inside save_income_text (dv-5465)
        return PROCESS_INCOME

    # Typed-input flow: the anchor message is the income prompt far above, so
    # a fresh menu message is sent — but with the menu text, not a
    # "Returning to main menu." filler (T-044).
    await update.effective_message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=create_main_menu_keyboard(texts),
        parse_mode=ParseMode.HTML,
    )
    return TRANSACTION
