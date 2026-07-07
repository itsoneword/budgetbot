"""
Records handlers for displaying transaction summaries and income processing.

Handles: current month records, last month records, income entry.
"""

from datetime import datetime, timedelta

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from language_util import check_language, cache_user_language, get_cached_currency, ensure_user_config_cached
from shared.di import get_repos
from src.logger import log_debug, log_user_interaction
from domain.session_loader import load_user_session
from domain.filters import get_records_summary, get_last_month_summary, calculate_limit_usage
from src.save_transaction import process_income_input
from src.states import TRANSACTION, PROCESS_INCOME


async def show_records(update: Update, context: CallbackContext):
    """Show monthly spending/income summary (from PostgreSQL via domain layer)."""
    user_id = update.effective_user.id

    # Get repos and cache language from DB
    repos = get_repos(context)
    await cache_user_language(context, repos, user_id)

    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )

    command = update.effective_message.text.split()[0][1:]
    record_type, record_type2 = (
        (texts.INCOME_TYPE1, texts.INCOME_TYPE2)
        if "income" in command
        else (texts.SPENDINGS_TYPE1, texts.SPENDINGS_TYPE2)
    )

    # Determine transaction type
    transaction_type = 'income' if "income" in command else 'spending'

    # Load user session (batch fetch from DB)
    session = await load_user_session(user_id, repos, transactions_months=2)
    currency = session.currency

    # Get records summary using pure Python filters
    records = get_records_summary(session.transactions, transaction_type)
    if records is None:
        await update.message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return

    sum_per_cat = records['sum_per_cat']
    av_per_day = records['av_per_day']
    total_spendings = records['total']
    total_av_per_day = records['total_av_per_day']
    prediction = records['prediction']
    comparison = records['comparison']

    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in sum_per_cat.items()
    )

    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in av_per_day.items()
    )
    av_per_day_sum = round(sum(av_per_day.values()))

    output_text = texts.RECORDS_TEMPLATE.format(
        total=total_spendings,
        sum_per_cat=sum_per_cat_text,
        av_per_day_sum=av_per_day_sum,
        av_per_day=av_per_day_text,
        total_av_per_day=total_av_per_day,
        predicted_total=prediction,
        comparison=comparison,
        currency=currency,
        record_type=record_type,
        record_type2=record_type2,
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(output_text, parse_mode=ParseMode.HTML)

    # Calculate limit usage using pure Python (only for spendings)
    if transaction_type == 'spending' and session.monthly_limit:
        try:
            limit_data = calculate_limit_usage(
                session.transactions, session.monthly_limit
            )

            if limit_data['exceeded']:
                await update.message.reply_text(
                    texts.LIMIT_EXCEEDED.format(
                        percent_difference=limit_data['percent_difference'],
                        current_daily_average=limit_data['current_daily_average'],
                        daily_limit=limit_data['daily_limit'],
                        days_zero_spending=limit_data['days_zero_spending'],
                        new_daily_limit=limit_data['new_daily_limit'],
                        currency=currency,
                    ),
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            log_debug(f"Exception in show_records when calculating limit: {e}")
            pass
    return TRANSACTION


async def show_last_month_records(update: Update, context: CallbackContext):
    """Show last month's spending/income summary (from PostgreSQL)."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    # Ensure user config is cached (for get_cached_currency)
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, int(user_id))

    command = "show"  # Default to showing spendings for last month
    if hasattr(update.effective_message, 'text') and update.effective_message.text:
        command = update.effective_message.text.split()[0][1:]

    # Determine transaction type
    tx_type = 'income' if "income" in command else 'spending'
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
        await update.message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return

    sum_per_cat = records['sum_per_cat']
    av_per_day = records['av_per_day']
    total_spendings = records['total']
    total_av_per_day = records['total_av_per_day']
    prediction = records['prediction']
    comparison = records['comparison']

    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in sum_per_cat.items()
    )

    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in av_per_day.items()
    )
    av_per_day_sum = round(sum(av_per_day.values()))

    # Add last month name to the output
    output_text = f"<b>{last_month_name} {record_type}</b>\n\n"
    output_text += texts.RECORDS_TEMPLATE.format(
        total=total_spendings,
        sum_per_cat=sum_per_cat_text,
        av_per_day_sum=av_per_day_sum,
        av_per_day=av_per_day_text,
        total_av_per_day=total_av_per_day,
        predicted_total=prediction,
        comparison=comparison,
        currency=currency,
        record_type=record_type,
        record_type2=record_type2,
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(output_text, parse_mode=ParseMode.HTML)

    return TRANSACTION


async def start_income(update: Update, context: CallbackContext) -> None:
    """Start income entry flow."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    await update.effective_message.reply_text(
        texts.INCOME_HELP, parse_mode=ParseMode.HTML
    )
    return PROCESS_INCOME


async def process_income(update: Update, context: CallbackContext):
    """Process and save income entry."""
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Ensure user config is cached (for get_cached_currency)
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, int(user_id))

    income_info = update.effective_message.text  # Get the income info from the message
    currency = get_cached_currency(context)
    parts = income_info.lower().split()
    try:
        amount = float(parts[-1])
    except ValueError:
        await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        return PROCESS_INCOME

    timestamp, category = process_income_input(user_id, parts)

    # Save income to PostgreSQL
    await repos.transactions.save_income(
        user_id=int(user_id),
        category=category,
        subcategory="",  # Income doesn't use subcategory
        amount=amount,
        currency=currency,
        timestamp=timestamp,
    )

    await update.effective_message.reply_text(texts.TRANSACTION_SAVED_TEXT)
    return ConversationHandler.END
