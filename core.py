import logging, configparser, inspect, re
from pandas_ops import show_sum_per_cat, show_top_subcategories, get_top_categories
from utils import process_transaction_input, get_user_currency
from file_ops import (
    create_user_dir_and_copy_dict,
    backup_spendings,
    save_user_setting,
    save_user_transaction,
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
    read_dictionary,
    archive_user_data,
)
from texts import (
    CHOOSE_CURRENCY_TEXT,
    TRANSACTION_START_TEXT,
    TRANSACTION_SAVED_TEXT,
    TRANSACTION_ERROR_TEXT,
    RECORDS_NOT_FOUND_TEXT,
    RECORDS_TEMPLATE,
    START_COMMAND_PROMPT,
    CAT_DICT_MESSAGE,
    ADD_CAT_PROMPT,
    ADD_CAT_SUCCESS,
    DEL_CAT_SUCCESS,
    WRONG_INPUT_FORMAT,
    INVALID_RECORD_NUM,
    NO_RECORDS,
    RECORD_LINE,
    INVALID_RECORD_NUM,
    NO_RECORDS_TO_DELETE,
    RECORD_DELETED,
    NOT_ENOUGH_RECORDS,
    CANCEL_TEXT,
    HELP_TEXT,
    LANGUAGE_REPLY,
    SELECT_LANGUAGE,
    CONFIRM_SAVE_CAT,
    REQUEST_CAT,
    SPECIFY_MANUALLY_PROMPT,
    CHOOSE_CATEGORY_PROMPT,
)


from telegram import (
    Update,
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logger = logging.getLogger("user_interactions")
logger.setLevel(logging.INFO)

# Create file handler
handler = logging.FileHandler("global_log.txt")
handler.setLevel(logging.INFO)

# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)


def log_user_interaction(user_id: str, username: str, tg_username: str):
    calling_function_name = inspect.stack()[1].function

    log_message = (
        f"UserID: {user_id}, {username}, {tg_username}, {calling_function_name}"
    )
    logger.info(log_message)


config = configparser.ConfigParser()
config.read("configs/config")
token = config["TELEGRAM"]["TOKEN"]

(
    NAME,
    LANGUAGE,
    CURRENCY,
    TRANSACTION,
    PROCESS_NEXT,
    CHOOSE_CATEGORY,
    SPECIFY_CATEGORY,
    ADD_CATEGORY,
) = range(8)
WAITING_FOR_DOCUMENT = 1


async def start(update: Update, context: CallbackContext):

    user_id = str(update.effective_user.id)
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

    await update.message.reply_text(SELECT_LANGUAGE, reply_markup=reply_markup)
    return LANGUAGE


async def language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_language = query.data
    user_id = update.effective_user.id

    # Save the chosen language into the config file
    save_user_setting(user_id, "LANGUAGE", user_language)

    await update.callback_query.message.edit_text(LANGUAGE_REPLY.format(user_language))
    return NAME


async def save_name(update: Update, context):
    user_id = str(update.effective_user.id)
    user_name = update.message.text

    save_user_setting(user_id, "NAME", user_name)

    inline_keyboard = [
        [
            InlineKeyboardButton("USD", callback_data="USD"),
            InlineKeyboardButton("EUR", callback_data="EUR"),
            InlineKeyboardButton("AMD", callback_data="AMD"),
            InlineKeyboardButton("RUB", callback_data="RUB"),
        ],
    ]
    markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(CHOOSE_CURRENCY_TEXT, reply_markup=markup)
    return CURRENCY


async def save_currency(update: Update, context):
    user_id = str(update.effective_user.id)
    user_currency = update.callback_query.data
    save_user_setting(user_id, "CURRENCY", user_currency)

    await update.callback_query.message.edit_text(
        TRANSACTION_START_TEXT,
        parse_mode="MarkdownV2",
    )
    return TRANSACTION


async def save_transaction(update: Update, context):
    print("ST-1", context.user_data.get("transactions"))
    user_id = str(update.effective_user.id)
    currency = get_user_currency(user_id)

    if (
        not context.user_data.get("transactions")
        and update.effective_message.from_user.id != context.bot.id
    ):
        context.user_data["transactions"] = re.split(
            ",|\n", update.effective_message.text.lower()
        )

    print("ST-1.1", context.user_data.get("transactions"))

    transaction = context.user_data["transactions"][0]
    parts = transaction.lower().split()
    try:
        amount = float(parts[-1])
    except ValueError:
        await update.effective_message.reply_text(TRANSACTION_ERROR_TEXT)
        context.user_data["transactions"] = []
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
        top_categories = get_top_categories(user_id)
        keyboard = [
            [InlineKeyboardButton(cat, callback_data=cat)] for cat in top_categories
        ]
        keyboard.append(
            [
                InlineKeyboardButton(
                    SPECIFY_MANUALLY_PROMPT, callback_data="enter_manually"
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(
            CHOOSE_CATEGORY_PROMPT.format(subcategory), reply_markup=reply_markup
        )

        context.user_data["subcategory"] = subcategory
        context.user_data["transaction_data"] = transaction_data

        if "state" not in context.user_data:
            context.user_data["state"] = "save_transaction"

        print("ST-2", context.user_data.get("transactions"))

        if context.user_data["state"] == "process_next":
            print("ST-3")
            return CHOOSE_CATEGORY
        else:
            return PROCESS_NEXT

    else:
        save_user_transaction(user_id, transaction_data)
        await update.effective_message.reply_text(TRANSACTION_SAVED_TEXT)

        if len(context.user_data["transactions"]) > 1:
            context.user_data["transactions"] = context.user_data["transactions"][1:]
            await save_transaction(update, context)
        else:
            context.user_data["transactions"] = []

    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    print("ST-4")
    return TRANSACTION


# async def prompt_specify_category(update: Update, context: CallbackContext):
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id, text="Please, manually enter category:"
#     )
#     return SPECIFY_CATEGORY


async def choose_category(update: Update, context: CallbackContext):
    print("CC-1", context.user_data.get("transactions"))

    context.user_data["state"] = "choose_category"
    user_id = str(update.effective_user.id)
    category = update.callback_query.data
    print("CC-1.1 cat is : ", category)
    if category == "enter_manually":
        print("CC-1.2 inside if", category)
        await update.effective_message.reply_text("Please, manualy eenter category:")
        return SPECIFY_CATEGORY

    print("CC-1.2 outside if", category)

    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")
    transaction_data["category"] = category

    if subcategory:
        add_category(user_id, category, subcategory)
        await update.effective_message.reply_text(
            CONFIRM_SAVE_CAT.format(category, subcategory), parse_mode=ParseMode.HTML
        )
        save_user_transaction(user_id, transaction_data)
        await update.effective_message.reply_text(TRANSACTION_SAVED_TEXT)
        print("CC-2, tx saved")

        if len(context.user_data["transactions"]) > 1:
            context.user_data["transactions"] = context.user_data["transactions"][1:]
            print("CC-3")
            await save_transaction(update, context)
        else:
            print("CC-5, clean txs cache")
            context.user_data["transactions"] = []

    else:
        await update.effective_message.reply_text(
            "An error occurred. Please try again."
        )

    print("CC-4, change state to TRANSACTION")
    return TRANSACTION


async def process_next(update: Update, context: CallbackContext):

    print("PN1: ", context.user_data["state"])
    context.user_data["state"] = "process_next"
    await choose_category(update, context)


async def handle_specify_category(update: Update, context: CallbackContext):
    print("HSC1")
    context.user_data["state"] = "handle_specify_category"

    user_id = str(update.effective_user.id)
    category = update.effective_message.text.lower()
    subcategory = context.user_data.get("subcategory")
    transaction_data = context.user_data.get("transaction_data")

    # Save the chosen category in the dictionary
    add_category(user_id, category, subcategory)

    # Update the category in the transaction_data dictionary
    transaction_data["category"] = category

    # Save the transaction with the updated category
    save_user_transaction(user_id, transaction_data)
    print("Tx saved by handle_specify_cat")

    # Send a confirmation message to the user
    await update.effective_message.reply_text(
        CONFIRM_SAVE_CAT.format(category, subcategory), parse_mode=ParseMode.HTML
    )
    await update.effective_message.reply_text(TRANSACTION_SAVED_TEXT)
    if len(context.user_data["transactions"]) > 1:
        # Remove the processed transaction from the list
        context.user_data["transactions"] = context.user_data["transactions"][1:]
        # Process the next transaction
        # await save_transaction(update, context)
        return save_transaction(update, context)

    return TRANSACTION


async def show_records(update: Update, context):
    user_id = str(update.effective_user.id)
    records = get_records(user_id)

    if records is None:
        await update.message.reply_text(RECORDS_NOT_FOUND_TEXT)
        return

    sum_per_cat, av_per_day, total_spendings = records
    sum_per_cat_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in sum_per_cat.items()
    )
    av_per_day_text = "\n".join(
        f"{cat}: {amount}" for cat, amount in av_per_day.items()
    )

    output_text = RECORDS_TEMPLATE.format(
        total=total_spendings,
        sum_per_cat=sum_per_cat_text,
        av_per_day=av_per_day_text,
    )

    await update.message.reply_text(output_text)
    return TRANSACTION


async def show_detailed(update: Update, context):
    user_id = str(update.effective_user.id)
    sum_per_cat = show_sum_per_cat(user_id)
    top_subcats = show_top_subcategories(user_id)

    output = "Detailed report:\n\n"
    for category, total in sum_per_cat.items():
        output += f"{category}: {total}\n"

        # Get the top subcategories for this category
        category_subcats = top_subcats[top_subcats["category"] == category]
        for _, row in category_subcats.iterrows():
            output += f"   {row['subcategory']}: {row['amount']}\n"

        output += "\n"

    await update.message.reply_text(output)

    return TRANSACTION


async def handle_text(update: Update, context):
    user_id = str(update.effective_user.id)

    # If the user has an existing config file
    if check_config_exists(user_id):
        # Check if the input is a valid transaction (e.g., "taxi 10")
        parts = update.message.text.lower().split()
        try:
            if float(parts[-1]):
                return await save_transaction(update, context)
        except ValueError:
            pass

    # If the input is not a valid transaction or the user hasn't started yet
    await update.message.reply_text(START_COMMAND_PROMPT)


async def show_cat(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    check_dictionary_format(user_id)
    cat_dict = read_dictionary(user_id)

    output = CAT_DICT_MESSAGE.format(
        "\n".join(
            f"{category}:\n    "
            + ", ".join(subcategory for subcategory in cat_dict[category])
            for category in cat_dict
        ),
        len(cat_dict),
    )

    await update.message.reply_text(output)


async def add_cat(update: Update, context: CallbackContext):
    await update.message.reply_text(
        ADD_CAT_PROMPT,
        parse_mode="MarkdownV2",
    ),
    return ADD_CATEGORY


async def save_category(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)

    text = update.message.text.lower()
    if ":" not in text or text.count(":") > 1:
        await update.message.reply_text(WRONG_INPUT_FORMAT)
        return ADD_CATEGORY

    category, subcategory = text.split(":", 1)

    if text.startswith("-"):
        # Remove category:subcategory
        category = category.lstrip("-")
        remove_category(user_id, category, subcategory)
        await update.message.reply_text(DEL_CAT_SUCCESS.format(category, subcategory))
    else:
        # Add category:subcategory
        add_category(user_id, category, subcategory)
        await update.message.reply_text(ADD_CAT_SUCCESS.format(category, subcategory))

    return TRANSACTION


async def latest_records(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    record_num = 5  # Default value

    if context.args:
        try:
            record_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text(INVALID_RECORD_NUM)
            return

    records = get_latest_records(user_id, record_num)

    if not records:
        await update.message.reply_text(NO_RECORDS)
    else:
        for i, record in enumerate(records, start=1):
            await update.message.reply_text(RECORD_LINE.format(i, record))


async def delete_records(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    record_num = 1  # Default value

    if context.args:
        try:
            record_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text(INVALID_RECORD_NUM)
            return

    if not record_exists(user_id):
        await update.message.reply_text(NO_RECORDS_TO_DELETE)
    else:
        deleted = delete_record(user_id, record_num)
        if deleted:
            await update.message.reply_text(RECORD_DELETED.format(record_num))
        else:
            await update.message.reply_text(NOT_ENOUGH_RECORDS.format(record_num))


async def help(update: Update, context):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)
    return TRANSACTION


async def cancel(update: Update, context):
    await update.message.reply_text(
        CANCEL_TEXT,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def download_spendings(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    spendings_file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    await context.bot.send_document(
        chat_id=update.effective_chat.id, document=open(spendings_file_path, "rb")
    )


async def start_upload(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Please upload your file")
    return WAITING_FOR_DOCUMENT


async def receive_document(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
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

    await update.message.reply_text("Spendings file updated!")

    return ConversationHandler.END


async def cancel_upload(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Upload cancelled.")
    return ConversationHandler.END


async def archive_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    result = await archive_user_data(user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)


def main():
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("show", show_records))
    application.add_handler(CommandHandler("showext", show_detailed))
    application.add_handler(CommandHandler("show_cat", show_cat))
    application.add_handler(CommandHandler("show_last", latest_records))
    application.add_handler(CommandHandler("delete", delete_records))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("download", download_spendings))
    application.add_handler(CommandHandler("cancel", cancel))

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

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("change_cat", add_cat),
            MessageHandler(filters.Regex(r"^\w+ \d+$"), handle_text),
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(language)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
            CURRENCY: [CallbackQueryHandler(save_currency)],
            TRANSACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_transaction)
            ],
            PROCESS_NEXT: [CallbackQueryHandler(process_next)],
            CHOOSE_CATEGORY: [
                CallbackQueryHandler(choose_category),
            ],
            SPECIFY_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_specify_category)
            ],
            ADD_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_category)
            ],
        },
        allow_reentry=True,
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    # message handler for text input
    # application.add_handler(
    #     MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    # )
    application.add_handler(CommandHandler("leave", archive_profile))

    application.run_polling()


if __name__ == "__main__":
    main()
