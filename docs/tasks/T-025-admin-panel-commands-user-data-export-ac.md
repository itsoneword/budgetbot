---
id: T-025
title: Admin panel commands: user data export + activity monitoring
status: todo
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
- [ ] TODO

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
