"""
Transaction editing and deletion handlers.
Uses PostgreSQL repositories for all data operations.
"""
import logging
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode

from src.language_util import check_language
from src.keyboards import (
    create_transaction_edit_keyboard,
    create_tx_del_confirmation_keyboard,
    create_numbered_transaction_keyboard,
    create_tx_categories_keyboard,
)
from src.states import *

# PostgreSQL imports
from shared.di import get_repos
from domain.session_loader import load_user_session
from domain.filters import filter_by_type, get_total
from domain.models.user_session import Transaction

import asyncio

logger = logging.getLogger(__name__)


async def show_recent_entries(update: Update, context: CallbackContext) -> int:
    """Show list of recent transactions with pagination."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)

    # Set default page to 0 if not set
    if 'tx_page' not in context.user_data:
        context.user_data['tx_page'] = 0

    page = context.user_data['tx_page']
    transactions_per_page = 15
    records_to_fetch = 30  # Fetch 30 records for 2 pages

    # Load recent transactions from PostgreSQL
    session = await load_user_session(
        user_id, repos,
        load_transactions=True,
        transactions_months=12  # Last year of transactions
    )

    # Get spending transactions and sort by timestamp (newest first)
    spending = filter_by_type(session.transactions, 'spending')
    spending = sorted(spending, key=lambda x: x.timestamp, reverse=True)
    transactions = spending[:records_to_fetch]

    if not transactions:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                texts.NO_RECORDS,
                parse_mode=ParseMode.HTML
            )
        else:
            await update.effective_message.reply_text(
                texts.NO_RECORDS,
                parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END

    # Calculate total amount for display
    total_amount = get_total(transactions)

    # Limit page number to available pages
    max_page = (len(transactions) - 1) // transactions_per_page
    if page > max_page:
        context.user_data['tx_page'] = max_page
        page = max_page

    # Paginate transactions
    start_idx = page * transactions_per_page
    end_idx = min(start_idx + transactions_per_page, len(transactions))
    display_transactions = transactions[start_idx:end_idx]

    # Store transactions in context for selection
    context.user_data['recent_transactions'] = transactions

    # Format transactions as text
    transaction_lines = []
    for i, tx in enumerate(display_transactions):
        line = f"{i+1}. {tx.date_str} - {tx.category}: {tx.subcategory} {tx.amount} {tx.currency}"
        transaction_lines.append(line)

    transactions_text = "\n".join(transaction_lines)

    # Format full message
    currency = session.config.currency
    message_text = texts.EDIT_TRANSACTIONS_PROMPT.format(total_amount, currency)
    message_text += f"\n\n{transactions_text}\n\n{texts.SELECT_TRANSACTION_TO_EDIT}"

    # Create keyboard with numbered buttons - pass display strings for compatibility
    tx_display_strings = [tx.to_display_string() for tx in display_transactions]
    reply_markup = create_numbered_transaction_keyboard(
        tx_display_strings,
        page,
        len(transactions),
        texts,
        items_per_page=transactions_per_page
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.effective_message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    return TRANSACTION_LIST


async def handle_transaction_selection(update: Update, context: CallbackContext) -> int:
    """Handle selection of a transaction to edit."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "tx_next_page":
        context.user_data['tx_page'] += 1
        return await show_recent_entries(update, context)

    elif callback_data == "tx_prev_page":
        context.user_data['tx_page'] = max(0, context.user_data['tx_page'] - 1)
        return await show_recent_entries(update, context)

    elif callback_data == "back_to_main_menu":
        from src.handlers.menu import menu
        return await menu(update, context)

    # Check if we have a stored transaction index from detailed transactions view
    if context.user_data.get('selected_tx_index'):
        tx_id = int(context.user_data['selected_tx_index'])
        del context.user_data['selected_tx_index']
    else:
        # Extract transaction ID from callback data (tx_INDEX)
        tx_id = int(callback_data.replace("tx_", ""))

    # Get the transaction from PostgreSQL
    try:
        repo_transaction = await repos.transactions.get_by_id(tx_id, user_id)

        if not repo_transaction:
            # Try to find in cached transactions if ID lookup fails
            recent_txs = context.user_data.get('recent_transactions', [])
            filtered_txs = context.user_data.get('filtered_transactions', [])

            # Search in recent or filtered transactions
            all_cached = recent_txs + filtered_txs
            matching = [tx for tx in all_cached if tx.id == tx_id]

            if matching:
                tx = matching[0]
                transaction = {
                    'id': tx.id,
                    'timestamp': tx.iso_timestamp,
                    'category': tx.category,
                    'subcategory': tx.subcategory,
                    'amount': float(tx.amount),
                    'currency': tx.currency
                }
            else:
                raise ValueError(f"Transaction not found with ID: {tx_id}")
        else:
            # Convert repository transaction to display dict
            transaction = {
                'id': repo_transaction.id,
                'timestamp': repo_transaction.timestamp.strftime('%Y-%m-%dT%H:%M:%S'),
                'category': repo_transaction.category_name,
                'subcategory': repo_transaction.subcategory_name,
                'amount': float(repo_transaction.amount),
                'currency': repo_transaction.currency
            }

        # Store in context
        context.user_data['current_transaction'] = transaction
        context.user_data['current_tx_id'] = transaction['id']

    except Exception as e:
        logger.exception("Error selecting transaction")
        await query.edit_message_text(
            texts.ERROR_SELECTING_TRANSACTION,
            parse_mode=ParseMode.HTML
        )
        return await show_recent_entries(update, context)

    # Create keyboard with edit options
    reply_markup = create_transaction_edit_keyboard(transaction, texts)

    # Format transaction details
    message_text = texts.TRANSACTION_DETAILS.format(
        timestamp=transaction['timestamp'],
        category=transaction['category'],
        subcategory=transaction['subcategory'],
        amount=transaction['amount'],
        currency=transaction['currency']
    )

    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION_EDIT


async def handle_edit_option(update: Update, context: CallbackContext) -> int:
    """Handle selection of what to edit in the transaction."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    try:
        filtered_tx = context.user_data['filtered_tx']
    except Exception:
        filtered_tx = 0

    if callback_data == "back_to_transactions" and filtered_tx == 1:
        from src.detailed_transactions import show_filtered_transactions
        return await show_filtered_transactions(update, context)
    elif callback_data == "back_to_transactions":
        return await show_recent_entries(update, context)
    elif callback_data == "edit_date":
        await query.edit_message_text(
            texts.ENTER_NEW_DATE_PROMPT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_DATE

    elif callback_data == "edit_category":
        # Get categories from PostgreSQL
        session = await load_user_session(user_id, repos, load_transactions=False)
        categories = list(session.categories.keys())
        context.user_data["categories"] = categories

        reply_markup = create_tx_categories_keyboard(categories, texts)

        await query.edit_message_text(
            texts.SELECT_NEW_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return EDIT_CATEGORY

    elif callback_data == "edit_subcategory":
        await query.edit_message_text(
            texts.ENTER_NEW_SUBCATEGORY,
            parse_mode=ParseMode.HTML
        )
        return EDIT_SUBCATEGORY

    elif callback_data == "edit_amount":
        await query.edit_message_text(
            texts.ENTER_NEW_AMOUNT_PROMPT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_AMOUNT

    elif callback_data == "delete_transaction":
        reply_markup = create_tx_del_confirmation_keyboard(texts)

        message_text = texts.CONFIRM_DELETE_TRANSACTION.format(
            timestamp=context.user_data['current_transaction']['timestamp'],
            category=context.user_data['current_transaction']['category'],
            subcategory=context.user_data['current_transaction']['subcategory'],
            amount=context.user_data['current_transaction']['amount'],
            currency=context.user_data['current_transaction']['currency']
        )

        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return CONFIRM_DELETE

    return TRANSACTION_EDIT


async def handle_edit_date(update: Update, context: CallbackContext) -> int:
    """Handle input of new date for the transaction."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)

    date_text = update.message.text.strip()

    try:
        if '.' in date_text:
            parts = date_text.split('.')
            if len(parts) == 2:
                day, month = map(int, parts)
                year = datetime.now().year
            else:
                day, month, year = map(int, parts)

            new_date = datetime(year, month, day, tzinfo=timezone.utc)
        else:
            raise ValueError("Invalid date format")

        # Get the old timestamp to preserve time part
        old_timestamp_str = context.user_data['current_transaction']['timestamp']
        old_timestamp = datetime.fromisoformat(old_timestamp_str.replace('Z', '+00:00'))

        # Create new timestamp preserving the time part
        new_timestamp = datetime.combine(
            new_date.date(),
            old_timestamp.time(),
            tzinfo=timezone.utc
        )

        # Update transaction in PostgreSQL
        tx_id = context.user_data['current_tx_id']
        success = await repos.transactions.update(
            tx_id, user_id,
            timestamp=new_timestamp
        )

        if success:
            await update.message.reply_text(
                texts.DATE_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )

            if context.user_data.get('return_to_detailed', False):
                from src.detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0
                return await show_filtered_transactions(update, context)
            else:
                context.user_data['tx_page'] = 0
                return await show_recent_entries(update, context)
        else:
            await update.message.reply_text(
                texts.ERROR_UPDATING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
            return EDIT_DATE

    except ValueError:
        await update.message.reply_text(
            texts.INVALID_DATE_FORMAT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_DATE


async def handle_edit_category(update: Update, context: CallbackContext) -> int:
    """Handle selection of a new category."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data.startswith("txpage_"):
        direction = callback_data.replace("txpage_", "")
        current_page = context.user_data.get('category_page', 0)

        if direction == "prev":
            context.user_data['category_page'] = max(0, current_page - 1)
        else:
            context.user_data['category_page'] = current_page + 1

        categories = context.user_data.get("categories", [])
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data['category_page'])

        await query.edit_message_text(
            texts.SELECT_NEW_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return EDIT_CATEGORY

    elif callback_data == "cancel_transaction":
        return await show_recent_entries(update, context)

    elif callback_data.startswith("txcat_"):
        category = callback_data.replace("txcat_", "")

        # Update transaction in PostgreSQL (use category_name for DB)
        tx_id = context.user_data['current_tx_id']
        success = await repos.transactions.update(
            tx_id, user_id,
            category_name=category
        )

        if success:
            await query.edit_message_text(
                texts.CATEGORY_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )

            if context.user_data.get('return_to_detailed', False):
                from src.detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0
                return await show_filtered_transactions(update, context)
            else:
                context.user_data['tx_page'] = 0
                return await show_recent_entries(update, context)
        else:
            await query.edit_message_text(
                texts.ERROR_UPDATING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
            return EDIT_CATEGORY

    return EDIT_CATEGORY


async def handle_edit_subcategory(update: Update, context: CallbackContext) -> int:
    """Handle editing a subcategory."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)

    # Check if this is a callback query (back button or cancel)
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "back_to_categories":
            session = await load_user_session(user_id, repos, load_transactions=False)
            categories = list(session.categories.keys())
            context.user_data["categories"] = categories

            reply_markup = create_tx_categories_keyboard(categories, texts)

            await query.edit_message_text(
                texts.SELECT_NEW_CATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return EDIT_CATEGORY

        elif callback_data == "cancel_transaction":
            return await show_recent_entries(update, context)

    # Handle text input for new subcategory name
    new_subcategory = update.message.text.strip().lower()

    # Update transaction in PostgreSQL
    tx_id = context.user_data['current_tx_id']
    success = await repos.transactions.update(
        tx_id, user_id,
        subcategory_name=new_subcategory
    )

    if success:
        await update.message.reply_text(
            texts.SUBCATEGORY_UPDATED_SUCCESS,
            parse_mode=ParseMode.HTML
        )

        if context.user_data.get('return_to_detailed', False):
            from src.detailed_transactions import show_filtered_transactions
            context.user_data['tx_page'] = 0
            return await show_filtered_transactions(update, context)
        else:
            context.user_data['tx_page'] = 0
            return await show_recent_entries(update, context)
    else:
        await update.message.reply_text(
            texts.ERROR_UPDATING_TRANSACTION,
            parse_mode=ParseMode.HTML
        )
        return EDIT_SUBCATEGORY


async def handle_edit_amount(update: Update, context: CallbackContext) -> int:
    """Handle input of new amount for the transaction."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)

    amount_text = update.message.text.strip()

    try:
        new_amount = Decimal(amount_text.replace(',', '.'))

        # Update transaction in PostgreSQL
        tx_id = context.user_data['current_tx_id']
        success = await repos.transactions.update(
            tx_id, user_id,
            amount=new_amount
        )

        if success:
            await update.message.reply_text(
                texts.AMOUNT_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )

            if context.user_data.get('return_to_detailed', False):
                from src.detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0
                return await show_filtered_transactions(update, context)
            else:
                context.user_data['tx_page'] = 0
                return await show_recent_entries(update, context)
        else:
            await update.message.reply_text(
                texts.ERROR_UPDATING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
            return EDIT_AMOUNT

    except (ValueError, InvalidOperation):
        await update.message.reply_text(
            texts.INVALID_AMOUNT_FORMAT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_AMOUNT


async def handle_delete_tx_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of transaction deletion."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "confirm":
        try:
            tx_id = context.user_data.get('current_tx_id')
            if not tx_id:
                raise ValueError("Transaction ID not found in context")

            # Delete from PostgreSQL
            success = await repos.transactions.delete(tx_id, user_id)

            if success:
                await query.edit_message_text(
                    texts.TRANSACTION_DELETED_SUCCESS,
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(1)
            else:
                await query.edit_message_text(
                    texts.ERROR_DELETING_TRANSACTION,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.exception("Error deleting transaction")
            await query.edit_message_text(
                texts.ERROR_DELETING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
    else:  # callback_data == "cancel"
        await query.edit_message_text(
            texts.DELETE_CANCELLED,
            parse_mode=ParseMode.HTML
        )

    # Return to appropriate view
    if context.user_data.get('return_to_detailed', False):
        from src.detailed_transactions import show_filtered_transactions
        return await show_filtered_transactions(update, context)
    else:
        context.user_data['tx_page'] = 0
        return await show_recent_entries(update, context)
