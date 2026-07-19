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
UNKNOWN_TEXT_FORMAT = "I couldn't recognize that format. Please use /help to review supported commands."

INCOME_HELP = """💵 Add income directly: <code>/income salary 2000</code> — or send the details as the next message. Expected formats:\n
<code>date category amount</code> (date as dd.mm)
<code>category amount</code>
<code>amount</code>\n
To see the monthly income statistic use /show_income; list records with IDs via <code>/show_last income</code>. Entered a wrong value? /delete_income removes the latest income record, or <code>/delete_income id</code> a specific one.
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
RECORD_DELETED_DETAILS = "🗑 Deleted record {record_id}: {date}, {category}{subcategory}, {amount} {currency}"
DELETE_TYPE_MISMATCH = "Record {record_id} is a {tx_type} — use the matching command: /delete for spendings, /delete_income for income."
NOT_ENOUGH_RECORDS = "There are less than {} records."
INCOME_SAVED = "💵 Income saved: {category}, {amount} {currency} ({date})"
LANG = "en"
HELP_INTRO = """👋 BudgetBot helps you track spendings and income right in Telegram.
💬 Add a spending by simply typing it, e.g. "coffee 4" — or "31.12 coffee 4" to backdate it.
📱 Try /menu — most features are available through the interactive menu.
Noticed a problem or want a new feature? Contact @dy0r2"""
UPLOAD_FILE_TEXT = "Please upload your spendings file. It should be in CSV format."
UPLOADING_FINISHED = "Spendings file updated!"
INCOME_TYPE1 = "income"
INCOME_TYPE2 = "earn"
SPENDINGS_TYPE1 = "spendings"
SPENDINGS_TYPE2 = "spent"
CANCEL_TEXT = "Cancelled. You can now enter a new command."
CONFIRM_SAVE_CAT = "Category '<code>{}</code>' has been chosen for subcategory '<code>{}</code>' and saved."
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
LAST_RECORDS_INCOME = "List of income records with index number.\nThe sum is: <b>{}</b> \n\n{} \n\nTo delete type /delete_income followed by the record index."
ABOUT = 'Hello, {}!\nYour current Currency is <b>{}</b> Language is <b>{}</b>, and \nMonthly limit is <b>{}</b> \nCurrent version is {} from {}'
NO_LIMIT = "no limit"

# Menu text strings
MAIN_MENU_TEXT = "📱 <b>Main Menu</b>\nWhat would you like to do?"
SHOW_TRANSACTIONS_MENU_TEXT = "📊 <b>Show Transactions</b>\nThis is the menu where you can see the analytic charts and statistics. \n Select what you would like to view:"
SETTINGS_MENU_TEXT = "⚙️ <b>Settings</b>\nSelect what you would like to configure:"
#EDIT_CATEGORIES_MENU_TEXT = "📝 <b>Edit Categories</b>\nWhat would you like to do?"
ADD_TRANSACTION_TEXT = "Please enter your transaction in one of the following formats:\n<code>date category subcategory amount</code>\n<code>category subcategory amount</code>\n<code>subcategory amount</code>"

# Chart fallbacks (referenced by handlers/charts.py; previously missing — T-039)
NO_DATA = "No data to chart yet — add some transactions first."
NO_YEARLY_DATA = "No yearly data to chart yet — add some transactions first."
ERROR_SENDING_CHARTS = "Something went wrong while sending the charts. Please try again."
ERROR_GENERATING_CHARTS = "Something went wrong while generating the charts. Please try again."

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
LOADING_MONTHLY_SUMMARY = "Loading monthly summary..."
LOADING_LAST_MONTH_SUMMARY = "Loading last month summary..."
LOADING_EXTENDED_STATS = "Loading extended statistics..."
LOADING_LAST_MONTH_EXTENDED_STATS = "Loading last month extended statistics..."
LOADING_INCOME_STATS = "Loading income statistics..."
GENERATING_MONTHLY_CHARTS = "Generating monthly charts..."
GENERATING_YEARLY_CHARTS = "Generating yearly charts..."

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
ADD_SPENDING_BUTTON = "💸 Add spending"
ADD_INCOME_BUTTON = "💵 Add income"
ADD_TX_MENU_TEXT = "💰 <b>Add transaction</b>\nWhat would you like to add? You can also just type a spending like <code>coffee 4.5</code>, or use <code>/income salary 2000</code>."
SHOW_TRANSACTIONS_BUTTON = "📊 Show transactions"
SETTINGS_BUTTON = "⚙️ Settings"
EDIT_CATEGORIES_BUTTON = "📝 Edit categories"
EDIT_TRANSACTIONS_BUTTON = "✏️ Edit Recent Entry"
HELP_BUTTON = "❓ Help"
MONTHLY_SUMMARY_BUTTON = "📊 This month summary"
LAST_MONTH_SUMMARY_BUTTON = "📊 Last month summary"
DETAILED_STAT_BUTTON = "📊 This month detailed summary"
LAST_MONTH_DETAILED_STAT_BUTTON = "📊 Last month detailed summary"
LAST_TRANSACTIONS_BUTTON = "📋 All transactions"
MONTHLY_CHARTS_BUTTON = "📈 Monthly charts"
YEARLY_CHARTS_BUTTON = "📈 Yearly charts"
INCOME_STATS_BUTTON = "💵 Income stats"
BACK_TO_MAIN_MENU_BUTTON = "🏠 Back to main menu"
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

DETAILED_REPORT_LAST_MONTH_TEXT = "Detailed report last month:"
DETAILED_REPORT_TEXT = "Detailed report:"
# Button text for detailed transactions
THREE_MONTH_BUTTON = "3 months"
SIX_MONTH_BUTTON = "6 months"
TWELVE_MONTH_BUTTON = "12 months"
YEAR_TO_DATE_BUTTON = "Year to date"
SELECT_ALL_BUTTON = "✅ Select All"
CONTINUE_BUTTON = "▶️ Continue"
VIEW_TRANSACTIONS_BUTTON = "📋 View Transactions"
# /ask — AI Q&A over spendings
ASK_USAGE = "Ask a question about your finances, e.g.:\n/ask how much did I spend on groceries last month?"
ASK_THINKING = "🤔 Analyzing your data..."
# AI paywall (T-023): shown instead of a plain denial wherever AI access is gated.
BUY_AI_OFFER = "🤖 AI features — voice messages and /ask questions about your finances — require an AI pass.\n\nGet {days} days of access for {price} ⭐ Telegram Stars."
BUY_AI_OFFER_PERPETUAL = "🤖 AI features — voice messages and /ask questions about your finances — require an AI pass.\n\nGet permanent access for {price} ⭐ Telegram Stars."
BUY_AI_BUTTON = "⭐ Buy AI access"
BUY_AI_TITLE = "AI access pass"  # Telegram invoice title, max 32 chars
BUY_AI_DESCRIPTION = "{days} days of AI access: voice input and /ask questions about your finances."
BUY_AI_DESCRIPTION_PERPETUAL = "Permanent AI access: voice input and /ask questions about your finances."
BUY_AI_RECEIPT_DAYS = "✅ Payment received! Your AI access is active until {expiry} (UTC).\nA repeat purchase extends the expiry date."
BUY_AI_RECEIPT_PERPETUAL = "✅ Payment received! You now have permanent AI access."
BUY_AI_ALREADY = "You already have AI access — paying this invoice extends it."
PAY_PRECHECKOUT_FAILED = "This invoice is no longer valid. Please send /buy_ai to get a fresh one."
ASK_AI_BUTTON = "🤖 Ask AI"
AI_HOWTO = "🤖 You have AI access!\n\n• Send a voice message — I'll turn it into a transaction or answer a question.\n• Or type /ask followed by a question, e.g. /ask how much did I spend on food this month?"
# Ask-AI typed-question mode (T-045): shown when an entitled user taps the menu button.
ASK_AI_PROMPT = "🤖 Ask me anything about your finances — e.g. \"how much did I spend on beer this year?\"\n\nJust type your question as the next message."
ASK_ERROR = "Could not get an answer right now. Please try again later."
ASK_NO_DATA = "You don't have any transactions yet — add some spendings first."

# Voice input & intent routing (T-019)
VOICE_TRANSCRIBING = "🎙 Transcribing..."
VOICE_TOO_LONG = "Voice message is too long — please keep it under {seconds} seconds."
VOICE_ERROR = "Could not transcribe the voice message. Please try again."
VOICE_NO_SPEECH = "I couldn't hear any speech in that voice message."
VOICE_HEARD = "🎙 Heard: “{transcript}”"
VOICE_ROUTING = "🤔 Working out what you meant..."
VOICE_CONFIRM_TX = "🎙 Heard: “{transcript}”\n\nAdd transaction: {transaction}?"
VOICE_TX_CONFIRM_BTN = "✅ Add"
VOICE_TX_CANCEL_BTN = "❌ Cancel"
VOICE_TX_ACCEPTED = "Adding: {transaction}"
VOICE_TX_CANCELLED = "Cancelled — nothing saved."
VOICE_CONFIRM_INCOME = "🎙 Heard: “{transcript}”\n\n💵 Add INCOME: {income}?"
VOICE_INCOME_ACCEPTED = "Adding income: {income}"
VOICE_UNKNOWN = (
    "🎙 Heard: “{transcript}”\n\n"
    "I couldn't map this to an action. You can add a spending like “coffee 4.5”, "
    "ask a question with /ask, or see /help."
)
# Voice correction of an already-saved transaction (T-041)
VOICE_CONFIRM_FIX = "🎙 Heard: “{transcript}”\n\nReplace {old} → {new}?"
VOICE_FIX_DONE = "Replaced. Adding: {transaction}"
VOICE_FIX_CANCELLED = "Cancelled — the saved record was kept."
VOICE_FIX_NOT_FOUND = "Couldn't find that record anymore — nothing was changed."

# Recurring transactions (T-026)
RECURRING_BUTTON = "🔁 Recurring"
RECURRING_USAGE = (
    "To add a monthly recurring transaction:\n"
    "/recurring add <name> <amount> <day>\n"
    "e.g. /recurring add rent 500 1"
)
RECURRING_LIST_EMPTY = (
    "You have no recurring transactions yet.\n\n"
    "To add a monthly recurring transaction:\n"
    "/recurring add <name> <amount> <day>\n"
    "e.g. /recurring add rent 500 1"
)
RECURRING_LIST_HEADER = "🔁 Your recurring transactions:"
RECURRING_PAUSED_LABEL = "paused"
RECURRING_DAY_WORD = "day"
RECURRING_ADDED = "Recurring transaction saved: {name} — {amount} {currency}, every month on day {day}."
RECURRING_DAY_CLAMP_NOTE = "In shorter months it will be added on the last day of the month."
RECURRING_INVALID_NAME = "Invalid name: 1-60 characters, cannot start with '/'."
RECURRING_INVALID_AMOUNT = "Invalid amount: must be a positive number."
RECURRING_INVALID_DAY = "Invalid day: must be a number from 1 to 31."
RECURRING_CONFIRM_DELETE = "Delete recurring transaction '{name}'? This cannot be undone."
RECURRING_POSTED = "🔁 Recurring transaction added: {name} — {amount} {currency} (for {date})."
RECURRING_PAUSE_BTN = "⏸ {}"
RECURRING_RESUME_BTN = "▶️ {}"
RECURRING_DELETE_BTN = "🗑"
RECURRING_CONFIRM_DELETE_BTN = "🗑 Delete"
RECURRING_BACK_BTN = "◀️ Back"

# Daily reminder + timezone (T-034)
REMINDER_BUTTON = "⏰ Daily reminder"
TIMEZONE_BUTTON = "🕒 Time zone"
# Sent by the scheduler sweep without parse_mode — keep it HTML-free.
REMINDER_TEXT = "⏰ Time to log today's spendings! Just type it, e.g. coffee 4.5 — or use /menu."
REMINDER_STATUS_OFF = (
    "⏰ Daily reminder is off.\n"
    "Pick a time (your local time) and I'll nudge you once a day to log your transactions. "
    "If you've already logged something that day, I'll stay quiet.\n\n"
    "You can also type /reminder 17:00 or /reminder off."
)
REMINDER_STATUS_ACTIVE = (
    "⏰ Daily reminder is set for {time} (your local time).\n"
    "Pick a new time or turn it off:"
)
REMINDER_SET = (
    "⏰ Done — I'll remind you every day at {time} (your local time) to log your transactions. "
    "On days you've already logged something, I'll stay quiet.\n"
    "Turn off anytime with /reminder off."
)
REMINDER_DISABLED = "🔕 Daily reminder turned off."
REMINDER_INVALID_TIME = "Invalid time — use HH:MM, e.g. 17:00."
REMINDER_USAGE = (
    "/reminder — reminder settings\n"
    "/reminder 17:00 — remind me daily at 17:00\n"
    "/reminder off — turn the reminder off"
)
REMINDER_OFF_BTN = "🔕 Turn off"
TZ_PICK_PROMPT = (
    "🕒 What time is it for you right now?\n"
    "Tap the button matching your clock — that's how I learn your time zone:"
)
TZ_SAVED = (
    "🕒 Time zone saved (UTC{offset}). "
    "If your clocks change (daylight saving), re-pick it in Settings → Time zone."
)
# Admin panel commands (T-025)
ADMIN_ONLY = "This command is restricted to the bot owner."
ADMIN_EXPORT_USAGE = "Usage: /admin_export <user_id>"
ADMIN_USER_NOT_FOUND = "User {user_id} not found."
ADMIN_NO_TRANSACTIONS = "User {user_id} has no transactions."
ADMIN_NO_USERS = "No users found."
ADMIN_USERS_HEADER = "Active users: {count} of {total} registered (sorted by last activity; /admin_users all for everyone)"

RATES_STALE_NOTE = "⚠️ Exchange rates are {hours}h old — converted amounts may be slightly off."
