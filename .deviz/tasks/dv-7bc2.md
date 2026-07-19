---
id: dv-7bc2
title: Analytics events table
status: todo
priority: low
assignee: 
labels: [backlog, feature, infra]
deps: []
parent: 
created: 2026-07-19T14:55:42Z
updated: 2026-07-19T14:55:42Z
---

## Description

Migrated from `docs/tasks/T-016-analytics-events.md`.

Usage analytics currently means parsing user_log.csv, which doesn't survive container rebuilds. Move to a user_events table.

## Acceptance Criteria

- [ ] user_events table with writes from handlers
- [ ] Usage chart (/show_log_chart) reads from the DB

## Notes

### Log

- 2026-07-07 created from REFACTORING Phase 5.3
