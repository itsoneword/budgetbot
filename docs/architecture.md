# BudgetBot Architecture

> Current as of 2026-04-26. Supersedes the historical `project_architecture.md` (which described the pre-migration CSV-based system).

## 1. Overview

BudgetBot is a Telegram-based personal expense tracker. Users send transactions as text (e.g., `Food 12`) or via inline keyboards; the bot stores them in PostgreSQL, runs aggregations in Python, and renders charts via matplotlib.

The codebase migrated from a CSV-per-user file architecture to PostgreSQL + a layered (handlers / domain / infrastructure) design. Migration is functionally complete; see `REFACTORING.md` for phase history and `production-readiness.md` for what's still needed before scaling to 1k–10k users.

## 2. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.9+ (tested on 3.12, 3.13) |
| Bot framework | `python-telegram-bot` 22 (async) |
| Database | PostgreSQL 15, accessed via `asyncpg` (async pool, min=2, max=10) |
| Data crunching | `pandas` 2.2, `numpy` 2.0 (used in charts and a few currency helpers) |
| Charts | `matplotlib` 3.9, `seaborn` 0.13 |
| HTTP (currency API) | `aiohttp` (with `requests` sync fallback) |
| Container | Docker / Docker Compose |
| Bot mode | Long polling (`application.run_polling()`) |

## 3. Layered structure

```
run.py                          # Entry point — sets sys.path and calls src.core.main()

src/                            # Telegram-facing layer (handlers, conversation flow, formatting)
├── core.py                     # Application bootstrap, ConversationHandler wiring, leftover handlers
├── handlers/                   # 9-module handler package, all converted to repos
│   ├── onboarding.py           #   /start → language → currency → limit
│   ├── settings.py             #   change language / currency / limit
│   ├── admin.py                #   /help, /about, /leave, /show_log_chart
│   ├── charts.py               #   /monthly_stat, /yearly_stat etc.
│   ├── records.py              #   monthly summary, /income
│   ├── menu.py                 #   main-menu dispatch table
│   ├── transactions.py         #   edit/delete an individual tx
│   ├── categories.py           #   add/rename/delete categories
│   └── tasks.py                #   add/rename/delete subcategories ("tasks")
├── save_transaction.py         # Multi-step parse → confirm → save flow (largest single file)
├── detailed_transactions.py    # Filterable history browser
├── charts.py                   # matplotlib chart generators (sync, CPU-heavy)
├── keyboards.py                # InlineKeyboard / ReplyKeyboard builders
├── language_util.py            # Language detection / config caching
├── states.py                   # Conversation state IDs
├── texts.py / texts_ru.py      # English / Russian copy
└── logger.py                   # Logging setup, debug toggle, user-interaction logging

domain/                         # Pure-Python business logic, no I/O
├── models/user_session.py      # UserSession, UserConfig, Transaction dataclasses
├── session_loader.py           # Single batch fetch from repos → UserSession
└── filters.py                  # filter_by_period, get_sum_per_category, calculate_limit_usage, …

infrastructure/                 # Outbound adapters
├── database/
│   ├── connection.py           # DatabaseConnection wrapper (asyncpg pool)
│   └── migrations/
│       └── 001_initial_schema.sql
├── repositories/               # CRUD + simple queries; no business logic
│   ├── base.py                 # BaseRepository (execute / fetch_one / fetch_all / fetch_val)
│   ├── transaction_repository.py
│   ├── user_repository.py
│   └── category_repository.py
└── external/
    └── currency_service.py     # Exchange-rate fetch + 12h DB cache + in-memory cache

shared/
├── di/
│   ├── container.py            # Container holds pool + repos + currency service
│   └── bot_integration.py      # setup_container / cleanup_container / get_repos(context)
└── utils/
    └── pagination.py           # paginate() + create_nav_buttons()

scripts/                        # One-off utilities
├── apply_schema.py             #   apply 001_initial_schema.sql
├── migrate_csv_to_postgres.py  #   one-shot migration from old user_data/*.csv tree
├── test_repositories.py        #   integration smoke test against running PG
└── verify_postgres.py          #   connectivity check

configs/
├── config                      # gitignored — TELEGRAM token, DEBUG flag
├── currency_defaults.json      # fallback exchange rates if API + DB both fail
├── exchangerates.json          # legacy cache from CSV era; superseded by exchange_rates table
├── dictionary.json             # default category seeds (en)
└── dictionary_ru.txt           # default category seeds (ru)

infrastructure/database/migrations/   # SQL migrations (only 001 so far; no migration framework)
```

## 4. Data model

### `users`
`user_id BIGINT PK | username TEXT | telegram_username TEXT | created_at | updated_at`

### `user_configs` (1:1 with users)
`user_id PK FK→users | language VARCHAR(10) | currency CHAR(3) | monthly_limit DECIMAL(15,2) | name | created_at | updated_at`
- `monthly_limit` defaults to `99999999.00` (sentinel for "no limit" — see production-readiness.md for a NULL-based fix).

### `user_categories`
`id SERIAL PK | user_id FK | language VARCHAR(10) | category_name | subcategory_name | created_at`
- Unique on `(user_id, language, category_name, subcategory_name)`.
- Per-language: changing language doesn't migrate existing entries; user effectively gets a fresh dictionary.

### `transactions`
`id SERIAL PK | user_id FK | timestamp TIMESTAMPTZ | transaction_type VARCHAR(10) {spending|income} | category_name | subcategory_name | amount DECIMAL(15,2) | currency CHAR(3) | created_at`

Indexes:
- `idx_transactions_user_timestamp (user_id, timestamp DESC)`
- `idx_transactions_user_month (user_id, date_trunc_month(timestamp))` — uses an `IMMUTABLE` SQL function so it can be indexed.
- `idx_transactions_user_category (user_id, category_name)`
- `idx_transactions_user_type (user_id, transaction_type)`

### `exchange_rates`
`base_currency CHAR(3) | target_currency CHAR(3) | rate DECIMAL(15,6) | last_updated`
- PK on `(base_currency, target_currency)`. Currently only `base='USD'` rows are populated.

### `migration_log`
Audit trail for the one-shot CSV→PG migration. Not used at runtime.

## 5. Request flow — "save a transaction"

1. **User sends** `Coffee 4` (or selects categories via inline keyboard).
2. **Conversation handler** in `core.py` matches the regex `\b\w+\s+\d+$` and routes to `save_transaction.save_transaction`.
3. **Parse + validate**: regex split, multi-line support, currency normalization.
4. **Category lookup**: `repos.categories.find_category_by_subcategory()` — if known, skip prompts; if ambiguous, show keyboard.
5. **Confirm**: user confirms via inline button → `handle_transaction_confirmation`.
6. **Persist**:
   - `repos.transactions.save_spending(...)` → INSERT into `transactions`.
   - `repos.categories.add_category(...)` → INSERT into `user_categories` (`ON CONFLICT DO NOTHING`).
7. **Limit check**: `load_user_session` → `calculate_limit_usage` → reply with daily-budget remaining.

## 6. Request flow — "show records"

1. User taps "Monthly summary" → `menu_call` dispatch table → `show_records`.
2. `load_user_session(user_id, repos, transactions_months=12)` — **single batched read**:
   - 1 query for config
   - 1 query for category dictionary
   - 1 query for transactions (date-range filtered)
3. All aggregation (`filter_by_period`, `get_sum_per_category`, `calculate_daily_average`) happens **in-process**.
4. Format text via `texts.RECORDS_TEMPLATE` and reply.

This "batch fetch + memory filter" pattern is the core decision of the new architecture: 3 round-trips per handler, regardless of how many aggregations the response needs. Trade-off: keeps up to ~12 months of one user's transactions in RAM during request handling. Reasonable while users are <10k transactions/year; at much higher cardinality, push aggregation back to SQL.

## 7. Currency conversion

`CurrencyService` (`infrastructure/external/currency_service.py`) implements 3-layer caching:

```
in-memory dict (12h TTL)
   ↓ miss
exchange_rates table (12h freshness check)
   ↓ stale or empty
open.er-api.com (10s timeout) → write-through to DB
   ↓ network failure
configs/currency_defaults.json (hardcoded fallback)
```

Conversion routes through USD: `from → USD → to`. Supported currencies: EUR, RUB, AMD, USD, THB.

## 8. Dependency injection

`shared/di/container.py` holds the asyncpg pool and three repo instances. It's a singleton initialized once via `setup_container()` (registered as PTB's `post_init` callback), torn down via `cleanup_container()` (`post_shutdown`).

Handlers access it via:

```python
from shared.di import get_repos
repos = get_repos(context)         # context is PTB's ContextTypes.DEFAULT_TYPE
await repos.transactions.save_spending(...)
await repos.users.get_config(user_id)
await repos.currency.get_rates()
```

The container is stashed in `application.bot_data['di_container']` so every handler can reach it through the standard PTB context.

## 9. Conversation states

All states live in `src/states.py`. `core.py:main()` wires one big `ConversationHandler` covering ~25 states for: onboarding, transaction entry, category management, task (subcategory) management, settings, detailed-history browsing, and edit/delete flows. Reentry is allowed (`allow_reentry=True`) and `/cancel` is the universal fallback.

## 10. Logging

`src/logger.py` configures three sinks:
- `app.log` — application logs (TimedRotatingFileHandler).
- `user_log.csv` — per-interaction CSV row (used to render usage charts).
- stdout — for container `docker logs`.

A debug flag in `configs/config` toggles verbosity at runtime; `/debug` (admin only) flips it.

Note: `structlog` is in `requirements.txt` but not actually wired up — see production-readiness.md.

## 11. Deployment (current)

```bash
docker compose up -d --build
```

- `postgres` service (PG 15-alpine) with `infrastructure/database/migrations/` mounted as initdb scripts → schema applied on first boot.
- `budgetbot` service depends on Postgres health check.
- `./user_data` mounted into the bot container — vestigial from the CSV era; can be unmounted post-migration.
- Token comes from `.env` via `env_file:` and Postgres password from `POSTGRES_PASSWORD`.

Single bot replica, long-polling — no horizontal scaling. See production-readiness.md.

## 12. What's *not* in this doc

- `REFACTORING.md` (root) — phase-by-phase history of the migration.
- `docs/production-readiness.md` — gap analysis for going from "works for me" to "1k–10k users".
- `docs/project.md` — high-level project overview, getting started, conventions.
