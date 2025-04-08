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

def create_category_keyboard(categories, current_page, texts, items_per_page=10):
    #print("DEBUG: Creating category keyboard")
    try:
        keyboard = []
        nav_buttons = []  # Define nav_buttons here
        
        # Calculate start and end indices for categories on current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(categories))
        # print(f"DEBUG: Page {current_page}, showing categories from index {start_idx} to {end_idx-1}")
        
        # Add category buttons for current page in 2 columns
        current_page_categories = categories[start_idx:end_idx]
        
        # Process categories in pairs for 2 columns
        for i in range(0, len(current_page_categories), 2):
            row = []
            # Add first category in the pair
            row.append(InlineKeyboardButton(current_page_categories[i], callback_data=f"cat_{current_page_categories[i]}"))
            
            # Add second category if it exists
            if i + 1 < len(current_page_categories):
                row.append(InlineKeyboardButton(current_page_categories[i+1], callback_data=f"cat_{current_page_categories[i+1]}"))
            
            keyboard.append(row)
        
        # Add previous page button if not on first page
        if current_page > 0:
            # print(f"DEBUG: Adding 'Back' button for page navigation")
            nav_buttons.append(InlineKeyboardButton(texts.BACK_BUTTON, callback_data="catpage_prev"))
        
        # Add next page button if not on last page
        if end_idx < len(categories):
            # print(f"DEBUG: Adding 'Next' button for page navigation")
            nav_buttons.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="catpage_next"))
        
        # Add navigation row if there are any navigation buttons
        if nav_buttons:
            # print(f"DEBUG: Adding navigation row with {len(nav_buttons)} buttons")
            keyboard.append(nav_buttons)
            
        # Add option to create a new category
        keyboard.append([InlineKeyboardButton(texts.CREATE_CATEGORY_BUTTON, callback_data="create_new_category")])
        
        # Add back button
        keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="cancel_transaction")])
        
        return InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        #print(f"DEBUG: ERROR in create_category_keyboard: {e}")
        # Return a simple fallback keyboard to not break the flow
        keyboard = [[InlineKeyboardButton("Error - Back to Menu", callback_data="back_to_main_menu")]]
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
        ],
        [
            InlineKeyboardButton(texts.YEARLY_CHARTS_BUTTON, callback_data="show_yearly_charts"),
            InlineKeyboardButton(texts.MONTHLY_CHARTS_BUTTON, callback_data="show_monthly_charts")

        ],
        [
            InlineKeyboardButton(texts.LAST_TRANSACTIONS_BUTTON, callback_data="show_last_transactions")

            # InlineKeyboardButton(texts.INCOME_STATS_BUTTON, callback_data="show_income_stats")
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

def create_category_edit_keyboard(categories: list, texts, current_page=0, items_per_page=16):
    """Create a keyboard with category buttons in 2 columns for category editing with pagination"""
    keyboard = []
    
    # Calculate start and end indices for current page
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    
    # Add category buttons, 2 per row
    for i in range(start_idx, end_idx, 2):
        row = []
        # Add first category button
        row.append(InlineKeyboardButton(categories[i], callback_data=f"cat_{categories[i]}"))
        
        # Add second category button if available
        if i + 1 < end_idx:
            row.append(InlineKeyboardButton(categories[i+1], callback_data=f"cat_{categories[i+1]}"))
        
        keyboard.append(row)
    
    # Add navigation buttons if needed
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="catpage_prev"))
        
    if end_idx < len(categories):
        nav_row.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="catpage_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
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

def create_tx_del_confirmation_keyboard(texts):
    """Create a keyboard for confirming an action"""
    keyboard = [
        [
            InlineKeyboardButton(texts.DELETE_TRANSACTION_BUTTON, callback_data="confirm"),
            InlineKeyboardButton(texts.CANCEL_BUTTON, callback_data="cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def create_category_selection_keyboard(categories, selected_categories, texts, current_page=0, items_per_page=16):
    """Create a keyboard with selectable categories for detailed stats"""
    keyboard = []
    
    # Calculate start and end indices for current page
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    
    # Add category buttons, 2 per row
    for i in range(start_idx, end_idx, 2):
        row = []
        # Add first category button with selection indicator
        category_text = categories[i]
        if category_text in selected_categories:
            category_text = f"✅ {category_text}"
        row.append(InlineKeyboardButton(category_text, callback_data=f"selcat_{categories[i]}"))
        
        # Add second category button if available
        if i + 1 < end_idx:
            category_text = categories[i+1]
            if category_text in selected_categories:
                category_text = f"✅ {category_text}"
            row.append(InlineKeyboardButton(category_text, callback_data=f"selcat_{categories[i+1]}"))
        
        keyboard.append(row)
    
    # Add navigation buttons if needed
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="selcatpage_prev"))
        
    if end_idx < len(categories):
        nav_row.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="selcatpage_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Add select all and continue buttons
    keyboard.append([
        InlineKeyboardButton(texts.SELECT_ALL_BUTTON, callback_data="selcat_all"),
        InlineKeyboardButton(texts.CONTINUE_BUTTON, callback_data="selcat_continue")
    ])
    
    # Add back button
    keyboard.append([InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_transactions")])
    
    return InlineKeyboardMarkup(keyboard)

def create_time_period_keyboard(texts):
    """Create a keyboard with time period options"""
    keyboard = [
        [
            InlineKeyboardButton(texts.THREE_MONTH_BUTTON, callback_data="period_3m"),
            InlineKeyboardButton(texts.SIX_MONTH_BUTTON, callback_data="period_6m")
        ],
        [
            InlineKeyboardButton(texts.TWELVE_MONTH_BUTTON, callback_data="period_12m"),
            InlineKeyboardButton(texts.YEAR_TO_DATE_BUTTON, callback_data="period_ytd")
        ],
        [InlineKeyboardButton(texts.BACK_BUTTON, callback_data="back_to_categories")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_detailed_transactions_keyboard(transactions, selected_categories, current_page, texts, items_per_page=15, total_count=None):
    """Create a keyboard with numbered buttons and navigation for detailed transactions view"""
    keyboard = []
    
    # Calculate the visible transactions range
    total_transactions = len(transactions)
    
    # Create number selection buttons, up to 5 buttons per row
    rows = []
    current_row = []
    
    # Create numbered buttons matching the display numbers (1-15)
    for i in range(1, total_transactions + 1):
        # For each visible transaction, create a button with its display number
        # Use the display number directly in the callback data
        current_row.append(InlineKeyboardButton(str(i), callback_data=f"dtx_display_{i}"))
        
        # Create rows with 5 buttons each
        if len(current_row) == 5:
            rows.append(current_row)
            current_row = []
    
    # Add any remaining buttons in the last row
    if current_row:
        rows.append(current_row)
    
    # Add all rows to the keyboard
    keyboard.extend(rows)
    
    # Add navigation buttons
    nav_buttons = []
    
    # Only show prev button if not on first page
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="dtx_prev_page"))
    
    # Only show next button if there are more transactions to show
    if total_count is not None and (current_page + 1) * items_per_page < total_count:
        nav_buttons.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="dtx_next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(texts.RETURN_BACK_BUTTON, callback_data="back_to_tx_list")])

    # Add back to main menu button
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def create_numbered_transaction_keyboard(transactions, current_page, total_transactions, texts, items_per_page=15):
    """Create a keyboard with numbered buttons for transaction selection"""
    keyboard = []
    
    # Create number selection buttons, up to 5 buttons per row
    rows = []
    current_row = []
    
    # Determine how many transactions are visible on the current page
    start_idx = current_page * items_per_page
    end_idx = max(start_idx + items_per_page, len(transactions))

    # Create numbered buttons for transaction selection (1-15 on first page, 1-15 on second page)
    for i in range(1, end_idx - start_idx + 1):
        #print(f"Debug: Keyboard - i: {i}")
        # Extract index from transaction for callback data
        tx = transactions[i-1]
        parts = tx.split(', ')
        index_part = parts[0].split(': ')[0]
        
        # Create button with sequential number and tx_ index callback
        current_row.append(InlineKeyboardButton(str(i), callback_data=f"tx_{index_part}"))
        
        # Create rows with 5 buttons each
        if len(current_row) == 5:
            rows.append(current_row)
            current_row = []
    
    # Add any remaining buttons in the last row
    if current_row:
        rows.append(current_row)
    
    # Add all rows to the keyboard
    keyboard.extend(rows)
    
    # Add navigation buttons
    nav_buttons = []
    
    # Only show prev button if not on first page
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(texts.PREVIOUS_BUTTON, callback_data="tx_prev_page"))
    
    # Show next button if there are more transactions to show
    # For 30 total transactions (2 pages of 15 each):
    # - Show Next on page 0 (first page)
    # - Don't show Next on page 1 (second page)
    max_page = (total_transactions - 1) // items_per_page
     
    if current_page < max_page:
        nav_buttons.append(InlineKeyboardButton(texts.NEXT_BUTTON, callback_data="tx_next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add back button
    keyboard.append([InlineKeyboardButton(texts.BACK_TO_MAIN_MENU_BUTTON, callback_data="back_to_main_menu")])
    
    return InlineKeyboardMarkup(keyboard) 