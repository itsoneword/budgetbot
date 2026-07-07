# BudgetBot

A Telegram bot for tracking personal expenses. Send a message like `Coffee 4`, get categorized, charted, currency-normalized history. Multi-language (English, Russian), multi-currency (EUR, USD, RUB, AMD, THB), self-hosted.

## Status

| | |
|---|---|
| Storage | PostgreSQL (migrated from per-user CSV in Jan 2026) |
| Architecture | Layered: handlers / domain / infrastructure |
| Deployment | Docker Compose, single instance, long-polling |
| Tested user base | Personal use; **not yet hardened for 1k–10k users** — see [`production-readiness.md`](./production-readiness.md) |
| Current version | 0.2.3 (per `core.py`'s `/about`) |

## Repository layout

```
run.py                  Entry point
src/                    Telegram handlers and conversation flow
domain/                 Pure-Python business logic (filters, models)
infrastructure/         Database, repositories, external APIs
shared/                 DI container, pagination utility
scripts/                One-off operational scripts
configs/                Runtime config + fallback data
docs/                   This documentation set
REFACTORING.md          Phase-by-phase migration history (root)
```

For the architecture deep-dive see [`docs/architecture.md`](./architecture.md).

## Quick start (development)

### Prerequisites
- Docker + Docker Compose
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Setup

```bash
# 1. Configure secrets
cp configs/config.example configs/config       # if you keep an example; otherwise create:
# configs/config:
#   [TELEGRAM]
#   TOKEN = 1234567890:AAAA...
#   [DEBUG]
#   DEBUG = false

# 2. Set Postgres password (used by docker-compose)
echo "POSTGRES_PASSWORD=changeme" > .env

# 3. Boot the stack
docker compose up -d --build

# 4. Tail logs
docker logs -f budgetbot-container
```

The Postgres schema is applied automatically from `infrastructure/database/migrations/001_initial_schema.sql` on first boot.

### Running outside Docker

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres                  # just the DB
export DATABASE_URL='postgresql://budgetbot:changeme@localhost:5432/budgetbot'
python3 run.py
```

### Smoke tests

```bash
docker compose up -d postgres
python3 scripts/verify_postgres.py             # connectivity
python3 scripts/test_repositories.py           # CRUD round-trip
```

## Bot commands

| Command | What it does |
|---|---|
| `/start` | Onboarding (language → currency → optional monthly limit) |
| `/menu` | Main menu (buttons for everything below) |
| `/show` / `/show_last_month` | Monthly summary |
| `/show_ext` | Detailed history with category/period filters |
| `/income` | Log income transaction |
| `/monthly_stat` / `/monthly_ext_stat` / `/yearly_stat` | Charts |
| `/upload` | Restore from CSV (admin/import path) |
| `/leave` | Archive your profile (delete-cascade) |
| `/help`, `/about` | Self-service docs |
| `/debug` | Admin-only — toggle debug logging |
| `/show_log_chart` | Admin-only — render usage chart |
| Free text matching `<word> <number>` | Quick-add transaction |

## Conventions

- **All handlers are async.** Repository calls return coroutines — always `await`.
- **User IDs are `int`** (Telegram's native type). Old code used `str`; that conversion is done — don't reintroduce stringification.
- **Read once, filter many.** A handler should call `load_user_session()` at most once and run all aggregations on the resulting `UserSession`. Don't sprinkle individual repo queries through a handler.
- **Currency normalization happens at display time**, not at write time — transactions store their original currency.
- **No file I/O in handlers.** All persistent state goes through repositories. The only remaining file reads are for currency fallback config and chart output buffers.

## How to add a feature

1. **DB change?** Add a new migration file in `infrastructure/database/migrations/` (no migration framework yet — see production-readiness gap). Apply via `python3 scripts/apply_schema.py` against your dev DB.
2. **Repo method?** Add to the relevant `infrastructure/repositories/*_repository.py`. Keep it dumb — pure CRUD or simple SQL queries, no business logic.
3. **Business logic?** Add a pure function to `domain/filters.py` (or a new module under `domain/`). It should take dataclasses, return dataclasses or primitives, never touch I/O.
4. **Handler?** Add to the right module under `src/handlers/`. Pattern:
   ```python
   async def my_handler(update, context):
       user_id = update.effective_user.id
       texts = check_language(update, context)
       repos = get_repos(context)
       session = await load_user_session(user_id, repos)
       result = some_filter(session.transactions)
       await update.message.reply_text(texts.MY_TEMPLATE.format(...))
       return SOME_STATE
   ```
5. **Wire it up** in `core.py:main()` (or the appropriate `ConversationHandler` state).
6. **Add copy** to both `texts.py` and `texts_ru.py`.

## Documentation index

- **[`docs/architecture.md`](./architecture.md)** — Layered structure, data model, request flows, DI, currency service.
- **[`docs/production-readiness.md`](./production-readiness.md)** — What's needed to go from personal use to 1k–10k users. Concrete bugs, gaps, and prioritized recommendations.
- **[`REFACTORING.md`](../REFACTORING.md)** — Migration history. Useful for understanding *why* the code looks the way it does. Mostly historical now.

## Removed (post-migration)

These files used to exist and are referenced in old commits / READMEs. They no longer exist:

- `src/file_ops.py` — CSV read/write helpers → replaced by repositories
- `src/pandas_ops.py` — pandas analytics → replaced by `domain/filters.py`
- `src/show_transactions.py` → split into `src/handlers/records.py` + `src/detailed_transactions.py`
- `src/change_data.py` → split into `src/handlers/categories.py` + `src/handlers/tasks.py`
- `src/change_transactions.py` → `src/handlers/transactions.py`
- `docs/handler_conversion_examples.md` — migration cookbook, no longer relevant
