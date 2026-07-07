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
