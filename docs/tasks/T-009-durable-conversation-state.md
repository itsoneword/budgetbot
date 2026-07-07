---
id: T-009
title: Durable conversation state
status: backlog
type: refactor
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
context.user_data is an in-process dict: restarts drop in-flight conversations, replicas can't share state, and detailed_transactions caches whole transaction lists in it (RAM per browsing user).

## Acceptance
- [ ] PTB persistence backend configured (Pickle for single replica; Redis-ready interface)
- [ ] Restart preserves an in-flight transaction conversation
- [ ] Transaction lists no longer cached in user_data — paginate by re-query

## Log
- 2026-07-07 created from production-readiness P3
