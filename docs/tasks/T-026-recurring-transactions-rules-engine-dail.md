---
id: T-026
title: Recurring transactions: rules engine, daily scheduler, manual management
status: review
type: feature
area: bot
priority: p1
deps: []
tags: [recurring, db]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Monthly payments (rent, subscriptions) auto-added on a chosen day. Design principle (owner): build as an internal action API — pure domain functions + repository — consumed by BOTH manual handlers and the AI intent router (T-019 pattern), so the LLM never gets its own write path. Storage: recurring_rules table (user_id, category, subcategory, amount, currency, day_of_month, active, last_run, created_at). Scheduler: daily job at fixed UTC hour (PTB JobQueue needs python-telegram-bot[job-queue]/APScheduler — check T-004 overlap; plain asyncio loop is fine too) materializes due rules into normal transactions via the existing save path. Rules: clamp day 29-31 to month end; idempotent via last_run so restarts never double-post; notify the user on each auto-add. Manual UX: list/add/pause/delete rules via command + menu.

## Acceptance
- [x] Alembic revision 0004 creates recurring_rules (constraints per plan) + partial active index; downgrade drops it
- [x] RecurringRepository with add/list_for_user/get_by_id/set_active/delete/get_active and atomic claim_run; DI property `repos.recurring`
- [x] domain/recurring.py pure functions: due_date_for (29-31 clamp to month end), is_due (single-period catch-up, backdated), validate_rule_input (strict), format_rules_list
- [x] src/scheduler.py run_recurring_rules: claim-first, posts via transactions.save_spending backdated to due date, syncs category dictionary, notifies user in their language, Forbidden/per-rule errors don't kill the batch
- [x] JobQueue registration in core.py: run_daily at RECURRING_HOUR_UTC (env, default 6) + run_once startup catch-up; requirements pin python-telegram-bot[job-queue]==22
- [x] /recurring lists rules with rr_pause_/rr_resume_/rr_del_ (+rr_delc_ confirm) inline buttons; /recurring add <name> <amount> <day> args-only; internal create/list/set_active/delete functions handler-independent for T-027
- [x] ^rr CallbackQueryHandler registered before spendings_handler; /recurring as CommandSpec registry row; main-menu Recurring button + menu_call branch; copy in texts.py and texts_ru.py

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

Status: **no engine code exists** — commit e525330 added docs only; greenfield.
Decisions: catch-up transactions backdated to the due date; spendings-only UI (schema future-proofed for income); `/recurring` open to all users (no LLM cost; T-027 AI channel keeps its own gate); startup catch-up run enabled. **Ships as alembic revision 0004 (down_revision 0003=T-022) — merges after T-022.**

1. Table `recurring_rules(id SERIAL PK, user_id BIGINT REFERENCES users ON DELETE CASCADE, transaction_type VARCHAR(10) CHECK (spending|income) DEFAULT 'spending', category_name TEXT, subcategory_name TEXT, amount DECIMAL(15,2) CHECK >0, currency CHAR(3), day_of_month SMALLINT CHECK 1-31, active BOOL DEFAULT TRUE, last_run DATE /*due-date of last posted period = idempotency key*/, created_at TIMESTAMPTZ)` + partial index `ON recurring_rules(active) WHERE active`.
2. `infrastructure/repositories/recurring_repository.py`: `RecurringRule` dataclass + `add`, `list_for_user`, `get_by_id(rule_id, user_id)`, `set_active`, `delete`, `get_active()`, and atomic `claim_run(rule_id, due_date) -> bool`: `UPDATE ... SET last_run=$2 WHERE id=$1 AND active AND (last_run IS NULL OR last_run < $2)` rowcount — restarts/overlaps never double-post. Export + DI property in `container.py`.
3. `domain/recurring.py` (pure — this is the action-API validation layer T-027 reuses): `due_date_for` (clamp 29–31 via `calendar.monthrange`), `is_due(rule, today) -> Optional[date]` (free catch-up after downtime), `validate_rule_input` (intent.py-style strictness), `format_rules_list`.
4. `requirements.txt`: `python-telegram-bot[job-queue]==22` (without the extra `application.job_queue` is None; image rebuild). New `src/scheduler.py` `run_recurring_rules(context)`: for each active+due rule — `claim_run` first (skip if False) → `transactions.save_spending(..., timestamp=due_date)` + `categories.add_category` (mirror `_save_transaction_to_db`, src/save_transaction.py:34) → notify user, catching `Forbidden` so one blocked user doesn't kill the batch. Register `run_daily(time=RECURRING_HOUR_UTC, tz=UTC)` (env in src/config.py, default 6) + `run_once(..., 60)` startup catch-up. Factor `get_texts_for_language(lang)` out of `src/language_util.py:37-44` for notification language.
5. `src/handlers/recurring.py`: `/recurring` lists rules with inline `rr_pause_<id>`/`rr_resume_<id>`/`rr_del_<id>` (+confirm `rr_delc_<id>`); `/recurring add <name> <amount> <day>` **args-only** (free-text add would be hijacked by quick-add regex core.py:926). Internal `create_rule`/`list_rules`/`deactivate_rule` handler-independent for T-027. `CallbackQueryHandler(pattern="^rr")` registered BEFORE `spendings_handler` (pattern-less menu_callback swallows callbacks — see vtx_ comment core.py:1055). Menu button in `keyboards.py:136` + branch in `handlers/menu.py`; copy in both texts files; registry row for `/recurring` (T-021).

Files: new recurring_repository.py, domain/recurring.py, src/scheduler.py, src/handlers/recurring.py, alembic 0004; modified repositories/__init__.py, container.py, core.py, config.py, language_util.py, keyboards.py, handlers/menu.py, texts.py, texts_ru.py, requirements.txt.
Risks: JobQueue extra forgotten → None at startup; handler ordering in core.py; UTC due-day semantics for far-west users (accepted, personal bot).
- 2026-07-11 started
- 2026-07-11 engine implemented: alembic 0004, RecurringRepository+claim_run, domain/recurring.py, scheduler, /recurring handler+menu+registry, texts EN/RU, job-queue extra
- 2026-07-11 verified: 43 domain unit checks, 33 DB/scheduler-cycle checks vs throwaway postgres (alembic 0001-0004 up+down), job-queue extra resolves, job_queue non-None

## Testing

Automated (done in worktree): 43 domain unit checks (clamping incl. Feb 29/30/31, catch-up/idempotency semantics, strict input validation); 33 integration checks against a throwaway postgres (alembic 0001→0004 up+down, claim_run sequential/replay/10-way concurrent race, full scheduler cycle: backdated post, category sync, EN+RU notification, no-op re-run); `python-telegram-bot[job-queue]==22` resolves and `application.job_queue is not None`.

Manual checklist (live bot, after image rebuild — the job-queue extra requires it):

### Critical
- [ ] Bot starts clean; log shows no "job_queue is None" RuntimeError; alembic upgrade applies 0004 (requires T-022's real 0003 merged first)
- [ ] `/recurring add rent 500 1` → confirmation message; `/recurring` lists the rule with pause + delete buttons
- [ ] `/recurring add netflix 9.99 31` → confirmation includes the month-end clamp note
- [ ] Startup catch-up (~60s after boot): a rule whose day already passed this month posts one transaction backdated to that day, with a notification; visible in /show_last
- [ ] Restart the bot → catch-up run does NOT double-post the same period
- [ ] ⏸ pause → rule marked "(paused)", no posting on next run; ▶️ resume works
- [ ] 🗑 → confirm prompt; confirm deletes, Back returns to list
- [ ] /menu → 🔁 Recurring button opens the same list; buttons work while the menu conversation is active (rr callbacks not swallowed)

### Important
- [ ] `/recurring add rent abc 1`, `... rent 5 0`, `... rent 5 32`, `/recurring foo` → localized error/usage text, nothing saved
- [ ] RU-language user gets RU list, buttons, and auto-add notification
- [ ] Rule added mid-month with an already-passed day does NOT backdate-post for the current month (first fires next month)
- [ ] /recurring appears in the Telegram command menu and /help (EN + RU)
- [ ] User who blocked the bot: auto-add still saves, batch continues (check logs)

### Nice-to-have
- [ ] New subcategory from a rule appears in the category dictionary after first auto-post
- [ ] RECURRING_HOUR_UTC env override respected
- 2026-07-11 moved to review
