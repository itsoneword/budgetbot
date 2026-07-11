---
id: T-025
title: Admin panel commands: user data export + activity monitoring
status: review
type: feature
area: bot
priority: p2
deps: []
tags: [admin]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Admin-only capabilities exist in code but are invisible in the bot (only show_log_chart and toggle_debug are gated to ADMIN_USER_ID today). Add admin commands, all gated by ADMIN_USER_ID: /admin_users (list users with last-activity, tx counts — data already logged via log_user_interaction), /admin_export <user_id> (download a user's transactions like /download does for self), /admin_stats (DAU/WAU, new users, AI usage counts). Surface them in the admin-scoped command menu + help section (depends loosely on the command registry task). No new data collection — only expose what repositories already store.

## Acceptance
- [x] `is_admin(user_id)` in src/config.py; inline admin checks in core.py toggle_debug and handlers/admin.py show_log_chart refactored to use it
- [x] `/admin_users`: all users with tx count + last activity, sorted last-active first, chunked into ≤4096-char messages
- [x] `/admin_export <user_id>`: validates user exists, sends CSV via domain/export.render_transactions_csv (T-028 renderer), no disk writes
- [x] `/admin_stats [days=30]`: DAU/WAU/MAU, new users (7d/30d), total users/transactions, per-function AI counts from global_log.txt
- [x] Usage-log parser extracted to src/usage_log.py; generate_usage_summary_chart consumes it and still renders
- [x] Registry rows in src/commands.py with admin_only=True (EN+RU, ≤256 chars) — admin menu scope + admin /help pick them up automatically
- [x] ADMIN_* error copy in both src/texts.py and src/texts_ru.py; non-admin invocation gets ADMIN_ONLY

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

Decisions: stats from `global_log.txt` (DAU/WAU/AI counts — only place non-transaction activity lives) + DB for user/tx counts; `/admin_users` flat chunked ≤4096-char messages sorted by last activity desc (72 users, no pagination); flat `/admin_*` commands (no button menu). Grant/revoke AI belongs to **T-022**, not here. **Merges after T-021 (registry rows), T-028 (consumes its `domain/export.py`), and T-022 (shared `handlers/admin.py`).**

1. `src/config.py`: `is_admin(user_id) -> bool`; refactor inline checks (`core.py:184` toggle_debug, `handlers/admin.py:83` show_log_chart). Single seam T-022 also uses.
2. `infrastructure/repositories/transaction_repository.py`: `get_activity_by_user()` — one query, `users LEFT JOIN transactions GROUP BY`, tx_count + last_tx_at, ORDER BY last_tx_at DESC NULLS LAST. Add `get_all_for_user(user_id)` only if T-028 didn't.
3. New `src/usage_log.py`: `parse_usage_log(days) -> list[UsageRecord]` lifted verbatim from the inline block in `src/charts.py:400-440`; refactor `generate_usage_summary_chart` to call it; missing file → [].
4. New `domain/admin_stats.py` (pure): `compute_usage_stats(records, now) -> AdminStats` (DAU/WAU/MAU, active-user lists, per-function AI counts) + format helpers.
5. Handlers in `src/handlers/admin.py`, each opening with `is_admin` guard: `/admin_users` (repo aggregate, one line per user, chunked); `/admin_export <user_id>` (validate via `users.user_exists`, fetch all tx, render via `domain/export.py` from T-028, send `InputFile(BytesIO(...))` — no disk writes); `/admin_stats [days=30]` (`parse_usage_log` in `asyncio.to_thread` + `compute_usage_stats` + DB counts). Registry rows `admin_only=True`; ADMIN_* copy in both texts files.

Files: new src/usage_log.py, domain/admin_stats.py; modified src/handlers/admin.py, src/core.py, src/config.py, transaction_repository.py, src/charts.py, texts.py, texts_ru.py.
Risks: log file starts fresh per deploy volume — stats cover only on-disk history (accepted); `/admin_export` exposes user data — admin scope only.
- 2026-07-11 started
- 2026-07-11 Implemented: is_admin seam, usage_log parser extraction, domain/admin_stats, get_activity_by_user, /admin_users /admin_export /admin_stats handlers + registry rows + EN/RU copy. Verified: import smoke, pure-fn unit tests, chart render on synthetic log, SQL against throwaway postgres.
- 2026-07-11 moved to review

## Testing

### Critical (must pass before merge)
- [ ] As admin: /admin_users lists all users, most recently active first, users without transactions last, no message over 4096 chars (72 users should arrive in 1-2 messages)
- [ ] As admin: /admin_export <known_user_id> returns spendings_<id>.csv; header is id,timestamp,category,subcategory,amount,currency,user_id,transaction_type and rows match that user's data
- [ ] As admin: /admin_stats replies with DAU/WAU/MAU, new users 7d/30d, total users/transactions, AI calls per function (ask, handle_voice)
- [ ] As non-admin: each of /admin_users, /admin_export 123, /admin_stats replies with the ADMIN_ONLY message (RU user gets Russian copy) and leaks no data
- [ ] /show_log_chart still renders both charts (30d + 1y) after the parser extraction
- [ ] Admin /help lists the three new commands; non-admin /help does not; admin chat command menu shows them after restart (sync_bot_commands)

### Important
- [ ] /admin_export with no args, non-numeric arg, or extra args → usage message
- [ ] /admin_export with an unknown user_id → "User ... not found"
- [ ] /admin_export for an existing user with zero transactions → "no transactions" message, no empty file
- [ ] /admin_stats 7 narrows event/AI counts to 7 days while MAU stays a 30-day window
- [ ] /admin_stats right after a fresh deploy (missing/empty global_log.txt) → zeros, no crash
- [ ] /debug still admin-gated after the is_admin refactor

### Nice-to-have
- [ ] Users with NULL telegram_username render as "-" in /admin_users rather than "None"
- [ ] /admin_stats active-users list shows readable "Name @username" labels
- 2026-07-11 owner feedback: /admin_users now defaults to users with >=1 tx (all arg shows everyone) and enriches names/@usernames from the usage log (users table name columns are never populated)
