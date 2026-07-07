---
id: T-004
title: Move chart rendering off the event loop
status: todo
type: refactor
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
src/charts.py runs matplotlib/seaborn/pandas synchronously inside async handlers; a 1-3s render blocks every other user. Currency conversion uses row-wise df.apply.

## Acceptance
- [ ] Chart generation call sites wrapped in asyncio.to_thread
- [ ] Currency conversion vectorized (no df.apply(axis=1))
- [ ] All three chart commands render correctly

## Log
- 2026-07-07 created from production-readiness P2
