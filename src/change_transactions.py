from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode 
from file_ops import read_dictionary, get_latest_records, delete_record, save_user_transaction, ensure_transaction_ids
from language_util import check_language
from pandas_ops import get_user_currency
from keyboards import create_transaction_keyboard, create_transaction_edit_keyboard, create_tx_del_confirmation_keyboard, create_numbered_transaction_keyboard
import asyncio
# Import states from central file
from src.states import *

async def show_recent_entries(update: Update, context: CallbackContext) -> int:
    """Show list of recent transactons with pagination"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Ensure all transactions have IDs
    ensure_transaction_ids(user_id)
    
    # Set default page to 0 if not set
    if 'tx_page' not in context.user_data:
        context.user_data['tx_page'] = 0
    
    # Get transactions, request more than needed to know if there are more
    page = context.user_data['tx_page']
    #print("Debug: page is:", page)
    
    # Always fetch exactly 30 transactions (for 2 pages of 15 each)
    transactions_per_page = 15  # Show 15 transactions per page
    records_to_fetch = 30  # Fetch exactly 30 records total
   # print(f"Debug: Fetching {records_to_fetch} records for page {page}")
    
    # Get latest 30 transactions
    transactions, total_amount = get_latest_records(user_id, records_to_fetch)
    #print(f"Debug: Got {len(transactions)} transactions in total")
    # Invert the transactions list to show newest transactions first
    transactions.reverse()
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
    
    # Limit page number to only show available pages (0 or 1 for 30 transactions)
    max_page = (len(transactions) - 1) // transactions_per_page
    if page > max_page:
        context.user_data['tx_page'] = max_page
        page = max_page
        #print(f"Debug: Adjusted page to max_page: {max_page}")
    
    # Paginate transactions
    start_idx = page * transactions_per_page
    end_idx = min(start_idx + transactions_per_page, len(transactions))
    
    #print(f"Debug: Showing transactions from index {start_idx} to {end_idx-1}")
    
    # Format transactions as text
    transaction_lines = []
    display_transactions = transactions[start_idx:end_idx]
    
    #print(f"Debug: Number of display transactions: {len(display_transactions)}")
    
    for i, tx in enumerate(display_transactions):
        # Parse the transaction string format: "index: timestamp, category, subcategory, amount, currency"
        parts = tx.split(', ')
        
        # Extract the parts we need
        index_part = parts[0].split(': ')[0]
        timestamp_part = parts[0].split(': ')[1]
        category = parts[1]
        subcategory = parts[2]
        amount = parts[3]
        currency = parts[4] if len(parts) > 4 else ""
        
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
        
        # Create the formatted transaction line with display number (i+1)
        line = f"{i+1}. {date_str} - {category}: {subcategory} {amount} {currency}"
        transaction_lines.append(line)
    
    # Create message text with transactions list
    transactions_text = "\n".join(transaction_lines)
    
    # Format full message
    currency = get_user_currency(user_id)
    message_text = texts.EDIT_TRANSACTIONS_PROMPT.format(total_amount, currency)
    message_text += f"\n\n{transactions_text}\n\n{texts.SELECT_TRANSACTION_TO_EDIT}"
    
    # Create keyboard with numbered buttons
    # Pass the total number of transactions (30) to limit pagination to 2 pages
    reply_markup = create_numbered_transaction_keyboard(
        display_transactions, 
        page,
        len(transactions),  # This is the total number of transactions (30)
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
    """Handle selection of a transaction to edit"""
   # print("handle_transaction_selection is called with data:", update.callback_query.data)
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "tx_next_page":
        # Go to next page (limited to max 1 for our 2-page setup)
        context.user_data['tx_page'] += 1
        #print(f"Debug: tx_next_page called, new page: {context.user_data['tx_page']}")
        return await show_recent_entries(update, context)
    
    elif callback_data == "tx_prev_page":
        # Go to previous page
        context.user_data['tx_page'] = max(0, context.user_data['tx_page'] - 1)
        #print(f"Debug: tx_prev_page called, new page: {context.user_data['tx_page']}")
        return await show_recent_entries(update, context)
    
    elif callback_data == "back_to_main_menu":
        # Go back to main menu
        from core import menu
        return await menu(update, context)
    
    # Check if we have a stored transaction index from detailed transactions view
    if context.user_data.get('selected_tx_index'):
        tx_id = context.user_data['selected_tx_index']
        #print(f"DEBUG: Using stored tx_index: {tx_id}")
        # Clear the stored index after using it
        del context.user_data['selected_tx_index']
    else:
        # Extract transaction ID from callback data (tx_INDEX)
        tx_id = callback_data.replace("tx_", "")
    
    # Get the transaction details from the CSV file
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    df = pd.read_csv(records_file)
    
    try:
        # Look for transaction with the matching ID directly in the dataframe
        tx_id_int = int(tx_id)
        matching_rows = df[df['id'] == tx_id_int]
        
        if not matching_rows.empty:
            # We found the transaction by ID
            transaction = matching_rows.iloc[0].to_dict()
            original_index = matching_rows.index[0]
        else:
            # Fall back to the original method if ID is not found
            print(f"Transaction ID {tx_id} not found, falling back to legacy method")
            # Get all transactions to find the right one
            transactions, _ = get_latest_records(user_id, 100)
            
            # Look for transaction with matching ID in the returned transactions
            matching_row = None
            for tx in transactions:
                tx_parts = tx.split(', ')
                current_id = tx_parts[0].split(': ')[0]
                
                if current_id == tx_id:
                    # We found the matching transaction
                    timestamp = tx_parts[0].split(': ')[1]
                    category = tx_parts[1]
                    subcategory = tx_parts[2]
                    amount = float(tx_parts[3])
                    
                    # Find this transaction in the dataframe
                    matching_rows = df[(df['timestamp'].str.contains(timestamp)) & 
                                      (df['category'] == category) &
                                      (df['subcategory'] == subcategory) &
                                      (df['amount'] == amount)]
                    
                    if not matching_rows.empty:
                        matching_row = matching_rows.iloc[0]
                        transaction = matching_row.to_dict()
                        original_index = matching_rows.index[0]
                        break
            
            # If still not found, try by index (legacy behavior)
            if matching_row is None:
                try:
                    tx_index = int(tx_id)
                    reversed_df = df.iloc[::-1].reset_index(drop=True)
                    transaction = reversed_df.iloc[tx_index-1].to_dict()
                    
                    # Find this row in the original dataframe to get the correct index
                    for idx, row in df.iterrows():
                        if (row['timestamp'] == transaction['timestamp'] and 
                            row['category'] == transaction['category'] and
                            row['subcategory'] == transaction['subcategory'] and
                            row['amount'] == transaction['amount']):
                            original_index = idx
                            break
                    else:
                        original_index = len(df) - tx_index
                except Exception as e:
                    print(f"Error finding transaction by index: {e}")
                    raise ValueError(f"Transaction not found with ID or index: {tx_id}")
        
        # Store in context
        context.user_data['current_transaction'] = transaction
        context.user_data['current_tx_index'] = original_index
        
    except Exception as e:
        print(f"Error selecting transaction: {e}")
        # Show error message
        await query.edit_message_text(
            texts.ERROR_SELECTING_TRANSACTION,
            parse_mode=ParseMode.HTML
        )
        # Return to transaction list
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
    print("Debug: returning to TRANSACTION_EDIT")
    return TRANSACTION_EDIT

async def handle_edit_option(update: Update, context: CallbackContext) -> int:
    """Handle selection of what to edit in the transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    #print(f"DEBUG: callback_data:",context.user_data)
    try:
        filtered_tx = context.user_data['filtered_tx']
    except Exception as e:
        print("DEBUG: filtered_tx not found in context.user_data", {e})
        filtered_tx = 0

    if callback_data == "back_to_transactions" and  filtered_tx == 1:
        # Return to filtered transaction list after Show filtered transactions
        print(f"DEBUG: Returning to filtered transaction list, first IF")
        from detailed_transactions import show_filtered_transactions
        return await show_filtered_transactions(update, context)
    elif callback_data == "back_to_transactions":
        # Return to transaction list
        print(f"DEBUG: Returning to transaction list, second IF")
        return await show_recent_entries(update, context)
    elif callback_data == "edit_date":
        # Edit date
        await query.edit_message_text(
            texts.ENTER_NEW_DATE_PROMPT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_DATE
    
    elif callback_data == "edit_category":
        # Edit category
        # Get categories from dictionary
        cat_dict = read_dictionary(user_id)
        categories = list(cat_dict.keys())
        
        # Store categories in context
        context.user_data["categories"] = categories
        
        # Create keyboard with categories
        from keyboards import create_tx_categories_keyboard
        reply_markup = create_tx_categories_keyboard(categories, texts)
        
        await query.edit_message_text(
            texts.SELECT_NEW_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return EDIT_CATEGORY
    
    elif callback_data == "edit_subcategory":
        # Edit subcategory
        await query.edit_message_text(
            texts.ENTER_NEW_SUBCATEGORY,
            parse_mode=ParseMode.HTML
        )
        return EDIT_SUBCATEGORY
    
    elif callback_data == "edit_amount":
        # Edit amount
        await query.edit_message_text(
            texts.ENTER_NEW_AMOUNT_PROMPT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_AMOUNT
    
    elif callback_data == "delete_transaction":
        # Delete transaction
        # Create confirmation keyboard
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
    
    # Default fallback
    return TRANSACTION_EDIT

async def handle_edit_date(update: Update, context: CallbackContext) -> int:
    """Handle input of new date for the transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get the new date text
    date_text = update.message.text.strip()
    
    # Parse the date
    try:
        if '.' in date_text:
            # Try to parse dd.mm or dd.mm.yyyy format
            parts = date_text.split('.')
            if len(parts) == 2:
                day, month = map(int, parts)
                year = datetime.now().year
            else:
                day, month, year = map(int, parts)
            
            # Create a datetime object
            new_date = datetime(year, month, day)
        else:
            # Invalid format
            raise ValueError("Invalid date format")
        
        # Update the transaction timestamp
        transaction = context.user_data['current_transaction']
        old_timestamp = transaction['timestamp']
        
        # Create new timestamp preserving the time part
        old_time = pd.to_datetime(old_timestamp).time()
        new_timestamp = datetime.combine(new_date.date(), old_time)
        
        # Update transaction in CSV
        success = update_transaction(user_id, context.user_data['current_tx_index'], 'timestamp', new_timestamp.strftime('%Y-%m-%dT%H:%M:%S'))
        
        if success:
            # Display success message
            await update.message.reply_text(
                texts.DATE_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )
            
            # Check if we should return to detailed transactions view
            if context.user_data.get('return_to_detailed', False):
                from detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0  # Reset to first page of detailed view
                return await show_filtered_transactions(update, context)
            else:
                # Return to transaction list
                context.user_data['tx_page'] = 0  # Reset to first page
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
    """Handle selection of a new category"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("txpage_"):
        # Handle page navigation
        direction = callback_data.replace("txpage_", "")
        current_page = context.user_data.get('category_page', 0)
        
        if direction == "prev":
            context.user_data['category_page'] = max(0, current_page - 1)
        else:  # direction == "next"
            context.user_data['category_page'] = current_page + 1
        
        # Refresh the categories keyboard
        categories = context.user_data.get("categories", [])
        from keyboards import create_tx_categories_keyboard
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data['category_page'])
        
        await query.edit_message_text(
            texts.SELECT_NEW_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return EDIT_CATEGORY
    
    elif callback_data == "cancel_transaction":
        # Cancel and return to transaction list
        return await show_recent_entries(update, context)
    
    elif callback_data.startswith("txcat_"):
        # Extract category from callback
        category = callback_data.replace("txcat_", "")
        
        # Update transaction in CSV
        success = update_transaction(user_id, context.user_data['current_tx_index'], 'category', category)
        
        if success:
            # Display success message
            await query.edit_message_text(
                texts.CATEGORY_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )
            
            # Check if we should return to detailed transactions view
            if context.user_data.get('return_to_detailed', False):
                print(f"DEBUG: Returning to detailed view after category update: '{category}'")
                from detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0  # Reset to first page of detailed view
                return await show_filtered_transactions(update, context)
            else:
                # Return to transaction list
                context.user_data['tx_page'] = 0  # Reset to first page
                return await show_recent_entries(update, context)
        else:
            await query.edit_message_text(
                texts.ERROR_UPDATING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
            return EDIT_CATEGORY
    
    # Default fallback
    return EDIT_CATEGORY

async def handle_edit_subcategory(update: Update, context: CallbackContext) -> int:
    """Handle editing a subcategory"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Check if this is a callback query (back button or cancel)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "back_to_categories":
            # Return to category selection
            cat_dict = read_dictionary(user_id)
            categories = list(cat_dict.keys())
            
            # Store categories in context
            context.user_data["categories"] = categories
            
            # Create keyboard with categories
            from keyboards import create_tx_categories_keyboard
            reply_markup = create_tx_categories_keyboard(categories, texts)
            
            await query.edit_message_text(
                texts.SELECT_NEW_CATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return EDIT_CATEGORY
        
        elif callback_data == "cancel_transaction":
            # Cancel and return to transaction list
            return await show_recent_entries(update, context)
    
    # Handle text input for new subcategory name
    new_subcategory = update.message.text.strip().lower()
    
    # Update transaction in CSV
    success = update_transaction(user_id, context.user_data['current_tx_index'], 'subcategory', new_subcategory)
    
    if success:
        # Display success message
        await update.message.reply_text(
            texts.SUBCATEGORY_UPDATED_SUCCESS,
            parse_mode=ParseMode.HTML
        )
        
        # Check if we should return to detailed transactions view
        if context.user_data.get('return_to_detailed', False):
            from detailed_transactions import show_filtered_transactions
            context.user_data['tx_page'] = 0  # Reset to first page of detailed view
            return await show_filtered_transactions(update, context)
        else:
            # Return to transaction list
            context.user_data['tx_page'] = 0  # Reset to first page
            return await show_recent_entries(update, context)
    else:
        await update.message.reply_text(
            texts.ERROR_UPDATING_TRANSACTION,
            parse_mode=ParseMode.HTML
        )
        return EDIT_SUBCATEGORY

async def handle_edit_amount(update: Update, context: CallbackContext) -> int:
    """Handle input of new amount for the transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get the new amount text
    amount_text = update.message.text.strip()
    
    # Parse the amount
    try:
        new_amount = float(amount_text.replace(',', '.'))
        
        # Update transaction in CSV
        success = update_transaction(user_id, context.user_data['current_tx_index'], 'amount', new_amount)
        
        if success:
            # Display success message
            await update.message.reply_text(
                texts.AMOUNT_UPDATED_SUCCESS,
                parse_mode=ParseMode.HTML
            )
            
            # Check if we should return to detailed transactions view
            if context.user_data.get('return_to_detailed', False):
                from detailed_transactions import show_filtered_transactions
                context.user_data['tx_page'] = 0  # Reset to first page of detailed view
                return await show_filtered_transactions(update, context)
            else:
                # Return to transaction list
                context.user_data['tx_page'] = 0  # Reset to first page
                return await show_recent_entries(update, context)
        else:
            await update.message.reply_text(
                texts.ERROR_UPDATING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
            return EDIT_AMOUNT
        
    except ValueError:
        await update.message.reply_text(
            texts.INVALID_AMOUNT_FORMAT,
            parse_mode=ParseMode.HTML
        )
        return EDIT_AMOUNT

async def handle_delete_tx_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of transaction deletion"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "confirm":
        # Delete the transaction
        try:
            # Get the transaction from context
            transaction = context.user_data.get('current_transaction')
            if not transaction:
                raise ValueError("Transaction not found in context")
                
            # Read the CSV file
            records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
            df = pd.read_csv(records_file)
            
            # Try to delete by ID first if available
            if 'id' in transaction and pd.notna(transaction['id']):
                tx_id = transaction['id']
                # Filter out the row with matching ID
                df = df[df['id'] != tx_id]
                df.to_csv(records_file, index=False)
                success = True
            else:
                # Fall back to index-based deletion
                index = context.user_data['current_tx_index']
                # Calculate the record position from the end for the delete_record function
                record_num = len(df) - index
                success = delete_record(user_id, record_num, "delete")
            
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
            print(f"Error deleting transaction: {e}")
            await query.edit_message_text(
                texts.ERROR_DELETING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
    else:  # callback_data == "cancel"
        await query.edit_message_text(
            texts.DELETE_CANCELLED,
            parse_mode=ParseMode.HTML
        )
    
    # Check if we should return to detailed transactions view
    if context.user_data.get('return_to_detailed', False):
        print(f"DEBUG: Returning to detailed view after delete confirmation")
        from detailed_transactions import show_filtered_transactions
        return await show_filtered_transactions(update, context)
    else:
        # Return to transaction list
        context.user_data['tx_page'] = 0  # Reset to first page
        return await show_recent_entries(update, context)

def update_transaction(user_id, index_or_id, field, value):
    """Update a transaction field in the CSV file"""
    try:
        # Read the CSV file
        records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
        df = pd.read_csv(records_file)
        
        # First try to use the value as an ID
        if isinstance(index_or_id, str) and index_or_id.isdigit():
            index_or_id = int(index_or_id)
            
        if isinstance(index_or_id, int):
            # Check if the ID exists in the dataframe
            matching_id_rows = df[df['id'] == index_or_id]
            if not matching_id_rows.empty:
                # Update the field for the matching ID
                df.loc[df['id'] == index_or_id, field] = value
                # Write back to the CSV file
                df.to_csv(records_file, index=False)
                return True
        
        # Fall back to using index if ID not found or index_or_id is directly an index
        if 0 <= index_or_id < len(df):
            # Update the field at the specified index
            df.loc[index_or_id, field] = value
            
            # Write back to the CSV file
            df.to_csv(records_file, index=False)
            return True
        else:
            print(f"Warning: Index/ID {index_or_id} not found")
            return False
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return False 