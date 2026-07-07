---
id: T-001
title: Fix admin check (int vs str comparison)
status: todo
type: bug
area: bot
priority: p0
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
src/core.py:183 and src/handlers/admin.py:82 compare int user_id to string literal "46304833" — int != str is always True, so every user including the admin is denied. Move the ID to env.

## Acceptance
- [ ] ADMIN_USER_ID read from env with int() cast, single constant, no string literals in handlers
- [ ] /debug and /show_log_chart work for the admin and are denied for everyone else

## Log
- 2026-07-07 created from production-readiness B1
