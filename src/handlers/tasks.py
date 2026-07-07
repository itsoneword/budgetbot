"""
Task (subcategory) management handlers.
Handles task listing, adding, editing, and deleting within categories.
"""
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode

from language_util import check_language
from keyboards import (
    create_tasks_keyboard,
    create_task_options_keyboard,
    create_confirmation_keyboard,
    create_category_options_keyboard,
)
from src.states import *
from shared.di import get_repos


async def show_tasks(update: Update, context: CallbackContext, category: str, subcategories: list) -> int:
    """Show list of tasks (subcategories) for a category."""
    texts = check_language(update, context)
    query = update.callback_query

    # Create keyboard with tasks
    reply_markup = create_tasks_keyboard(subcategories, category, texts)

    await query.edit_message_text(
        texts.CATEGORY_TASKS.format(category),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return TASK_MANAGEMENT


async def handle_tasks_action(update: Update, context: CallbackContext) -> int:
    """Handle actions related to tasks (subcategories)."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data.startswith("back_to_category_"):
        category = callback_data.replace("back_to_category_", "")
        context.user_data["current_category"] = category

        # Create keyboard with category options
        reply_markup = create_category_options_keyboard(category, texts)

        await query.edit_message_text(
            texts.CATEGORY_OPTIONS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return CATEGORY_EDIT

    elif callback_data.startswith("add_task_"):
        category = callback_data.replace("add_task_", "")
        context.user_data["current_category"] = category

        await query.edit_message_text(
            texts.ENTER_NEW_TASK.format(category),
            parse_mode=ParseMode.HTML
        )

        return TASK_EDIT

    elif callback_data.startswith("task_"):
        # Extract category and task
        _, category, task = callback_data.split("_", 2)
        context.user_data["current_category"] = category
        context.user_data["current_task"] = task

        # Create keyboard with task options
        reply_markup = create_task_options_keyboard(category, task, texts)

        await query.edit_message_text(
            texts.TASK_OPTIONS.format(task, category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    return TASK_MANAGEMENT


async def handle_task_option(update: Update, context: CallbackContext) -> int:
    """Handle selection of task options."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    callback_data = query.data

    if callback_data.startswith("back_to_tasks_"):
        category = callback_data.replace("back_to_tasks_", "")
        context.user_data["current_category"] = category

        # Get subcategories for this category from PostgreSQL
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)

        await query.edit_message_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    elif callback_data.startswith("edit_task_"):
        # Extract category and task
        parts = callback_data.replace("edit_task_", "").split("_", 1)
        category = parts[0]
        task = parts[1]
        context.user_data["current_category"] = category
        context.user_data["current_task"] = task

        await query.edit_message_text(
            texts.ENTER_NEW_TASK_NAME.format(task),
            parse_mode=ParseMode.HTML
        )

        return TASK_EDIT

    elif callback_data.startswith("delete_task_"):
        # Extract category and task
        parts = callback_data.replace("delete_task_", "").split("_", 1)
        category = parts[0]
        task = parts[1]
        context.user_data["current_category"] = category
        context.user_data["current_task"] = task

        # Create confirmation keyboard
        reply_markup = create_confirmation_keyboard("delete_task", f"{category}|{task}", texts)

        await query.edit_message_text(
            texts.CONFIRM_DELETE_TASK.format(task, category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    return TASK_MANAGEMENT


async def handle_add_task(update: Update, context: CallbackContext) -> int:
    """Handle adding a new task (subcategory)."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Get the new task name
    new_task = update.message.text.strip().lower()
    category = context.user_data.get("current_category")

    if not category:
        await update.message.reply_text(texts.ERROR_PROCESSING_REQUEST)
        return ConversationHandler.END

    # Add new task to category using PostgreSQL
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    await repos.categories.add_category(user_id, category, new_task, language)

    await update.message.reply_text(
        texts.TASK_ADDED.format(new_task, category),
        parse_mode=ParseMode.HTML
    )

    # Get updated subcategories for this category
    subcategories = await repos.categories.get_subcategories(user_id, category, language)
    context.user_data["current_subcategories"] = subcategories

    # Create keyboard with tasks
    reply_markup = create_tasks_keyboard(subcategories, category, texts)

    await update.message.reply_text(
        texts.CATEGORY_TASKS.format(category),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return TASK_MANAGEMENT


async def handle_edit_task(update: Update, context: CallbackContext) -> int:
    """Handle editing a task (subcategory) name."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Get the new task name
    new_task_name = update.message.text.strip().lower()
    category = context.user_data.get("current_category")
    old_task_name = context.user_data.get("current_task")

    if not category or not old_task_name:
        await update.message.reply_text(texts.ERROR_PROCESSING_REQUEST)
        return ConversationHandler.END

    context.user_data["new_task_name"] = new_task_name

    # Create confirmation keyboard
    reply_markup = create_confirmation_keyboard(
        "rename_task", f"{category}|{old_task_name}|{new_task_name}", texts
    )

    await update.message.reply_text(
        texts.CONFIRM_RENAME_TASK.format(old_task_name, new_task_name, category),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return TASK_EDIT


async def handle_task_edit_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of task name edit."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    callback_data = query.data

    if callback_data.startswith("confirm_rename_task_"):
        # Extract data
        data = callback_data.replace("confirm_rename_task_", "")
        category, old_task, new_task = data.split("|")

        # Use repository's rename method
        await repos.categories.rename_subcategory(user_id, category, old_task, new_task, language)

        await query.edit_message_text(
            texts.TASK_RENAMED.format(old_task, new_task, category),
            parse_mode=ParseMode.HTML
        )

        # Get updated subcategories for this category
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)

        await query.message.reply_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    elif callback_data.startswith("cancel_rename_task_"):
        # Extract data
        data = callback_data.replace("cancel_rename_task_", "")
        category, old_task, _ = data.split("|")

        await query.edit_message_text(
            texts.RENAME_TASK_CANCELLED.format(old_task),
            parse_mode=ParseMode.HTML
        )

        # Get subcategories for this category
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)

        await query.message.reply_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return await handle_tasks_action(update, context)

    # Fallback to categories list
    from src.handlers.categories import show_categories
    return await show_categories(update, context)


async def handle_task_delete_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of task deletion."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    callback_data = query.data

    if callback_data.startswith("confirm_delete_task_"):
        # Extract data
        data = callback_data.replace("confirm_delete_task_", "")
        category, task = data.split("|")

        # Remove task using PostgreSQL
        await repos.categories.delete_subcategory(user_id, category, task, language)

        await query.edit_message_text(
            texts.TASK_DELETED.format(task, category),
            parse_mode=ParseMode.HTML
        )

        # Get updated subcategories for this category
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)

        await query.message.reply_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    elif callback_data.startswith("cancel_delete_task_"):
        # Extract data
        data = callback_data.replace("cancel_delete_task_", "")
        category, task = data.split("|")

        await query.edit_message_text(
            texts.DELETE_TASK_CANCELLED.format(task),
            parse_mode=ParseMode.HTML
        )

        # Get subcategories for this category
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)

        await query.message.reply_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return TASK_MANAGEMENT

    return TASK_MANAGEMENT
