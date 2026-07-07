"""
Detailed transactions view - browse and filter transactions by category and period.
Converted to use batch fetch + memory filter architecture (Phase 3.1).
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
import asyncio

# Domain layer - batch fetch + filter in memory
from domain.session_loader import load_user_session
from domain.filters import (
    filter_by_period,
    filter_by_categories,
    filter_by_type,
    sort_by_date,
    get_unique_categories,
    calculate_summary,
    format_period_text,
    create_tx_display_mapping,
)

# Bot components
from keyboards import (
    create_category_selection_keyboard,
    create_time_period_keyboard,
    create_detailed_transactions_keyboard,
    create_main_menu_keyboard,
    create_show_transactions_keyboard
)
from language_util import check_language
from src.handlers.transactions import handle_transaction_selection
from shared.di import get_repos

# Import states from central file
from src.states import *


async def start_detailed_transactions(update: Update, context: CallbackContext):
    """Start the detailed transactions flow by showing category selection"""
    print(f"DEBUG: Fn start_detailed_transactions")
    user_id = update.effective_user.id  # int, not str
    texts = check_language(update, context)
    query = update.callback_query

    # Load user session with transactions (batch fetch)
    repos = get_repos(context)
    session = await load_user_session(user_id, repos, transactions_months=12)

    # Store session in context for reuse
    context.user_data['user_session'] = session

    # Get unique categories from transactions (pure Python)
    spending_tx = filter_by_type(session.transactions, 'spending')
    categories = get_unique_categories(spending_tx)

    if not categories:
        await query.edit_message_text(texts.NO_CATEGORIES_FOUND)
        return await back_to_transactions_menu(update, context)

    # Initialize context data
    context.user_data['selected_categories'] = []
    context.user_data['category_page'] = 0
    context.user_data['all_categories'] = categories

    # Create keyboard with categories
    reply_markup = create_category_selection_keyboard(
        categories,
        context.user_data['selected_categories'],
        texts,
        context.user_data['category_page']
    )

    await query.edit_message_text(
        texts.SELECT_CATEGORIES_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    print(f"DEBUG: Returning state SELECT_CATEGORIES after start_detailed_transactions")
    return SELECT_CATEGORIES


async def handle_category_selection(update: Update, context: CallbackContext):
    """Handle selection of categories"""
    texts = check_language(update, context)
    query = update.callback_query
    action = query.data

    # Navigate pages
    if action == "selcatpage_prev":
        context.user_data['category_page'] = max(0, context.user_data['category_page'] - 1)
        reply_markup = create_category_selection_keyboard(
            context.user_data['all_categories'],
            context.user_data['selected_categories'],
            texts,
            context.user_data['category_page']
        )
        await query.edit_message_text(
            texts.SELECT_CATEGORIES_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print(f"DEBUG: Returning state SELECT_CATEGORIES after handle_category_selection")
        return SELECT_CATEGORIES

    elif action == "selcatpage_next":
        context.user_data['category_page'] += 1
        reply_markup = create_category_selection_keyboard(
            context.user_data['all_categories'],
            context.user_data['selected_categories'],
            texts,
            context.user_data['category_page']
        )
        await query.edit_message_text(
            texts.SELECT_CATEGORIES_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print(f"DEBUG: Returning state SELECT_CATEGORIES after handle_category_selection")
        return SELECT_CATEGORIES

    # Select all categories
    elif action == "selcat_all":
        context.user_data['selected_categories'] = context.user_data['all_categories'].copy()
        reply_markup = create_category_selection_keyboard(
            context.user_data['all_categories'],
            context.user_data['selected_categories'],
            texts,
            context.user_data['category_page']
        )
        await query.edit_message_text(
            texts.SELECT_CATEGORIES_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print(f"DEBUG: Returning state SELECT_CATEGORIES after selcat_all")
        return SELECT_CATEGORIES

    # Continue to time period selection
    elif action == "selcat_continue" or action == "back_to_time_period":
        if not context.user_data['selected_categories']:
            # If no categories selected, select all
            context.user_data['selected_categories'] = context.user_data['all_categories'].copy()

        # Show time period selection keyboard
        reply_markup = create_time_period_keyboard(texts)
        await query.edit_message_text(
            texts.SELECT_TIME_PERIOD_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print(f"DEBUG: Returning state SELECT_TIME_PERIOD after selcat_continue")
        return SELECT_TIME_PERIOD

    # Go back to transactions menu
    elif action == "back_to_transactions":
        print(f"DEBUG: Returning state SELECT_CATEGORIES after back_to_transactions")
        return await back_to_transactions_menu(update, context)

    # Select individual category
    elif action.startswith("selcat_"):
        # Extract category name from callback data
        category = action[7:]  # Remove "selcat_" prefix

        # Toggle selection
        if category in context.user_data['selected_categories']:
            context.user_data['selected_categories'].remove(category)
        else:
            context.user_data['selected_categories'].append(category)

        reply_markup = create_category_selection_keyboard(
            context.user_data['all_categories'],
            context.user_data['selected_categories'],
            texts,
            context.user_data['category_page']
        )
        await query.edit_message_text(
            texts.SELECT_CATEGORIES_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return SELECT_CATEGORIES

    # Handle unexpected action
    await query.answer("Unexpected option")
    print(f"DEBUG: Returning state SELECT_CATEGORIES after handle_category_selection")
    return SELECT_CATEGORIES


async def handle_time_period_selection(update: Update, context: CallbackContext):
    """Handle selection of time period"""
    print(f"DEBUG: Fn handle_time_period_selection")
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    action = query.data

    if action == "back_to_categories":
        # Go back to category selection
        reply_markup = create_category_selection_keyboard(
            context.user_data['all_categories'],
            context.user_data['selected_categories'],
            texts,
            context.user_data['category_page']
        )
        await query.edit_message_text(
            texts.SELECT_CATEGORIES_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return SELECT_CATEGORIES

    elif action.startswith("period_") or context.user_data.get('selected_period'):
        # Extract period from callback data
        try:
            period = context.user_data['selected_period']
        except Exception:
            period = action[7:]  # Remove "period_" prefix
            context.user_data['selected_period'] = period

        # Get session from context (loaded in start_detailed_transactions)
        session = context.user_data.get('user_session')
        if not session:
            # Reload if needed
            repos = get_repos(context)
            session = await load_user_session(user_id, repos, transactions_months=12)
            context.user_data['user_session'] = session

        # Filter transactions using pure Python (no SQL)
        filtered_tx = filter_by_type(session.transactions, 'spending')
        filtered_tx = filter_by_period(filtered_tx, period)
        filtered_tx = filter_by_categories(filtered_tx, context.user_data['selected_categories'])
        filtered_tx = sort_by_date(filtered_tx, descending=True)

        # Calculate summary using pure Python
        summary = calculate_summary(
            filtered_tx,
            context.user_data['selected_categories'],
            session.currency
        )

        # Format the summary message
        period_text = format_period_text(period)
        message = texts.DETAILED_SUMMARY_TEMPLATE.format(
            period=period_text,
            total=summary['total'],
            currency=summary['currency'],
            transaction_count=summary['transaction_count']
        )

        # Add category sums to the message
        message += "\n\n<b>Category Totals:</b>\n"
        for category, amount in summary['category_sums'].items():
            message += f"{category}: {amount} {summary['currency']}\n"

        # Add subcategory details to the message
        message += "\n\n<b>Top Subcategories:</b>\n"
        for category, subcats in summary['subcategory_data'].items():
            if subcats:  # Only add if there are subcategories
                message += f"\n<b>{category}:</b>\n"
                for subcat, amount in subcats.items():
                    message += f"  {subcat}: {amount} {summary['currency']}\n"

        # Store filtered Transaction objects (not strings) for display
        context.user_data['filtered_transactions'] = filtered_tx

        # Add buttons to show transactions or go back to main menu
        keyboard = [
            [InlineKeyboardButton(texts.VIEW_TRANSACTIONS_BUTTON, callback_data="view_transactions")],
            [InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_time_period")],
            [InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print("Message edited, SHOW_SUMMARY returned", SHOW_SUMMARY)
        return SHOW_SUMMARY

    # Handle unexpected action
    await query.answer("Unexpected option")
    return SELECT_TIME_PERIOD


async def handle_summary_action(update: Update, context: CallbackContext):
    """Handle actions from the summary screen"""
    texts = check_language(update, context)
    query = update.callback_query
    action = query.data

    if action == "view_transactions":
        # Initialize transaction page
        context.user_data['tx_page'] = 0
        context.user_data['filtered_tx'] = 1
        # Show transactions
        return await show_filtered_transactions(update, context)

    elif action == "back_to_time_period":
        # Clear the selected period when going back
        if 'selected_period' in context.user_data:
            del context.user_data['selected_period']
        return await handle_category_selection(update, context)

    elif action == "back_to_main_menu":
        # Return to main menu
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION

    # Handle unexpected action
    await query.answer("Unexpected option")
    return SHOW_SUMMARY


async def show_filtered_transactions(update: Update, context: CallbackContext):
    """Show transactions filtered by selected categories and period"""
    print(f"DEBUG: Fn show_filtered_transactions")
    texts = check_language(update, context)
    query = update.callback_query

    # Get filtered Transaction objects (not strings)
    transactions = context.user_data.get('filtered_transactions', [])

    if not transactions:
        await query.edit_message_text(
            texts.NO_TRANSACTIONS_FOUND,
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(2)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION

    # Calculate pagination
    page = context.user_data.get('tx_page', 0)
    page_size = 15
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(transactions))

    # Create mapping from display number to transaction ID
    tx_mapping = create_tx_display_mapping(transactions, page, page_size)
    context.user_data['tx_display_mapping'] = tx_mapping
    print(f"DEBUG: Created tx_display_mapping: {tx_mapping}")

    # Format transactions for display
    transaction_lines = []
    for i, tx in enumerate(transactions[start_idx:end_idx], start=1):
        line = f"{i}. {tx.date_str} - {tx.category}: {tx.subcategory} {tx.amount} {tx.currency}"
        transaction_lines.append(line)

    # Store total count for pagination
    context.user_data['total_tx_count'] = len(transactions)

    # Create the message
    period_text = format_period_text(context.user_data['selected_period'])
    categories_text = ", ".join(context.user_data['selected_categories'])

    transactions_text = "\n".join(transaction_lines)
    message = texts.FILTERED_TRANSACTIONS_TEXT.format(
        period=period_text,
        categories=categories_text
    )
    message += f"\n\n{transactions_text}\n\n{texts.SELECT_TRANSACTION_TO_EDIT}"

    # Create keyboard - convert Transaction objects to display strings for keyboard
    tx_display_strings = [tx.to_display_string() for tx in transactions[start_idx:end_idx]]
    reply_markup = create_detailed_transactions_keyboard(
        tx_display_strings,
        context.user_data['selected_categories'],
        page,
        texts,
        total_count=len(transactions)
    )

    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    print(f"DEBUG: Returning state SHOW_TRANSACTIONS after show_filtered_transactions", SHOW_TRANSACTIONS)
    return SHOW_TRANSACTIONS


async def handle_transaction_navigation(update: Update, context: CallbackContext):
    """Handle transaction navigation (next/prev page) and transaction selection"""
    print(f"DEBUG: Fn handle_transaction_navigation with callback data")
    query = update.callback_query
    action = query.data

    if action == "dtx_prev_page":
        context.user_data['tx_page'] = max(0, context.user_data['tx_page'] - 1)
        return await show_filtered_transactions(update, context)

    elif action == "dtx_next_page":
        context.user_data['tx_page'] += 1
        return await show_filtered_transactions(update, context)

    elif action == "back_to_tx_list":
        return await handle_time_period_selection(update, context)

    elif action.startswith("dtx_display_"):
        # Extract the display number from the callback data
        display_num = int(action.replace("dtx_display_", ""))
        print(f"DEBUG: dtx_display_ handler with display_num={display_num}")

        # Use the mapping to get the actual transaction ID
        tx_mapping = context.user_data.get('tx_display_mapping', {})
        print(f"DEBUG: tx_mapping = {tx_mapping}")

        if display_num in tx_mapping:
            tx_id = tx_mapping[display_num]
            print(f"DEBUG: Found mapping for display {display_num} -> tx_id={tx_id}")

            # Store the transaction ID for handle_transaction_selection
            context.user_data['selected_tx_index'] = tx_id
            context.user_data['return_to_detailed'] = True

            print(f"DEBUG: Using stored tx_id={tx_id} for handle_transaction_selection")
            return await handle_transaction_selection(update, context)
        else:
            print(f"DEBUG: No mapping found for display_num={display_num}")
            await query.answer("Transaction not found. Please try again.")
            return SHOW_TRANSACTIONS

    elif action.startswith("tx_"):
        context.user_data['return_to_detailed'] = True
        print(f"DEBUG: action.startswith(tx_) after handle_transaction_selection")
        return await handle_transaction_selection(update, context)

    elif action == "back_to_main_menu":
        texts = check_language(update, context)
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION

    # Handle unexpected action
    await query.answer("Unexpected option")
    await asyncio.sleep(1)
    print(f"DEBUG: Returning state SHOW_TRANSACTIONS after handle_transaction_navigation", SHOW_TRANSACTIONS)
    return SHOW_TRANSACTIONS


async def back_to_transactions_menu(update: Update, context: CallbackContext):
    """Helper function to go back to transactions menu"""
    texts = check_language(update, context)
    query = update.callback_query

    reply_markup = create_show_transactions_keyboard(texts)
    await query.edit_message_text(
        texts.SHOW_TRANSACTIONS_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION
