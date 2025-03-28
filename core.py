import os, logging, configparser, inspect, re, importlib
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from dateutil.relativedelta import relativedelta

from pandas_ops import (
    show_sum_per_cat,
    show_top_subcategories,
    get_top_categories,
    calculate_limit,
    get_user_path,get_user_currency, 
)
from charts import monthly_line_chart, monthly_pivot_chart, make_yearly_pie_chart,monthly_ext_pivot_chart
from utils import process_transaction_input, process_income_input
from file_ops import (
    create_user_dir_and_copy_dict,
    backup_spendings,
    save_user_setting,
    save_user_transaction,
    save_user_income,
    get_records,
    check_config_exists,
    read_dictionary,
    add_category,
    remove_category,
    get_latest_records,
    delete_record,
    record_exists,
    check_dictionary_format,
    update_user_list,
    archive_user_data,
    backup_charts,
    read_config,
    check_log,
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


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO , handlers=[
        TimedRotatingFileHandler(
            'user_data/app.log',
            when="m",
            interval=10,
            backupCount=5
        )
    ])
logging.getLogger("httpx").setLevel(logging.WARNING)

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
print (config["TELEGRAM"]["TEST"])
(
    LANGUAGE,
    CURRENCY,
    LIMIT,
    TRANSACTION,
    CHOOSE_CATEGORY,
    SPECIFY_CATEGORY,
    ADD_CATEGORY,
    SETTINGS_LANGUAGE,
    SETTINGS_CURRENCY,
    SETTINGS_LIMIT,
) = range(10)
WAITING_FOR_DOCUMENT = 1
PROCESS_INCOME = 1


def get_user_language(user_id):
    config = configparser.ConfigParser()
    config_path = f"user_data/{user_id}/config.ini"
    config.read(config_path)
    language = config.get(
        "DEFAULT", "language", fallback="en"
    )  # Fallback to 'en' if not set
   # print(language)
    return language


def check_language(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    language = get_user_language(user_id)

    # Dynamically import the correct texts module based on language
    if language == "ru":
        texts_module = importlib.import_module("texts_ru")
    else:
        texts_module = importlib.import_module("texts")

    return texts_module


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
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Русский", callback_data="ru"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(texts.SELECT_LANGUAGE, reply_markup=reply_markup)
    return LANGUAGE


async def language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_language = query.data
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    # Save the chosen language into the config file
    save_user_setting(user_id, "LANGUAGE", user_language)
    inline_keyboard = [
        [
            InlineKeyboardButton("USD", callback_data="USD"),
            InlineKeyboardButton("EUR", callback_data="EUR"),
            InlineKeyboardButton("AMD", callback_data="AMD"),
            InlineKeyboardButton("RUB", callback_data="RUB"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)
    await query.edit_message_text(texts.LANGUAGE_REPLY.format(user_language))
    await update.effective_message.reply_text(
        texts.CHOOSE_CURRENCY_TEXT, reply_markup=reply_markup
    )
    return CURRENCY


async def save_currency(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    user_currency = update.callback_query.data
    save_user_setting(user_id, "CURRENCY", user_currency)

    keyboard = [[InlineKeyboardButton("Skip", callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

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
    save_user_setting(user_id, "MONTHLY_LIMIT", str(9999999))

    await update.effective_message.reply_text(texts.NO_LIMIT)
    await update.effective_message.reply_text(texts.TRANSACTION_START_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION  # Or whatever state should come next


async def save_transaction(update: Update, context):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    currency = get_user_currency(user_id)
    transactions = re.split(",|\n", update.message.text.lower())
    list_subcat = []
    for transaction in transactions:
        parts = transaction.lower().split()
        try:
            amount = float(parts[-1])
        except ValueError:
            await update.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
            return TRANSACTION

        timestamp, category, subcategory, unknown_cat = process_transaction_input(
            user_id, parts
        )
        transaction_data = {
            "id": user_id,
            "amount": amount,
            "currency": currency,
            "category": category,
            "subcategory": subcategory,
            "timestamp": timestamp,
        }
        if unknown_cat:
            if len(transactions) > 1:
                # Save the transaction with category as 'Other'
                transaction_data["category"] = "other"
                save_user_transaction(user_id, transaction_data)
                list_subcat.append(subcategory)
            else:
                # Get the top 5 categories
                user_path = get_user_path(user_id)
                top_categories = get_top_categories(user_path)
                # Create an inline keyboard with the top categories
                keyboard = [
                    [InlineKeyboardButton(cat, callback_data=cat)]
                    for cat in top_categories
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                # Send the keyboard to the user
                await update.message.reply_text(
                    texts.CHOOSE_CATEGORY_PROMPT.format(subcategory),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
                # The chosen category will be handled in the handle_button_press function
                context.user_data["subcategory"] = subcategory
                context.user_data["transaction_data"] = transaction_data

                return CHOOSE_CATEGORY
        else:
            save_user_transaction(user_id, transaction_data)
    if len(transactions) and unknown_cat > 1:
        await update.message.reply_text(
            texts.NOTIFY_OTHER_CAT.format(list_subcat), parse_mode=ParseMode.HTML
        )
    try:
        (
            current_daily_average,
            percent_difference,
            daily_limit,
            days_zero_spending,
            new_daily_limit,
        ) = calculate_limit(user_id)
        await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)
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
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        await update.message.reply_text(texts.TRANSACTION_SAVED_TEXT)

    return TRANSACTION


async def choose_category(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    category = update.callback_query.data
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")
    transaction_data["category"] = category

    if subcategory:
        add_category(user_id, category, subcategory)
        await update.effective_message.reply_text(
            texts.CONFIRM_SAVE_CAT.format(category, subcategory),
            parse_mode=ParseMode.HTML,
        )
        save_user_transaction(user_id, transaction_data)
        await update.effective_message.reply_text(texts.TRANSACTION_SAVED_TEXT)

    else:
        await update.effective_message.reply_text(
            "An error occurred. Please try again."
        )

    return TRANSACTION


async def handle_specify_category(update: Update, context: CallbackContext):
    context.user_data["state"] = "handle_specify_category"
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    category = update.effective_message.text.lower()
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")

    # Save the chosen category in the dictionary
    add_category(user_id, category, subcategory)
    # Update the category in the transaction_data dictionary
    transaction_data["category"] = category
    # Save the transaction with the updated category
    save_user_transaction(user_id, transaction_data)
    # Send a confirmation message to the user
    await update.effective_message.reply_text(
        texts.CONFIRM_SAVE_CAT.format(category, subcategory), parse_mode=ParseMode.HTML
    )
    await update.effective_message.reply_text(texts.TRANSACTION_SAVED_TEXT)

    return TRANSACTION


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
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        print(f"Exception: {e}")       
        pass
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

    await update.message.reply_text(output)

    return TRANSACTION


async def handle_text(update: Update, context):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    if context.user_data.get('awaiting_limit'):
        try:
            new_limit = float(update.message.text)
            save_user_setting(user_id, "MONTHLY_LIMIT", str(new_limit))
            context.user_data['awaiting_limit'] = False
            await update.message.reply_text(texts.LIMIT_SET)
            return TRANSACTION
        except ValueError:
            await update.message.reply_text("Invalid limit. Please enter a number.")
            return SETTINGS_LIMIT

    if check_config_exists(user_id):
        parts = update.message.text.lower().split()
        try:
            if float(parts[-1]):
                return await save_transaction(update, context)
        except ValueError:
            pass

    await update.message.reply_text(texts.START_COMMAND_PROMPT)


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

    return TRANSACTION


async def latest_records(update: Update, context: CallbackContext):
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
        await update.message.reply_text(texts.NO_RECORDS)
    else:
        records_message = texts.LAST_RECORDS.format(total_amount, "\n".join(records))
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
    
    keyboard = [
        [
            InlineKeyboardButton("Change Language", callback_data="change_language"),
            InlineKeyboardButton("Change Currency", callback_data="change_currency"),
        ],
        [InlineKeyboardButton("Change Limit", callback_data="change_limit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        texts.ABOUT.format(name, currency, language, limit), 
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
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
    await update.message.reply_text("Please upload your file")
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
    backup_spendings(user_id)
    spendings_file_path = f"user_data/{user_id}/spendings_{user_id}.csv"

    # Download the new file directly to the spendings file path
    await new_spendings_file.download_to_drive(custom_path=spendings_file_path)

    await update.message.reply_text(texts.UPLOADING_FINISHED)

    return ConversationHandler.END


async def cancel_upload(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Upload cancelled.")
    return ConversationHandler.END


async def archive_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    result = await archive_user_data(user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
    return ConversationHandler.END


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


async def settings_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    action = query.data
    
    if action == "change_language":
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="lang_en"),
                InlineKeyboardButton("Русский", callback_data="lang_ru"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            texts.SELECT_LANGUAGE,
            reply_markup=reply_markup
        )
        return SETTINGS_LANGUAGE
        
    elif action == "change_currency":
        keyboard = [
            [
                InlineKeyboardButton("USD", callback_data="cur_USD"),
                InlineKeyboardButton("EUR", callback_data="cur_EUR"),
                InlineKeyboardButton("AMD", callback_data="cur_AMD"),
                InlineKeyboardButton("RUB", callback_data="cur_RUB"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            texts.CHOOSE_CURRENCY_TEXT,
            reply_markup=reply_markup
        )
        return SETTINGS_CURRENCY
        
    elif action == "change_limit":
        context.user_data['awaiting_limit'] = True
        await query.edit_message_text(texts.CHOOSE_LIMIT_TEXT)
        return SETTINGS_LIMIT

async def handle_settings_language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    new_lang = query.data.split('_')[1]
    save_user_setting(user_id, "LANGUAGE", new_lang)
    await query.edit_message_text(texts.LANGUAGE_REPLY.format(new_lang))
    return TRANSACTION

async def handle_settings_currency(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    new_currency = query.data.split('_')[1]
    save_user_setting(user_id, "CURRENCY", new_currency)
    await query.edit_message_text(texts.CURRENCY_REPLY.format(new_currency))
    return TRANSACTION

async def handle_settings_limit(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    try:
        new_limit = float(update.message.text)
        save_user_setting(user_id, "MONTHLY_LIMIT", str(new_limit))
        await update.message.reply_text(texts.LIMIT_SET)
    except ValueError:
        await update.message.reply_text("Invalid limit. Please enter a number.")
        return SETTINGS_LIMIT
    
    return TRANSACTION
async def show_statistics(update: Update, context: CallbackContext) -> None:
    """Show statistics of bot usage for the last 3 months"""
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    tg_username = update.effective_user.username
    log_user_interaction(user_id, username, tg_username, "show_statistics")
    
    print(f"[STATS] Starting statistics generation for user {user_id}")
    await update.message.reply_text("Analyzing bot usage statistics for the last 3 months... Please wait.")
    
    # Path to the global log file
    log_file_path = "user_data/global_log.txt"
    
    if not os.path.exists(log_file_path):
        print(f"[STATS] Error: Log file not found at {log_file_path}")
        await update.message.reply_text("No log data found.")
        return
    
    print(f"[STATS] Reading log file from {log_file_path}")
    # Read the log file
    with open(log_file_path, 'r') as file:
        log_lines = file.readlines()
    
    print(f"[STATS] Found {len(log_lines)} log entries to process")
    
    # Calculate the date 3 months ago from today
    three_months_ago = datetime.datetime.now() - relativedelta(months=3)
    print(f"[STATS] Filtering data from {three_months_ago} onwards")
    
    # Parse log data
    data = []
    skipped_entries = 0
    for line in log_lines:
        try:
            # Extract timestamp, user info, and action
            parts = line.strip().split(' - ')
            if len(parts) != 2:
                skipped_entries += 1
                continue
                
            timestamp_str = parts[0]
            user_action_info = parts[1]
            
            # Parse timestamp
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            
            # Skip entries older than 3 months
            if timestamp < three_months_ago:
                skipped_entries += 1
                continue
                
            # Extract user info and action
            user_action_parts = user_action_info.split(', ')
            if len(user_action_parts) < 4:
                skipped_entries += 1
                continue
                
            user_id = user_action_parts[0].replace("UserID: ", "")
            username = user_action_parts[1]
            tg_username = user_action_parts[2]
            action = user_action_parts[3]
            
            data.append({
                'timestamp': timestamp,
                'date': timestamp.date(),
                'user_id': user_id,
                'username': username,
                'tg_username': tg_username,
                'action': action
            })
            
        except Exception as e:
            print(f"[STATS] Error parsing log line: {e}")
            skipped_entries += 1
            continue
    
    print(f"[STATS] Successfully parsed {len(data)} entries, skipped {skipped_entries} entries")
    
    if not data:
        print("[STATS] No valid data found for the last 3 months")
        await update.message.reply_text("No data found for the last 3 months.")
        return
    
    # Create DataFrame
    print("[STATS] Creating DataFrame from parsed data")
    df = pd.DataFrame(data)
    
    # Generate statistics
    total_actions = len(df)
    unique_users = df['user_id'].nunique()
    action_counts = df['action'].value_counts().to_dict()
    daily_counts = df.groupby('date').size()
    
    print(f"[STATS] Statistics summary: {total_actions} actions, {unique_users} unique users")
    print(f"[STATS] Top actions: {list(sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5])}")
    
    # Create a plot for daily activity by user
    print("[STATS] Generating daily activity by user plot")
    plt.figure(figsize=(14, 8))
    
    # Group by date and user, then count actions
    user_daily_counts = df.groupby(['date', 'username']).size().unstack().fillna(0)
    
    # Plot stacked bar chart for user activity
    user_daily_counts.plot(kind='bar', stacked=True)
    plt.title('Daily Bot Activity by User (Last 3 Months)')
    plt.xlabel('Date')
    plt.ylabel('Number of Actions')
    plt.grid(True, axis='y')
    plt.legend(title='Users', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Save the plot
    plot_path = "user_data/bot_statistics_by_user.png"
    plt.savefig(plot_path)
    plt.close()
    print(f"[STATS] Daily activity by user plot saved to {plot_path}")
    
    # Create a plot for action distribution
    print("[STATS] Generating action distribution plot")
    plt.figure(figsize=(12, 6))
    action_series = pd.Series(action_counts)
    action_series.sort_values(ascending=False).head(10).plot(kind='bar')
    plt.title('Top 10 Bot Actions (Last 3 Months)')
    plt.xlabel('Action')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    action_plot_path = "user_data/action_statistics.png"
    plt.savefig(action_plot_path)
    plt.close()
    print(f"[STATS] Action distribution plot saved to {action_plot_path}")
    
    # Create a plot for user activity summary
    print("[STATS] Generating user activity summary plot")
    plt.figure(figsize=(12, 6))
    user_counts = df.groupby('username').size().sort_values(ascending=False)
    user_counts.plot(kind='bar')
    plt.title('Total Actions by User (Last 3 Months)')
    plt.xlabel('User')
    plt.ylabel('Number of Actions')
    plt.grid(True, axis='y')
    plt.tight_layout()
    
    # Save the plot
    user_plot_path = "user_data/user_statistics.png"
    plt.savefig(user_plot_path)
    plt.close()
    print(f"[STATS] User activity summary plot saved to {user_plot_path}")
    
    # Prepare statistics message
    stats_message = f"📊 *Bot Usage Statistics (Last 3 Months)*\n\n"
    stats_message += f"Total actions: {total_actions}\n"
    stats_message += f"Unique users: {unique_users}\n\n"
    stats_message += "*Top 5 Actions:*\n"
    
    # Add top 5 actions to the message
    for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        stats_message += f"- {action}: {count}\n"
    
    # Add top 5 users to the message
    stats_message += "\n*Top 5 Users by Activity:*\n"
    for username, count in user_counts.head(5).items():
        stats_message += f"- {username}: {count} actions\n"
    
    # Send statistics message
    print("[STATS] Sending statistics message to user")
    await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    # Send the plots
    print("[STATS] Sending plots to user")
    await update.message.reply_photo(open(plot_path, 'rb'), caption="Daily activity by user over the last 3 months")
    await update.message.reply_photo(open(action_plot_path, 'rb'), caption="Top 10 actions over the last 3 months")
    await update.message.reply_photo(open(user_plot_path, 'rb'), caption="Total actions by user over the last 3 months")
    print("[STATS] Statistics generation completed successfully")

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
    application.add_handler(CommandHandler("leave", archive_profile))
    application.add_handler(CommandHandler("monthly_stat", send_chart))
    application.add_handler(CommandHandler("monthly_ext_stat", send_ext_chart))
    application.add_handler(CommandHandler("yearly_stat", send_yearly_piechart))
    application.add_handler(CommandHandler("show_log", show_log))
    application.add_handler(CommandHandler("statistic", show_statistics))
    application.add_handler(CommandHandler("statistics", show_statistics))  # Add plural form


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

    spendings_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("change_cat", add_cat),
            MessageHandler(filters.Regex(r"\b\w+\s+\d+$"), handle_text),
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(language)],
            CURRENCY: [CallbackQueryHandler(save_currency)],
            LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_limit),
                CallbackQueryHandler(skip_limit, pattern="^skip$"),
            ],
            TRANSACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_transaction),
                CallbackQueryHandler(settings_callback, pattern="^change_"),
            ],
            CHOOSE_CATEGORY: [
                CallbackQueryHandler(choose_category),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_specify_category
                ),
            ],
            ADD_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_category)
            ],
            SETTINGS_LANGUAGE: [CallbackQueryHandler(handle_settings_language, pattern="^lang_")],
            SETTINGS_CURRENCY: [CallbackQueryHandler(handle_settings_currency, pattern="^cur_")],
            SETTINGS_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_limit)],
        },
        allow_reentry=True,
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(spendings_handler)
    # message handler for text input
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    # Add handlers for settings changes
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^change_"))
    application.add_handler(CallbackQueryHandler(handle_settings_language, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(handle_settings_currency, pattern="^cur_"))
    
    application.run_polling()


if __name__ == "__main__":
    main()
