---
id: dv-f0d5
title: Read tool: query_transactions for raw-row questions (show tx, full history)
status: todo
priority: high
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T15:31:18Z
updated: 2026-07-19T15:31:18Z
---

## Description

query_transactions(period, category, subcategory, min/max amount, limit) — parameterized only, user_id scoping injected server-side, model never writes SQL. Answers what prompt-stuffing cannot: specific dates, 'all spendings over 100', last purchase of X beyond aggregates. Carries the deep-history manual testing folded in from dv-4a58: 3-year breakdown with max/min months per year, 'when did I start tracking' (May 2023), latency on ~18KB prompt, fresh account with 1-2 tx no crash.

## Acceptance Criteria

## Notes

## Comments
