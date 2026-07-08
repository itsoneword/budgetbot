---
id: T-001
title: Fix admin check (int vs str comparison)
status: done
type: bug
area: bot
priority: p0
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-08
---

## Context
src/core.py:183 and src/handlers/admin.py:82 compare int user_id to string literal "46304833" — int != str is always True, so every user including the admin is denied. Move the ID to env.

## Acceptance
- [x] ADMIN_USER_ID read from env with int() cast, single constant, no string literals in handlers
- [x] /debug and /show_log_chart work for the admin and are denied for everyone else

## Log
- 2026-07-07 created from production-readiness B1
- 2026-07-07 started
- 2026-07-07 Added src/config.py with ADMIN_USER_ID from env (int cast, default 0); replaced string-literal checks in core.py toggle_debug and handlers/admin.py show_log_chart; added ADMIN_USER_ID to .env
- 2026-07-07 moved to review

## Testing

### Critical
- [x] With ADMIN_USER_ID=46304833 in .env, /debug from the admin account toggles debug mode (replies "Debug mode is now ON/OFF")
- [x] /show_log_chart from the admin account sends the two usage charts
- [x] /debug from a non-admin account replies "Sorry, only admin users can toggle debug mode."
- [x] /show_log_chart from a non-admin account replies "This command is restricted to the bot owner."

### Important
- [ ] With ADMIN_USER_ID unset (removed from .env), both commands are denied for everyone, including the admin (fail-closed default 0)
- [x] Container picks up the env var: `docker compose exec budgetbot python -c "from src.config import ADMIN_USER_ID; print(ADMIN_USER_ID)"` prints 46304833
- [x] Bot stays responsive (returns to normal transaction handling) after a denied admin command

### Regression
- [ ] Debug-mode setting still persists to the config file after toggling (save_debug_setting_to_config path unchanged)
- [ ] Non-admin handlers in src/handlers/admin.py (/help, about) still work
- 2026-07-08 Dockerfile was missing domain/infrastructure/shared packages - fixed; bot runs in compose, container sees ADMIN_USER_ID=46304833 as int
- 2026-07-08 Manual testing passed in test bot: admin allowed, non-admin denied for /debug and /show_log_chart
- 2026-07-08 done
