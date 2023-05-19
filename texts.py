SELECT_LANGUAGE = "Please choose the language of the dictionary you want to use:"
LANGUAGE_REPLY = "Dictionary language set to {}. \nNow please, Let me know your name:"
CHOOSE_CURRENCY_TEXT = "Now, please choose your preferred currency:"
TRANSACTION_START_TEXT = """Currency saved\. Now, please send me your transactions in the format: \n\n`date category subcategory amount`\. \n
        or in a short way: \n    `taxi 5` \n
        it will be saved with _current date and time_ into category \- _transport_\n
        Multiple lines and coma separated lines are supported\.\n\n
        To see available categories type /show_cat, /change_cat to modify existing records or get /help for all the known commands\."""
TRANSACTION_SAVED_TEXT = "Transaction saved!"
TRANSACTION_ERROR_TEXT = "You need to enter an amount. Please try again."

RECORDS_NOT_FOUND_TEXT = "No records found."
RECORDS_TEMPLATE = (
    "Total spending for current month:{total}\n\n"
    "Sum per category:\n{sum_per_cat}\n\n"
    "Average per day:\n{av_per_day}"
)
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
Bellow the list of available commands. We are working on new features now, so if you have noticed any problems or 
want to have additional functionality, contact  @dy0r2 

<b>/start</b> - Create profile or re\write current settings. Dictionary language, name and currency will be asked
<b>/show</b> - Show current month spendings, per category and average.
<b>/showext</b> - Detailed spendings list with top3 subcategories
<b>/show_last N</b> - Show N latest trnsactions saved. 5 is default value
<b>/delete N</b> - Delete transaction with number = N. Number is shown in /latest command. 1 is default value.
<b>/show_cat</b> - Show currently used dictionary
<b>/change_cat</b> - Modify existing dictionary, add or delete category.  
<b>/cancel</b> - Return to main menu, expecting /start command or spending record.
<b>/help</b> - Show this menu.
<b>/download</b> - Download current spendings file.
<b>/upload</b> - Upload new spendings file.
<b>/leave</b> - Archive your profile completely to start from the begining. 

"""

CANCEL_TEXT = "Cancelled. You can now enter a new command."
