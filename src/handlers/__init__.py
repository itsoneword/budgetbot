"""
Handler modules extracted from core.py for better organization.

This package contains:
- onboarding: User registration flow (start, language, currency, limit)
- settings: Settings modification handlers
- admin: Administrative commands (help, about, archive)
- charts: Chart generation and sending
- records: Transaction records display and income processing
- menu: Main menu navigation and routing
- transactions: Transaction editing and deletion
- categories: Category management (add, rename, delete)
- tasks: Task/subcategory management within categories
"""

from src.handlers.onboarding import (
    start,
    save_language,
    save_currency,
    save_limit,
    skip_limit,
)

from src.handlers.settings import (
    handle_settings_language,
    handle_settings_currency,
    handle_settings_limit,
)

from src.handlers.admin import (
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
)

from src.handlers.charts import (
    send_chart,
    send_ext_chart,
    send_yearly_piechart,
)

from src.handlers.records import (
    show_records,
    show_last_month_records,
    start_income,
    process_income,
    process_income_menu,
)

from src.handlers.menu import (
    show_menu,
    menu_call,
    menu_callback,
)

from src.handlers.transactions import (
    show_recent_entries,
    handle_transaction_selection,
    handle_edit_option,
    handle_edit_date,
    handle_edit_category,
    handle_edit_subcategory,
    handle_edit_amount,
    handle_delete_tx_confirmation,
)

from src.handlers.categories import (
    show_categories,
    handle_category_selection,
    handle_category_option,
    handle_change_name,
    handle_add_new_category,
    handle_rename_confirmation,
    handle_delete_cat_confirmation,
)

from src.handlers.tasks import (
    show_tasks,
    handle_tasks_action,
    handle_task_option,
    handle_add_task,
    handle_edit_task,
    handle_task_edit_confirmation,
    handle_task_delete_confirmation,
)

__all__ = [
    # Onboarding
    'start',
    'save_language',
    'save_currency',
    'save_limit',
    'skip_limit',
    # Settings
    'handle_settings_language',
    'handle_settings_currency',
    'handle_settings_limit',
    # Admin
    'help',
    'about',
    'archive_profile',
    'show_log_chart',
    'grant_ai',
    'revoke_ai',
    'list_ai',
    'admin_users',
    'admin_export',
    'admin_stats',
    # Charts
    'send_chart',
    'send_ext_chart',
    'send_yearly_piechart',
    # Records
    'show_records',
    'show_last_month_records',
    'start_income',
    'process_income',
    'process_income_menu',
    # Menu
    'show_menu',
    'menu_call',
    'menu_callback',
    # Transactions
    'show_recent_entries',
    'handle_transaction_selection',
    'handle_edit_option',
    'handle_edit_date',
    'handle_edit_category',
    'handle_edit_subcategory',
    'handle_edit_amount',
    'handle_delete_tx_confirmation',
    # Categories
    'show_categories',
    'handle_category_selection',
    'handle_category_option',
    'handle_change_name',
    'handle_add_new_category',
    'handle_rename_confirmation',
    'handle_delete_cat_confirmation',
    # Tasks
    'show_tasks',
    'handle_tasks_action',
    'handle_task_option',
    'handle_add_task',
    'handle_edit_task',
    'handle_task_edit_confirmation',
    'handle_task_delete_confirmation',
]
