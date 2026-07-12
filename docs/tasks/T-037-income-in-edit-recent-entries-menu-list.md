---
id: T-037
title: Income in Edit-recent-entries menu: list, edit, delete income records
status: todo
type: feature
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-12
---

## Context
Owner request 2026-07-12 (T-035 wrap-up): the menu Edit-recent-entries flow (handlers/transactions.py show_recent_entries) filters to spendings only, so income can only be deleted via /delete_income, not edited at all. Wanted: include income records in the edit list (visually marked, e.g. 💵 prefix) so they can be edited and deleted from the menu like spendings. Design constraint: the per-transaction edit keyboard offers edit category/subcategory backed by the SPENDING category dictionary — wrong for income (free-form category, no subcategory). For income rows show a reduced keyboard: edit date / edit category (free text) / edit amount / delete. Reuse repos.transactions.update/delete (type-agnostic by id) and the type-mismatch guards from T-035. Owner explicitly parked the alternative of merging /delete + /delete_income into one command: type-split commands stay, but menu editing should be unified.

## Acceptance
- [ ] TODO

## Log
- 2026-07-12 created
