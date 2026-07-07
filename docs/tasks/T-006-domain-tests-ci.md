---
id: T-006
title: Unit tests for domain/ + CI gating
status: todo
type: ops
area: infra
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Only integration smoke script exists (scripts/test_repositories.py). domain/ is pure functions — ideal for pytest. CI should gate on tests.

## Acceptance
- [ ] pytest + pytest-asyncio set up; tests/domain/ covers filters.py aggregations and session_loader (mocked repos)
- [ ] Parser tests for save_transaction multi-line/ambiguous input
- [ ] GitHub workflow runs the suite on push

## Log
- 2026-07-07 created from production-readiness T1 + O2
