SELECT_LANGUAGE = "Please choose the language of the dictionary you want to use:"
LANGUAGE_REPLY = "Dictionary language set to {}."
CHOOSE_CURRENCY_TEXT = "Now, please choose your preferred currency:"
CURRENCY_REPLY = "Currency saved as {}"
CHOOSE_LIMIT_TEXT = "Please, enter your expected monthly limit or click Skip"
NO_LIMIT = "No Limit set!"
LIMIT_SET = "Limit successfully set."
TRANSACTION_START_TEXT = """Settings successfully saved. Now you can use the bot to track your expenses! 
\n
There are 2 possible formats: 
1. Through /menu => Add transaction
2. Through text input:
<b>full:</b>
<code>date category subcategory amount</code>
<b>With category:</b> 
<code>transport taxi amount</code>
<b>Without category:</b> 
<code>taxi amount</code>

Few examples for reference:
<code>taxi 5</code>
<code>home groccery 25</code>
 
If the date is not specified, the transaction will be saved with the current date and time.

If the category is not specified, the bot will suggest choosing it from the dictionary.

Saved categories and transactions can be viewed and edited through /menu => Edit categories \ Edit transactions

Multiple line inputs and comma-separated lines are supported, for example, <code>taxi 4, food 5, beauty 10</code>

Open /menu to view available functions.
\n/help for all known commands.
"""
TRANSACTION_SAVED_TEXT = "Transaction saved!"
LIMIT_EXCEEDED = """
Current daily average is <b>{current_daily_average}{currency}</b> and higher than your limit <b>{daily_limit}{currency}</b> on {percent_difference}%❗️
Please, <b>avoid spending for the next {days_zero_spending} days</b>✋🏼 or decrease daily limit to <b>{new_daily_limit}</b> till the end of the month.🙄"
"""
TRANSACTION_ERROR_TEXT = "You need to enter an amount. e.g. 'category amount' or 'date category amount'. Please try again."

INCOME_HELP = """This module allows to add income and track it. Expected formats:\n
<code>date category amount</code>
<code>category amount</code>
<code>amount</code> \n
To see overal month statistic use /show_income. If you accidently entered incorrect value, use /delete_income to delete latest transaction.
 """

RECORDS_NOT_FOUND_TEXT = "No records found."
RECORDS_TEMPLATE = """
Total {record_type}: <b>{total}</b>{currency}\n
Sum per category:\n{sum_per_cat}\n
Average per day for top 5 most often categories is {av_per_day_sum}{currency}, which is {comparison}% from yesterday.\n
Per category:\n{av_per_day}

Total average {record_type} per day: {total_av_per_day}{currency}, excluding Rent and Investing
You will {record_type2}: <b>{predicted_total}</b>{currency} by the end of the month with the same load.
"""
START_COMMAND_PROMPT = """Oups, something went wrong. It seems the transaction entry cannot be processed.
 Please, go to main /menu or /start from the beginning.\n\n
 Kindly reminder, transaction format isitem followed by price: <code>groccery 15</code>.
"""
CAT_DICT_MESSAGE = """
{}
Total number of categories: {}
"""
ADD_CAT_PROMPT = """Please send me the new category and subcategory in the format: <code>category:subcategory</code>
If you want to delete already existing category, use
         
<code>-category:subcategory</code>"""
ADD_CAT_SUCCESS = "Added {}: {} to your dictionary."
DEL_CAT_SUCCESS = "Deleted {}: {} from your dictionary."
WRONG_INPUT_FORMAT = (
    "The input format is incorrect. Please use the format: subcategory:category"
)
INVALID_RECORD_NUM = "Invalid record number. Please enter a valid number."
NO_RECORDS = "No records to show."
RECORD_LINE = "{}: {}"
INVALID_RECORD_NUM = "Invalid record number. Please enter a valid number."
NO_RECORDS_TO_DELETE = "No records to delete."
RECORD_DELETED = "Deleted record number {}."
NOT_ENOUGH_RECORDS = "There are less than {} records."
HELP_TEXT = """
About☝🏼 New Major release 0.2.0 from 01.04.25. 👌🏼 
New features were added. 🎉
Interactive menu system for easier navigation. Try /menu to access it!

Bellow the list of available commands. We are constantly working on the product, so if you have noticed any problems or 
want to have additional functionality, contact @dy0r2 

/menu - Open the interactive menu for intuitive navigation
/start - Create profile or re-write current settings. Dictionary language, currency, monthly limit will be asked
/show - Show current month spendings, per category and average.
----Since 0.3 most of the direct commands will be available through the menu only. Command based interactions will be depricated.

/show_last N - Show N latest transactions saved(default 5) or transactions for dedicated category (/show_last transport)
/show_ext - Detailed spendings list with top3 subcategories
/income - Add your income. 🆕
/show_income - Show current month income, per category and average.🆕
/monthly_stat - Show monthly chart and heatmap based on your spendings.🆕
/monthly_ext_stat - Show monthly based heatmap for current year per Subcategory.🆕
/show_cat - Show currently used dictionary.
/change_cat - Modify existing dictionary, add or delete category.  
/delete N - Delete transaction with number = N. Number is shown in /show_last command. 1 is default value.
/cancel - Return to main menu, expecting /start command or transaction record.
/download - Download current spendings file.
/upload - Upload new spendings file.
/help - Show this menu.
/leave - Deleting your profile! Please, be accurate as this action cannot be reversed.

"""
UPLOAD_FILE_TEXT = "Please upload your spendings file. It should be in CSV format."
UPLOADING_FINISHED = "Spendings file updated!"
INCOME_TYPE1 = "income"
INCOME_TYPE2 = "earn"
SPENDINGS_TYPE1 = "spendings"
SPENDINGS_TYPE2 = "spent"
CANCEL_TEXT = "Cancelled. You can now enter a new command."
CONFIRM_SAVE_CAT = "Category '<code>{}</code>' has been chosen for subcategory '<code>{}</code>' and saved into dictionary."
REQUEST_CAT = "Please send me a category, you want to use for '<code>{}</code>'. It will be added into your dictionary and next time will be automatically selected for <i>'{}'</i>:"
SPECIFY_MANUALLY_PROMPT = "Specify manually"
CHOOSE_CATEGORY_PROMPT = """I could not find category for '<code>{}</code>' in your dictionary. 
Please choose one of the recently used or <b>enter a new one manually</b>:"""
CREATE_CATEGORY_PROMPT = """Please enter a new category name for '<code>{}</code>':"""
SUBCAT_NOT_FOUND = """I could not find a category for '<code>{}</code>' in your dictionary. Please choose from the following categories or create a new one:"""
SUBCAT_FOUND_ONE = """I found the subcategory '<code>{}</code>' in the category '<code>{}</code>'. Would you like to use this category or choose another one?"""
SUBCAT_FOUND_MULTIPLE = """I found the subcategory '<code>{}</code>' in multiple categories: {}. Please select which one you want to use:"""
CHOOSE_FROM_ALL_CATEGORIES = """Please choose a category for '<code>{}</code>' from all available categories:"""
TRANSACTION_CANCELED = """Transaction has been canceled."""
NOTIFY_OTHER_CAT = """Your transactions for '<code>{}</code>'  were saved under category 'other', because we could not find any match in the dictionary.
If you know which Category to use, please, add it into the dictionary via /change_cat , or add another transaction in <code>category subcategory amount</code> format, and it will be automatically updated in the database."""
LAST_RECORDS = "List of transactions with index number.\nThe sum is: <b>{}</b> \n\n{} \n\nTo delete type /delete followed by the transaction index."
ABOUT = 'Hello, {}!\nYour curent Currency is <b>{}</b> Language is <b>{}</b>, and \nMonthly limit is <b>{}</b> \nCurrent version is 0.1.3 from 12.3 25'

# Menu text strings
MAIN_MENU_TEXT = "📱 <b>Main Menu</b>\nWhat would you like to do?"
SHOW_TRANSACTIONS_MENU_TEXT = "📊 <b>Show Transactions</b>\nSelect what you would like to view:"
SETTINGS_MENU_TEXT = "⚙️ <b>Settings</b>\nSelect what you would like to configure:"
#EDIT_CATEGORIES_MENU_TEXT = "📝 <b>Edit Categories</b>\nWhat would you like to do?"
ADD_TRANSACTION_TEXT = "Please enter your transaction in one of the following formats:\n<code>date category subcategory amount</code>\n<code>category subcategory amount</code>\n<code>subcategory amount</code>"
BACK_TO_MAIN_MENU = "Returning to main menu."

# Category editor text strings
NO_CATEGORIES_FOUND = "No categories found in your dictionary."
EDIT_CATEGORIES_PROMPT = "📝 <b>Choose a category to edit:</b>"
CATEGORY_OPTIONS = "Options for category '<code>{}</code>':"
ENTER_NEW_CATEGORY_NAME = "Please enter a new name for category '<code>{}</code>':"
CONFIRM_RENAME_CATEGORY = "Rename category '<code>{}</code>' to '<code>{}</code>'?"
CATEGORY_RENAMED = "Category '<code>{}</code>' has been renamed to '<code>{}</code>'."
RENAME_CANCELLED = "Renaming cancelled."
CONFIRM_DELETE_CATEGORY = "Are you sure you want to delete category '<code>{}</code>' and all its spendings?"
CATEGORY_DELETED = "Category '<code>{}</code>' has been deleted."
DELETE_CANCELLED = "Deletion of '<code>{}</code>' cancelled."
CATEGORY_TASKS = "Tasks in category '<code>{}</code>':"
ENTER_NEW_TASK = "Please enter a new spending for category '<code>{}</code>':"
TASK_ADDED = "Task '<code>{}</code>' added to category '<code>{}</code>'."
TASK_OPTIONS = "Options for spending '<code>{}</code>' in category '<code>{}</code>':"
ENTER_NEW_TASK_NAME = "Please enter a new name for spending '<code>{}</code>':"
CONFIRM_RENAME_TASK = "Rename spending '<code>{}</code>' to '<code>{}</code>' in category '<code>{}</code>'?"
TASK_RENAMED = "Task '<code>{}</code>' has been renamed to '<code>{}</code>' in category '<code>{}</code>'."
RENAME_TASK_CANCELLED = "Renaming spending '<code>{}</code>' cancelled."
CONFIRM_DELETE_TASK = "Are you sure you want to delete spending '<code>{}</code>' from category '<code>{}</code>'?"
TASK_DELETED = "Task '<code>{}</code>' has been deleted from category '<code>{}</code>'."
DELETE_TASK_CANCELLED = "Deletion of spending '<code>{}</code>' cancelled."
ERROR_PROCESSING_REQUEST = "Error processing your request. Please try again."

CATEGORY_ADDED = "Category '<code>{}</code>' has been added successfully."

SELECT_RECORDS_COUNT = "Select the number of records to display:"
LOADING_TRANSACTIONS = "Loading {count} last transactions..."

# Transaction entry texts
SELECT_TRANSACTION_CATEGORY = """Please select a category where you would like to save your expense.
You can also send a transaction in the chat in one of the following formats:

<code>taxi 5</code>
<code>home groceries 25</code>
<code>01.04 travel tickets 125</code>

If the date is not specified, the transaction will be saved with the current date and time.
If the category is not specified, the bot will suggest choosing it from existing ones or creating a new one.
"""
SELECT_TRANSACTION_SUBCATEGORY = "Please select a subcategory or enter manually in format 'Subcategory amount':"
RECENT_SUBCATEGORY_AMOUNTS = "Recent amounts for '{subcategory}':"
ENTER_TRANSACTION_AMOUNT = "Please enter the amount for '{subcategory}':"
CONFIRM_TRANSACTION_DETAILS = "Please confirm your transaction:\n\n<b>Category:</b> {category}\n<b>Subcategory:</b> {subcategory}\n<b>Amount:</b> {amount} {currency}\n<b>Date:</b> {date}"
TRANSACTION_CONFIRMED = "Transaction saved successfully!"
MANUAL_SUBCATEGORY_DETECTED = "I detected subcategory '{subcategory}' and amount {amount}."
NO_SUBCATEGORIES_FOUND = "No subcategories found for this category. Please enter a subcategory and amount manually."
PROGRESS_MSG = "Transaction {}/{} saved: {} {}"
MULTI_TRANSACTION_START = "Processing {} transactions..."

# Transaction edit text strings
EDIT_TRANSACTIONS_PROMPT = """📝 <b>Edit recent transactions</b>
This menu allows you see last 30 transactions and quicly edit it. For more detailed view, go to Show Transactions => All transactions.
\nTotal: <b>{}</b> {}\nSelect a transaction to edit:"""
TRANSACTION_DETAILS = "<b>Transaction Details</b>\n\nDate: {timestamp}\nCategory: {category}\nSubcategory: {subcategory}\nAmount: {amount} {currency}\n\nSelect what you want to edit:"
ENTER_NEW_DATE_PROMPT = "Please enter the new date in format <code>DD.MM</code> or <code>DD.MM.YYYY</code>:"
SELECT_NEW_CATEGORY = "Please select the new category:"

ENTER_NEW_SUBCATEGORY = "Please enter the new subcategory name:"
ENTER_NEW_AMOUNT_PROMPT = "Please enter the new amount:"
CONFIRM_DELETE_TRANSACTION = "Are you sure you want to delete this transaction?\n\nDate: {timestamp}\nCategory: {category}\nSubcategory: {subcategory}\nAmount: {amount} {currency}"
DATE_UPDATED_SUCCESS = "✅ Transaction date has been updated."
CATEGORY_UPDATED_SUCCESS = "✅ Transaction category has been updated."
SUBCATEGORY_UPDATED_SUCCESS = "✅ Transaction subcategory has been updated."
AMOUNT_UPDATED_SUCCESS = "✅ Transaction amount has been updated."
TRANSACTION_DELETED_SUCCESS = "✅ Transaction has been deleted."
DELETE_CANCELLED = "❌ Deletion cancelled."
INVALID_DATE_FORMAT = "❌ Invalid date format. Please use DD.MM or DD.MM.YYYY format."
INVALID_AMOUNT_FORMAT = "❌ Invalid amount format. Please enter a valid number."
ERROR_DELETING_TRANSACTION = "❌ Error deleting transaction. Please try again."
ERROR_UPDATING_TRANSACTION = "❌ Error updating transaction. Please try again."
ERROR_SELECTING_TRANSACTION = "❌ Error selecting transaction. Please try again."

# Detailed transactions view texts
SELECT_TRANSACTION_TO_EDIT = "Click on a number to edit the corresponding transaction."
FILTERED_TRANSACTIONS_TEXT = "📊 <b>Filtered Transactions</b>\n\nPeriod: <b>{period}</b>\nCategories: <b>{categories}</b>"
SELECT_CATEGORIES_TEXT = "📂 <b>Select Categories</b>\nChoose categories to view their transactions:"
SELECT_TIME_PERIOD_TEXT = "⏱️ <b>Select Time Period</b>\nChoose which time period to view:"
NO_TRANSACTIONS_FOUND = "No transactions found for the selected categories and period."
NO_CATEGORIES_FOUND = "No categories found in your transaction history."
DETAILED_SUMMARY_TEMPLATE = "<b>Detailed Summary</b>\n\nPeriod: <b>{period}</b>\nTotal: <b>{total} {currency}</b>\nTransactions: <b>{transaction_count}</b>"
VIEW_TRANSACTIONS_BUTTON = "📋 View transactions"

# Button text variables
SKIP_BUTTON = "Skip"
CHANGE_LANGUAGE_BUTTON = "🌍 Change language"
CHANGE_CURRENCY_BUTTON = "💱 Change currency"
CHANGE_LIMIT_BUTTON = "💰 Change monthly limit"
BACK_BUTTON = "◀️ Back"
NEXT_BUTTON = "Next ▶️"
PREVIOUS_BUTTON = "⬅️ Previous"
CREATE_CATEGORY_BUTTON = "💚 Create new category"
CANCEL_BUTTON = "❌ Cancel"
USE_CATEGORY_BUTTON = "✅ Use '{}'"
CHOOSE_OTHER_CATEGORY_BUTTON = "🔄 Choose another category"
SHOW_ALL_CATEGORIES_BUTTON = "🔄 Show all categories"
ADD_TRANSACTION_BUTTON = "💰 Add transaction"
SHOW_TRANSACTIONS_BUTTON = "📊 Show transactions"
SETTINGS_BUTTON = "⚙️ Settings"
EDIT_CATEGORIES_BUTTON = "📝 Edit categories"
EDIT_TRANSACTIONS_BUTTON = "✏️ Edit Recent Entry"
HELP_BUTTON = "❓ Help"
MONTHLY_SUMMARY_BUTTON = "📊 Monthly summary"
LAST_MONTH_SUMMARY_BUTTON = "📈 Last month"
LAST_TRANSACTIONS_BUTTON = "📋 All transactions"
MONTHLY_CHARTS_BUTTON = "📈 Monthly charts"
DETAILED_STAT_BUTTON = "📊 Detailed stat"
YEARLY_CHARTS_BUTTON = "📊 Yearly charts"
INCOME_STATS_BUTTON = "💵 Income stats"
BACK_TO_MAIN_MENU_BUTTON = "🔙 Back to main menu"
RETURN_BACK_BUTTON = "👈🏻 Return back"
CONFIRM_BUTTON = "✅ Confirm"
CONFIRM_DELETE_BUTTON = "Confirm delete!"
EDIT_DATE_BUTTON = "📅 Edit date"
EDIT_CATEGORY_BUTTON = "📁 Edit category"
EDIT_SUBCATEGORY_BUTTON = "📂 Edit name"
EDIT_AMOUNT_BUTTON = "💰 Edit amount"
DELETE_TRANSACTION_BUTTON = "🗑️ Delete transaction"
DELETE_CATEGORY_BUTTON = "🗑️ Delete category"
EDIT_TASKS_BUTTON = "📝 Edit spendings"

ADD_NEW_TASK_BUTTON = "➕ Add new spending"
BACK_TO_CATEGORY_BUTTON = "🔙 Back to category"
EDIT_TASK_BUTTON = "✏️ Edit spending"
DELETE_TASK_BUTTON = "🗑️ Delete spending"
BACK_TO_TASKS_BUTTON = "🔙 Back to spending"
DELETE_PROFILE_CONFIRMATION = "Do you <b>really want to delete profile</b>? This action is unchangeable. Please, send <code>Delete profile</code> in the chat to confirm."
ALL_TRANSACTIONS_PROCESSED = "All transactions have been processed successfully!"
ABOUT_BUTTON = "ℹ️ About"
SHOW_CATEGORIES_BUTTON = "📋 Show categories"
ADD_REMOVE_CATEGORY_BUTTON = "➕ Add/remove category"
CHANGE_NAME_BUTTON = "✏️ Change name"

# New text templates for detailed transactions feature
SELECT_CATEGORIES_TEXT = "📊 <b>Select Categories</b>\nChoose categories to include in the detailed report. Select multiple categories by tapping on them (they will be marked with ✅)."
SELECT_TIME_PERIOD_TEXT = "⏱️ <b>Select Time Period</b>\nChoose a time period for your transaction report:"
DETAILED_SUMMARY_TEMPLATE = """📊 <b>Detailed Summary for {period}</b>

Total spending: <b>{total} {currency}</b>
Number of transactions: {transaction_count}"""
FILTERED_TRANSACTIONS_TEXT = """📋 <b>Transactions for {period}</b>
Categories: {categories}

Select a transaction to view details:"""
NO_CATEGORIES_FOUND = "❌ No categories found in your spending history."
NO_TRANSACTIONS_FOUND = "❌ No transactions found for the selected categories and time period."

# Button text for detailed transactions
THREE_MONTH_BUTTON = "3 months"
SIX_MONTH_BUTTON = "6 months"
TWELVE_MONTH_BUTTON = "12 months"
YEAR_TO_DATE_BUTTON = "Year to date"
SELECT_ALL_BUTTON = "✅ Select All"
CONTINUE_BUTTON = "▶️ Continue"
VIEW_TRANSACTIONS_BUTTON = "📋 View Transactions"