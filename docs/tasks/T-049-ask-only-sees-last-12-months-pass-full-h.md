---
id: T-049
title: /ask only sees last 12 months: pass full history to finance summary
status: todo
type: bug
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner repro 2026-07-19 (screenshot): asked for 3-year alcohol breakdown, bot answered 'data only goes back to 2025-07-24' though DB has data since 2023. Cause: src/core.py:704 loads transactions_months=12 for the ask flow. Fix: transactions_months=None (full history) — build_finance_summary scales fine (1 line per month); also extend per-category-by-month breakdown beyond last-6-months (or per year) so max/min month per year questions are answerable. Watch prompt size for very long histories.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
