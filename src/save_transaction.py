from typing import Any, Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode
import asyncio
from datetime import datetime
import re

from file_ops import (
    read_dictionary, add_category, save_user_transaction,
    get_frequently_used_categories, get_frequently_used_subcategories,
    get_recent_amounts
)
from language_util import check_language
from keyboards import (
    create_main_menu_keyboard, create_category_keyboard, 
    create_found_category_keyboard,
    create_multiple_categories_keyboard, create_subcategories_keyboard,
    create_amounts_keyboard, create_confirm_transaction_keyboard,
    create_tx_categories_keyboard
)
from src.show_transactions import (
    process_transaction_input
)
from pandas_ops import get_user_currency, calculate_limit
# Import states from central states file
from src.states import *

async def save_transaction(update: Update, context):
    """Process a transaction from a user's text input"""
    print(f"DEBUG: Fn save_transaction")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Extract the text from the update
    text = update.message.text
    
    # Clean up excess spaces in the input
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Process all lines separately (multi-transaction support)
    lines = text.strip().split("\n") if "\n" in text else text.strip().split(",")
    
    # Store the transactions in context for later processing
    if len(lines) > 1:
        print(f"DEBUG: Condition multi-line transaction input")
        # This is a multi-line transaction input
        context.user_data["all_transactions"] = lines
        context.user_data["current_transaction_index"] = 0
        await update.message.reply_text(
            texts.MULTI_TRANSACTION_START.format(len(lines))
        )
        print(f"DEBUG: Return process_next_transaction")
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
        print(f"DEBUG: Condition invalid amount format")
        await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        print(f"DEBUG: Return TRANSACTION")
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
        print(f"DEBUG: Condition category known and not short format")
        transaction_data["category"] = category
        save_user_transaction(user_id, transaction_data)
        
        # For single transactions that successfully save, show menu at the end
        await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)
        
        # # Show a menu after saving the transaction
        # reply_markup = create_main_menu_keyboard(texts)
        # await update.message.reply_text(
        #     texts.BACK_TO_MAIN_MENU,
        #     reply_markup=reply_markup,
        #     parse_mode=ParseMode.HTML
        # )
        
        print(f"DEBUG: Return TRANSACTION (single transaction saved directly)")
        return TRANSACTION
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        print(f"DEBUG: Condition short format input")
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
            print(f"DEBUG: Condition subcategory not found in any category")
            # Create an inline keyboard with pagination for all categories
            reply_markup = create_category_keyboard(all_categories, 0, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_NOT_FOUND.format(subcategory),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            print(f"DEBUG: Return TX_CHOOSE_CATEGORY (showing category selection)")
            return TX_CHOOSE_CATEGORY
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            print(f"DEBUG: Condition subcategory found in exactly one category")
            found_category = matching_categories[0]
            context.user_data["found_category"] = found_category
            
            # Create keyboard with options to use the found category or choose another
            reply_markup = create_found_category_keyboard(found_category, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_ONE.format(subcategory, found_category),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            print(f"DEBUG: Return TX_CHOOSE_CATEGORY (showing found category)")
            return TX_CHOOSE_CATEGORY
        
        # Case 3: Subcategory found in multiple categories
        else:
            print(f"DEBUG: Condition subcategory found in multiple categories")
            # Create keyboard with the matching categories
            reply_markup = create_multiple_categories_keyboard(matching_categories, texts)
            
            # Format the list of matching categories for the message
            cat_list = ", ".join([f"<code>{cat}</code>" for cat in matching_categories])
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_MULTIPLE.format(subcategory, cat_list),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            print(f"DEBUG: Return TX_CHOOSE_CATEGORY (showing multiple categories)")
            return TX_CHOOSE_CATEGORY
    
    # For unknown subcategories (should not reach here with our new logic but kept for safety)
    print(f"DEBUG: Condition handling unknown subcategory case")
    reply_markup = create_category_keyboard(context.user_data.get("all_categories", []), context.user_data.get("current_page", 0), texts)
    
    await update.message.reply_text(
        texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    print(f"DEBUG: Return TX_CHOOSE_CATEGORY (showing category selection)")
    return TX_CHOOSE_CATEGORY

async def process_next_transaction(update: Update, context: CallbackContext) -> int:
    """Process the next transaction in a multi-transaction sequence or show main menu"""
    print(f"DEBUG: Fn process_next_transaction")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get stored transactions and current index
    all_transactions = context.user_data.get("all_transactions", [])
    current_index = context.user_data.get("current_transaction_index", 0)
    
    # Check if we've processed all transactions
    if current_index >= len(all_transactions):
        print(f"DEBUG: Condition all transactions processed")
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
        print(f"DEBUG: Return TRANSACTION (all transactions processed)")
        return TRANSACTION
    
    # Get the current transaction to process
    transaction = all_transactions[current_index]
    parts = transaction.lower().split()
    
    # Skip empty transactions
    if not parts:
        print(f"DEBUG: Condition empty transaction")
        # Increment the index and process the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        print(f"DEBUG: Return process_next_transaction (skipping empty transaction)")
        return await process_next_transaction(update, context)
    
    try:
        amount = float(parts[-1])
    except ValueError:
        print(f"DEBUG: Condition invalid transaction format")
        # Invalid transaction format, skip it
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Notify user about invalid format and move to next transaction
        if update.callback_query:
            await update.callback_query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        else:
            await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        
        print(f"DEBUG: Return process_next_transaction (skipping invalid transaction)")
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
        print(f"DEBUG: Condition category known and not short format in multi-transaction")
        transaction_data["category"] = category
        save_user_transaction(user_id, transaction_data)
        
        # Increment the index for the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Show progress message
        progress_msg = texts.PROGRESS_MSG.format(current_index+1, len(all_transactions), subcategory, amount)
        if update.callback_query:
            await update.callback_query.message.reply_text(progress_msg)
        else:
            await update.message.reply_text(progress_msg)
        
        # Process the next transaction
        print(f"DEBUG: Return process_next_transaction (moving to next transaction)")
        return await process_next_transaction(update, context)
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        print(f"DEBUG: Condition short format input in multi-transaction")
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
            print(f"DEBUG: Condition subcategory not found in any category in multi-transaction")
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
            print(f"DEBUG: Return TRANSACTION (showing category selection in multi-transaction)")
            return TX_CHOOSE_CATEGORY
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            print(f"DEBUG: Condition subcategory found in exactly one category in multi-transaction")
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
            print(f"DEBUG: Return TRANSACTION (showing found category in multi-transaction)")
            return TRANSACTION
        
        # Case 3: Subcategory found in multiple categories
        else:
            print(f"DEBUG: Condition subcategory found in multiple categories in multi-transaction")
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
            print(f"DEBUG: Return TRANSACTION (showing multiple categories in multi-transaction)")
            return TRANSACTION
    
    # For unknown subcategories
    print(f"DEBUG: Condition unknown subcategory in multi-transaction")
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
    
    print(f"DEBUG: Return TRANSACTION (showing category selection for unknown subcategory)")
    return TRANSACTION

async def create_new_category_transaction(update: Update, context: CallbackContext) -> int:
    """Handle creating a new category during transaction input flow"""
    print(f"DEBUG: Fn create_new_category_transaction")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get the new category name from the user's message
    new_category = update.message.text.lower().strip()
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")
    
    if not subcategory or not transaction_data:
        print(f"DEBUG: Condition missing transaction data")
        await update.message.reply_text("Error: transaction data not found.")
        print(f"DEBUG: Return TRANSACTION (missing transaction data)")
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
        print(f"DEBUG: Condition multi-transaction process")
        # Increment the index and move to the next transaction
        context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
        await asyncio.sleep(1)  # Small delay for user to read confirmation
        print(f"DEBUG: Return process_next_transaction (moving to next transaction)")
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
            print(f"DEBUG: Condition limit exceeded")
            await update.message.reply_text(
                texts.LIMIT_EXCEEDED.format(
                    percent_difference=percent_difference,
                    current_daily_average=current_daily_average,
                    daily_limit=daily_limit,
                    days_zero_spending=days_zero_spending,
                    new_daily_limit=new_daily_limit,
                    currency=currency,
                ),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"DEBUG: Exception calculating limit: {e}")
    
    print(f"DEBUG: Return TRANSACTION (single transaction completed)")
    return TRANSACTION

async def select_category_for_transaction(update: Update, context: CallbackContext) -> int:
    """Handle category selection for a transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    # Handle pagination navigation
    if query.data == "catpage_next":
        context.user_data["current_page"] += 1
        all_categories = context.user_data.get("all_categories", [])
        keyboard = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return TX_CHOOSE_CATEGORY
    
    elif query.data == "catpage_prev":
        context.user_data["current_page"] -= 1
        all_categories = context.user_data.get("all_categories", [])
        keyboard = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return TX_CHOOSE_CATEGORY
    
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
        
        keyboard = create_category_keyboard(all_categories, context.user_data["current_page"], texts)
        
        await query.edit_message_text(
            texts.CHOOSE_FROM_ALL_CATEGORIES.format(subcategory),
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        return TX_CHOOSE_CATEGORY
    
    # Handle "use the found category" button
    elif query.data.startswith("use_"):
        print(f"DEBUG: Condition use_found_category")
        category = query.data[4:]  # Remove "use_" prefix
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            print(f"DEBUG: Condition missing transaction data")
            await query.edit_message_text("Error: transaction data not found.")
            print(f"DEBUG: Return TRANSACTION (missing transaction data)")
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
            print(f"DEBUG: Condition multi-transaction process")
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            print(f"DEBUG: Return process_next_transaction (moving to next transaction)")
            return await process_next_transaction(update, context)
        
        # For single transactions, show main menu
        await asyncio.sleep(1)
        # reply_markup = create_main_menu_keyboard(texts)
        # await query.message.reply_text(
        #     texts.MAIN_MENU_TEXT,
        #     reply_markup=reply_markup,
        #     parse_mode=ParseMode.HTML
        # )
        
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
                print(f"DEBUG: Condition limit exceeded")
                await query.message.reply_text(
                    texts.LIMIT_EXCEEDED.format(
                        percent_difference=percent_difference,
                        current_daily_average=current_daily_average,
                        daily_limit=daily_limit,
                        days_zero_spending=days_zero_spending,
                        new_daily_limit=new_daily_limit,
                        currency=currency,
                    ),
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"DEBUG: Exception calculating limit: {e}")
        
        print(f"DEBUG: Return TRANSACTION (single transaction completed)")
        return TRANSACTION
    
    # Extract the category from the callback data (standard cat_[category] button)
    elif query.data.startswith("cat_"):
        print(f"DEBUG: Condition cat_category_selection")
        category = query.data.replace("cat_", "")
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            print(f"DEBUG: Condition missing transaction data")
            await query.edit_message_text("Error: transaction data not found.")
            print(f"DEBUG: Return TRANSACTION (missing transaction data)")
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
            print(f"DEBUG: Condition multi-transaction process")
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            print(f"DEBUG: Return process_next_transaction (moving to next transaction)")
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
                print(f"DEBUG: Condition limit exceeded")
                await query.message.reply_text(
                    texts.LIMIT_EXCEEDED.format(
                        percent_difference=percent_difference,
                        current_daily_average=current_daily_average,
                        daily_limit=daily_limit,
                        days_zero_spending=days_zero_spending,
                        new_daily_limit=new_daily_limit,
                        currency=currency,
                    ),
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"DEBUG: Exception calculating limit: {e}")
        
        print(f"DEBUG: Return TRANSACTION (single transaction completed)")
        return TRANSACTION
        
    else:
        print(f"DEBUG: Condition unexpected callback data")
        # Unexpected callback data
        await query.edit_message_text(
            "Error: Unexpected callback data received. Please try again.",
            parse_mode=ParseMode.HTML
        )
        print(f"DEBUG: Return TRANSACTION (error handling)", TRANSACTION)

        return TRANSACTION 

async def handle_transaction_category(update: Update, context: CallbackContext):
    """Handle category selection for transaction entry"""
    print(f"DEBUG: Fn handle_transaction_category")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    action = query.data
    
    # Handle page navigation
    if action == "txpage_prev":
        print(f"DEBUG: Condition txpage_prev")
        context.user_data["tx_page"] -= 1
        categories = get_frequently_used_categories(user_id)
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await query.edit_message_text(
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return SELECT_TRANSACTION_CATEGORY
        
    elif action == "txpage_next":
        context.user_data["tx_page"] += 1
        categories = get_frequently_used_categories(user_id)
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await query.edit_message_text(
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return SELECT_TRANSACTION_CATEGORY
    
    elif action == "cancel_transaction":
        await query.edit_message_text(
            texts.TRANSACTION_CANCELED,
            parse_mode=ParseMode.HTML
        )
        # Show main menu
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION
    
    # Handle category selection
    elif action.startswith("txcat_"):
        # Extract category name from callback data
        category = action[6:]  # Remove "txcat_" prefix
        
        # Store selected category in context
        context.user_data["tx_category"] = category
        context.user_data["tx_subpage"] = 0
        
        # Get frequently used subcategories for this category
        subcategories = get_frequently_used_subcategories(user_id, category)
        
        # If no subcategories found, check dictionary
        if not subcategories:
            cat_dict = read_dictionary(user_id)
            if category in cat_dict and cat_dict[category]:
                subcategories = cat_dict[category]
        
        # Store subcategories in context
        context.user_data["tx_subcategories"] = subcategories
        
        if subcategories:
            # Create and show the subcategories keyboard
            reply_markup = create_subcategories_keyboard(subcategories, category, context.user_data["tx_subpage"], texts)
            await query.edit_message_text(
                texts.SELECT_TRANSACTION_SUBCATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            # No subcategories found, ask user to enter manually
            await query.edit_message_text(
                texts.NO_SUBCATEGORIES_FOUND,
                parse_mode=ParseMode.HTML
            )
        print("Debug: Returning state SELECT_TRANSACTION_SUBCATEGORY")
        return SELECT_TRANSACTION_SUBCATEGORY
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return SELECT_TRANSACTION_CATEGORY

async def handle_transaction_subcategory(update: Update, context: CallbackContext):
    """Handle subcategory selection or manual entry for transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Check if this is a callback query (inline button click)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        action = query.data
        
        # Handle page navigation for subcategories
        if action == "txsubpage_prev":
            context.user_data["tx_subpage"] -= 1
            subcategories = context.user_data.get("tx_subcategories", [])
            category = context.user_data.get("tx_category", "")
            reply_markup = create_subcategories_keyboard(subcategories, category, context.user_data["tx_subpage"], texts)
            await query.edit_message_text(
                texts.SELECT_TRANSACTION_SUBCATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_SUBCATEGORY
            
        elif action == "txsubpage_next":
            context.user_data["tx_subpage"] += 1
            subcategories = context.user_data.get("tx_subcategories", [])
            category = context.user_data.get("tx_category", "")
            reply_markup = create_subcategories_keyboard(subcategories, category, context.user_data["tx_subpage"], texts)
            await query.edit_message_text(
                texts.SELECT_TRANSACTION_SUBCATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_SUBCATEGORY
        
        # Handle back to categories
        elif action == "back_to_categories":
            context.user_data["tx_page"] = 0
            categories = get_frequently_used_categories(user_id)
            reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
            await query.edit_message_text(
                texts.SELECT_TRANSACTION_CATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_CATEGORY
        
        # Handle subcategory selection
        elif action.startswith("txsubcat_"):
            # Extract subcategory name from callback data
            subcategory = action[9:]  # Remove "txsubcat_" prefix
            
            # Store selected subcategory in context
            context.user_data["tx_subcategory"] = subcategory
            
            # Get recent amounts for this subcategory
            amounts = get_recent_amounts(user_id, subcategory)
            
            if amounts:
                # Show recent amounts keyboard
                reply_markup = create_amounts_keyboard(amounts, texts)
                await query.edit_message_text(
                    texts.RECENT_SUBCATEGORY_AMOUNTS.format(subcategory=subcategory),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                # No recent amounts, ask for amount entry
                await query.edit_message_text(
                    texts.ENTER_TRANSACTION_AMOUNT.format(subcategory=subcategory),
                    parse_mode=ParseMode.HTML
                )
            
            return ENTER_TRANSACTION_AMOUNT
        
        # Handle cancel
        elif action == "cancel_transaction":
            await query.edit_message_text(
                texts.TRANSACTION_CANCELED,
                parse_mode=ParseMode.HTML
            )
            # Show main menu
            reply_markup = create_main_menu_keyboard(texts)
            await query.message.reply_text(
                texts.MAIN_MENU_TEXT,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return TRANSACTION
    
    # Handle manual entry (text message)
    else:
        # Parse the text to extract subcategory and amount
        parts = update.message.text.lower().split()
        
        try:
            # Check if the format is correct (last part should be a number)
            amount = float(parts[-1])
            subcategory = " ".join(parts[:-1])
            
            # Store subcategory and amount in context
            context.user_data["tx_subcategory"] = subcategory
            context.user_data["tx_amount"] = amount
            
            # Inform user about detected values
            await update.message.reply_text(
                texts.MANUAL_SUBCATEGORY_DETECTED.format(subcategory=subcategory, amount=amount),
                parse_mode=ParseMode.HTML
            )
            
            # Move to confirmation step
            category = context.user_data.get("tx_category", "")
            currency = get_user_currency(user_id)
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            reply_markup = create_confirm_transaction_keyboard(texts)
            await update.message.reply_text(
                texts.CONFIRM_TRANSACTION_DETAILS.format(
                    category=category,
                    subcategory=subcategory,
                    amount=amount,
                    currency=currency,
                    date=current_date
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            return CONFIRM_TRANSACTION
            
        except (ValueError, IndexError):
            # Invalid format, ask user to try again
            await update.message.reply_text(
                texts.TRANSACTION_ERROR_TEXT,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_SUBCATEGORY
    
    # Handle unexpected callback data
    await update.callback_query.answer("Unexpected option")
    return SELECT_TRANSACTION_SUBCATEGORY

async def handle_transaction_amount(update: Update, context: CallbackContext):
    """Handle amount entry or selection for transaction"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Check if this is a callback query (amount selected from keyboard)
    if update.callback_query:
        query = update.callback_query
        action = query.data
        
        # Handle back to subcategories
        if action == "back_to_subcategories":
            subcategories = context.user_data.get("tx_subcategories", [])
            category = context.user_data.get("tx_category", "")
            reply_markup = create_subcategories_keyboard(subcategories, category, context.user_data.get("tx_subpage", 0), texts)
            await query.edit_message_text(
                texts.SELECT_TRANSACTION_SUBCATEGORY,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_SUBCATEGORY
        
        # Handle amount selection
        elif action.startswith("txamount_"):
            # Extract amount from callback data
            amount = float(action[9:])  # Remove "txamount_" prefix
            
            # Store selected amount in context
            context.user_data["tx_amount"] = amount
            
            # Move to confirmation step
            category = context.user_data.get("tx_category", "")
            subcategory = context.user_data.get("tx_subcategory", "")
            currency = get_user_currency(user_id)
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            reply_markup = create_confirm_transaction_keyboard(texts)
            await query.edit_message_text(
                texts.CONFIRM_TRANSACTION_DETAILS.format(
                    category=category,
                    subcategory=subcategory,
                    amount=amount,
                    currency=currency,
                    date=current_date
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            return CONFIRM_TRANSACTION
        
        # Handle cancel
        elif action == "cancel_transaction":
            await query.edit_message_text(
                texts.TRANSACTION_CANCELED,
                parse_mode=ParseMode.HTML
            )
            #Show main menu
            reply_markup = create_main_menu_keyboard(texts)
            await query.message.reply_text(
                texts.MAIN_MENU_TEXT,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return TRANSACTION
    
    # Handle manual entry (text message)
    else:
        try:
            # Convert the text to a float
            amount = float(update.message.text.strip())
            
            # Store amount in context
            context.user_data["tx_amount"] = amount
            
            # Move to confirmation step
            category = context.user_data.get("tx_category", "")
            subcategory = context.user_data.get("tx_subcategory", "")
            currency = get_user_currency(user_id)
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            reply_markup = create_confirm_transaction_keyboard(texts)
            await update.message.reply_text(
                texts.CONFIRM_TRANSACTION_DETAILS.format(
                    category=category,
                    subcategory=subcategory,
                    amount=amount,
                    currency=currency,
                    date=current_date
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            return CONFIRM_TRANSACTION
            
        except ValueError:
            # Invalid format, ask user to try again
            await update.message.reply_text(
                texts.TRANSACTION_ERROR_TEXT,
                parse_mode=ParseMode.HTML
            )
            return SELECT_TRANSACTION_SUBCATEGORY
    
    # Handle unexpected callback data
    if update.callback_query:
        await update.callback_query.answer("Unexpected option")
    return SELECT_TRANSACTION_SUBCATEGORY

async def handle_transaction_confirmation(update: Update, context: CallbackContext):
    """Handle transaction confirmation"""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    action = query.data
    
    if action == "confirm_transaction":
        # Get transaction details from context
        category = context.user_data.get("tx_category", "")
        subcategory = context.user_data.get("tx_subcategory", "")
        amount = context.user_data.get("tx_amount", 0)
        currency = get_user_currency(user_id)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create transaction data
        transaction_data = {
            "id": user_id,
            "amount": amount,
            "currency": currency,
            "category": category,
            "subcategory": subcategory,
            "timestamp": timestamp,
        }
        
        # Save the transaction
        save_user_transaction(user_id, transaction_data)
        
        # Add subcategory to category dictionary if it's not there already
        cat_dict = read_dictionary(user_id)
        if category in cat_dict and subcategory not in cat_dict[category]:
            add_category(user_id, category, subcategory)
        
        # Inform user about successful save
        await query.edit_message_text(
            texts.TRANSACTION_CONFIRMED,
            parse_mode=ParseMode.HTML
        )
        
        # Show main menu
        # reply_markup = create_main_menu_keyboard(texts)
        # await query.message.reply_text(
        #     texts.MAIN_MENU_TEXT,
        #     reply_markup=reply_markup,
        #     parse_mode=ParseMode.HTML
        # )
        
        # Check if we need to show limit warnings
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
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"Exception calculating limit: {e}")
        
        return TRANSACTION
    
    elif action == "cancel_transaction":
        await query.edit_message_text(
            texts.TRANSACTION_CANCELED,
            parse_mode=ParseMode.HTML
        )
        # Show main menu
        # reply_markup = create_main_menu_keyboard(texts)
        # await query.message.reply_text(
        #     texts.MAIN_MENU_TEXT,
        #     reply_markup=reply_markup,
        #     parse_mode=ParseMode.HTML
        # )
        return TRANSACTION
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return CONFIRM_TRANSACTION 