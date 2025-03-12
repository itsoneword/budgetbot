SELECT_LANGUAGE = "Please choose the language of the dictionary you want to use:"
LANGUAGE_REPLY = "Dictionary language set to {}."
CHOOSE_CURRENCY_TEXT = "Now, please choose your preferred currency:"
CURRENCY_REPLY = "Currency saved as {}"
CHOOSE_LIMIT_TEXT = "Please, enter your expected monthly limit or click Skip"
NO_LIMIT = "No Limit set!"
LIMIT_SET = "Limit successfully set."
TRANSACTION_START_TEXT = """Now, you can send transactions. The following formats are supported: \n
Full:   <code>date category subcategory amount</code> 
W/ category:    <code>transport taxi 5</code>
W/o category:     <code>taxi 5</code>

the last example will be saved with <b>current date and time</b> and use the category from the dictionary - <b>transport</b>\n
Multiple lines and coma separated lines are supported,e.g.\ntaxi 4, food 5\nbeauty 10

Type /show_cat to get predefined category dictionary, or /change_cat to modify it. 
\n/help for all the known commands.
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
START_COMMAND_PROMPT = "Please type /start to begin or /help to get help."
CAT_DICT_MESSAGE = """
{}
Total number of categories: {}
"""
ADD_CAT_PROMPT = """Please send me the new category and subcategory in the format: `category:subcategory`\n
        If you want to delete already existing category, use '\-' \n `-category:subcategory`"""
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
About☝🏼 New release 0.0.6 from 24.02.24. 👌🏼 
New features were added. 🎉
Possibility to set monthly limit and track daily. Please, consider re-running /start to set up the limit.
Rent and investing categoies are excluded from daily average.
Onboarding Start message is fixed. Consider sending /start to check it.

Bellow the list of available commands. We are constantly working on the product, so if you have noticed any problems or 
want to have additional functionality, contact @dy0r2 

<b>/start</b> - Create profile or re-write current settings. Dictionary language, currency, monthly limit will be asked
<b>/show</b> - Show current month spendings, per category and average.
<b>/show_last N</b> - Show N latest transactions saved(default 5) or transactions for dedicated category (/show_last transport)
<b>/show_ext</b> - Detailed spendings list with top3 subcategories
<b>/income</b> - Add your income. 🆕
<b>/show_income</b> - Show current month income, per category and average.🆕
<b>/monthly_stat</b> - Show monthly chart and heatmap based on your spendings.🆕
<b>/monthly_ext_stat</b> - Show monthly based heatmap for current year per Subcategory.🆕
<b>/show_cat</b> - Show currently used dictionary.
<b>/change_cat</b> - Modify existing dictionary, add or delete category.  
<b>/delete N</b> - Delete transaction with number = N. Number is shown in /show_last command. 1 is default value.
<b>/cancel</b> - Return to main menu, expecting /start command or transactoin record.
<b>/download</b> - Download current spendings file.
<b>/upload</b> - Upload new spendings file.
<b>/help</b> - Show this menu.
<b>/leave</> - Deleting your profile! Please, be accurate as this action cannot be reversed.

"""
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
NOTIFY_OTHER_CAT = """Your transactions for '<code>{}</code>'  were saved under category 'other', because we could not find any match in the dictionary.
If you know which Category to use, please, add it into the dictionary via /change_cat , or add another transaction in <code>category subcategory amount</code> format, and it will be automatically updated in the database."""
LAST_RECORDS = "List of transactoins with index number.\nThe sum is: <b>{}</b> \n\n{} \n\nTo delete type /delete followed by the transaction index."
ABOUT = 'Hello, {}!\nYour curent Currency is <b>{}</b> Language is <b>{}</b>, and \nMonthly limit is <b>{}</b> \nCurrent version is 0.1.3 from 12.3 25'
