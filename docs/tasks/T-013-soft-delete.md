---
id: T-013
title: Soft delete and recovery
status: backlog
type: feature
area: db
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Transactions and users are hard-deleted (/leave cascades). No recovery, no audit trail.

## Acceptance
- [ ] deleted_at columns on transactions and users; all queries filter deleted_at IS NULL
- [ ] Periodic job hard-deletes records older than N days

## Log
- 2026-07-07 created from production-readiness D1 / REFACTORING Phase 5.1
