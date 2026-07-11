---
id: T-003
title: Replace print() with logger in runtime code
status: todo
type: ops
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
shared/di/bot_integration.py:29,40 and some scripts print to stdout, bypassing logging config (no timestamps, no levels, can't be silenced).

## Acceptance
- [ ] No print() in runtime code paths (shared/, src/, domain/, infrastructure/)
- [ ] Replaced with logger calls at appropriate levels

## Log
- 2026-07-07 created from production-readiness B3

## Implementation plan (approved 2026-07-11)

Decisions: full sweep (all 84 active prints); strip redundant `DEBUG:`/`[OK]` prefixes; except-block prints → `logger.exception` (gains tracebacks); console stays quiet in non-debug mode — that's the point. **No config work needed**: `setup_logging()` in `src/logger.py` already provides rotating file + console handlers and /debug toggling; convention precedent (`logger = logging.getLogger(__name__)`) exists in claude_agent.py/whisper_local.py.

Inventory (active prints, runtime code only — domain/, infrastructure/, run.py are clean):
- `src/save_transaction.py` — 59 (~57 DEBUG traces → logger.debug; except-blocks e.g. line 241 → logger.exception)
- `src/detailed_transactions.py` — 21 (all → logger.debug)
- `src/handlers/transactions.py` — 2 (except blocks lines 197, 571 → logger.exception)
- `shared/di/bot_integration.py` — 2 (lifecycle → logger.info)

Steps: add module logger to each of the 4 files; convert per mapping above; SKIP the commented-out prints in core.py/keyboards.py for now (avoids core.py conflict with parallel tasks — later hygiene). Verify: `grep -rn "print(" src/ domain/ infrastructure/ shared/ run.py` clean of active calls; `python -m py_compile`; boot + add a transaction, traces land in `user_data/app.log` with /debug on.

Risks: debug traces disappear from `docker logs` unless /debug is on (intended); 84 mechanical edits → py_compile + smoke run.
Follow-up flagged (out of scope): `src/logger.py:95-100` rotates app.log every 10 MINUTES (`when="m", interval=10, backupCount=5`) — only ~50 min of history retained; likely meant daily.
