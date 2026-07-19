---
id: dv-3cdc
title: Soft delete and recovery
status: todo
priority: low
assignee: 
labels: [backlog, feature, db]
deps: []
parent: 
created: 2026-07-19T14:55:41Z
updated: 2026-07-19T14:55:41Z
---

## Description

Migrated from `docs/tasks/T-013-soft-delete.md`.

Transactions and users are hard-deleted (/leave cascades). No recovery, no audit trail.

## Acceptance Criteria

- [ ] deleted_at columns on transactions and users; all queries filter deleted_at IS NULL
- [ ] Periodic job hard-deletes records older than N days

## Notes

### Log

- 2026-07-07 created from production-readiness D1 / REFACTORING Phase 5.1
