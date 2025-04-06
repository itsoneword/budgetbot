from typing import Any, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode
import asyncio
from datetime import datetime
import re

from file_ops import read_dictionary, add_category, save_user_transaction
from language_util import check_language
from keyboards import (
    create_main_menu_keyboard, create_all_categories_keyboard,
    create_category_keyboard, create_found_category_keyboard,
    create_multiple_categories_keyboard
)
from utils import (

    process_transaction_input
)
from pandas_ops import get_user_currency,calculate_limit 
# Define transaction states
TRANSACTION = 4  # Keep this for compatibility with existing code
HANDLE_TRANSACTION_CREATE_CATEGORY = 8  # State for creating a new category during transaction

async def save_transaction(update: Update, context):
    """Process a transaction from a user's text input"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Extract the text from the update
    text = update.message.text
    
    # Clean up excess spaces in the input
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Process all lines separately (multi-transaction support)
    lines = text.strip().split("\n")
    
    # Store the transactions in context for later processing
    if len(lines) > 1:
        # This is a multi-line transaction input
        context.user_data["all_transactions"] = lines
        context.user_data["current_transaction_index"] = 0
        await update.message.reply_text(
            texts.MULTI_TRANSACTION_START.format(len(lines))
        )
        return await process_next_transaction(update, context)
    
    # Single transaction processing
    parts = text.lower().split()
    
    # Process the input to get structured data
    timestamp, category, subcategory, unknown_cat = process_transaction_input(
        user_id, parts
    )
    
    # Extract the amount, assuming it's the last part
    try:
        amount = float(parts[-1])
    except ValueError:
        await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        return TRANSACTION
    
    # Check if this is a short format input (only subcategory and amount)
    is_short_format = len(parts) == 2
    
    # Prepare transaction data
    transaction_data = {
        "id": user_id,
        "amount": amount,
        "currency": get_user_currency(user_id),
        "subcategory": subcategory,
        "timestamp": timestamp,
    }
    
    # Store data in context for later use if needed
    context.user_data["transaction_data"] = transaction_data
    context.user_data["subcategory"] = subcategory
    context.user_data["is_multi_transaction"] = False  # Flag for single transaction
    
    # If category is known and it's not a short format input, save directly
    if not unknown_cat and not is_short_format:
        print(" Category known and not short format, saving directly")
        transaction_data["category"] = category
        save_user_transaction(user_id, transaction_data)
        
        # For single transactions that successfully save, show menu at the end
        await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)
        
        # Show a menu after saving the transaction
        reply_markup = create_main_menu_keyboard(texts)
        await update.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        print(" Single transaction saved directly, returning TRANSACTION state")
        return TRANSACTION
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        print(" Processing short format input")
        # Get all categories where this subcategory exists
        cat_dict = read_dictionary(user_id)
        matching_categories = []
        
        for cat, subcats in cat_dict.items():
            if subcategory in subcats:
                matching_categories.append(cat)
        
        # Get all categories for context and pagination
        all_categories = list(cat_dict.keys())
        context.user_data["all_categories"] = all_categories
        context.user_data["matching_categories"] = matching_categories
        context.user_data["current_page"] = 0
        
        # Case 1: Subcategory not found in any category
        if len(matching_categories) == 0:
            print(" Subcategory not found in any category")
            # Create an inline keyboard with pagination for all categories
            reply_markup = create_category_keyboard(all_categories, 0, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_NOT_FOUND.format(subcategory),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            print(" Returning TRANSACTION state after showing category selection")
            return TRANSACTION
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            print(" Subcategory found in exactly one category")
            found_category = matching_categories[0]
            context.user_data["found_category"] = found_category
            
            # Create keyboard with options to use the found category or choose another
            reply_markup = create_found_category_keyboard(found_category, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_ONE.format(subcategory, found_category),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            print(" Returning TRANSACTION state after showing found category")
            return TRANSACTION
        
        # Case 3: Subcategory found in multiple categories
        else:
            print(" Subcategory found in multiple categories")
            # Create keyboard with the matching categories
            reply_markup = create_multiple_categories_keyboard(matching_categories, texts)
            
            # Format the list of matching categories for the message
            cat_list = ", ".join([f"<code>{cat}</code>" for cat in matching_categories])
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_MULTIPLE.format(subcategory, cat_list),
                reply_markup=reply_markup,
            )
            print(" Returning TRANSACTION state after showing multiple categories")
            return TRANSACTION
    
    # For unknown subcategories (should not reach here with our new logic but kept for safety)
    print(" Handling unknown subcategory case")
    reply_markup = create_category_keyboard(context.user_data.get("all_categories", []), context.user_data.get("current_page", 0), texts)
    
    await update.message.reply_text(
        texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    print(" Returning TRANSACTION state after showing category selection")
    return TRANSACTION

async def process_next_transaction(update: Update, context: CallbackContext) -> int:
    """Process the next transaction in a multi-transaction sequence or show main menu"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get stored transactions and current index
    all_transactions = context.user_data.get("all_transactions", [])
    current_index = context.user_data.get("current_transaction_index", 0)
    
    # Check if we've processed all transactions
    if current_index >= len(all_transactions):
        # All transactions processed, show main menu
        reply_markup = create_main_menu_keyboard(texts)
        
        # Use effective_message to work with both message and callback_query
        if update.callback_query:
            await update.callback_query.message.reply_text(
                texts.ALL_TRANSACTIONS_PROCESSED,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                texts.ALL_TRANSACTIONS_PROCESSED,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        return TRANSACTION
    
    # Get the current transaction to process
    transaction = all_transactions[current_index]
    parts = transaction.lower().split()
    
    # Skip empty transactions
    if not parts:
        # Increment the index and process the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        return await process_next_transaction(update, context)
    
    try:
        amount = float(parts[-1])
    except ValueError:
        # Invalid transaction format, skip it
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Notify user about invalid format and move to next transaction
        if update.callback_query:
            await update.callback_query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        else:
            await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        
        return await process_next_transaction(update, context)
    
    # Process the current transaction
    timestamp, category, subcategory, unknown_cat = process_transaction_input(
        user_id, parts
    )
    
    # Check if this is a short format input (only subcategory and amount)
    is_short_format = len(parts) == 2
    
    transaction_data = {
        "id": user_id,
        "amount": amount,
        "currency": get_user_currency(user_id),
        "subcategory": subcategory,
        "timestamp": timestamp,
    }
    
    # Store the transaction data in context for later use
    context.user_data["transaction_data"] = transaction_data
    context.user_data["subcategory"] = subcategory
    
    # Mark this as part of a multi-transaction process for later use
    context.user_data["is_multi_transaction"] = True
    context.user_data["multi_transaction_index"] = current_index
    
    # If category is known and it's not a short format input, save directly and move to next
    if not unknown_cat and not is_short_format:
        transaction_data["category"] = category
        save_user_transaction(user_id, transaction_data)
        
        # Increment the index for the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Show progress message
        progress_msg = f"Transaction {current_index+1}/{len(all_transactions)} saved: {subcategory} {amount}"
        if update.callback_query:
            await update.callback_query.message.reply_text(progress_msg)
        else:
            await update.message.reply_text(progress_msg)
        
        # Process the next transaction
        return await process_next_transaction(update, context)
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        # Get all categories where this subcategory exists
        cat_dict = read_dictionary(user_id)
        matching_categories = []
        
        for cat, subcats in cat_dict.items():
            if subcategory in subcats:
                matching_categories.append(cat)
        
        # Get all categories for context
        all_categories = list(cat_dict.keys())
        
        # Store data in context for pagination and later use
        context.user_data["all_categories"] = all_categories
        context.user_data["matching_categories"] = matching_categories
        context.user_data["current_page"] = 0
        
        # Include transaction number in the message
        transaction_number_msg = f"Transaction {current_index+1}/{len(all_transactions)}: "
        
        # Case 1: Subcategory not found in any category
        if len(matching_categories) == 0:
            # Create an inline keyboard with pagination for all categories
            reply_markup = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
            
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_NOT_FOUND.format(subcategory),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_NOT_FOUND.format(subcategory),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            return TRANSACTION
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            found_category = matching_categories[0]
            context.user_data["found_category"] = found_category
            
            # Create keyboard with options to use the found category or choose another
            reply_markup = create_found_category_keyboard(found_category, texts)
            
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_FOUND_ONE.format(subcategory, found_category),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_FOUND_ONE.format(subcategory, found_category),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            return TRANSACTION
        
        # Case 3: Subcategory found in multiple categories
        else:
            # Create keyboard with the matching categories
            reply_markup = create_multiple_categories_keyboard(matching_categories, texts)
            
            # Format the list of matching categories for the message
            cat_list = ", ".join([f"<code>{cat}</code>" for cat in matching_categories])
            
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_FOUND_MULTIPLE.format(subcategory, cat_list),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    transaction_number_msg + texts.SUBCAT_FOUND_MULTIPLE.format(subcategory, cat_list),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            return TRANSACTION
    
    # For unknown subcategories
    reply_markup = create_category_keyboard(context.user_data.get("all_categories", []), context.user_data.get("current_page", 0), texts)
    
    transaction_number_msg = f"Transaction {current_index+1}/{len(all_transactions)}: "
    if update.callback_query:
        await update.callback_query.message.reply_text(
            transaction_number_msg + texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            transaction_number_msg + texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    return TRANSACTION

async def create_new_category_transaction(update: Update, context: CallbackContext) -> int:
    """Handle creating a new category during transaction input flow"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get the new category name from the user's message
    new_category = update.message.text.lower().strip()
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")
    
    if not subcategory or not transaction_data:
        await update.message.reply_text("Error: transaction data not found.")
        return TRANSACTION
    
    # Add the new category and subcategory to the dictionary
    add_category(user_id, new_category, subcategory)
    
    # Update the transaction data with the new category
    transaction_data["category"] = new_category
    
    # Save the transaction
    save_user_transaction(user_id, transaction_data)
    
    # Inform the user
    await update.message.reply_text(
        texts.CONFIRM_SAVE_CAT.format(new_category, subcategory),
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)
    
    # Check if this is part of a multi-transaction process
    if context.user_data.get("is_multi_transaction", False):
        # Increment the index and move to the next transaction
        context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
        await asyncio.sleep(1)  # Small delay for user to read confirmation
        return await process_next_transaction(update, context)
    
    # For single transactions, show main menu
    reply_markup = create_main_menu_keyboard(texts)
    await update.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Check if we need to show limit warnings
    currency = get_user_currency(user_id)
    try:
        (
            current_daily_average,
            percent_difference,
            daily_limit,
            days_zero_spending,
            new_daily_limit,
        ) = calculate_limit(user_id)
        
        if current_daily_average > daily_limit:
            await update.message.reply_text(
                texts.LIMIT_EXCEEDED.format(
                    percent_difference=percent_difference,
                    current_daily_average=current_daily_average,
                    daily_limit=daily_limit,
                    days_zero_spending=days_zero_spending,
                    new_daily_limit=new_daily_limit,
                    currency=currency,
                ),
            )
    except Exception as e:
        print(f"Exception calculating limit: {e}")
    
    return TRANSACTION

async def select_category_for_transaction(update: Update, context: CallbackContext) -> int:
    """Handle category selection for a transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    # Handle pagination navigation
    if query.data == "page_next":
        context.user_data["current_page"] += 1
        all_categories = context.user_data.get("all_categories", [])
        from keyboards import create_category_keyboard
        keyboard = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return TRANSACTION
    
    elif query.data == "page_prev":
        context.user_data["current_page"] -= 1
        all_categories = context.user_data.get("all_categories", [])
        from keyboards import create_category_keyboard
        keyboard = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return TRANSACTION
    
    # Handle "create new category" button
    elif query.data == "create_new_category":
        subcategory = context.user_data.get("subcategory")
        await query.edit_message_text(
            texts.CREATE_CATEGORY_PROMPT.format(subcategory),
            parse_mode=ParseMode.HTML
        )
        # This is the key difference - we return HANDLE_TRANSACTION_CREATE_CATEGORY state
        # to handle the transaction flow differently from regular category management
        return HANDLE_TRANSACTION_CREATE_CATEGORY
    
    # Handle "show all categories" button
    elif query.data == "show_all_categories":
        subcategory = context.user_data.get("subcategory")
        all_categories = context.user_data.get("all_categories", [])
        context.user_data["current_page"] = 0
        from keyboards import create_all_categories_keyboard
        keyboard = create_all_categories_keyboard(all_categories, 0, texts)
        await query.edit_message_text(
            texts.CHOOSE_FROM_ALL_CATEGORIES.format(subcategory),
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION
    
    # Handle "use the found category" button
    elif query.data.startswith("use_"):
        category = query.data[4:]  # Remove "use_" prefix
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            await query.edit_message_text("Error: transaction data not found.")
            return TRANSACTION
        
        # Update the transaction data with the selected category
        transaction_data["category"] = category
        
        # Save the transaction with the selected category
        save_user_transaction(user_id, transaction_data)
        
        # Inform the user with an edit first
        await query.edit_message_text(
            texts.CONFIRM_SAVE_CAT.format(category, subcategory),
            parse_mode=ParseMode.HTML
        )
        
        # Check if this is part of a multi-transaction process
        if context.user_data.get("is_multi_transaction", False):
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            return await process_next_transaction(update, context)
        
        # For single transactions, show main menu
        await asyncio.sleep(1)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Check if we need to show limit warnings
        currency = get_user_currency(user_id)
        try:
            (
                current_daily_average,
                percent_difference,
                daily_limit,
                days_zero_spending,
                new_daily_limit,
            ) = calculate_limit(user_id)
            
            if current_daily_average > daily_limit:
                await query.message.reply_text(
                    texts.LIMIT_EXCEEDED.format(
                        percent_difference=percent_difference,
                        current_daily_average=current_daily_average,
                        daily_limit=daily_limit,
                        days_zero_spending=days_zero_spending,
                        new_daily_limit=new_daily_limit,
                        currency=currency,
                    ),
                )
        except Exception as e:
            print(f"Exception calculating limit: {e}")
        
        return TRANSACTION
    
    # Extract the category from the callback data (standard cat_[category] button)
    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            await query.edit_message_text("Error: transaction data not found.")
            return TRANSACTION
        
        # Update the transaction data with the selected category
        transaction_data["category"] = category
        
        # Save the subcategory to the category in the dictionary
        add_category(user_id, category, subcategory)
        
        # Save the transaction with the selected category
        save_user_transaction(user_id, transaction_data)
        
        # Inform the user with an edit first
        await query.edit_message_text(
            texts.CONFIRM_SAVE_CAT.format(category, subcategory),
            parse_mode=ParseMode.HTML
        )
        
        # Check if this is part of a multi-transaction process
        if context.user_data.get("is_multi_transaction", False):
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            return await process_next_transaction(update, context)
        
        # For single transactions, show main menu
        await asyncio.sleep(1)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Check if we need to show limit warnings
        currency = get_user_currency(user_id)
        try:
            (
                current_daily_average,
                percent_difference,
                daily_limit,
                days_zero_spending,
                new_daily_limit,
            ) = calculate_limit(user_id)
            
            if current_daily_average > daily_limit:
                await query.message.reply_text(
                    texts.LIMIT_EXCEEDED.format(
                        percent_difference=percent_difference,
                        current_daily_average=current_daily_average,
                        daily_limit=daily_limit,
                        days_zero_spending=days_zero_spending,
                        new_daily_limit=new_daily_limit,
                        currency=currency,
                    ),
                )
        except Exception as e:
            print(f"Exception calculating limit: {e}")
        
        return TRANSACTION
        
    else:
        # Unexpected callback data
        await query.edit_message_text(
            "Error: Unexpected callback data received. Please try again.",
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION 