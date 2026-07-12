import os, logging, configparser, inspect, re, asyncio
from datetime import datetime, timedelta, time as dt_time, timezone as dt_timezone
from io import BytesIO
from src.language_util import check_language, cache_user_language, get_cached_currency, ensure_user_config_cached

# Database integration
from shared.di import setup_container, cleanup_container, get_repos

from src.config import ADMIN_USER_ID, RECURRING_HOUR_UTC, is_admin

# Command registry: single source for handler registration, /help and menu sync
from src.commands import COMMANDS, build_help_text, sync_bot_commands

# Recurring transactions (T-026): recurring_command must be importable here —
# the registry loop resolves CommandSpec.handler names from this module's globals.
from src.handlers.recurring import recurring_command, handle_recurring_callback
from src.scheduler import run_recurring_rules

# Domain layer - batch fetch + filter
from domain.session_loader import load_user_session
from domain.export import render_transactions_csv
from domain.filters import (
    filter_by_type,
    filter_current_month,
    filter_by_period,
    get_sum_per_category,
    get_sum_per_subcategory,
    get_records_summary,
    calculate_limit_usage,
)
import sys
from logging.handlers import TimedRotatingFileHandler

# Replace debug_utils import with logger import
from src.logger import (
    setup_logging, 
    log_debug, 
    log_function_call, 
    log_state_transition, 
    timed_function, 
    measure_execution,
    log_user_interaction,
    load_debug_setting_from_config,
    save_debug_setting_to_config
)

# pandas_ops imports removed - all functions migrated to domain/filters.py and repos
# chart imports removed - chart handlers live in src/handlers/ (charts.py, admin.py)
# process_income_input moved to save_transaction.py (pure parsing, no file I/O)
from src.save_transaction import process_income_input

# Extracted handlers from core.py for better organization
from src.handlers import (
    # Onboarding
    start,
    save_language,
    save_currency,
    save_limit,
    skip_limit,
    # Settings
    handle_settings_language,
    handle_settings_currency,
    handle_settings_limit,
    # Admin
    help,
    about,
    archive_profile,
    show_log_chart,
    grant_ai,
    revoke_ai,
    list_ai,
    admin_users,
    admin_export,
    admin_stats,
    # Charts
    send_chart,
    send_ext_chart,
    send_yearly_piechart,
    # Records
    show_records,
    show_last_month_records,
    start_income,
    process_income,
    process_income_menu,
    # Menu
    show_menu,
    menu_call,
    menu_callback,
)
from src.keyboards import (
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
    create_tx_categories_keyboard,
    create_subcategories_keyboard,
    create_amounts_keyboard,
    create_confirm_transaction_keyboard,
)


from src.handlers.categories import (
    show_categories, handle_category_selection, handle_category_option,
    handle_change_name, handle_add_new_category, handle_rename_confirmation,
    handle_delete_cat_confirmation,
)

from src.handlers.tasks import (
    handle_tasks_action, handle_task_option, handle_add_task, handle_edit_task,
    handle_task_edit_confirmation, handle_task_delete_confirmation,
)

from src.handlers.transactions import (
    show_recent_entries, handle_transaction_selection, handle_edit_option,
    handle_edit_date, handle_edit_category, handle_edit_subcategory,
    handle_edit_amount, handle_delete_tx_confirmation,
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
from src.save_transaction import (
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

# Read configuration
config = configparser.ConfigParser()
config.read("configs/config")
token = config["TELEGRAM"]["TOKEN"]

if token == "":
    config.read("config")
    token = config["TELEGRAM"]["TOKEN"]

# Initialize logging with debug mode off
setup_logging("INFO")

# Read debug mode from config if available
try:
    debug_mode = load_debug_setting_from_config(config)
    setup_logging(debug_mode)
    log_debug(f"Debug mode set to {debug_mode} from config file")
except Exception as e:
    log_debug(f"Error reading debug configuration: {e}")


# Command to toggle debug mode
async def toggle_debug(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Only allow admin users to toggle debug mode
    if not is_admin(user_id):
        await update.message.reply_text("Sorry, only admin users can toggle debug mode.")
        return TRANSACTION
    
    # Get current debug mode from config
    current_debug_mode = load_debug_setting_from_config(config)
    
    # Toggle debug mode
    new_debug_mode = not current_debug_mode
    
    # Update the logger configuration
    setup_logging(new_debug_mode)
    
    # Save to config file
    save_debug_setting_to_config(config, new_debug_mode)
    
    status = "ON" if new_debug_mode else "OFF"
    await update.message.reply_text(f"Debug mode is now {status}")
    log_debug(f"Debug mode toggled to {new_debug_mode}")
    return TRANSACTION








async def show_detailed(update: Update, context, period: str = 'current_month'):
    """Show detailed spending report for specified period (from PostgreSQL).
    
    Args:
        period: 'current_month' or 'last_month'
    """
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )

    # Load session from DB (batch fetch)
    repos = get_repos(context)
    session = await load_user_session(user_id, repos, transactions_months=2)

    # Filter to specified period
    spending_tx = filter_by_type(session.transactions, 'spending')
    if period == 'last_month':
        filtered_tx = filter_by_period(spending_tx, 'last_month')
        header = texts.DETAILED_REPORT_LAST_MONTH_TEXT
    else:
        filtered_tx = filter_current_month(spending_tx)
        header = texts.DETAILED_REPORT_TEXT

    # Calculate sum per category
    sum_per_cat = get_sum_per_category(filtered_tx)

    output = header + "\n\n"
    for category, total in sum_per_cat.items():
        output += f"{category}: {total} {session.currency}\n"

        # Get top subcategories for this category
        top_subcats = get_sum_per_subcategory(filtered_tx, category=category, limit=5)
        for subcat, amount in top_subcats.items():
            output += f"   {subcat}: {amount} {session.currency}\n"

        output += "\n"

    if update.callback_query:
        await update.callback_query.message.reply_text(output)
    else:
        await update.message.reply_text(output)

    return TRANSACTION

async def show_cat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    # Get categories from PostgreSQL
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    cat_dict = await repos.categories.get_dictionary(user_id, language)

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
    user_id =update.effective_user.id
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
    user_id = update.effective_user.id  # Use int, not str
    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )
    text = update.message.text.lower()
    if ":" not in text or text.count(":") > 1:
        await update.message.reply_text(texts.WRONG_INPUT_FORMAT)
        return ADD_CATEGORY

    category, subcategory = text.split(":", 1)
    
    # Get repos and language
    repos = get_repos(context)
    language = context.user_data.get('cached_language', 'en')

    if text.startswith("-"):
        # Remove category:subcategory from PostgreSQL
        category = category.lstrip("-")
        await repos.categories.delete_subcategory(user_id, category.strip(), subcategory.strip(), language)
        await update.message.reply_text(
            texts.DEL_CAT_SUCCESS.format(category, subcategory)
        )
    else:
        # Add category:subcategory to PostgreSQL
        await repos.categories.add_subcategory(user_id, category.strip(), subcategory.strip(), language)
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
    user_id =update.effective_user.id
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
        log_state_transition(TRANSACTION)
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
        log_state_transition(TRANSACTION)
        return TRANSACTION
    
    # Handle unexpected callback data
    await query.answer("Unexpected option")
    return TRANSACTION

async def latest_records(update: Update, context):
    """Show latest transactions (from PostgreSQL)."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )
    
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    currency = get_cached_currency(context)
    
    # "/show_last income [N]" lists income records with their IDs — the way to
    # find an ID for /delete_income (T-035).
    tx_type = 'spending'
    args = list(context.args or [])
    for word in ("income", "доход", "доходы"):
        if word in args:
            tx_type = 'income'
            args.remove(word)
            break

    record_num_or_category = args[0] if args else "5"

    # Determine if argument is a number or category name
    try:
        limit = int(record_num_or_category)
        # Get latest N transactions (convert to domain model for .category/.subcategory)
        from domain.models.user_session import Transaction as DomainTransaction
        repo_transactions = await repos.transactions.get_latest(user_id, limit=limit, transaction_type=tx_type)
        transactions = [DomainTransaction.from_repo(tx) for tx in repo_transactions]
    except ValueError:
        # It's a category name - load more and filter
        from domain.session_loader import load_user_session
        from domain.filters import filter_by_categories
        
        session = await load_user_session(user_id, repos, load_transactions=True, transactions_months=12)
        transactions = filter_by_categories(session.transactions, [record_num_or_category])

    if not transactions:
        if update.callback_query:
            await update.callback_query.message.reply_text(texts.NO_RECORDS)
        else:
            await update.message.reply_text(texts.NO_RECORDS)
    else:
        # Format records and calculate total
        total_amount = sum(tx.amount for tx in transactions)
        records = [
            f"{tx.id}: {tx.timestamp.strftime('%Y-%m-%d')}, {tx.category}, {tx.subcategory}, {tx.amount}, {currency}"
            for tx in transactions
        ]
        
        records_message = texts.LAST_RECORDS.format(total_amount, "\n".join(records))
        if update.callback_query:
            await update.callback_query.message.reply_text(records_message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(records_message, parse_mode=ParseMode.HTML)


async def delete_records(update: Update, context: CallbackContext):
    """/delete and /delete_income. Type-aware (T-035): each command only
    touches its own transaction type. No argument deletes the latest record
    of that type and echoes it; an ID must belong to that type."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        str(user_id), update.effective_user.first_name, update.effective_user.username
    )
    command = update.effective_message.text.split()[0][1:]
    tx_type = 'income' if "income" in command else 'spending'
    repos = get_repos(context)

    if context.args:
        try:
            record_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(texts.INVALID_RECORD_NUM)
            return
        tx = await repos.transactions.get_by_id(record_id, user_id)
        if tx is None:
            await update.message.reply_text(texts.NOT_ENOUGH_RECORDS.format(record_id))
            return
        if tx.transaction_type != tx_type:
            await update.message.reply_text(
                texts.DELETE_TYPE_MISMATCH.format(record_id=record_id, tx_type=tx.transaction_type)
            )
            return
    else:
        # No ID: delete the latest record of this command's type
        latest = await repos.transactions.get_latest(user_id, limit=1, transaction_type=tx_type)
        if not latest:
            await update.message.reply_text(texts.NO_RECORDS_TO_DELETE)
            return
        tx = latest[0]
        record_id = tx.id

    deleted = await repos.transactions.delete(record_id, user_id)
    if deleted:
        await update.message.reply_text(
            texts.RECORD_DELETED_DETAILS.format(
                record_id=record_id,
                date=tx.timestamp.strftime("%Y-%m-%d"),
                category=tx.category_name,
                subcategory=f" {tx.subcategory_name}" if tx.subcategory_name else "",
                amount=tx.amount,
                currency=tx.currency,
            ),
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(texts.NOT_ENOUGH_RECORDS.format(record_id))


async def cancel(update: Update, context):
    texts = check_language(update, context)
    await update.message.reply_text(
        texts.CANCEL_TEXT,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def download_spendings(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    repos = get_repos(context)
    # transactions_months=None -> get_latest(limit=10000): exports all
    # transactions, but silently truncates users with >10k records.
    session = await load_user_session(user_id, repos, transactions_months=None)
    if not session.transactions:
        await update.message.reply_text(texts.RECORDS_NOT_FOUND_TEXT)
        return
    csv_str = render_transactions_csv(session.transactions)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=BytesIO(csv_str.encode("utf-8")),
        filename=f"spendings_{user_id}.csv",
    )


async def start_upload(update: Update, context: CallbackContext) -> int:
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    texts = check_language(update, context)
    await update.message.reply_text(texts.UPLOAD_FILE_TEXT)
    return WAITING_FOR_DOCUMENT


async def receive_document(update: Update, context: CallbackContext) -> int:
    user_id =update.effective_user.id
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
    #backup_spendings(user_id, spendings_file_path)

    # Download the new file directly to the spendings file path
    await new_spendings_file.download_to_drive(custom_path=spendings_file_path)

    await update.message.reply_text(texts.UPLOADING_FINISHED)

    return ConversationHandler.END


async def cancel_upload(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Upload cancelled.")
    return ConversationHandler.END







async def handle_text(update: Update, context):
    """Handle messages that aren't commands."""
    user_id =update.effective_user.id
    texts = check_language(update, context)

    log_user_interaction(user_id, update.effective_user.first_name, update.effective_user.username)

    if update.message:
        # Handle text messages outside of commands
        text = update.message.text

        # Limit entry started from the /about settings keyboard outside an
        # active conversation (T-031): no SETTINGS_LIMIT state to catch the
        # number, so route it here. The handler clears the flag.
        if context.user_data.get('awaiting_limit'):
            return await handle_settings_limit(update, context)

        # Check if user exists in database, create if needed
        repos = get_repos(context)
        if not await repos.users.user_exists(int(user_id)):
            # Create user and default config in PostgreSQL
            await repos.users.setup_new_user(
                int(user_id),
                username=update.effective_user.first_name,
                telegram_username=update.effective_user.username,
            )
            await update.message.reply_text(texts.USER_CONFIG_CREATED)

        # Pattern matching based on update text format
        if re.match(r".*\s+\d+(\.\d+)?$", text):
            # Return a save transaction
            log_debug(f"Text message matching spending pattern, calling save_transaction: {text}")
            return await save_transaction(update, context)

        # Free text with no pattern match: LLM intent routing for allowed users
        # (T-019). Routed transactions/commands are re-injected as typed text,
        # which always matches the pattern above or a CommandHandler — no loop.
        from src.ai_access import check_ai_access
        if await check_ai_access(user_id, context):
            from src.handlers.voice import route_free_text
            await route_free_text(update, context, text)
            return TRANSACTION

        # Default message back to the user if no patterns match
        await update.message.reply_text(
            texts.UNKNOWN_TEXT_FORMAT,
            parse_mode=ParseMode.HTML
        )
        
    return TRANSACTION


async def ask(update: Update, context: CallbackContext):
    """AI Q&A over the user's spendings (T-018). Data is aggregated in memory
    and packed into the prompt; the model never touches the DB."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    from src.ai_access import check_ai_access
    if not await check_ai_access(user_id, context):
        await update.effective_message.reply_text(texts.ASK_NOT_ALLOWED)
        return

    question = " ".join(context.args) if context.args else ""
    if not question.strip():
        await update.effective_message.reply_text(texts.ASK_USAGE)
        return

    thinking_message = await update.effective_message.reply_text(texts.ASK_THINKING)

    try:
        from domain.ask_summary import build_finance_summary, build_ask_system_prompt
        from infrastructure.llm import get_llm_client, LLMError

        repos = get_repos(context)
        session = await load_user_session(
            user_id, repos, load_transactions=True, transactions_months=12
        )
        if not session.transactions:
            await thinking_message.edit_text(texts.ASK_NO_DATA)
            return

        summary = build_finance_summary(session)
        prompt = (
            f"User's financial data:\n{summary}\n\n"
            f"User's question: {question}"
        )
        client = get_llm_client()
        answer = await client.complete(prompt, build_ask_system_prompt(session.language))
        await thinking_message.edit_text(answer)
    except LLMError as e:
        logging.error(f"/ask LLM failure for user {user_id}: {e}")
        await thinking_message.edit_text(texts.ASK_ERROR)


async def global_error_handler(update: object, context) -> None:
    """Log unhandled handler exceptions with user context; send a short apology to the user."""
    user_ctx = ""
    if isinstance(update, Update) and update.effective_user:
        user_ctx = f" [user_id={update.effective_user.id}"
        if update.effective_message and update.effective_message.text:
            user_ctx += f", input={update.effective_message.text!r}"
        elif update.callback_query and update.callback_query.data:
            user_ctx += f", callback={update.callback_query.data!r}"
        user_ctx += "]"
    logging.error(f"Unhandled exception{user_ctx}", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            texts = check_language(update, context)
            await update.effective_message.reply_text(texts.ERROR_PROCESSING_REQUEST)
        except Exception:
            logging.exception("Failed to notify user about the error")


async def on_post_init(application: Application) -> None:
    """PTB accepts a single post_init callable: DB container first, then menu sync."""
    await setup_container(application)
    await sync_bot_commands(application)


def main():
    # Build application with database container lifecycle hooks
    application = (
        Application.builder()
        .token(token)
        .post_init(on_post_init)
        .post_shutdown(cleanup_container)
        .build()
    )

    # Register plain commands from the registry (src/commands.py).
    # spec.handler is None for ConversationHandler entry points (leave, income,
    # upload, start, menu, change_cat) — registering those here too would make
    # them dispatch twice.
    for spec in COMMANDS:
        if spec.handler is None:
            continue
        handler_fn = globals().get(spec.handler)
        if handler_fn is None:
            raise RuntimeError(
                f"Command /{spec.name}: handler '{spec.handler}' not found in src.core"
            )
        application.add_handler(CommandHandler(spec.name, handler_fn))

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
        # A repeated /income while the prompt is pending must re-enter instead
        # of falling through to other handlers (T-035).
        allow_reentry=True,
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
            # ~COMMAND: without it "/income trading 300" falling out of the
            # income conversation was swallowed here and saved as a spending
            # with category "/income" (T-035).
            MessageHandler(filters.Regex(r"\b\w+\s+\d+$") & ~filters.COMMAND, handle_text),
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
                CallbackQueryHandler(menu_call, pattern="^(show_monthly_summary|show_last_month_summary|show_last_transactions|show_monthly_charts|show_extended_stats|show_last_month_extended_stats|show_yearly_charts|show_income_stats)"),
                # For text input of transaction amount
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction_amount),
            ],
            # Category management states (handlers/categories.py, handlers/tasks.py)
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
            # Add-income via the menu button (T-035); the /income command has
            # its own ConversationHandler — this state only serves menu taps.
            PROCESS_INCOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_income_menu)
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
    # Voice input + intent routing (T-019). Registered before spendings_handler
    # so the vtx_ confirm callback isn't swallowed by its pattern-less
    # menu_callback fallback while a conversation is active.
    from src.handlers.voice import (
        handle_voice,
        handle_voice_tx_confirmation,
        handle_voice_income_confirmation,
    )
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(
        CallbackQueryHandler(handle_voice_tx_confirmation, pattern="^vtx_")
    )
    application.add_handler(
        CallbackQueryHandler(handle_voice_income_confirmation, pattern="^vinc_")
    )
    # Recurring rules inline buttons (T-026): same ordering requirement as vtx_.
    application.add_handler(
        CallbackQueryHandler(handle_recurring_callback, pattern="^rr")
    )

    application.add_handler(spendings_handler)
    # Settings buttons attached by /about (T-031). While a spendings_handler
    # conversation is active its pattern-less menu_callback fallback routes
    # settings_* and transitions to the SETTINGS_* states, where lang_/cur_/
    # limit-text follow-ups are handled. With no active conversation those
    # presses fell through unhandled — catch them here. Registered AFTER
    # spendings_handler (unlike ^rr/^vtx_) on purpose: registering before
    # would swallow settings_* mid-conversation and break the state
    # transitions the menu -> settings path depends on.
    application.add_handler(CallbackQueryHandler(menu_call, pattern="^settings_"))
    application.add_handler(CallbackQueryHandler(handle_settings_language, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(handle_settings_currency, pattern="^cur_"))
    # message handler for text input
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    application.add_error_handler(global_error_handler)

    # Recurring transactions scheduler (T-026): daily run at a fixed UTC hour
    # plus a startup catch-up 60s after boot (claim_run makes replays no-ops).
    # job_queue is None when the [job-queue] extra is missing — fail loudly
    # instead of silently never posting recurring transactions.
    if application.job_queue is None:
        raise RuntimeError(
            "application.job_queue is None — install python-telegram-bot[job-queue]"
        )
    application.job_queue.run_daily(
        run_recurring_rules,
        time=dt_time(hour=RECURRING_HOUR_UTC, tzinfo=dt_timezone.utc),
        name="recurring_rules_daily",
    )
    application.job_queue.run_once(run_recurring_rules, 60, name="recurring_rules_catchup")

    application.run_polling()


if __name__ == "__main__":
    main()
