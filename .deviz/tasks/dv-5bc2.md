---
id: dv-5bc2
title: Fix show_last: Transaction attribute mismatch
status: done
priority: high
assignee: 
labels: [bug, bot]
deps: []
parent: 
created: 2026-07-19T15:01:13Z
updated: 2026-07-19T15:01:13Z
---

## Description

Migrated from `docs/tasks/T-020-fix-show-last-transaction-attribute-mism.md`.

src/core.py:423 latest_records formats tx.category/tx.subcategory but the Transaction dataclass (infrastructure/repositories/transaction_repository.py) has category_name/subcategory_name -> AttributeError on /show_last. Found during first prod run 2026-07-09. Check the rest of core.py for the same stale attribute names.

## Acceptance Criteria

- [ ] TODO

## Notes

### Log

- 2026-07-09 created
- 2026-07-09 started
- 2026-07-09 Root cause: latest_records numeric path returned repo Transactions (category_name) formatted with domain attrs (.category). Added Transaction.from_repo() to domain model, converted in core.py, deduped 2 inline conversions in session_loader. Deployed to prod container.
- 2026-07-09 moved to review

### Testing

#### Happy Path Tests
- [ ] `/show_last` (no args) — returns 5 most recent spendings, each line formatted `id: YYYY-MM-DD, category, subcategory, amount, currency`, plus total
- [ ] `/show_last 10` — returns 10 most recent spendings
- [ ] `/show_last <category>` (e.g. `/show_last transport`) — returns last 12 months of that category (path was already working, confirm no regression)

#### Edge Cases
- [ ] `/show_last 999` with fewer records — returns all available, no crash
- [ ] `/show_last nonexistentcategory` — returns "no records" message
- [ ] Trigger via inline menu button (callback_query path) — same output as typed command

#### Regression (session_loader refactor touched shared code)
- [ ] `/show` — stats render normally
- [ ] `/monthly_stat` — charts render normally
- [ ] Menu → recent transactions list — dates and categories display correctly
- 2026-07-19 done
- 2026-07-19 changelog: Fixed show_last Transaction attribute crash
