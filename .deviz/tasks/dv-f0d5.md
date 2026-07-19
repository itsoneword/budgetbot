---
id: dv-f0d5
title: Read tool: query_transactions for raw-row questions (show tx, full history)
status: in_progress
priority: high
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T15:31:18Z
updated: 2026-07-19T16:28:44Z
---

## Description

query_transactions(period, category, subcategory, min/max amount, limit) — parameterized only, user_id scoping injected server-side, model never writes SQL. Answers what prompt-stuffing cannot: specific dates, 'all spendings over 100', last purchase of X beyond aggregates. Carries the deep-history manual testing folded in from dv-4a58: 3-year breakdown with max/min months per year, 'when did I start tracking' (May 2023), latency on ~18KB prompt, fresh account with 1-2 tx no crash.

## Acceptance Criteria

## Notes

## Notes

### Implementation plan (plan agent, 2026-07-19)

Key decision: query_transactions is a PURE IN-MEMORY filter over session.transactions (ask flow already loads full history for the summary, 10k-row cap). No new repository method, no SQL surface the model can influence — user scoping is structural. Matches load-once/filter-in-memory convention. If summary loading is ever windowed, that is the moment to add repos.transactions.search(...).

1. NEW domain/ask_tools.py (pure): QUERY_TRANSACTIONS_SCHEMA (period/category/subcategory/transaction_type/min_amount/max_amount/limit, all optional); parse_period ('YYYY', 'YYYY-MM', 'YYYY-MM-DD..YYYY-MM-DD', presets 3m/6m/12m/ytd/current_month/last_month/all; ValueError with model-readable msg); query_transactions(transactions, ...) -> QueryResult(rows newest-first truncated to limit, total_matches, totals over ALL matches — answers 'sum of spendings over 100' even truncated); format_query_result (~45 chars/row, 8KB hard cap with note); format_no_match(known_categories) so the model self-corrects category spellings in one round.
2. NEW src/ask_agent_tools.py: build_ask_toolspecs(session) — thin async glue (Decimal conversion, limit clamp 1..200, ValueError->ToolInputError); no I/O; keeps core.py from growing (T-030).

Tests (pure, injectable now=): parse_period matrix incl. boundary inclusivity matching filter_by_period; filters case-insensitive/combined/bounds; ordering; truncation with correct totals; empty list (fresh account); clamps; format caps; system prompt with/without tools; wrapper is_error paths.

Manual (folded-in from dv-4a58): 3-year breakdown = zero tool calls (check logs); 'when did I start' (summary, no tool); 'all spendings over 100' -> min_amount=100; last-purchase-of-X beyond 92d; specific-date question; latency vs today; fresh 1-2 tx; adversarial 'list every transaction one by one' -> ends at turn cap with usable partial answer; RU account; llm-usage.jsonl one row per turn, no doubling.

## Comments
