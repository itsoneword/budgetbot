---
id: dv-86de
title: Durable conversation state
status: todo
priority: medium
assignee: 
labels: [backlog, refactor, bot]
deps: []
parent: 
created: 2026-07-19T14:55:41Z
updated: 2026-07-19T14:55:41Z
---

## Description

Migrated from `docs/tasks/T-009-durable-conversation-state.md`.

context.user_data is an in-process dict: restarts drop in-flight conversations, replicas can't share state, and detailed_transactions caches whole transaction lists in it (RAM per browsing user).

## Acceptance Criteria

- [ ] PTB persistence backend configured (Pickle for single replica; Redis-ready interface)
- [ ] Restart preserves an in-flight transaction conversation
- [ ] Transaction lists no longer cached in user_data — paginate by re-query

## Notes

### Log

- 2026-07-07 created from production-readiness P3
