# BudgetBot Refactoring Plan

## Overview
Transform monolithic CSV-based Telegram bot into modular PostgreSQL-backed system.

**Status**: Phase 4.2 complete (change_data/change_transactions reorganization).

---

## Completed Phases (Summary)

### Phase 1: PostgreSQL Foundation [DONE - 2025-01-25]
- Database schema created (`infrastructure/database/migrations/001_initial_schema.sql`)
- Docker Compose setup with PostgreSQL
- Data migration script (`scripts/migrate_csv_to_postgres.py`)
- Repository layer implemented (`infrastructure/repositories/`)

### Phase 2: Service Extraction [DONE - 2025-01-26]
- CurrencyService with DB-backed exchange rates (`infrastructure/external/currency_service.py`)
- Dependency injection container (`shared/di/`)
- Batch fetch + memory filter architecture (`domain/filters.py`, `domain/session_loader.py`)

### Phase 3: Handler Migration [DONE - 2025-01-26]
- All handlers converted to use PostgreSQL repositories
- Legacy files removed: `pandas_ops.py`, `show_transactions.py`
- `file_ops.py` cleaned up (only admin utilities remain)
- Critical path verified working: transaction save/view, charts, settings

---

## Current Architecture

```
src/                          # Handlers
├── core.py                   # ~980 lines - main entry point, conversation setup
├── handlers/                 # Extracted handlers (~1900 lines total, 9 modules)
│   ├── onboarding.py         # start, save_language, save_currency, save_limit, skip_limit
│   ├── settings.py           # handle_settings_language, handle_settings_currency, handle_settings_limit
│   ├── admin.py              # help, about, archive_profile, show_log_chart
│   ├── charts.py             # send_chart, send_ext_chart, send_yearly_piechart
│   ├── records.py            # show_records, show_last_month_records, start_income, process_income
│   ├── menu.py               # show_menu, menu_call, menu_callback (~290 lines)
│   ├── transactions.py       # Transaction edit/delete (8 functions, ~600 lines)
│   ├── categories.py         # Category management (7 functions, ~270 lines)
│   └── tasks.py              # Task/subcategory management (7 functions, ~330 lines)
├── save_transaction.py       # Transaction creation flow
├── detailed_transactions.py  # Detailed views
├── charts.py                 # Chart generation logic
├── keyboards.py              # Keyboard builders
├── language_util.py          # Language helpers
├── texts.py, texts_ru.py     # Text constants
└── states.py                 # Conversation states

domain/                       # Business logic (clean)
├── models/user_session.py    # Data models
├── filters.py                # Pure Python filters
└── session_loader.py         # Batch data loading

infrastructure/               # Data access (clean)
├── database/                 # DB connection
├── repositories/             # Data access layer
└── external/                 # Currency service

shared/di/                    # Dependency injection
shared/utils/                 # Shared utilities
└── pagination.py             # Pagination helpers for keyboards
```

---

## Phase 4: Code Optimization [IN PROGRESS]

### 4.1 Handler Extraction from core.py [DONE - 2025-01-26]

**Result**: Reduced core.py from ~1740 to ~1120 lines (~620 lines, 35% reduction)

**Created `src/handlers/` package** (813 lines total):
| Module | Lines | Handlers |
|--------|-------|----------|
| `onboarding.py` | 155 | start, save_language, save_currency, save_limit, skip_limit |
| `settings.py` | 100 | handle_settings_language, handle_settings_currency, handle_settings_limit |
| `admin.py` | 116 | help, about, archive_profile, show_log_chart |
| `charts.py` | 123 | send_chart, send_ext_chart, send_yearly_piechart |
| `records.py` | 248 | show_records, show_last_month_records, start_income, process_income |

**Also completed**:
- Refactored `menu_call()` with dispatch table pattern
- Added helper functions: `_show_and_return_to_menu()`, `_handle_settings_about()`
- Added loading message constants to texts.py/texts_ru.py

**Remaining in core.py** (15 functions):
- `toggle_debug` - admin utility
- `show_detailed` - detailed views (combined current + last month)
- `show_cat`, `add_cat`, `save_category` - category management
- `handle_records_count`, `latest_records`, `delete_records` - record management
- `cancel` - cancel handler
- `download_spendings`, `start_upload`, `receive_document`, `cancel_upload` - file upload
- `handle_text` - text input routing
- `main` - application entry point

### 4.2 Handler Consolidation [DONE - 2025-01-26]

**Result**: Deleted `change_transactions.py` and `change_data.py`, moved to handlers/

**Created 3 new handler modules**:
| Module | Lines | Functions | Source |
|--------|-------|-----------|--------|
| `handlers/transactions.py` | ~600 | 8 | From change_transactions.py |
| `handlers/categories.py` | ~270 | 7 | From change_data.py (category mgmt) |
| `handlers/tasks.py` | ~330 | 7 | From change_data.py (task/subcategory mgmt) |

**Files deleted**:
- `src/change_transactions.py` (moved to handlers/transactions.py)
- `src/change_data.py` (split into handlers/categories.py + handlers/tasks.py)

**Benefits**:
- All handlers now consolidated in `handlers/` package
- Clear separation: categories vs tasks (subcategories)
- Consistent import pattern: `from src.handlers.X import Y`

### 4.3 Files Remaining for Analysis

| File | Lines | Issue | Action |
|------|-------|-------|--------|
| `charts.py` | ~400 | Verify batch-fetch pattern | Confirm no extra queries |
| `save_transaction.py` | ~1100 | Complex but functional | Low priority, review later |

### 4.4 Code Consolidation [DONE - 2025-01-26]
- Consolidated `get_records_summary()` + `get_last_month_summary()` → `get_period_summary()`

### 4.5 Deferred Items
- [ ] Decorator abstraction for handler boilerplate (not urgent)
- [ ] i18n refactoring to shared/i18n/ (not urgent)
- [ ] Analytics logging to DB (separate phase)

---

## Phase 5: Future Features [PLANNED]

### 5.1 Soft Delete & Data Archival
**Problem**: Transactions are hard-deleted. No recovery possible.

**Solution**: Add `deleted_at` column for soft delete:
```sql
ALTER TABLE transactions ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
```

### 5.2 CSV Upload/Download Restore
Bulk edit feature - download transactions, edit externally, re-upload.

### 5.3 Analytics Infrastructure
- User event tracking table
- Usage patterns analysis
- Feature adoption metrics

### 5.4 Web UI / API Layer
FastAPI backend for future web interface.

---

## Implementation Order

1. ~~**Extract onboarding handlers**~~ ✅ Done
2. ~~**Extract settings handlers**~~ ✅ Done
3. ~~**Extract admin handlers**~~ ✅ Done
4. ~~**Extract chart handlers**~~ ✅ Done
5. ~~**Extract records handlers**~~ ✅ Done
6. ~~**Refactor menu_call() with dispatch table**~~ ✅ Done
7. ~~**Extract menu handlers to handlers/menu.py**~~ ✅ Done
8. ~~**Combine show_detailed() + show_last_month_detailed()**~~ ✅ Done
9. ~~**Extract pagination utility**~~ ✅ Done - shared/utils/pagination.py
10. ~~**Move change_transactions.py to handlers/transactions.py**~~ ✅ Done
11. ~~**Split change_data.py into handlers/categories.py + handlers/tasks.py**~~ ✅ Done
12. **Verify charts.py** - confirm batch-fetch, no extra queries
13. **Refactor remaining keyboard functions** to use pagination utility (optional)

---

---

## Function Inventory

### Summary by File (Updated 2025-01-26)

| File | Lines | Functions | Notes |
|------|-------|-----------|-------|
| `core.py` | ~980 | 15 | Main entry point, conversation setup |
| `handlers/` | ~1900 | 44 | All handlers consolidated (9 modules) |
| ├── `onboarding.py` | ~155 | 5 | User registration flow |
| ├── `settings.py` | ~100 | 3 | Settings modification |
| ├── `admin.py` | ~116 | 4 | Admin commands |
| ├── `charts.py` | ~123 | 3 | Chart handlers |
| ├── `records.py` | ~248 | 4 | Records display |
| ├── `menu.py` | ~290 | 3 | Menu navigation |
| ├── `transactions.py` | ~600 | 8 | Transaction edit/delete |
| ├── `categories.py` | ~270 | 7 | Category management |
| └── `tasks.py` | ~330 | 7 | Task/subcategory management |
| `save_transaction.py` | ~1248 | 13 | Transaction creation flow |
| `keyboards.py` | ~565 | 26 | Keyboard builders |
| `charts.py` | ~694 | 7 | Chart generation logic |
| `detailed_transactions.py` | ~469 | 7 | Detailed views |
| `language_util.py` | ~109 | 6 | Language helpers |
| `logger.py` | ~379 | 12 | Logging utilities |

**Total: ~5400 lines in src/ (handlers fully organized)**

### Dead Code [DELETED - 2025-01-26]
~~- `keyboards.py:create_transaction_keyboard()` - unused~~
~~- `keyboards.py:create_records_count_keyboard()` - unused~~
~~- `keyboards.py:create_edit_categories_keyboard()` - unused~~
~~- `core.py:show_log()` - stub returning hardcoded value~~
All deleted (-104 lines total)

### Highly Reused Functions (Keep/Optimize)
| Function | File | Calls | Purpose |
|----------|------|-------|---------|
| `create_main_menu_keyboard()` | keyboards.py | 11+ | Main menu display |
| `_save_transaction_to_db()` | save_transaction.py | 3 | DB persistence |
| `process_transaction_input_async()` | save_transaction.py | 2 | Parse tx input |
| `create_category_keyboard()` | keyboards.py | 3 | Category selection |

### Complex Functions (Candidates for Splitting)
| Function | File | Lines | Issue |
|----------|------|-------|-------|
| ~~`menu_call()`~~ | ~~core.py~~ | ~~287~~ | ✅ Extracted to handlers/menu.py with dispatch table |
| `process_next_transaction()` | save_transaction.py | 180 | Recursive, 4-level nesting |
| `save_transaction()` | save_transaction.py | 160 | 5-level nesting |

### Duplicate Patterns (Extract to Utilities)
1. ~~**Pagination logic**~~ ✅ Extracted to shared/utils/pagination.py
2. **Category matching** - duplicated between `save_transaction()` and `process_next_transaction()`
3. **Rename/delete confirmation** - similar patterns in handlers/categories.py and handlers/tasks.py
4. ~~**Show detailed reports**~~ ✅ Combined into single function
### Priority Table (Updated 2025-01-26)

| Priority | Finding | Action |
|----------|---------|--------|
| ✅ DONE | 4 dead functions deleted (-104 lines) | Completed 2025-01-26 |
| ✅ DONE | Handler extraction from core.py (-760 lines) | Completed 2025-01-26 |
| ✅ DONE | menu_call() extracted to handlers/menu.py | Completed 2025-01-26 |
| ✅ DONE | show_detailed() combined with show_last_month_detailed() | Completed 2025-01-26 |
| ✅ DONE | Pagination utility created in shared/utils/pagination.py | Completed 2025-01-26 |
| ✅ DONE | change_transactions.py → handlers/transactions.py | Completed 2025-01-26 |
| ✅ DONE | change_data.py → handlers/categories.py + handlers/tasks.py | Completed 2025-01-26 |
| Medium | Category matching duplicated | Extract utility |
| Low | Remaining functions in core.py | Consider extracting if needed |    
---

## Quick Reference

### How to access repositories in handlers:
```python
from shared.di import get_repos
repos = get_repos(context)
# repos.transactions, repos.users, repos.categories, repos.currency
```

### How to load user data (batch fetch):
```python
from domain.session_loader import load_user_session
session = await load_user_session(user_id, repos, transactions_months=12)
# session.transactions, session.categories, session.currency, session.monthly_limit
```

### How to filter in memory:
```python
from domain.filters import filter_by_type, get_period_summary
spending = filter_by_type(session.transactions, 'spending')
summary = get_period_summary(session.transactions, 'current_month', 'spending')
```

### How to use pagination utility:
```python
from shared.utils.pagination import paginate, create_nav_buttons

# All-in-one helper
page_items, nav_buttons = paginate(
    items, page=0, texts=texts,
    items_per_page=8,
    prev_callback="mypage_prev",
    next_callback="mypage_next"
)

# Add nav_buttons to keyboard if not empty
if nav_buttons:
    keyboard.append(nav_buttons)
```
