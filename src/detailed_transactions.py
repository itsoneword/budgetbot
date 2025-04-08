from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from show_transactions import (
    get_all_user_categories,
    get_transactions_by_categories,
    calculate_category_summary,
    format_period_text
)
import asyncio
from keyboards import (
    create_category_selection_keyboard,
    create_time_period_keyboard,
    create_detailed_transactions_keyboard,
    create_main_menu_keyboard,
    create_show_transactions_keyboard
)
from language_util import check_language
from change_transactions import handle_transaction_selection
from file_ops import ensure_transaction_ids
# Import states from central file
from src.states import *

async def start_detailed_transactions(update: Update, context: CallbackContext):
    """Start the detailed transactions flow by showing category selection"""
    print(f"DEBUG: Fn start_detailed_transactions")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    
    # Ensure all transactions have IDs
    ensure_transaction_ids(user_id)
    
    # Get all categories from user's spending file
    categories = get_all_user_categories(user_id)
    
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
    print(f"DEBUG: Fn handle_category_selection")
    user_id = str(update.effective_user.id)
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
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    action = query.data
    
    if action == "back_to_categories": #should be back to timeperiod selectoin
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
        print(f"DEBUG: Returning state SHOW_SUMMARY after handle_time_period_selection")
        # Extract period from callback data
        try:
            period = context.user_data['selected_period']
            print(f"DEBUG: period from context.user_data['selected_period'] = {period}")
        except Exception as e:
            print(f"DEBUG: Exception inside handle_time_period_selection", {e})
            period = action[7:]  # Remove "period_" prefix
            context.user_data['selected_period'] = period
        
        # Calculate summary for selected categories and period
        summary = calculate_category_summary(
            user_id, 
            context.user_data['selected_categories'], 
            period
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
        
        # Show the summary and offer to view transactions
        context.user_data['transactions'] = get_transactions_by_categories(
            user_id, 
            context.user_data['selected_categories'], 
            period
        )
        # Add buttons to show transactions or go back to main menu
        keyboard = [
            [InlineKeyboardButton(texts.VIEW_TRANSACTIONS_BUTTON, callback_data="view_transactions")],
            [InlineKeyboardButton(texts.RETURN_BACK_BUTTON, callback_data="back_to_time_period")],
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

    user_id = str(update.effective_user.id)
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
        # Return to timeperiod selection    # Clear the selected period when going back to category selection
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
        return TRANSACTION  # TRANSACTION state from core.py
    
    # Handle unexpected action
    await query.answer("Unexpected option")
    return SHOW_SUMMARY

async def show_filtered_transactions(update: Update, context: CallbackContext):
    """Show transactions filtered by selected categories and period"""
    print(f"DEBUG: Fn show_filtered_transactions")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    
    transactions = context.user_data.get('transactions', [])
    
    if not transactions:
        await query.edit_message_text(
            texts.NO_TRANSACTIONS_FOUND,
            parse_mode=ParseMode.HTML
        )
        # Go back to main menu
        await asyncio.sleep(2)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION  # TRANSACTION state from core.py
    
    # We no longer need to reverse transactions here as they're already sorted
    # in get_transactions_by_categories function
    
    # Calculate pagination for displaying 15 transactions at a time
    page = context.user_data.get('tx_page', 0)
    start_idx = page * 15
    end_idx = min(start_idx + 15, len(transactions))
    
    # Create a mapping of display numbers to transaction IDs
    tx_mapping = {}
    
    # Format transactions as text
    transaction_lines = []
    for i in range(start_idx, end_idx):
        tx = transactions[i]
        # Parse the transaction string format: "id: timestamp, category, subcategory, amount, currency"
        parts = tx.split(', ')
        
        # Extract the transaction details
        id_timestamp_part = parts[0]
        id_part = id_timestamp_part.split(': ')[0]
        timestamp_part = id_timestamp_part.split(': ')[1]
        category = parts[1]
        subcategory = parts[2]
        amount = parts[3]
        currency = parts[4] if len(parts) > 4 else ""
        
        # Store the mapping of display number to actual transaction ID
        display_num = i - start_idx + 1
        tx_mapping[display_num] = id_part
        
        # Format the date for display (DD.MM.YYYY)
        date_str = ""
        if "T" in timestamp_part:
            date_only = timestamp_part.split('T')[0]
            try:
                year, month, day = date_only.split('-')
                date_str = f"{day}.{month}.{year}"
            except:
                date_str = timestamp_part
        else:
            date_str = timestamp_part
        
        # Create the formatted transaction line with display number
        line = f"{display_num}. {date_str} - {category}: {subcategory} {amount} {currency}"
        transaction_lines.append(line)
    
    # Store the mapping in context
    context.user_data['tx_display_mapping'] = tx_mapping
    print(f"DEBUG: Created tx_display_mapping: {tx_mapping}")
    # Store total count for pagination
    context.user_data['total_tx_count'] = len(transactions)
    
    # Create the message with transactions list
    period_text = format_period_text(context.user_data['selected_period'])
    categories_text = ", ".join(context.user_data['selected_categories'])
    
    transactions_text = "\n".join(transaction_lines)
    message = texts.FILTERED_TRANSACTIONS_TEXT.format(
        period=period_text,
        categories=categories_text
    )
    message += f"\n\n{transactions_text}\n\n{texts.SELECT_TRANSACTION_TO_EDIT}"
    
    # Create keyboard with transaction selection numbers
    reply_markup = create_detailed_transactions_keyboard(
        transactions[start_idx:end_idx],
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
    #print(f"DEBUG: query.data = {query.data}")
    action = query.data
    
    if action == "dtx_prev_page":
        # Go to previous page
        context.user_data['tx_page'] = max(0, context.user_data['tx_page'] - 1)
        return await show_filtered_transactions(update, context)
    
    elif action == "dtx_next_page":
        # Go to next page
        context.user_data['tx_page'] += 1
        return await show_filtered_transactions(update, context)
    
    # return to time period selection
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
            # Get the actual transaction ID
            tx_id = tx_mapping[display_num]
            print(f"DEBUG: Found mapping for display {display_num} -> tx_id={tx_id}")
            
            # Store the transaction ID in user_data for handle_transaction_selection
            context.user_data['selected_tx_index'] = tx_id
            
            # Set flag to return to detailed view after edits
            context.user_data['return_to_detailed'] = True
            
            print(f"DEBUG: Using stored tx_id={tx_id} for handle_transaction_selection")
            
            # Call handle_transaction_selection with the ID
            return await handle_transaction_selection(update, context)
        else:
            # Error handling if mapping not found
            print(f"DEBUG: No mapping found for display_num={display_num}")
            await query.answer("Transaction not found. Please try again.")
            return SHOW_TRANSACTIONS
    
    elif action.startswith("tx_"):
        # Transaction selection - redirect to the existing edit workflow
         
        # Set flag to return to detailed view after edits
        context.user_data['return_to_detailed'] = True
        
        print(f"DEBUG: action.startswith(tx_) after handle_transaction_selection")
        # The selected transaction ID is in the context user_data
        return await handle_transaction_selection(update, context)
    
    elif action == "back_to_main_menu":
        # Return to main menu
        texts = check_language(update, context)
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION  # TRANSACTION state from core.py
    
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
    return TRANSACTION  # TRANSACTION state from core.py