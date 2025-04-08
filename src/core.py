import os, logging, configparser, inspect, re, asyncio
from datetime import datetime, timedelta
from language_util import check_language
import sys

from pandas_ops import (
    show_sum_per_cat,
    show_top_subcategories,
    calculate_limit,
    get_user_path,
    get_exchange_rate,
    get_user_currency,
)
from charts import monthly_line_chart, monthly_pivot_chart, make_yearly_pie_chart,monthly_ext_pivot_chart
from src.show_transactions import process_transaction_input, process_income_input
from keyboards import (
    create_language_keyboard,
    create_skip_keyboard,
    create_settings_keyboard,
    create_category_keyboard,
    create_found_category_keyboard,
    create_multiple_categories_keyboard,
    create_settings_language_keyboard,
    create_settings_currency_keyboard,
    create_main_menu_keyboard,
    create_show_transactions_keyboard,
    create_settings_keyboard_menu,
    create_records_count_keyboard,
    create_tx_categories_keyboard,
    create_subcategories_keyboard,
    create_amounts_keyboard,
    create_confirm_transaction_keyboard,
)
from file_ops import *

from change_data import (
    show_categories, handle_category_selection, handle_category_option, 
    handle_change_name, handle_add_new_category, handle_rename_confirmation, 
    handle_delete_cat_confirmation, handle_tasks_action, handle_task_option,
    handle_add_task, handle_edit_task, handle_task_edit_confirmation,
    handle_task_delete_confirmation
)

from change_transactions import (
    show_recent_entries, handle_transaction_selection, handle_edit_option, handle_edit_date,
    handle_edit_category, handle_edit_subcategory, handle_edit_amount, handle_delete_tx_confirmation
)

from telegram import (
    Update,
    InputMediaPhoto,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from logging.handlers import TimedRotatingFileHandler

# Import transaction handlers directly
from save_transaction import (
    save_transaction ,
    process_next_transaction ,
    create_new_category_transaction ,
    select_category_for_transaction ,
    handle_transaction_category ,
    handle_transaction_subcategory ,
    handle_transaction_amount ,
    handle_transaction_confirmation 
)

# Import the detailed transactions module
from src.detailed_transactions import (
    start_detailed_transactions,
    handle_category_selection as handle_detailed_category_selection,
    handle_time_period_selection,
    handle_summary_action,
    handle_transaction_navigation,
)

# Import all states from the central states file
from src.states import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[
        TimedRotatingFileHandler(
            'user_data/app.log',
            when="m",
            interval=10,
            backupCount=5
        ),
    ])

# Add console handler for warnings and errors
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)  # Only show WARNING and above
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

logging.getLogger("httpx").setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger = logging.getLogger("user_interactions")
logger.setLevel(logging.INFO)

# Create file handler
handler = logging.FileHandler("./user_data/global_log.txt")
handler.setLevel(logging.INFO)
# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)
# Add the handler to the logger
logger.addHandler(handler)


def log_user_interaction(user_id: str, username: str, tg_username: str, function_name=None):
    calling_function_name = function_name if function_name else inspect.stack()[1].function

    log_message = (
        f"UserID: {user_id}, {username}, {tg_username}, {calling_function_name}"
    )
    logger.info(log_message)


config = configparser.ConfigParser()
config.read("configs/config")
token = config["TELEGRAM"]["TOKEN"]

if token == "":

    config.read("config")
    token = config["TELEGRAM"]["TOKEN"]

#print (config["TELEGRAM"]["TOKEN"])


async def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)

    create_user_dir_and_copy_dict(user_id)

    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    update_user_list(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    
    reply_markup = create_language_keyboard()

    await update.message.reply_text(texts.SELECT_LANGUAGE, reply_markup=reply_markup)
  
    return LANGUAGE


async def save_language(update: Update, context: CallbackContext):
    #print("language is called! ")
    query = update.callback_query
    user_language = query.data
    user_id = update.effective_user.id
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    # Save the chosen language into the config file
    save_user_setting(user_id, "LANGUAGE", user_language)
    texts = check_language(update, context)
    #print("language functoin check_language returned")
    reply_markup = create_settings_currency_keyboard()
    #print("language functoin create_settings_currency_keyboard returned")
    await query.edit_message_text(texts.LANGUAGE_REPLY.format(user_language))
    await update.effective_message.reply_text(
        texts.CHOOSE_CURRENCY_TEXT, reply_markup=reply_markup
    )
    #print("language functoin CURRENCY returned")
    return CURRENCY


async def save_currency(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    user_currency = query.data.split('_')[1]

    #user_currency = update.callback_query.data
    save_user_setting(user_id, "CURRENCY", user_currency)

    reply_markup = create_skip_keyboard(texts)

    await query.edit_message_text(texts.CURRENCY_REPLY.format(user_currency))
    await update.effective_message.reply_text(
        texts.CHOOSE_LIMIT_TEXT, reply_markup=reply_markup
    )

    return LIMIT


async def save_limit(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    try:
        # Try to convert the entered data to a float
        limit = float(update.effective_message.text)
    except ValueError:
        # If the conversion fails, send an error message and skip the step
        await update.effective_message.reply_text(
            "Invalid limit. Please enter a number."
        )
        return LIMIT

    # Save the limit to the config file as a string
    save_user_setting(user_id, "MONTHLY_LIMIT", str(limit))
    await update.effective_message.reply_text(texts.LIMIT_SET)
    await update.effective_message.reply_text(texts.TRANSACTION_START_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION  # Or whatever state should come next


async def skip_limit(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    await context.bot.edit_message_reply_markup(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        reply_markup=None,
    )
    save_user_setting(user_id, "MONTHLY_LIMIT", str(99999999))

    await update.effective_message.reply_text(texts.NO_LIMIT)
    await update.effective_message.reply_text(texts.TRANSACTION_START_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION  # Or whatever state should come next


async def show_records(update: Update, context):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    
    command = update.effective_message.text.split()[0][1:]
    record_type, record_type2 = (
        (texts.INCOME_TYPE1, texts.INCOME_TYPE2)
        if "income" in command
        else (texts.SPENDINGS_TYPE1, texts.SPENDINGS_TYPE2)
    )

    currency = get_user_currency(user_id)
    records = get_records(user_id, command)
    if records is None:
        await update.message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return
    (
        sum_per_cat,
        av_per_day,
        total_spendings,
        total_av_per_day,
        prediction,
        comparison,
    ) = records
    
    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in sum_per_cat.items()
    )
    
    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in av_per_day.items()
    )
    av_per_day_sum = round(av_per_day.sum())

    output_text = texts.RECORDS_TEMPLATE.format(
        total=total_spendings,
        sum_per_cat=sum_per_cat_text,
        av_per_day_sum=av_per_day_sum,
        av_per_day=av_per_day_text,
        total_av_per_day=total_av_per_day,
        predicted_total=prediction,
        comparison=comparison,
        currency=currency,
        record_type=record_type,
        record_type2=record_type2,
    )
    
    if  update.callback_query:
        await update.callback_query.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    
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
        #print(f"Exception in show_records when calculating limit: {e}")       
        pass
    return TRANSACTION


async def show_last_month_records(update: Update, context):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    
    command = "show" # Default to showing spendings for last month
    if hasattr(update.effective_message, 'text') and update.effective_message.text:
        command = update.effective_message.text.split()[0][1:]
    
    record_type, record_type2 = (
        (texts.INCOME_TYPE1, texts.INCOME_TYPE2)
        if "income" in command
        else (texts.SPENDINGS_TYPE1, texts.SPENDINGS_TYPE2)
    )

    # Get last month name for display
    current_date = datetime.now()
    last_month_date = current_date.replace(day=1) - timedelta(days=1)
    last_month_name = last_month_date.strftime("%B %Y")

    currency = get_user_currency(user_id)
    records = get_last_month_records(user_id, command)
    if records is None:
        await update.message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return
    (
        sum_per_cat,
        av_per_day,
        total_spendings,
        total_av_per_day,
        prediction,
        comparison,
    ) = records
    
    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in sum_per_cat.items()
    )
    
    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in av_per_day.items()
    )
    av_per_day_sum = round(av_per_day.sum())

    # Add last month name to the output
    output_text = f"<b>{last_month_name} {record_type}</b>\n\n"
    output_text += texts.RECORDS_TEMPLATE.format(
        total=total_spendings,
        sum_per_cat=sum_per_cat_text,
        av_per_day_sum=av_per_day_sum,
        av_per_day=av_per_day_text,
        total_av_per_day=total_av_per_day,
        predicted_total=prediction,
        comparison=comparison,
        currency=currency,
        record_type=record_type,
        record_type2=record_type2,
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(output_text, parse_mode=ParseMode.HTML)
    
    return TRANSACTION


async def show_detailed(update: Update, context):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    file_path = get_user_path(user_id)
    sum_per_cat = show_sum_per_cat(user_id, file_path)
    top_subcats = show_top_subcategories(user_id)

    output = "Detailed report:\n\n"
    for category, total in sum_per_cat.items():
        output += f"{category}: {total}\n"

        # Get the top subcategories for this category
        category_subcats = top_subcats[top_subcats["category"] == category]
        for _, row in category_subcats.iterrows():
            output += f"   {row['subcategory']}: {row['amount_cr_currency']}\n"

        output += "\n"
    if update.callback_query:
        await update.callback_query.message.reply_text(output)
    else:
        await update.message.reply_text(output)

    return TRANSACTION


async def show_cat(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    check_dictionary_format(user_id)
    cat_dict = read_dictionary(user_id)

    output = texts.CAT_DICT_MESSAGE.format(
        "\n".join(
            f"{category}:\n    "
            + ", ".join(subcategory for subcategory in cat_dict[category])
            for category in cat_dict
        ),
        len(cat_dict),
    )

    await update.message.reply_text(output)


async def add_cat(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    await update.message.reply_text(
        texts.ADD_CAT_PROMPT,
        parse_mode="MarkdownV2",
    ),
    return ADD_CATEGORY


async def save_category(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    text = update.message.text.lower()
    if ":" not in text or text.count(":") > 1:
        await update.message.reply_text(texts.WRONG_INPUT_FORMAT)
        return ADD_CATEGORY

    category, subcategory = text.split(":", 1)

    if text.startswith("-"):
        # Remove category:subcategory
        category = category.lstrip("-")
        remove_category(user_id, category, subcategory)
        await update.message.reply_text(
            texts.DEL_CAT_SUCCESS.format(category, subcategory)
        )
    else:
        # Add category:subcategory
        add_category(user_id, category, subcategory)
        await update.message.reply_text(
            texts.ADD_CAT_SUCCESS.format(category, subcategory)
        )
    
    # Show main menu after adding/removing category
    reply_markup = create_main_menu_keyboard(texts)
    await update.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return TRANSACTION


# Add a new handler function for the records count selection
async def handle_records_count(update: Update, context: CallbackContext):
    """Handle selection of how many records to display"""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    action = query.data
    
    if action == "back_to_transactions":
        # Go back to transactions menu
        reply_markup = create_show_transactions_keyboard(texts)
        await query.edit_message_text(
            texts.SHOW_TRANSACTIONS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after back_to_transactions")
        return TRANSACTION
    
    elif action.startswith("count_"):
        # Extract the count from the callback data
        count = action.split("_")[1]
        
        # Set the count as argument for latest_records
        context.args = [count]
        
        # Show loading message
        await query.edit_message_text(
            texts.LOADING_TRANSACTIONS.format(count=count)
        )
        
        # Call latest_records function
        await latest_records(update, context)
        
        # Return to main menu after showing transactions
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after showing {count} transactions")
        return TRANSACTION
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return TRANSACTION

async def latest_records(update: Update, context):
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    record_num_or_category = "5"  # Default value

    if context.args:
        record_num_or_category = context.args[0]

    records, total_amount = get_latest_records(user_id, record_num_or_category)

    if not records:
        if update.callback_query:
            await update.callback_query.message.reply_text(texts.NO_RECORDS)
        else:
            await update.message.reply_text(texts.NO_RECORDS)
    else:
        records_message = texts.LAST_RECORDS.format(total_amount, "\n".join(records))
        if update.callback_query:
            await update.callback_query.message.reply_text(records_message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(records_message, parse_mode=ParseMode.HTML)


async def delete_records(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    # Remove the leading '/' from the command
    command = update.effective_message.text.split()[0][1:]
    record_num = 1  # Default value

    if context.args:
        try:
            record_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text(texts.INVALID_RECORD_NUM)
            return

    if not record_exists(user_id):
        await update.message.reply_text(texts.NO_RECORDS_TO_DELETE)
    else:
        deleted = delete_record(user_id, record_num, command)
        if deleted:
            await update.message.reply_text(texts.RECORD_DELETED.format(record_num))
        else:

            await update.message.reply_text(texts.NOT_ENOUGH_RECORDS.format(record_num))


async def help(update: Update, context):
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    await update.message.reply_text(texts.HELP_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION

async def about(update: Update, context):
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    user_id = update.effective_user.id
    texts = check_language(update, context)
    name, currency, language, limit = read_config(user_id)
    
    reply_markup = create_settings_keyboard(texts)
    
    await update.message.reply_text(
        texts.ABOUT.format(name, currency, language, limit), 
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION

async def show_log(update: Update, context: CallbackContext):
    texts = check_language(update, context)
    #command = update.effective_message.text.split()[0][1:]
    record_num = 10  # Default value

    if context.args:
        try:
            record_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text(texts.INVALID_RECORD_NUM)
            return
        
    log_info = check_log(record_num)
    await update.message.reply_text(
        log_info,
        reply_markup=ReplyKeyboardRemove(),

    )
    return TRANSACTION

async def cancel(update: Update, context):
    texts = check_language(update, context)
    await update.message.reply_text(
        texts.CANCEL_TEXT,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def download_spendings(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    spendings_file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    await context.bot.send_document(
        chat_id=update.effective_chat.id, document=open(spendings_file_path, "rb")
    )


async def start_upload(update: Update, context: CallbackContext) -> int:
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    await update.message.reply_text(UPLOAD_FILE_TEXT)
    return WAITING_FOR_DOCUMENT


async def receive_document(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    document = update.message.document

    if not document.file_name.lower().endswith(".csv"):
        await update.message.reply_text(
            "Only CSV files are allowed. Please send a CSV file."
        )
        return WAITING_FOR_DOCUMENT

    new_spendings_file = await context.bot.get_file(update.message.document.file_id)

    # Create the backup and get the path to the current spendings file
    spendings_file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    backup_spendings(user_id, spendings_file_path)

    # Download the new file directly to the spendings file path
    await new_spendings_file.download_to_drive(custom_path=spendings_file_path)

    await update.message.reply_text(texts.UPLOADING_FINISHED)

    return ConversationHandler.END


async def cancel_upload(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Upload cancelled.")
    return ConversationHandler.END


async def archive_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    texts = check_language(update, context)
    # Check if this is a confirmation or initial request
    if update.message and update.message.text == "Delete profile" or update.message.text == "Удалить профиль":
        # User confirmed deletion
        result = await archive_user_data(user_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        return ConversationHandler.END
    else:
        # Initial request - ask for confirmation
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=texts.DELETE_PROFILE_CONFIRMATION,
            parse_mode=ParseMode.HTML
        )
        return DELETE_PROFILE  # Return to a state where we can catch the confirmation


async def send_chart(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    monthly_pivot_chart(user_id)
    monthly_line_chart(user_id)
    directory = f"user_data/{user_id}"

    # List all files in the directory and filter for those containing 'Monthly'
    monthly_images = [
        file
        for file in os.listdir(directory)
        if "monthly" in file and file.endswith(".jpg")
    ]
    # Create a list of InputMediaPhoto objects
    media = []
    for image in monthly_images:
        with open(os.path.join(directory, image), "rb") as file:
            media.append(InputMediaPhoto(file))

    backup_charts(user_id, monthly_images)
    await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)


async def send_ext_chart(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    monthly_ext_pivot_chart(user_id)
    #monthly_line_chart(user_id)
    directory = f"user_data/{user_id}"

    # List all files in the directory and filter for those containing 'Monthly'
    monthly_images = [
        file
        for file in os.listdir(directory)
        if "monthly_pivot" in file and file.endswith(".jpg")
    ]
    # Create a list of InputMediaPhoto objects
    media = []
    for image in monthly_images:
        with open(os.path.join(directory, image), "rb") as file:
            media.append(InputMediaPhoto(file))

    backup_charts(user_id, monthly_images)
    await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)


async def send_yearly_piechart(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    years = make_yearly_pie_chart(user_id)
    media, images = [], []
    for year in years:
        # Define the paths to your images
        image_path = f"user_data/{user_id}/yearly_pie_chart_{year}_{user_id}.jpg"
        images.append(image_path)
        with open(image_path, "rb") as file:
            media.append(InputMediaPhoto(file))
    backup_charts(user_id, images)

    await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)


async def start_income(update: Update, context: CallbackContext) -> None:
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    await update.effective_message.reply_text(
        texts.INCOME_HELP, parse_mode=ParseMode.HTML
    )
    return PROCESS_INCOME


async def process_income(update: Update, context: CallbackContext):
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    income_info = update.effective_message.text  # Get the income info from the message
    currency = get_user_currency(user_id)
    parts = income_info.lower().split()
    try:
        amount = float(parts[-1])
    except ValueError:
        await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
        return PROCESS_INCOME

    timestamp, category = process_income_input(user_id, parts)
    transaction_data = {
        "amount": amount,
        "currency": currency,
        "category": category,
        "timestamp": timestamp,
    }
    save_user_income(user_id, transaction_data)

    await update.effective_message.reply_text(texts.TRANSACTION_SAVED_TEXT)
    return ConversationHandler.END


# async def settings_callback(update: Update, context: CallbackContext):
#     query = update.callback_query
#     user_id = str(update.effective_user.id)
#     texts = check_language(update, context)
#     action = query.data
    
#     if action == "change_language":
#         reply_markup = create_settings_language_keyboard()
#         await query.edit_message_text(
#             texts.SELECT_LANGUAGE,
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#         return SETTINGS_LANGUAGE
        
#     elif action == "change_currency":
#         reply_markup = create_settings_currency_keyboard()
#         await query.edit_message_text(
#             texts.CHOOSE_CURRENCY_TEXT,
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#         return SETTINGS_CURRENCY
        
#     elif action == "change_limit":
#         context.user_data['awaiting_limit'] = True
#         await query.edit_message_text(texts.CHOOSE_LIMIT_TEXT)
#         return SETTINGS_LIMIT

async def handle_settings_language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(update.effective_user.id)    
    new_lang = query.data.split('_')[1]
    save_user_setting(user_id, "LANGUAGE", new_lang)
    texts = check_language(update, context)

    await query.edit_message_text(texts.LANGUAGE_REPLY.format(new_lang))
    
    # Send a new message with the main menu keyboard to continue interaction
    reply_markup = create_main_menu_keyboard(texts)
    await query.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION

async def handle_settings_currency(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    new_currency = query.data.split('_')[1]
    print("new_currency is", new_currency)
    save_user_setting(user_id, "CURRENCY", new_currency)
    await query.edit_message_text(texts.CURRENCY_REPLY.format(new_currency))
    
    # Send a new message with the main menu keyboard to continue interaction
    reply_markup = create_main_menu_keyboard(texts)
    await query.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    return TRANSACTION

async def handle_settings_limit(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    try:
        new_limit = float(update.message.text)
        save_user_setting(user_id, "MONTHLY_LIMIT", str(new_limit))
        await update.message.reply_text(texts.LIMIT_SET)
        
        # Show main menu after setting the limit
        reply_markup = create_main_menu_keyboard(texts)
        await update.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except ValueError:
        await update.message.reply_text("Invalid limit. Please enter a number.")
        return SETTINGS_LIMIT
    
    return TRANSACTION

async def show_menu(update: Update, context: CallbackContext):
    """Display the main menu"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    
    # Clear user_data cache when returning to main menu
    # Keep only essential data like language settings
    language = context.user_data.get('language', None)
    context.user_data.clear()
    print("context.user_data is", context.user_data)
    if language:
        context.user_data['language'] = language
    
    reply_markup = create_main_menu_keyboard(texts)
    await update.message.reply_text(
        texts.MAIN_MENU_TEXT,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    print("menu called, Transaction returned")
    return TRANSACTION

async def handle_text(update: Update, context):
    """Handle messages that aren't commands."""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)

    log_user_interaction(user_id, update.effective_user.first_name, update.effective_user.username)

    if update.message:
        # Handle text messages outside of commands
        text = update.message.text

        # Check if user directory exists
        user_dir = f"user_data/{user_id}"
        if not os.path.exists(user_dir):
            # If not, create the initial config for the user
            create_user_dir_and_copy_dict(user_id)
            await update.message.reply_text(texts.USER_CONFIG_CREATED)

        # Pattern matching based on update text format
        if re.match(r".*\s+\d+(\.\d+)?$", text):
            # Return a save transaction
            print(f" Text message matching spending pattern, calling save_transaction: {text}")
            return await save_transaction(update, context)
        
        # Default message back to the user if no patterns match
        await update.message.reply_text(
            texts.UNKNOWN_TEXT_FORMAT,
            parse_mode=ParseMode.HTML
        )
        
    return TRANSACTION


async def menu_call(update: Update, context: CallbackContext):
    """Handle menu callbacks"""
    query = update.callback_query
    print("debug printing: menu_call called")

    user_id = str(update.effective_user.id)
    texts = check_language(update, context)

    action = query.data
    
    # Menu option for edit_show_categories - this is what we need to modify
    if action == "edit_show_categories":
        await query.answer()
        # Call our show_categories function
        return await show_categories(update, context)
    
    # Add handler for edit_transactions menu option
    elif action == "menu_edit_transactions":
        await query.answer()
        # Use our dedicated wrapper function
        return await show_recent_entries(update, context)
    
    # Show transactions menu options
    elif action == "show_monthly_summary":
        print(" show_monthly_summary called")
        # Use existing function for monthly stats
        await query.answer()
        await query.edit_message_text("Loading monthly summary...")
        await show_records(update, context)
        
        # Return to main menu after showing stats
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after show_monthly_summary")
        return TRANSACTION
        
    elif action == "show_last_month_summary":
        print(" show_last_month_summary called")
        # Use new function for last month stats
        await query.answer()
        await query.edit_message_text("Loading last month summary...")
        await show_last_month_records(update, context)
        
        # Return to main menu after showing stats
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION
        
    elif action == "show_last_transactions":
        # UPDATED: Start the detailed transactions flow instead of showing record count keyboard
        await query.answer()
        # Call our new function to show category selection
        return await start_detailed_transactions(update, context)
        
        
    elif action == "show_monthly_charts":
        # Use existing function for monthly charts
        await query.answer()
        await query.edit_message_text("Generating monthly charts...")
        await send_chart(update, context)
        
        # Return to main menu after showing charts
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after show_monthly_charts")
        return TRANSACTION
        
    elif action == "show_extended_stats":
        # Use existing function for extended stats
        await query.answer()
        await query.edit_message_text("Loading extended statistics...")
        await show_detailed(update, context)
        
        # Return to main menu after showing extended stats
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after show_extended_stats")
        return TRANSACTION
        
    elif action == "show_yearly_charts":
        # Use existing function for yearly charts
        await query.answer()
        await query.edit_message_text("Generating yearly charts...")
        await send_yearly_piechart(update, context)
        
        # Return to main menu after showing yearly charts
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after show_yearly_charts")
        return TRANSACTION
        
    elif action == "show_income_stats":
        # Use existing function for income stats
        await query.answer()
        await query.edit_message_text("Loading income statistics...")
        
        # Adjust context to simulate the command
        update.effective_message.text = "/show_income"
        await show_records(update, context)
        
        # Return to main menu after showing income stats
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after show_income_stats")
        return TRANSACTION
    
    # Main menu options
    elif action == "menu_add_transaction" or action == "back_to_categories":
        # Get frequently used categories
        print("Debug: menu_add_transaction or back_to_categories called")
        categories = get_frequently_used_categories(user_id)
        
        # If no categories found, use the dictionary keys
        if not categories:
            cat_dict = read_dictionary(user_id)
            categories = list(cat_dict.keys())
        
        # Store categories and current page in context
        context.user_data["tx_categories"] = categories
        context.user_data["tx_page"] = 0
        
        # Create and show the categories keyboard
        reply_markup = create_tx_categories_keyboard(categories, texts, context.user_data["tx_page"])
        await query.edit_message_text(
            texts.SELECT_TRANSACTION_CATEGORY,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state SELECT_TRANSACTION_CATEGORY after menu_add_transaction")
        return SELECT_TRANSACTION_CATEGORY
    
    elif action == "menu_show_transactions":
        reply_markup = create_show_transactions_keyboard(texts)
        await query.edit_message_text(
            texts.SHOW_TRANSACTIONS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after menu_show_transactions")
        return TRANSACTION
        
    elif action == "menu_settings":
        reply_markup = create_settings_keyboard_menu(texts)
        await query.edit_message_text(
            texts.SETTINGS_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after menu_settings")
        return TRANSACTION
        
    elif action == "menu_edit_categories":
        await query.answer()
        # Import show_categories from change_data
        from change_data import show_categories, CATEGORY_MANAGEMENT
        
        # Reset the current page when entering category management
        context.user_data["current_page"] = 0
        
        return await show_categories(update, context)
        
    elif action == "menu_help":
        await query.edit_message_text(
            texts.HELP_TEXT,
        )
        # Send a new message with the main menu keyboard to continue interaction
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after menu_help")
        return TRANSACTION
        
    # Back to main menu from any submenu
    elif action == "back_to_main_menu":
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after back_to_main_menu")
        return TRANSACTION
    
    # Settings submenu
    elif action == "settings_change_language":
        reply_markup = create_settings_language_keyboard()
        await query.edit_message_text(
            texts.SELECT_LANGUAGE,
            reply_markup=reply_markup
        )
        return SETTINGS_LANGUAGE
        
    elif action == "settings_change_currency":
        reply_markup = create_settings_currency_keyboard()
        await query.edit_message_text(
            texts.CHOOSE_CURRENCY_TEXT,
            reply_markup=reply_markup
        )
        return SETTINGS_CURRENCY
        
    elif action == "settings_change_limit":
        context.user_data['awaiting_limit'] = True
        await query.edit_message_text(texts.CHOOSE_LIMIT_TEXT)
        return SETTINGS_LIMIT
        
    elif action == "settings_about":
        # Get user info for about page
        name, currency, language, limit = read_config(user_id)
        await query.edit_message_text(
            texts.ABOUT.format(query.from_user.first_name, currency, language, limit),
            parse_mode=ParseMode.HTML
        )
        
        # Send a new message with the main menu keyboard to continue interaction
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.BACK_TO_MAIN_MENU,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION
    elif action == "cancel_transaction":
        print(" cancel_transaction called")
        await query.edit_message_text(
            texts.TRANSACTION_CANCELED,
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(1)
        reply_markup = create_main_menu_keyboard(texts)
        await query.message.reply_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        #print(f" Returning state TRANSACTION after cancel_transaction")
        return TRANSACTION
    # Edit categories submenu
    elif action == "edit_add_remove_category":
        await query.edit_message_text(
            texts.ADD_CAT_PROMPT,
            parse_mode="MarkdownV2"
        )
        return ADD_CATEGORY
    print(f" Returning state TRANSACTION after menu_call")
    return TRANSACTION
 
async def menu_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    print(f" menu_callback called")
    return await menu_call(update, context)
    
async def update_file_structure(update: Update, context: CallbackContext) -> None:
    """Handle the /update_file command to update the structure of the user's spendings file."""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    if user_id == "46304833":
        # Call the function to update the file structure
        result = migrate_all_user_files_to_new_structure()
        
    # Send a message back to the user with the result
    if result["success"]:
        await update.message.reply_text(f"✅ {result['message']}")
    else:
        await update.message.reply_text(f"❌ {result['message']}")
    
    return TRANSACTION

def main():
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("show", show_records))
    application.add_handler(CommandHandler("show_ext", show_detailed))
    application.add_handler(CommandHandler("show_income", show_records))
    application.add_handler(CommandHandler("show_cat", show_cat))
    application.add_handler(CommandHandler("show_last", latest_records))
    application.add_handler(CommandHandler("delete", delete_records))
    application.add_handler(CommandHandler("delete_income", delete_records))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("download", download_spendings))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("monthly_stat", send_chart))
    application.add_handler(CommandHandler("monthly_ext_stat", send_ext_chart))
    application.add_handler(CommandHandler("yearly_stat", send_yearly_piechart))
    application.add_handler(CommandHandler("show_log", show_log))
    application.add_handler(CommandHandler("update_files", update_file_structure))

    # Handler for the leave command to archive user profile
    leave_handler = ConversationHandler(
        entry_points=[CommandHandler("leave", archive_profile)],
        states={
            DELETE_PROFILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, archive_profile)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(leave_handler)

    income_handler = ConversationHandler(
        entry_points=[CommandHandler("income", start_income)],
        states={
            PROCESS_INCOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_income)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(income_handler)

    upload_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("upload", start_upload)],
        states={
            WAITING_FOR_DOCUMENT: [
                MessageHandler(filters.Document.ALL, receive_document)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)],
    )
    application.add_handler(upload_conv_handler)

#Main handler
    spendings_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", show_menu),
            CommandHandler("change_cat", show_menu),
            # This regex catches strings that contain a word followed by a space and then a number at the end of the string.
            MessageHandler(filters.Regex(r"\b\w+\s+\d+$"), handle_text),
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(save_language)],
            CURRENCY: [CallbackQueryHandler(save_currency)],
            LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_limit),
                CallbackQueryHandler(skip_limit, pattern="^skip$"),
            ],
            TRANSACTION: [
                # Transaction category selection
                CallbackQueryHandler(select_category_for_transaction, pattern="^(cat_|show_all_categories|use_|create_new_category)"),
                # Transaction flow
                CallbackQueryHandler(handle_transaction_category, pattern="^txcat_"),
                CallbackQueryHandler(handle_transaction_subcategory, pattern="^txsubcat_"),
                CallbackQueryHandler(handle_transaction_amount, pattern="^txamount_"),
                CallbackQueryHandler(handle_transaction_confirmation, pattern="^confirm_transaction"),
                # Navigation and menus
                CallbackQueryHandler(menu_call, pattern="^(cancel_transaction|back_to_main_menu)"),
                CallbackQueryHandler(menu_call, pattern="^menu_"),
                # For showing various reports
                CallbackQueryHandler(menu_call, pattern="^(show_monthly_summary|show_last_month_summary|show_last_transactions|show_monthly_charts|show_extended_stats|show_yearly_charts|show_income_stats)"),
                # For text input of transaction amount
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction_amount),
            ],
            # Add the category management states from change_data
            CATEGORY_MANAGEMENT: [
                CallbackQueryHandler(handle_category_selection, pattern="^cat_"),
                CallbackQueryHandler(handle_category_selection, pattern="^catpage_(prev|next)$"),
                CallbackQueryHandler(handle_category_selection, pattern="^add_new_category$"),
                CallbackQueryHandler(handle_category_selection, pattern="^back_to_main_menu$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_new_category),
            ],
            CATEGORY_EDIT: [
                CallbackQueryHandler(handle_category_option, pattern="^(change_name_|delete_category_|edit_tasks_|back_to_categories)"),
                CallbackQueryHandler(handle_rename_confirmation, pattern="^(confirm_rename_|cancel_rename_)"),
                CallbackQueryHandler(handle_delete_cat_confirmation, pattern="^(confirm_delete_|cancel_delete_)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_name),
            ],
            TASK_MANAGEMENT: [
                CallbackQueryHandler(handle_tasks_action, pattern="^(back_to_category_|add_task_|task_)"),
                CallbackQueryHandler(handle_task_option, pattern="^(back_to_tasks_|edit_task_|delete_task_)"),
                CallbackQueryHandler(handle_task_delete_confirmation, pattern="^(confirm_delete_task_|cancel_delete_task_)"),
            ],
            SETTINGS_LANGUAGE: [
                CallbackQueryHandler(handle_settings_language, pattern="^(lang_)"),
            ],
            SETTINGS_CURRENCY: [
                CallbackQueryHandler(handle_settings_currency, pattern="^(cur_)"),
            ],
            SETTINGS_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_limit)
            ],
            SELECT_RECORDS_COUNT: [
                CallbackQueryHandler(handle_records_count, pattern="^(count_|back_to_transactions)"),
            ],
            TASK_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_task),
                CallbackQueryHandler(handle_task_edit_confirmation, pattern="^(confirm_rename_task_|cancel_rename_task_)"),
            ],

            SELECT_TRANSACTION_CATEGORY: [
                CallbackQueryHandler(handle_transaction_category, pattern="^(txcat_|txpage_|cancel_transaction)"),

            ],
            SELECT_TRANSACTION_SUBCATEGORY: [
                CallbackQueryHandler(handle_transaction_subcategory, pattern="^(txsubcat_|txsubpage_|back_to_categories|cancel_transaction)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction_subcategory),
            ],
            ENTER_TRANSACTION_AMOUNT: [
                CallbackQueryHandler(handle_transaction_amount, pattern="^(txamount_|back_to_subcategories|cancel_transaction)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction_amount),
            ],
            CONFIRM_TRANSACTION: [
                CallbackQueryHandler(handle_transaction_confirmation, pattern="^(confirm_transaction|cancel_transaction)"),
            ],
            HANDLE_TRANSACTION_CREATE_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_new_category_transaction),
            ],
            TRANSACTION_LIST: [
                CallbackQueryHandler(handle_transaction_selection, pattern="^(tx_|tx_next_page|tx_prev_page)"),
                CallbackQueryHandler(menu_call, pattern="^back_to_main_menu"),
            ],
            TRANSACTION_EDIT: [
                CallbackQueryHandler(handle_edit_option, pattern="^(edit_date|edit_category|edit_subcategory|edit_amount|delete_transaction)"),
                CallbackQueryHandler(handle_edit_option, pattern="^back_to_transactions"),
            ],
            EDIT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_date),
            ],
            EDIT_CATEGORY: [
                CallbackQueryHandler(handle_edit_category, pattern="^(txcat_|txpage_|cancel_transaction)"),
            ],
            EDIT_SUBCATEGORY: [
                CallbackQueryHandler(handle_edit_subcategory, pattern="^(back_to_categories|cancel_transaction)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_subcategory),
            ],
            EDIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_amount),
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(handle_delete_tx_confirmation, pattern="^(confirm|cancel)"),
            ],
            TX_CHOOSE_CATEGORY: [
                CallbackQueryHandler(select_category_for_transaction, pattern="^cat_"),
                CallbackQueryHandler(select_category_for_transaction, pattern="^catpage_(prev|next)$"),
                CallbackQueryHandler(select_category_for_transaction, pattern="^(show_all_categories|use_|create_new_category)"),
                CallbackQueryHandler(menu_call, pattern="^back_to_main_menu"),
            ],
            # Add the new detailed transactions states
            SELECT_CATEGORIES: [
                CallbackQueryHandler(handle_detailed_category_selection, pattern="^(selcat_|selcatpage_|back_to_transactions)"),
            ],
            SELECT_TIME_PERIOD: [
                CallbackQueryHandler(handle_time_period_selection, pattern="^(period_|back_to_categories)"),
            ],
            SHOW_SUMMARY: [
                CallbackQueryHandler(handle_summary_action, pattern="^(view_transactions|back_|back_to_main_menu)"),
            ],
            SHOW_TRANSACTIONS: [
                CallbackQueryHandler(handle_transaction_navigation, pattern="^(tx_|dtx_display_|dtx_prev_page|dtx_next_page|back_)"),
            ],
        },
        allow_reentry=True,
        fallbacks=[CommandHandler("cancel", cancel),
                   CallbackQueryHandler(menu_callback)
                   ],

    )
    application.add_handler(spendings_handler)
    # message handler for text input
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
