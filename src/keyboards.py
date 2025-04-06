from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from language_util import check_language
import sys

def create_language_keyboard():
    """Create a keyboard for language selection"""
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Русский", callback_data="ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# def create_currency_keyboard(texts=None):
#     """Create a keyboard for currency selection"""
#     keyboard = [
#         [
#             InlineKeyboardButton("USD", callback_data="USD"),
#             InlineKeyboardButton("EUR", callback_data="EUR"),
#             InlineKeyboardButton("AMD", callback_data="AMD"),
#             InlineKeyboardButton("RUB", callback_data="RUB"),
#             InlineKeyboardButton("THB", callback_data="THB"),

#         ],
#     ]
#     return InlineKeyboardMarkup(keyboard)

def create_skip_keyboard(texts):
    """Create a keyboard with just a skip button"""
    keyboard = [[InlineKeyboardButton(texts.SKIP_BUTTON, callback_data="skip")]]
    return InlineKeyboardMarkup(keyboard)

def create_settings_keyboard(texts):
    """Create a keyboard for settings options"""
    keyboard = [
        [
            InlineKeyboardButton(texts.CHANGE_LANGUAGE_BUTTON, callback_data="change_language"),
            InlineKeyboardButton(texts.CHANGE_CURRENCY_BUTTON, callback_data="change_currency"),
        ],
        [InlineKeyboardButton(texts.CHANGE_LIMIT_BUTTON, callback_data="change_limit")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_category_keyboard(categories, current_page, texts, items_per_page=5):
    """
    Create a paginated inline keyboard for selecting categories.
    
    Args:
        categories: List of all categories
        current_page: Current page number (0-based)
        texts: The texts module with localized strings
        items_per_page: Number of categories to show per page
        
    Returns:
        InlineKeyboardMarkup: Keyboard with category buttons
    """
    #print("DEBUG: Creating category keyboard")
    keyboard = []
    
    # Calculate start and end indices for categories on current page
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    #print(f"DEBUG: Page {current_page}, showing categories from index {start_idx} to {end_idx-1}")
    
    # Add category buttons for current page
    for cat in categories[start_idx:end_idx]:
        #print(f"DEBUG: Adding category button for '{cat}'")
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
    
    # Add navigation buttons
    nav_buttons = []
    
    # Add previous page button if not on first page
    if current_page > 0:
        #print(f"DEBUG: Adding 'Back' button for page navigation")
        nav_buttons.append(InlineKeyboardButton(texts.BACK_BUTTON, callback_data="page_prev"))
    
    # Add next page button if not on last page
    if end_idx < len(categories):
        #print(f"DEBUG: Adding 'Next' button for page navigation")
        nav_buttons.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="page_next"))
    
    # Add navigation row if there are any navigation buttons
    if nav_buttons:
        #print(f"DEBUG: Adding navigation row with {len(nav_buttons)} buttons")
        keyboard.append(nav_buttons)
    
    # Add option to create a new category
    #print("DEBUG: Adding 'Create new category' button")
    keyboard.append([InlineKeyboardButton(texts.CREATE_CATEGORY_BUTTON, callback_data="create_new_category")])
    
    #print("DEBUG: Adding 'Cancel' button")
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="cancel_transaction")])
    
    #print(f"DEBUG: Completed keyboard with {len(keyboard)} rows")
    return InlineKeyboardMarkup(keyboard)

def create_found_category_keyboard(found_category, texts):
    """Create a keyboard for when a category is found for a subcategory"""
    keyboard = [
        [InlineKeyboardButton(texts.USE_CATEGORY_BUTTON.format(found_category), callback_data=f"use_{found_category}")],
        [InlineKeyboardButton(texts.CHOOSE_OTHER_CATEGORY_BUTTON, callback_data="show_all_categories")],
        [InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel_transaction")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_multiple_categories_keyboard(matching_categories, texts):
    """Create a keyboard for selecting from multiple matching categories"""
    keyboard = []
    for cat in matching_categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
    
    # Add option to see all categories
    keyboard.append([InlineKeyboardButton(texts.SHOW_ALL_CATEGORIES_BUTTON, callback_data="show_all_categories")])
    keyboard.append([InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel_transaction")])
    
    return InlineKeyboardMarkup(keyboard)

def create_all_categories_keyboard(all_categories, current_page, texts):
    """Create a keyboard with all categories and a cancel button"""
    #print("DEBUG: Creating all categories keyboard")
    keyboard = create_category_keyboard(all_categories, current_page, texts)
    #print(f"DEBUG: Got keyboard with {len(keyboard.inline_keyboard)} rows")
    # Add cancel button to the list of buttons
    #print("DEBUG: Adding cancel button to keyboard")
    # keyboard.inline_keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_transaction")])
    #print(f"DEBUG: Final keyboard has {len(keyboard.inline_keyboard)} rows")
    return keyboard

def create_settings_language_keyboard():
    """Create a keyboard specifically for language settings with lang_ prefixed callbacks"""
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_settings_currency_keyboard():
    """Create a keyboard specifically for currency settings with cur_ prefixed callbacks"""
    keyboard = [
        [
            InlineKeyboardButton("USD", callback_data="cur_USD"),
            InlineKeyboardButton("EUR", callback_data="cur_EUR"),
            InlineKeyboardButton("AMD", callback_data="cur_AMD"),
            InlineKeyboardButton("RUB", callback_data="cur_RUB"),
            InlineKeyboardButton("THB", callback_data="cur_THB"),

        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_main_menu_keyboard(texts):
    """Create the main menu keyboard"""
    #print("DEBUG: Creating main menu keyboard with texts module:", texts)
    keyboard = [
        [
            InlineKeyboardButton(texts.ADD_TRANSACTION_BUTTON, callback_data="menu_add_transaction"),
            InlineKeyboardButton(texts.SHOW_TRANSACTIONS_BUTTON, callback_data="menu_show_transactions")
        ],
        [
            InlineKeyboardButton(texts.EDIT_CATEGORIES_BUTTON, callback_data="menu_edit_categories"),
            InlineKeyboardButton(texts.EDIT_TRANSACTIONS_BUTTON, callback_data="menu_edit_transactions")
        ],
        [
            InlineKeyboardButton(texts.SETTINGS_BUTTON, callback_data="menu_settings"),

            InlineKeyboardButton(texts.HELP_BUTTON, callback_data="menu_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_show_transactions_keyboard(texts):
    """Create a keyboard for the show transactions submenu"""
    keyboard = [
        [
            InlineKeyboardButton(texts.MONTHLY_SUMMARY_BUTTON, callback_data="show_monthly_summary"),
            InlineKeyboardButton(texts.LAST_MONTH_SUMMARY_BUTTON, callback_data="show_last_month_summary"),
        ],
        [
            InlineKeyboardButton(texts.DETAILED_STAT_BUTTON, callback_data="show_extended_stats"),
            InlineKeyboardButton(texts.LAST_TRANSACTIONS_BUTTON, callback_data="show_last_transactions"),
        ],
        [
            InlineKeyboardButton(texts.YEARLY_CHARTS_BUTTON, callback_data="show_yearly_charts"),
            InlineKeyboardButton(texts.MONTHLY_CHARTS_BUTTON, callback_data="show_monthly_charts")

        ],
        [
            InlineKeyboardButton(texts.INCOME_STATS_BUTTON, callback_data="show_income_stats")
        ],
        [
            InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_settings_keyboard_menu(texts):
    """Create a keyboard for the settings submenu"""
    keyboard = [
        [
            InlineKeyboardButton(texts.CHANGE_LANGUAGE_BUTTON, callback_data="settings_change_language"),
            InlineKeyboardButton(texts.CHANGE_CURRENCY_BUTTON, callback_data="settings_change_currency")
        ],
        [
            InlineKeyboardButton(texts.CHANGE_LIMIT_BUTTON, callback_data="settings_change_limit"),
            InlineKeyboardButton(texts.ABOUT_BUTTON, callback_data="settings_about")
        ],
        [
            InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_edit_categories_keyboard(texts):
    """Create a keyboard for the edit categories submenu"""
    keyboard = [
        [
            InlineKeyboardButton(texts.SHOW_CATEGORIES_BUTTON, callback_data="edit_show_categories"),
            InlineKeyboardButton(texts.ADD_REMOVE_CATEGORY_BUTTON, callback_data="edit_add_remove_category")
        ],
        [
            InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_records_count_keyboard(texts):
    """Create keyboard with record count options"""
    keyboard = [
        [
            InlineKeyboardButton("5", callback_data="count_5"),
            InlineKeyboardButton("10", callback_data="count_10"),
        ],
        [
            InlineKeyboardButton("15", callback_data="count_15"),
            InlineKeyboardButton("20", callback_data="count_20"),
        ],
        [
            InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_transactions"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_tx_categories_keyboard(categories, texts, page=0, items_per_page=8):
    """Create a keyboard with categories for transaction entry"""
    keyboard = []
    
    # Calculate pagination
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    
    # Create buttons for categories, 2 per row
    for i in range(start_idx, end_idx, 2):
        row = []
        # Add the first category button
        row.append(InlineKeyboardButton(categories[i], callback_data=f"txcat_{categories[i]}"))
        
        # Add the second category button if available
        if i + 1 < end_idx:
            row.append(InlineKeyboardButton(categories[i+1], callback_data=f"txcat_{categories[i+1]}"))
        
        keyboard.append(row)
    # Add pagination controls if needed
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="txpage_prev"))
    if end_idx < len(categories):
        pagination_row.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="txpage_next"))
    
    if pagination_row:
        keyboard.append(pagination_row)
    # Add cancel button
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="cancel_transaction")])
    
    return InlineKeyboardMarkup(keyboard)

def create_subcategories_keyboard(subcategories, category, page=0, texts=None, items_per_page=8):
    """Create a keyboard with subcategories for transaction entry"""
    keyboard = []
    
    # Calculate pagination
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(subcategories))
    
    # Create buttons for subcategories, 2 per row
    for i in range(start_idx, end_idx, 2):
        row = []
        # Add the first subcategory button
        row.append(InlineKeyboardButton(subcategories[i], callback_data=f"txsubcat_{subcategories[i]}"))
        
        # Add the second subcategory button if available
        if i + 1 < end_idx:
            row.append(InlineKeyboardButton(subcategories[i+1], callback_data=f"txsubcat_{subcategories[i+1]}"))
        
        keyboard.append(row)
    
    # Add pagination controls if needed
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="txsubpage_prev"))
    if end_idx < len(subcategories):
        pagination_row.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="txsubpage_next"))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Add back and cancel buttons
    keyboard.append([
        InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_categories"),
        InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel_transaction")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_amounts_keyboard(amounts, texts):
    """Create a keyboard with recent transaction amounts"""
    keyboard = []
    
    # Create buttons for amounts, 2 per row
    for i in range(0, len(amounts), 2):
        row = []
        # Add the first amount button
        row.append(InlineKeyboardButton(str(amounts[i]), callback_data=f"txamount_{amounts[i]}"))
        
        # Add the second amount button if available
        if i + 1 < len(amounts):
            row.append(InlineKeyboardButton(str(amounts[i+1]), callback_data=f"txamount_{amounts[i+1]}"))
        
        keyboard.append(row)
    
    # Add back and cancel buttons
    keyboard.append([
        InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_subcategories"),
        InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel_transaction")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_confirm_transaction_keyboard(texts):
    """Create a keyboard to confirm or cancel a transaction"""
    keyboard = [
        [
            InlineKeyboardButton(texts.CONFIRM_BUTTON, callback_data="confirm_transaction"),
            InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel_transaction")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_category_edit_keyboard(categories: list, texts):
    """Create a keyboard with category buttons in 2 columns for category editing"""
    keyboard = []
    row = []
    
    for i, category in enumerate(categories):
        row.append(InlineKeyboardButton(category, callback_data=f"cat_{category}"))
        
        # Create a new row after every 2 buttons
        if len(row) == 2 or i == len(categories) - 1:
            keyboard.append(row)
            row = []
    
    # Add new category button
    keyboard.append([InlineKeyboardButton(texts.CREATE_CATEGORY_BUTTON, callback_data="add_new_category")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def create_category_options_keyboard(category: str, texts):
    """Create a keyboard with options for the selected category"""
    keyboard = [
        [InlineKeyboardButton(texts.CHANGE_NAME_BUTTON, callback_data=f"change_name_{category}")],
        [InlineKeyboardButton(texts.DELETE_CATEGORY_BUTTON, callback_data=f"delete_category_{category}")],
        [InlineKeyboardButton(texts.EDIT_TASKS_BUTTON, callback_data=f"edit_tasks_{category}")],
        [InlineKeyboardButton(texts.BACK_TO_CATEGORIES_BUTTON, callback_data="back_to_categories")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_tasks_keyboard(tasks: list, category: str, texts):
    """Create a keyboard showing tasks (subcategories) for a category"""
    keyboard = []
    
    for task in tasks:
        keyboard.append(
            [InlineKeyboardButton(task, callback_data=f"task_{category}_{task}")]
        )
    
    # Add buttons to add new task or go back
    keyboard.append([InlineKeyboardButton(texts.ADD_NEW_TASK_BUTTON, callback_data=f"add_task_{category}")])
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_CATEGORY_BUTTON, callback_data=f"back_to_category_{category}")])
    
    return InlineKeyboardMarkup(keyboard)

def create_task_options_keyboard(category: str, task: str, texts):
    """Create a keyboard with options for the selected task"""
    keyboard = [
        [InlineKeyboardButton(texts.EDIT_TASK_BUTTON, callback_data=f"edit_task_{category}_{task}")],
        [InlineKeyboardButton(texts.DELETE_TASK_BUTTON, callback_data=f"delete_task_{category}_{task}")],
        [InlineKeyboardButton(texts.BACK_TO_TASKS_BUTTON, callback_data=f"back_to_tasks_{category}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_confirmation_keyboard(action: str, data: str, texts):
    """Create a confirmation keyboard for actions like delete or rename"""
    keyboard = [
        [InlineKeyboardButton(texts.CONFIRM_BUTTON, callback_data=f"confirm_{action}_{data}")],
        [InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data=f"cancel_{action}_{data}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_transaction_keyboard(transactions, page, texts, total_transactions=7):
    """Create a keyboard with transaction buttons"""
    keyboard = []
    
    # Add transaction buttons
    for i, tx in enumerate(transactions):
        # Parse the transaction string format: "index: timestamp, category, subcategory, amount, currency"
        parts = tx.split(', ')
        
        # Extract the parts we need
        index_part = parts[0].split(': ')[0]
        timestamp_part = parts[0].split(': ')[1]
        subcategory = parts[2]
        amount = parts[3]
        
        # Extract just the date portion from the timestamp (format typically: YYYY-MM-DDTHH:MM:SS)
        date_str = ""
        if "T" in timestamp_part:
            date_only = timestamp_part.split('T')[0]
            # Convert YYYY-MM-DD to DD.MM format
            try:
                year, month, day = date_only.split('-')
                date_str = f"{day}.{month} "
            except:
                date_str = ""
        
        # Create a short display text if the full text is too long
        label = f"{index_part}: {date_str}{subcategory} {amount}"
        if len(label) > 35:  # Limit button text length
            label = f"{index_part}: {date_str}{subcategory[:8]}... {amount}"
            
        keyboard.append([InlineKeyboardButton(label, callback_data=f"tx_{index_part}")])
    
    # Add navigation buttons
    nav_buttons = []
    
    # Only show prev button if not on first page
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="tx_prev_page"))
    
    # Only show next button if we have 10 transactions in the current page
    # This means there might be more to show on the next page
    if len(transactions) >= 8:
        nav_buttons.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="tx_next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add back to main menu button
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def create_transaction_edit_keyboard(transaction, texts):
    """Create a keyboard with options to edit a transaction"""
    keyboard = [
        [
            InlineKeyboardButton(texts.EDIT_DATE_BUTTON, callback_data="edit_date"),
            InlineKeyboardButton(texts.EDIT_AMOUNT_BUTTON, callback_data="edit_amount")
        ],
        [
            InlineKeyboardButton(texts.EDIT_CATEGORY_BUTTON, callback_data="edit_category"),
            InlineKeyboardButton(texts.EDIT_SUBCATEGORY_BUTTON, callback_data="edit_subcategory")
        ],
        [
            InlineKeyboardButton(texts.DELETE_TRANSACTION_BUTTON, callback_data="delete_transaction")
        ],
        [
            InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_transactions")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def create_transaction_confirmation_keyboard(texts):
    """Create a keyboard for confirming an action"""
    keyboard = [
        [
            InlineKeyboardButton(texts.CONFIRM_BUTTON, callback_data="confirm"),
            InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard) 