"""
Category management handlers.
Handles category listing, renaming, adding, and deleting.
"""
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode

from language_util import check_language
from keyboards import (
    create_category_edit_keyboard,
    create_category_options_keyboard,
    create_confirmation_keyboard,
    create_main_menu_keyboard,
)
from src.states import *
from shared.di import get_repos


async def show_categories(update: Update, context: CallbackContext) -> int:
    """Show list of categories as inline keyboard."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Get categories from PostgreSQL
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    cat_dict = await repos.categories.get_dictionary(user_id, language)
    categories = list(cat_dict.keys())

    # Get current page from context or default to 0
    current_page = context.user_data.get("current_page", 0)

    # Store categories in context
    context.user_data["categories"] = categories

    if not categories:
        await update.effective_message.reply_text(
            texts.NO_CATEGORIES_FOUND,
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    # Create keyboard with categories
    reply_markup = create_category_edit_keyboard(categories, texts, current_page)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            texts.EDIT_CATEGORIES_PROMPT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.effective_message.reply_text(
            texts.EDIT_CATEGORIES_PROMPT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    return CATEGORY_MANAGEMENT


async def handle_category_selection(update: Update, context: CallbackContext) -> int:
    """Handle category selection from the keyboard."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "back_to_main_menu":
        # Return to main menu
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TRANSACTION

    # Handle pagination for categories
    if callback_data == "catpage_prev":
        current_page = context.user_data.get("current_page", 0)
        context.user_data["current_page"] = max(0, current_page - 1)
        return await show_categories(update, context)

    if callback_data == "catpage_next":
        current_page = context.user_data.get("current_page", 0)
        categories = context.user_data.get("categories", [])
        items_per_page = 15

        # Check if there are more pages
        if (current_page + 1) * items_per_page < len(categories):
            context.user_data["current_page"] = current_page + 1

        return await show_categories(update, context)

    if callback_data == "add_new_category":
        # Prompt user to enter new category name
        await query.edit_message_text(
            texts.CREATE_CATEGORY_PROMPT.format(""),
            parse_mode=ParseMode.HTML
        )
        return CATEGORY_MANAGEMENT

    category = callback_data.replace("cat_", "")
    context.user_data["current_category"] = category

    # Get subcategories for this category from PostgreSQL
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    subcategories = await repos.categories.get_subcategories(user_id, category, language)
    context.user_data["current_subcategories"] = subcategories

    # Create keyboard with category options
    reply_markup = create_category_options_keyboard(category, texts)

    await query.edit_message_text(
        texts.CATEGORY_OPTIONS.format(category),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return CATEGORY_EDIT


async def handle_category_option(update: Update, context: CallbackContext) -> int:
    """Handle selection of category options."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "back_to_categories":
        return await show_categories(update, context)

    if callback_data.startswith("change_name_"):
        category = callback_data.replace("change_name_", "")
        context.user_data["current_category"] = category

        await query.edit_message_text(
            texts.ENTER_NEW_CATEGORY_NAME.format(category),
            parse_mode=ParseMode.HTML
        )
        return CATEGORY_EDIT

    elif callback_data.startswith("delete_category_"):
        category = callback_data.replace("delete_category_", "")
        context.user_data["current_category"] = category

        # Create confirmation keyboard
        reply_markup = create_confirmation_keyboard("delete", category, texts)

        await query.edit_message_text(
            texts.CONFIRM_DELETE_CATEGORY.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return CATEGORY_EDIT

    elif callback_data.startswith("edit_tasks_"):
        category = callback_data.replace("edit_tasks_", "")
        context.user_data["current_category"] = category

        # Get subcategories for this category from PostgreSQL
        repos = get_repos(context)
        language = context.user_data.get('language', 'en')
        subcategories = await repos.categories.get_subcategories(user_id, category, language)
        context.user_data["current_subcategories"] = subcategories

        # Import here to avoid circular imports
        from src.handlers.tasks import show_tasks
        return await show_tasks(update, context, category, subcategories)

    return CATEGORY_EDIT


async def handle_change_name(update: Update, context: CallbackContext) -> int:
    """Handle input of new category name."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Get the new category name
    new_name = update.message.text.strip().lower()
    old_name = context.user_data.get("current_category")

    # If old_name is not set, this is not a name change operation
    if not old_name:
        return await handle_add_new_category(update, context)

    context.user_data["new_category_name"] = new_name

    # Create confirmation keyboard
    reply_markup = create_confirmation_keyboard("rename", f"{old_name}|{new_name}", texts)

    await update.message.reply_text(
        texts.CONFIRM_RENAME_CATEGORY.format(old_name, new_name),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

    return CATEGORY_EDIT


async def handle_add_new_category(update: Update, context: CallbackContext) -> int:
    """Handle input of new category name when adding a new category."""
    user_id = update.effective_user.id
    texts = check_language(update, context)

    # Clear any existing category context
    if "current_category" in context.user_data:
        del context.user_data["current_category"]

    # Get the new category name
    new_category = update.message.text.strip().lower()

    # Add the category with a default subcategory to ensure it appears in the dictionary
    default_subcategory = "general"
    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    await repos.categories.add_category(user_id, new_category, default_subcategory, language)

    await update.message.reply_text(
        texts.CATEGORY_ADDED.format(new_category),
        parse_mode=ParseMode.HTML
    )

    # Return to the categories list
    return await show_categories(update, context)


async def handle_rename_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of category name change."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    callback_data = query.data

    if callback_data.startswith("confirm_rename_"):
        # Extract old and new names
        data = callback_data.replace("confirm_rename_", "")
        old_name, new_name = data.split("|")

        # Use repository's rename method (updates all subcategories at once)
        await repos.categories.rename_category(user_id, old_name, new_name, language)

        await query.edit_message_text(
            texts.CATEGORY_RENAMED.format(old_name, new_name),
            parse_mode=ParseMode.HTML
        )

        return await show_categories(update, context)

    elif callback_data.startswith("cancel_rename_"):
        await query.edit_message_text(
            texts.RENAME_CANCELLED,
            parse_mode=ParseMode.HTML
        )

        return await show_categories(update, context)

    return CATEGORY_EDIT


async def handle_delete_cat_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of category deletion."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()

    repos = get_repos(context)
    language = context.user_data.get('language', 'en')
    callback_data = query.data

    if callback_data.startswith("confirm_delete_"):
        category = callback_data.replace("confirm_delete_", "")

        # Delete category and all its subcategories at once
        await repos.categories.delete_category(user_id, category, language)

        await query.edit_message_text(
            texts.CATEGORY_DELETED.format(category),
            parse_mode=ParseMode.HTML
        )

        return await show_categories(update, context)

    elif callback_data.startswith("cancel_delete_"):
        category = callback_data.replace("cancel_delete_", "")

        # Create keyboard with category options
        reply_markup = create_category_options_keyboard(category, texts)

        await query.edit_message_text(
            texts.DELETE_CANCELLED.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        return CATEGORY_EDIT

    return CATEGORY_EDIT
