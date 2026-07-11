---
id: T-028
title: Fix /download: export transactions from PostgreSQL, not stale user_data CSV
status: todo
type: bug
area: bot
priority: p1
deps: []
tags: [db]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
download_spendings (src/core.py:511) sends user_data/{id}/spendings_{id}.csv — a frozen pre-migration file; everything added since the PostgreSQL migration is missing from the export. Fix: load transactions via repositories (load_user_session or repos.transactions), render CSV in memory (or scratch temp), send as document. Also fixes convention violations: file I/O in a handler + blocking open() on the event loop. Mind /download vs admin export overlap (T-025) — same CSV renderer should serve both.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
