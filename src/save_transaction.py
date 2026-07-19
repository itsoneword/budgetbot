import logging
from typing import Any, Dict, Optional
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode
import asyncio
from datetime import datetime, timezone
import re

# Database integration
from shared.di import get_repos

# Domain layer for limit calculation
from domain.session_loader import load_user_session
from domain.filters import calculate_limit_usage
from domain.validation import resolve_backdated_year

# file_ops imports removed - using PostgreSQL repositories instead
from src.language_util import check_language, get_cached_currency, ensure_user_config_cached
from src.keyboards import (
    create_main_menu_keyboard, create_category_keyboard, 
    create_found_category_keyboard,
    create_multiple_categories_keyboard, create_subcategories_keyboard,
    create_amounts_keyboard, create_confirm_transaction_keyboard,
    create_tx_categories_keyboard
)
# Removed: process_transaction_input moved here as async version using PostgreSQL
# pandas_ops imports removed - using language_util and domain.filters instead
# Import states from central states file
from src.states import *

logger = logging.getLogger(__name__)


async def _save_transaction_to_db(context: CallbackContext, user_id: int, transaction_data: dict) -> int:
    """
    Helper function to save a transaction to PostgreSQL.
    Returns the transaction ID.
    """
    repos = get_repos(context)
    config = await repos.users.get_config(user_id)

    # Honor the timestamp parsed from a "dd.mm" prefix (T-033); default to now.
    timestamp = transaction_data.get("timestamp")
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        except ValueError:
            timestamp = None
    if not isinstance(timestamp, datetime):
        timestamp = datetime.now(timezone.utc)

    tx_id = await repos.transactions.save_spending(
        user_id=user_id,
        category=transaction_data.get("category", ""),
        subcategory=transaction_data.get("subcategory", ""),
        amount=float(transaction_data.get("amount", 0)),
        currency=transaction_data.get("currency", config.currency if config else "EUR"),
        timestamp=timestamp,
    )
    
    # Also update category dictionary if needed
    category = transaction_data.get("category", "")
    subcategory = transaction_data.get("subcategory", "")
    if category and subcategory:
        language = config.language if config else 'en'
        await repos.categories.add_category(user_id, category, subcategory, language)
    
    return tx_id


def process_income_input(user_id, parts: list) -> tuple:
    """
    Process income input text and extract timestamp and category.
    Pure parsing function - no file I/O.
    
    Args:
        user_id: User ID (not used, kept for API compatibility)
        parts: List of input text parts (split by space)
    
    Returns:
        tuple: (timestamp, category)
    """
    # user_id not used in this function, but kept for API compatibility
    timestamp = datetime.now(timezone.utc)
    category = "salary"  # Default category for income

    if len(parts) == 3:
        # Format: date category amount OR category something amount
        parsed = _parse_income_date(parts[0])
        if parsed:
            timestamp = parsed
            category = parts[1]
        else:
            category = parts[0]
    elif len(parts) == 2:
        # Format: date amount OR category amount
        parsed = _parse_income_date(parts[0])
        if parsed:
            timestamp = parsed
        else:
            category = parts[0]

    return timestamp, category


def _parse_income_date(text: str) -> Optional[datetime]:
    """
    Parse a date token from income input; None if it isn't a date.
    When the year was not given explicitly (dd.mm), a future result means the
    user was backfilling — roll back one year (T-033). Explicit future years
    are left alone here and caught by the save-path clamp.
    """
    from dateutil.parser import parse, ParserError

    now = datetime.now(timezone.utc)

    # "dd.mm" first — dateutil mangles it (reads "31.12" as day 31 of the
    # *default* month, discarding the month), so parse it explicitly.
    try:
        ddmm = datetime.strptime(f"{now.year}-{text}", "%Y-%d.%m")
        return resolve_backdated_year(ddmm.replace(tzinfo=timezone.utc), now)
    except ValueError:
        pass

    today = datetime(now.year, now.month, now.day)
    try:
        parsed = parse(text, dayfirst=True, default=today)
        # Re-parse with a different default year: if the result changes, the
        # input had no explicit year and the current year was assumed.
        year_was_assumed = parse(
            text, dayfirst=True, default=today.replace(year=now.year - 4)
        ).year != parsed.year
    except (ValueError, OverflowError, ParserError):
        return None

    parsed = parsed.replace(tzinfo=timezone.utc)
    if year_was_assumed:
        parsed = resolve_backdated_year(parsed, now)
    return parsed


def _parse_date_to_utc(mdate: str) -> str:
    """
    Parse a date string in 'dd.mm' format and convert to UTC ISO format.
    Tries the current year first; if that lands in the future the user was
    backfilling and meant the previous year (T-033).
    """
    current_year = datetime.now(timezone.utc).year
    date_obj = datetime.strptime(f"{current_year}-{mdate}", "%Y-%d.%m")
    date_obj = resolve_backdated_year(date_obj.replace(tzinfo=timezone.utc))
    return date_obj.strftime("%Y-%m-%dT%H:%M:%S")


async def process_transaction_input_async(
    user_id,  # int or str - will be converted
    parts: list,
    repos,
    language: str = 'en'
) -> tuple:
    """
    Process transaction input text and extract structured data.
    Uses PostgreSQL repositories for category lookup.
    
    Args:
        user_id: User ID (int or str - will be converted to int)
        parts: List of input text parts (split by space)
        repos: Repository container with categories access
        language: User's language for category lookup
    
    Returns:
        tuple: (timestamp, category, subcategory, unknown_cat)
    """
    # Ensure user_id is int for PostgreSQL
    user_id = int(user_id)
    
    subcategory = " ".join(parts[:-1])  # Everything except the amount
    category = None
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    
    if len(parts) > 2:
        # Check if first part looks like a date (starts and ends with digit)
        if parts[0][0].isdigit() and parts[0][-1].isdigit():
            try:
                timestamp = _parse_date_to_utc(parts[0])
            except Exception:
                pass
            
            if len(parts) > 3:
                # Format: date category subcategory amount
                category = parts[1]
                subcategory = parts[2]
            else:
                # Format: date subcategory amount
                subcategory = parts[1]
                # Look up category from PostgreSQL
                categories = await repos.categories.find_category_by_subcategory(
                    user_id, subcategory, language
                )
                category = categories[0] if categories else None
        else:
            # Format: category subcategory amount
            category = parts[0]
            subcategory = parts[1]
            # Add the category:subcategory mapping to PostgreSQL
            await repos.categories.add_subcategory(user_id, category, subcategory, language)
    else:
        # Format: subcategory amount (short format)
        category = None
        subcategory = parts[0]
    
    # If category still not found, look it up from PostgreSQL
    if category is None:
        categories = await repos.categories.find_category_by_subcategory(
            user_id, subcategory, language
        )
        category = categories[0] if categories else None
    
    # Default to "other" if no category found
    if category is None:
        category = "other"
        unknown_cat = True
    else:
        unknown_cat = False
    
    return timestamp, category, subcategory, unknown_cat


async def _check_and_show_limit_warning(update_or_query, context: CallbackContext, user_id: int, texts) -> None:
    """
    Check if spending limit is exceeded and show warning if necessary.
    Uses domain.filters.calculate_limit_usage() with data from PostgreSQL.
    
    Args:
        update_or_query: Either Update object (has message) or CallbackQuery (use message attribute)
        context: CallbackContext to access repos and cached config
        user_id: User ID to check limits for
        texts: Texts module for localized messages
    """
    from domain.session_loader import load_user_session
    from domain.filters import calculate_limit_usage
    from decimal import Decimal
    from src.language_util import get_cached_currency, get_cached_monthly_limit
    
    try:
        repos = get_repos(context)
        
        # Get cached monthly limit, or fetch if not cached
        monthly_limit = get_cached_monthly_limit(context)
        if monthly_limit is None:
            config = await repos.users.get_config(user_id)
            monthly_limit = config.monthly_limit if config else Decimal('99999999.00')
        
        # Load current month transactions
        session = await load_user_session(
            user_id, repos,
            load_transactions=True,
            transactions_months=1,
            transaction_type='spending'
        )
        
        # Calculate limit usage
        limit_info = calculate_limit_usage(
            transactions=session.transactions,
            monthly_limit=monthly_limit
        )
        
        if limit_info['exceeded']:
            currency = get_cached_currency(context)
            
            # Determine how to send message
            if hasattr(update_or_query, 'message') and update_or_query.message:
                reply_func = update_or_query.message.reply_text
            elif hasattr(update_or_query, 'effective_message') and update_or_query.effective_message:
                reply_func = update_or_query.effective_message.reply_text
            else:
                return  # Can't send message
            
            await reply_func(
                texts.LIMIT_EXCEEDED.format(
                    percent_difference=limit_info['percent_difference'],
                    current_daily_average=limit_info['current_daily_average'],
                    daily_limit=limit_info['daily_limit'],
                    days_zero_spending=limit_info['days_zero_spending'],
                    new_daily_limit=limit_info['new_daily_limit'],
                    currency=currency,
                ),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.exception("Exception calculating limit")


async def save_transaction(update: Update, context):
    """Process a transaction from a user's text input"""
    logger.debug(f"Fn save_transaction")
    user_id =update.effective_user.id
    texts = check_language(update, context)
    
    # Extract the text from the update
    text = update.message.text
    
    # Clean up excess spaces in the input
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Process all lines separately (multi-transaction support)
    lines = text.strip().split("\n") if "\n" in text else text.strip().split(",")
    
    # Store the transactions in context for later processing
    if len(lines) > 1:
        logger.debug(f"Condition multi-line transaction input")
        # This is a multi-line transaction input
        context.user_data["all_transactions"] = lines
        context.user_data["current_transaction_index"] = 0
        await update.message.reply_text(
            texts.MULTI_TRANSACTION_START.format(len(lines))
        )
        logger.debug(f"Return process_next_transaction")
        return await process_next_transaction(update, context)
    
    # Single transaction processing
    parts = text.lower().split()
    
    # Process the input to get structured data (async with PostgreSQL lookup)
    repos = get_repos(context)
    language = context.user_data.get('cached_language', 'en')
    timestamp, category, subcategory, unknown_cat = await process_transaction_input_async(
        user_id, parts, repos, language
    )
    
    # Extract the amount, assuming it's the last part
    try:
        amount = float(parts[-1])
    except ValueError:
        logger.debug(f"Condition invalid amount format")
        await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        logger.debug(f"Return TRANSACTION")
        return TRANSACTION
    
    # Check if this is a short format input (only subcategory and amount)
    is_short_format = len(parts) == 2
    
    # Prepare transaction data
    transaction_data = {
        "id": user_id,
        "amount": amount,
        "currency": get_cached_currency(context),
        "subcategory": subcategory,
        "timestamp": timestamp,
    }
    
    # Store data in context for later use if needed
    context.user_data["transaction_data"] = transaction_data
    context.user_data["subcategory"] = subcategory
    context.user_data["is_multi_transaction"] = False  # Flag for single transaction
    
    # If category is known and it's not a short format input, save directly
    if not unknown_cat and not is_short_format:
        logger.debug(f"Condition category known and not short format")
        transaction_data["category"] = category
        await _save_transaction_to_db(context, int(user_id), transaction_data)
        
        # For single transactions that successfully save, show menu at the end
        await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)

        logger.debug(f"Return TRANSACTION (single transaction saved directly)")
        return TRANSACTION
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        logger.debug(f"Condition short format input")
        # Get all categories where this subcategory exists from PostgreSQL
        repos = get_repos(context)
        language = context.user_data.get('language', 'en')
        cat_dict = await repos.categories.get_dictionary(int(user_id), language)
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
            logger.debug(f"Condition subcategory not found in any category")
            # Create an inline keyboard with pagination for all categories
            reply_markup = create_category_keyboard(all_categories, 0, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_NOT_FOUND.format(subcategory),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            logger.debug(f"Return TX_CHOOSE_CATEGORY (showing category selection)")
            return TX_CHOOSE_CATEGORY
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            logger.debug(f"Condition subcategory found in exactly one category")
            found_category = matching_categories[0]
            context.user_data["found_category"] = found_category
            
            # Create keyboard with options to use the found category or choose another
            reply_markup = create_found_category_keyboard(found_category, texts)
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_ONE.format(subcategory, found_category),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            logger.debug(f"Return TX_CHOOSE_CATEGORY (showing found category)")
            return TX_CHOOSE_CATEGORY
        
        # Case 3: Subcategory found in multiple categories
        else:
            logger.debug(f"Condition subcategory found in multiple categories")
            # Create keyboard with the matching categories
            reply_markup = create_multiple_categories_keyboard(matching_categories, texts)
            
            # Format the list of matching categories for the message
            cat_list = ", ".join([f"<code>{cat}</code>" for cat in matching_categories])
            
            await update.message.reply_text(
                texts.SUBCAT_FOUND_MULTIPLE.format(subcategory, cat_list),
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            logger.debug(f"Return TX_CHOOSE_CATEGORY (showing multiple categories)")
            return TX_CHOOSE_CATEGORY
    
    # For unknown subcategories (should not reach here with our new logic but kept for safety)
    logger.debug(f"Condition handling unknown subcategory case")
    reply_markup = create_category_keyboard(context.user_data.get("all_categories", []), context.user_data.get("current_page", 0), texts)
    
    await update.message.reply_text(
        texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    logger.debug(f"Return TX_CHOOSE_CATEGORY (showing category selection)")
    return TX_CHOOSE_CATEGORY

async def process_next_transaction(update: Update, context: CallbackContext) -> int:
    """Process the next transaction in a multi-transaction sequence or show main menu"""
    logger.debug(f"Fn process_next_transaction")
    user_id =update.effective_user.id
    texts = check_language(update, context)
    
    # Get stored transactions and current index
    all_transactions = context.user_data.get("all_transactions", [])
    current_index = context.user_data.get("current_transaction_index", 0)
    
    # Check if we've processed all transactions
    if current_index >= len(all_transactions):
        logger.debug(f"Condition all transactions processed")
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
        logger.debug(f"Return TRANSACTION (all transactions processed)")
        return TRANSACTION
    
    # Get the current transaction to process
    transaction = all_transactions[current_index]
    parts = transaction.lower().split()
    
    # Skip empty transactions
    if not parts:
        logger.debug(f"Condition empty transaction")
        # Increment the index and process the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        logger.debug(f"Return process_next_transaction (skipping empty transaction)")
        return await process_next_transaction(update, context)
    
    try:
        amount = float(parts[-1])
    except ValueError:
        logger.debug(f"Condition invalid transaction format")
        # Invalid transaction format, skip it
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Notify user about invalid format and move to next transaction
        if update.callback_query:
            await update.callback_query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        else:
            await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        
        logger.debug(f"Return process_next_transaction (skipping invalid transaction)")
        return await process_next_transaction(update, context)
    
    # Process the current transaction (async with PostgreSQL lookup)
    repos = get_repos(context)
    language = context.user_data.get('cached_language', 'en')
    timestamp, category, subcategory, unknown_cat = await process_transaction_input_async(
        user_id, parts, repos, language
    )
    
    # Check if this is a short format input (only subcategory and amount)
    is_short_format = len(parts) == 2
    
    transaction_data = {
        "id": user_id,
        "amount": amount,
        "currency": get_cached_currency(context),
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
        logger.debug(f"Condition category known and not short format in multi-transaction")
        transaction_data["category"] = category
        await _save_transaction_to_db(context, int(user_id), transaction_data)
        
        # Increment the index for the next transaction
        context.user_data["current_transaction_index"] = current_index + 1
        
        # Show progress message
        progress_msg = texts.PROGRESS_MSG.format(current_index+1, len(all_transactions), subcategory, amount)
        if update.callback_query:
            await update.callback_query.message.reply_text(progress_msg)
        else:
            await update.message.reply_text(progress_msg)
        
        # Process the next transaction
        logger.debug(f"Return process_next_transaction (moving to next transaction)")
        return await process_next_transaction(update, context)
    
    # Handle short format inputs with different behavior based on category matches
    if is_short_format:
        logger.debug(f"Condition short format input in multi-transaction")
        # Get all categories where this subcategory exists from PostgreSQL
        repos = get_repos(context)
        language = context.user_data.get('language', 'en')
        cat_dict = await repos.categories.get_dictionary(int(user_id), language)
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
            logger.debug(f"Condition subcategory not found in any category in multi-transaction")
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
            logger.debug(f"Return TRANSACTION (showing category selection in multi-transaction)")
            return TX_CHOOSE_CATEGORY
        
        # Case 2: Subcategory found in exactly one category
        elif len(matching_categories) == 1:
            logger.debug(f"Condition subcategory found in exactly one category in multi-transaction")
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
            logger.debug(f"Return TRANSACTION (showing found category in multi-transaction)")
            return TRANSACTION
        
        # Case 3: Subcategory found in multiple categories
        else:
            logger.debug(f"Condition subcategory found in multiple categories in multi-transaction")
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
            logger.debug(f"Return TRANSACTION (showing multiple categories in multi-transaction)")
            return TRANSACTION
    
    # For unknown subcategories
    logger.debug(f"Condition unknown subcategory in multi-transaction")
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
    
    logger.debug(f"Return TRANSACTION (showing category selection for unknown subcategory)")
    return TRANSACTION

async def create_new_category_transaction(update: Update, context: CallbackContext) -> int:
    """Handle creating a new category during transaction input flow"""
    logger.debug(f"Fn create_new_category_transaction")
    user_id =update.effective_user.id
    texts = check_language(update, context)
    
    # Get the new category name from the user's message
    new_category = update.message.text.lower().strip()
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")
    
    if not subcategory or not transaction_data:
        logger.debug(f"Condition missing transaction data")
        await update.message.reply_text("Error: transaction data not found.")
        logger.debug(f"Return TRANSACTION (missing transaction data)")
        return TRANSACTION
    
    # Update the transaction data with the new category
    transaction_data["category"] = new_category
    
    # Save the transaction
    await _save_transaction_to_db(context, int(user_id), transaction_data)
    
    # Inform the user
    await update.message.reply_text(
        texts.CONFIRM_SAVE_CAT.format(new_category, subcategory),
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)
    
    # Check if this is part of a multi-transaction process
    if context.user_data.get("is_multi_transaction", False):
        logger.debug(f"Condition multi-transaction process")
        # Increment the index and move to the next transaction
        context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
        await asyncio.sleep(1)  # Small delay for user to read confirmation
        logger.debug(f"Return process_next_transaction (moving to next transaction)")
        return await process_next_transaction(update, context)
    
    # For single transactions, show main menu
    reply_markup = create_main_menu_keyboard(texts)
    await update.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Check if we need to show limit warnings
    await _check_and_show_limit_warning(update, context, int(user_id), texts)
    
    logger.debug(f"Return TRANSACTION (single transaction completed)")
    return TRANSACTION

async def select_category_for_transaction(update: Update, context: CallbackContext) -> int:
    """Handle category selection for a transaction"""
    user_id =update.effective_user.id
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
        logger.debug(f"Condition use_found_category")
        category = query.data[4:]  # Remove "use_" prefix
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            logger.debug(f"Condition missing transaction data")
            await query.edit_message_text("Error: transaction data not found.")
            logger.debug(f"Return TRANSACTION (missing transaction data)")
            return TRANSACTION
        
        # Update the transaction data with the selected category
        transaction_data["category"] = category
        
        # Save the transaction with the selected category
        await _save_transaction_to_db(context, int(user_id), transaction_data)
        
        # Inform the user with an edit first
        await query.edit_message_text(
            texts.CONFIRM_SAVE_CAT.format(category, subcategory),
            parse_mode=ParseMode.HTML
        )
        
        # Check if this is part of a multi-transaction process
        if context.user_data.get("is_multi_transaction", False):
            logger.debug(f"Condition multi-transaction process")
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            logger.debug(f"Return process_next_transaction (moving to next transaction)")
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
        await _check_and_show_limit_warning(query, context, int(user_id), texts)
        
        logger.debug(f"Return TRANSACTION (single transaction completed)")
        return TRANSACTION
    
    # Extract the category from the callback data (standard cat_[category] button)
    elif query.data.startswith("cat_"):
        logger.debug(f"Condition cat_category_selection")
        category = query.data.replace("cat_", "")
        subcategory = context.user_data.get("subcategory")
        transaction_data = context.user_data.get("transaction_data")
        
        if not subcategory or not transaction_data:
            logger.debug(f"Condition missing transaction data")
            await query.edit_message_text("Error: transaction data not found.")
            logger.debug(f"Return TRANSACTION (missing transaction data)")
            return TRANSACTION
        
        # Update the transaction data with the selected category
        transaction_data["category"] = category
        
        # Save the transaction with the selected category
        await _save_transaction_to_db(context, int(user_id), transaction_data)
        
        # Inform the user with an edit first
        await query.edit_message_text(
            texts.CONFIRM_SAVE_CAT.format(category, subcategory),
            parse_mode=ParseMode.HTML
        )
        
        # Check if this is part of a multi-transaction process
        if context.user_data.get("is_multi_transaction", False):
            logger.debug(f"Condition multi-transaction process")
            # Increment the index and move to the next transaction
            context.user_data["current_transaction_index"] = context.user_data.get("current_transaction_index", 0) + 1
            await asyncio.sleep(1)  # Small delay for user to read confirmation
            logger.debug(f"Return process_next_transaction (moving to next transaction)")
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
        await _check_and_show_limit_warning(query, context, int(user_id), texts)
        
        logger.debug(f"Return TRANSACTION (single transaction completed)")
        return TRANSACTION
        
    else:
        logger.debug(f"Condition unexpected callback data")
        # Unexpected callback data
        await query.edit_message_text(
            "Error: Unexpected callback data received. Please try again.",
            parse_mode=ParseMode.HTML
        )
        logger.debug(f"Return TRANSACTION (error handling) {TRANSACTION}")

        return TRANSACTION 

async def handle_transaction_category(update: Update, context: CallbackContext):
    """Handle category selection for transaction entry"""
    logger.debug(f"Fn handle_transaction_category")
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    action = query.data
    
    # Handle page navigation
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')

    if action == "txpage_prev":
        logger.debug(f"Condition txpage_prev")
        context.user_data["tx_page"] -= 1
        categories = await repos.categories.get_all_categories(user_id, language)
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await query.edit_message_text(
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return SELECT_TRANSACTION_CATEGORY

    elif action == "txpage_next":
        context.user_data["tx_page"] += 1
        categories = await repos.categories.get_all_categories(user_id, language)
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

        # Get subcategories for this category from PostgreSQL
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        
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
        logger.debug("Returning state SELECT_TRANSACTION_SUBCATEGORY")
        return SELECT_TRANSACTION_SUBCATEGORY
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return SELECT_TRANSACTION_CATEGORY

async def handle_transaction_subcategory(update: Update, context: CallbackContext):
    """Handle subcategory selection or manual entry for transaction"""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
    language = context.user_data.get('cached_language', 'en')
    
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
            categories = await repos.categories.get_all_categories(user_id, language)
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
            category = context.user_data.get("tx_category", "")

            # Store selected subcategory in context
            context.user_data["tx_subcategory"] = subcategory

            # Get recent amounts for this category/subcategory from PostgreSQL
            amounts = await repos.transactions.get_recent_amounts(user_id, category, subcategory, limit=5)

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
            currency = get_cached_currency(context)
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
    user_id =update.effective_user.id
    texts = check_language(update, context)
    repos = get_repos(context)
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
            currency = get_cached_currency(context)
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
            currency = get_cached_currency(context)
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
    user_id = update.effective_user.id  # Use int, not str
    texts = check_language(update, context)
    action = query.data
    
    if action == "confirm_transaction":
        # Get transaction details from context
        category = context.user_data.get("tx_category", "")
        subcategory = context.user_data.get("tx_subcategory", "")
        amount = context.user_data.get("tx_amount", 0)
        
        # Get user config for currency
        repos = get_repos(context)
        config = await repos.users.get_config(user_id)
        currency = config.currency if config else "EUR"
        
        # Prepare transaction data
        transaction_data = {
            "category": category,
            "subcategory": subcategory,
            "amount": amount,
            "currency": currency,
        }
        
        # Save transaction to database using helper
        await _save_transaction_to_db(context, user_id, transaction_data)
        
        # Inform user about successful save
        await query.edit_message_text(
            texts.TRANSACTION_CONFIRMED,
            parse_mode=ParseMode.HTML
        )
        
        # Check if we need to show limit warnings (using domain layer)
        if config and config.monthly_limit:
            try:
                # Load fresh session to include the just-saved transaction
                session = await load_user_session(user_id, repos, transactions_months=1)
                limit_data = calculate_limit_usage(
                    session.transactions, session.monthly_limit
                )

                if limit_data['exceeded']:
                    await query.message.reply_text(
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
                logger.exception("Exception calculating limit")
        
        return TRANSACTION
    
    elif action == "cancel_transaction":
        await query.edit_message_text(
            texts.TRANSACTION_CANCELED,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return CONFIRM_TRANSACTION 