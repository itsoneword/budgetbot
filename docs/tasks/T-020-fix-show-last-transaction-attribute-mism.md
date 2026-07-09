---
id: T-020
title: Fix show_last: Transaction attribute mismatch (tx.category vs category_name)
status: todo
type: bug
area: bot
priority: p0
deps: []
tags: []
blocked: 
created: 2026-07-09
updated: 2026-07-09
---

## Context
src/core.py:423 latest_records formats tx.category/tx.subcategory but the Transaction dataclass (infrastructure/repositories/transaction_repository.py) has category_name/subcategory_name -> AttributeError on /show_last. Found during first prod run 2026-07-09. Check the rest of core.py for the same stale attribute names.

## Acceptance
- [ ] TODO

## Log
- 2026-07-09 created
