from typing import List, Tuple, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode 
from file_ops import read_dictionary, add_category, remove_category
from language_util import check_language
from keyboards import (
    create_category_edit_keyboard, create_category_options_keyboard,
    create_tasks_keyboard, create_task_options_keyboard, create_confirmation_keyboard, create_main_menu_keyboard
)
# Import states from central file
from src.states import *

# Map old states to new ones for reference during refactoring
# SHOW_CATEGORIES, SELECT_CATEGORY -> CATEGORY_MANAGEMENT
# CATEGORY_OPTIONS, CHANGE_NAME, CONFIRM_NAME_CHANGE, DELETE_CATEGORY, CONFIRM_DELETE -> CATEGORY_EDIT
# EDIT_TASKS, SELECT_TASK_ACTION, DELETE_TASK -> TASK_MANAGEMENT
# EDIT_TASK, CONFIRM_TASK_EDIT, ADD_TASK, CONFIRM_TASK_DELETE -> TASK_EDIT

# # Keep these for backward compatibility with existing imports

# CATEGORY_OPTIONS = CATEGORY_EDIT
# CHANGE_NAME = CATEGORY_EDIT
# CONFIRM_NAME_CHANGE = CATEGORY_EDIT
# DELETE_CATEGORY = CATEGORY_EDIT
# CONFIRM_DELETE = CATEGORY_EDIT
# EDIT_TASKS = TASK_MANAGEMENT
# SELECT_TASK_ACTION = TASK_MANAGEMENT
# EDIT_TASK = TASK_EDIT
# CONFIRM_TASK_EDIT = TASK_EDIT
# ADD_TASK = TASK_EDIT
# DELETE_TASK = TASK_MANAGEMENT
# CONFIRM_TASK_DELETE = TASK_EDIT

async def show_categories(update: Update, context: CallbackContext) -> int:
    """Show list of categories as inline keyboard"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get categories from dictionary
    cat_dict = read_dictionary(user_id)
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
    print(f"DEBUG: show_categories returning CATEGORY_MANAGEMENT state")
    return CATEGORY_MANAGEMENT

async def handle_category_selection(update: Update, context: CallbackContext) -> int:
    """Handle category selection from the keyboard"""
    #print("DEBUG, handle_category_selection called")
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    # Extract category from callback data
    callback_data = query.data
    
    if callback_data == "back_to_main_menu":
        # Return to main menu
        reply_markup = create_main_menu_keyboard(texts)
        await query.edit_message_text(
            texts.MAIN_MENU_TEXT,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Return TRANSACTION state to ensure menu commands work
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
        # Stay in the same state to handle text input
        return CATEGORY_MANAGEMENT
    
    category = callback_data.replace("cat_", "")
    context.user_data["current_category"] = category
    
    # Get subcategories for this category
    cat_dict = read_dictionary(user_id)
    subcategories = cat_dict.get(category, [])
    context.user_data["current_subcategories"] = subcategories

    # Create keyboard with category options
    reply_markup = create_category_options_keyboard(category, texts)

    await query.edit_message_text(
        texts.CATEGORY_OPTIONS.format(category),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    #print(f"DEBUG: handle_category_selection returning CATEGORY_EDIT")
    return CATEGORY_EDIT

async def handle_category_option(update: Update, context: CallbackContext) -> int:
    """Handle selection of category options"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "back_to_categories":
        # Return to categories list
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
        
        # Get subcategories for this category
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
        context.user_data["current_subcategories"] = subcategories
        
        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)
        
        await query.edit_message_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return TASK_MANAGEMENT
    
    return CATEGORY_EDIT

async def handle_change_name(update: Update, context: CallbackContext) -> int:
    """Handle input of new category name"""
    user_id = str(update.effective_user.id)
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
    """Handle input of new category name when adding a new category"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Clear any existing category context
    if "current_category" in context.user_data:
        del context.user_data["current_category"]
    
    # Get the new category name
    new_category = update.message.text.strip().lower()
    
    # Add the category with a default subcategory to ensure it appears in the dictionary
    default_subcategory = "general"  # You can choose any default name that makes sense
    add_category(user_id, new_category, default_subcategory)
    
    await update.message.reply_text(
        texts.CATEGORY_ADDED.format(new_category),
        parse_mode=ParseMode.HTML
    )
    
    # Return to the categories list
    return await show_categories(update, context)

async def handle_rename_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of category name change"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("confirm_rename_"):
        # Extract old and new names
        data = callback_data.replace("confirm_rename_", "")
        old_name, new_name = data.split("|")
        
        # Get dictionary
        cat_dict = read_dictionary(user_id)
        
        # Get subcategories for old category
        subcategories = cat_dict.get(old_name, [])
        
        # Add new category with all subcategories
        for subcategory in subcategories:
            add_category(user_id, new_name, subcategory)
        
        # Remove old category and all its subcategories
        for subcategory in subcategories:
            remove_category(user_id, old_name, subcategory)
        
        await query.edit_message_text(
            texts.CATEGORY_RENAMED.format(old_name, new_name),
            parse_mode=ParseMode.HTML
        )
        
        # Return to categories list
        return await show_categories(update, context)
    
    elif callback_data.startswith("cancel_rename_"):
        await query.edit_message_text(
            texts.RENAME_CANCELLED,
            parse_mode=ParseMode.HTML
        )
        
        # Return to categories list
        return await show_categories(update, context)
    
    return CATEGORY_EDIT

async def handle_delete_cat_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of category deletion"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("confirm_delete_"):
        category = callback_data.replace("confirm_delete_", "")
        
        # Get dictionary
        cat_dict = read_dictionary(user_id)
        
        # Get subcategories for category
        subcategories = cat_dict.get(category, [])
        
        # Remove category and all its subcategories
        for subcategory in subcategories:
            remove_category(user_id, category, subcategory)
        
        await query.edit_message_text(
            texts.CATEGORY_DELETED.format(category),
            parse_mode=ParseMode.HTML
        )
        
        # Return to categories list
        return await show_categories(update, context)
    
    elif callback_data.startswith("cancel_delete_"):
        category = callback_data.replace("cancel_delete_", "")
        
        # Create keyboard with category options
        reply_markup = create_category_options_keyboard(category,texts)
        
        await query.edit_message_text(
            texts.DELETE_CANCELLED.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        return CATEGORY_EDIT
    
    return CATEGORY_EDIT

async def handle_tasks_action(update: Update, context: CallbackContext) -> int:
    """Handle actions related to tasks (subcategories)"""
    user_id = str(update.effective_user.id)
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
    """Handle selection of task options"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("back_to_tasks_"):
        category = callback_data.replace("back_to_tasks_", "")
        context.user_data["current_category"] = category
        
        # Get subcategories for this category
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
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
    """Handle adding a new task (subcategory)"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    
    # Get the new task name
    new_task = update.message.text.strip().lower()
    category = context.user_data.get("current_category")
    
    if not category:
        await update.message.reply_text(texts.ERROR_PROCESSING_REQUEST)
        return ConversationHandler.END
    
    # Add new task to category
    add_category(user_id, category, new_task)
    
    await update.message.reply_text(
        texts.TASK_ADDED.format(new_task, category),
        parse_mode=ParseMode.HTML
    )
    
    # Get updated subcategories for this category
    cat_dict = read_dictionary(user_id)
    subcategories = cat_dict.get(category, [])
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
    """Handle editing a task (subcategory) name"""
    user_id = str(update.effective_user.id)
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
    """Handle confirmation of task name edit"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("confirm_rename_task_"):
        # Extract data
        data = callback_data.replace("confirm_rename_task_", "")
        category, old_task, new_task = data.split("|")
        
        # Add new task
        add_category(user_id, category, new_task)
        
        # Remove old task
        remove_category(user_id, category, old_task)
        
        await query.edit_message_text(
            texts.TASK_RENAMED.format(old_task, new_task, category),
            parse_mode=ParseMode.HTML
        )
        
        # Get updated subcategories for this category
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
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
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
        context.user_data["current_subcategories"] = subcategories
        
        # Create keyboard with tasks
        reply_markup = create_tasks_keyboard(subcategories, category, texts)
        
        await query.message.reply_text(
            texts.CATEGORY_TASKS.format(category),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return await handle_tasks_action(update, context)

    return await show_categories(update, context)
    #return TASK_EDIT

async def handle_task_delete_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle confirmation of task deletion"""
    user_id = str(update.effective_user.id)
    texts = check_language(update, context)
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("confirm_delete_task_"):
        # Extract data
        data = callback_data.replace("confirm_delete_task_", "")
        category, task = data.split("|")
        
        # Remove task
        remove_category(user_id, category, task)
        
        await query.edit_message_text(
            texts.TASK_DELETED.format(task, category),
            parse_mode=ParseMode.HTML
        )
        
        # Get updated subcategories for this category
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
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
        cat_dict = read_dictionary(user_id)
        subcategories = cat_dict.get(category, [])
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