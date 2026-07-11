---
id: T-026
title: Recurring transactions: rules engine, daily scheduler, manual management
status: todo
type: feature
area: bot
priority: p1
deps: []
tags: [recurring, db]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Monthly payments (rent, subscriptions) auto-added on a chosen day. Design principle (owner): build as an internal action API — pure domain functions + repository — consumed by BOTH manual handlers and the AI intent router (T-019 pattern), so the LLM never gets its own write path. Storage: recurring_rules table (user_id, category, subcategory, amount, currency, day_of_month, active, last_run, created_at). Scheduler: daily job at fixed UTC hour (PTB JobQueue needs python-telegram-bot[job-queue]/APScheduler — check T-004 overlap; plain asyncio loop is fine too) materializes due rules into normal transactions via the existing save path. Rules: clamp day 29-31 to month end; idempotent via last_run so restarts never double-post; notify the user on each auto-add. Manual UX: list/add/pause/delete rules via command + menu.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
