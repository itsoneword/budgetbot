---
id: T-016
title: Analytics events table
status: backlog
type: feature
area: infra
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Usage analytics currently means parsing user_log.csv, which doesn't survive container rebuilds. Move to a user_events table.

## Acceptance
- [ ] user_events table with writes from handlers
- [ ] Usage chart (/show_log_chart) reads from the DB

## Log
- 2026-07-07 created from REFACTORING Phase 5.3
