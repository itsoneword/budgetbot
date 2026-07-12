# Changelog

Newest first. One dated line per shipped task or release. Entries are appended
under `## Unreleased` by `python3 scripts/tasks.py done T-NNN --changelog "..."`
(the gate — closing a task without a changelog line is impossible; use
`--no-changelog` only for docs/meta tasks).

## Unreleased

- 2026-07-12 T-035: Income tracking works end-to-end: /income inline args, type-safe /delete_income, voice/text add_income intent with confirm, /ask income-vs-spending analysis, Add-income menu button, /show_last income
- 2026-07-11 release designation 0.3.0: version now a single constant in src/config.py (VERSION/VERSION_DATE), displayed by /about (T-031).

## 2026-07 — Task-tracked development

- 2026-07-11 T-019: voice input — local faster-whisper transcription, LLM intent routing to transaction entry / stats / /ask with confirm gate; multi-transaction messages and relative dates (dd.mm prefix per comma-separated item).
- 2026-07-09 T-020: fix /show_last crash — AttributeError on Transaction.category (repo model vs domain model mismatch in latest_records).
- 2026-07-09 T-018: /ask — AI Q&A over spendings; prompt-packed user data (no text-to-SQL), Claude Agent SDK backend behind a provider-agnostic LLM client, python 3.12 image; gated by admin + allowlist.
- 2026-07-09 T-011 (partial): global error handler — tracebacks logged with user context, user notified on failure.
- 2026-07-09 ops: Postgres data moved to ./pgdata bind mount (survives `down -v`); Docker Hub build workflow made manual-only until T-012.
- 2026-07-09 T-007: automated Postgres backups.
- 2026-07-08 T-002: standardized intra-project imports to src.* prefix.
- 2026-07-08 T-001: fix admin check — ADMIN_USER_ID read from env as int (was str comparison, always False); Docker image now ships domain/infrastructure/shared packages.
- 2026-07-07 ops: task tracker — file-per-task kanban in docs/tasks/ with generated BOARD.md, scripts/tasks.py CLI and Claude Code hooks; architecture/project/production-readiness docs.

## 2026-01 — PostgreSQL migration & layered refactor

- 2026-01: storage migrated from per-user CSV files to PostgreSQL (asyncpg, repository pattern, batch-fetch then filter-in-memory); codebase refactored into layers — src/ handlers, domain/ pure logic, infrastructure/ repositories and external APIs, shared/ DI container (`docs/REFACTORING.md`).

## 2025 and earlier — v0.x releases (imported from README)

### 0.2.3 (2025-10-18)
Fixed Upload command; added logging and analytics; usage charts.

### 0.2.2 (2025-04-23)
Minor changes in Ru version (saving message was changed).
Behavior for single-car transaction was changed (no more Permanent Menu return).

### 0.2.0 (2025-04-01)
Communication changed mostly to inline keyboard.
Adding transaction now offers a list of existing cat|subcat.
Namings of cats|subcats do not allow symbols anymore.
Category edit process is now easier with inline keyboard.
Deletion of transactions is more interactive with inline keyboard.

### Fix patch (2025-03-12)
Fix minor issues with charts.

### Fix patch (2025-02-16)
Changed About command logic, how it handles settings changes.

### 0.1.2 (2024-12-01)
Updated monthly pivot charts to cover 1st month of the range fully (was covering only since 1st month day, current time).
Updated monthly_ext_stat function to use log scale and show sorted per category (was subcat).
Minor logging changes and bug fixes.

### Minor fix (2024-09-19)
Updated logging and error handling for currency exchange functions.
Fixed "A value is trying to be set on a copy of a slice from a DataFrame." issue.

### 0.1.0 (2024-07-16)
Fixed minor issues; added version control to /about.
Changed monthly stat charts and ShowExt command — now showing 8 months and 5 top cats accordingly.
Added detailed subcat_cat chart showing monthly based statistic (monthly_ext_stat).
First users milestone: 3 people constantly using the app.

### 0.0.6 (2024-02-24)
Fixed minor issues; added version control to /about.

### 0.0.5 (2023-11-13)
Fixed sorting months over the year (January shown after December as expected).
Added /about command (current currency, limits, language).
Added currency conversion — transactions in other currencies re-calculated to the current one at today's exchange rate.

### 0.0.4 (2023-11-13)
Yearly piecharts — per-category spending overview on a yearly basis.
Fixed bugs related to getting stuck in Income mode.

### 0.0.3 (2023-06-14)
Charts and heatmap for monthly spending.
Income tracking alongside spending.
Monthly and daily limit tracking with overspend notifications.
Reworked /show_last command — total sum and filtering by category name (e.g. /show_last transport).
