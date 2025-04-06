from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode 
from file_ops import read_dictionary, get_latest_records, delete_record, save_user_transaction
from language_util import check_language
from pandas_ops import get_user_currency
from keyboards import create_transaction_keyboard, create_transaction_edit_keyboard, create_transaction_confirmation_keyboard

# Define states for the conversation
(
    TRANSACTION_LIST, 
    TRANSACTION_EDIT, 
    EDIT_DATE, 
    EDIT_CATEGORY, 
    EDIT_SUBCATEGORY, 
    EDIT_AMOUNT, 
    CONFIRM_DELETE
) = range(22, 29)

async def show_transactions(update: Update, context: CallbackContext) -> int:
    """Show list of recent transactions with pagination"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Set default page to 0 if not set
    if 'tx_page' not in context.user_data:
        context.user_data['tx_page'] = 0
    
    # Get transactions, request more than 10 to know if we have more
    page = context.user_data['tx_page']
    print("Debag: page is:", page)
    records_to_fetch = 8 # Fetch 7 to know if there are more than 7
    transactions, total_amount = get_latest_records(user_id, records_to_fetch)
    
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
    
    
    # If we're on page > 0, get a new set of records for this page
    if page > 0:
        print("Debag: page >0:", page)
        # Calculate the number of records to skip
        skip_records = page * 8
        # Get a new batch of records
        transactions, _ = get_latest_records(user_id, skip_records + records_to_fetch)
     
        # Take only the last 11 (or fewer) records
        if len(transactions) > skip_records:
            # This line slices the transactions list to get only the records for the current page
            print("Debag: len(transactions) is:",len(transactions),    "skip_records: start:", skip_records, "end:", skip_records + records_to_fetch)
            transactions = transactions[:8]
            print("Debag: transactions:", transactions)
        else:
            # If we've gone past the available records, go back to the last valid page
            context.user_data['tx_page'] -= 1
            return await show_transactions(update, context)
    
    # Display only 10 records max
    display_transactions = transactions[:8]
    
    reply_markup = create_transaction_keyboard(display_transactions, page, texts)
    
    # Format message text
    currency = get_user_currency(user_id)
    message_text = texts.EDIT_TRANSACTIONS_PROMPT.format(total_amount, currency)
    
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
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "tx_next_page":
        # Go to next page
        context.user_data['tx_page'] += 1
        print("tx_next_page is called:", context.user_data['tx_page'])
        return await show_transactions(update, context)
    
    elif callback_data == "tx_prev_page":
        # Go to previous page
        context.user_data['tx_page'] = max(0, context.user_data['tx_page'] - 1)
        return await show_transactions(update, context)
    
    elif callback_data == "back_to_main_menu":
        # Go back to main menu
        from core import menu
        return await menu(update, context)
    
    # Extract transaction ID from callback data (tx_INDEX)
    tx_id = callback_data.replace("tx_", "")
    
    # Get the transaction details from the CSV file
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    df = pd.read_csv(records_file)
    
    # Find the transaction matching the ID in the latest transactions
    try:
        # Get the transaction details by index or search for it in the dataframe
        matching_row = None
        
        # First try to get transactions using get_latest_records to ensure we get the same data
        # that was used to create the buttons
        transactions, _ = get_latest_records(user_id, 100)  # Get a larger batch to ensure we have the transaction
        
        # Look for transaction with matching ID in the returned transactions
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
                    # Store the index of the row in the dataframe for later updates
                    original_index = matching_rows.index[0]
                    break
        
        # If we couldn't find the transaction by details, try directly by index
        if matching_row is None:
            tx_index = int(tx_id)
            # The CSV is reversed in display (newest first), so we need to adjust
            # Original data is oldest first, display is newest first
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
                # If we couldn't find it by matching, just use the index
                original_index = len(df) - tx_index
        
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
        return await show_transactions(update, context)
    
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
    """Handle selection of what to edit in the transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "back_to_transactions":
        # Return to transaction list
        return await show_transactions(update, context)
    
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
        reply_markup = create_transaction_confirmation_keyboard(texts)
        
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
            
            # Return to transaction list
            context.user_data['tx_page'] = 0  # Reset to first page
            return await show_transactions(update, context)
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
        return await show_transactions(update, context)
    
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
            
            # Return to transaction list
            context.user_data['tx_page'] = 0  # Reset to first page
            return await show_transactions(update, context)
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
            return await show_transactions(update, context)
    
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
        
        # Return to transaction list
        context.user_data['tx_page'] = 0  # Reset to first page
        return await show_transactions(update, context)
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
            
            # Return to transaction list
            context.user_data['tx_page'] = 0  # Reset to first page
            return await show_transactions(update, context)
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
        tx_index = context.user_data['current_tx_index'] + 1  # Convert to 1-based index for delete_record
        success = delete_record(user_id, tx_index, "delete")
        
        if success:
            await query.edit_message_text(
                texts.TRANSACTION_DELETED_SUCCESS,
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                texts.ERROR_DELETING_TRANSACTION,
                parse_mode=ParseMode.HTML
            )
    else:  # callback_data == "cancel"
        await query.edit_message_text(
            texts.DELETE_CANCELLED,
            parse_mode=ParseMode.HTML
        )
    
    # Return to transaction list
    context.user_data['tx_page'] = 0  # Reset to first page
    return await show_transactions(update, context)

def update_transaction(user_id, index, field, value):
    """Update a transaction field in the CSV file"""
    try:
        # Read the CSV file
        records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
        df = pd.read_csv(records_file)
        
        # Check if the index exists in the dataframe
        if 0 <= index < len(df):
            # Update the field at the specified index
            df.loc[index, field] = value
            
            # Write back to the CSV file
            df.to_csv(records_file, index=False)
            return True
        else:
            print(f"Warning: Index {index} out of bounds for dataframe with {len(df)} rows")
            return False
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return False 