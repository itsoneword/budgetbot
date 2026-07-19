---
id: T-050
title: states.py collision: PROCESS_INCOME/WAITING_FOR_DOCUMENT/DELETE_PROFILE redefined, PROCESS_INCOME==LIMIT shadows onboarding limit state
status: todo
type: bug
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Found during T-046. src/states.py defines 35 states via tuple/range, then lines ~45-47 REDEFINE WAITING_FOR_DOCUMENT=1, PROCESS_INCOME=2, DELETE_PROFILE=3. Inside spendings_handler's states dict both LIMIT (2) and PROCESS_INCOME (now also 2) are keys -> the later PROCESS_INCOME entry overwrites LIMIT's handlers, so the onboarding limit step routes typed input to process_income_menu instead of save_limit. Fix: delete the redefinition lines; audit any behavior that accidentally depended on the collision (onboarding /start flow: language -> currency -> limit). Add a test asserting all names in src.states have unique values.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
