---
id: T-014
title: Data-model cleanups (limit sentinel, timezone, enums, category language)
status: backlog
type: refactor
area: db
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Four small schema-quality issues: monthly_limit sentinel 99999999.00 should be NULL; no per-user timezone (everything renders UTC); transaction_type is VARCHAR+CHECK not enum; per-language category dictionaries leave users with an empty dictionary after switching language.

## Acceptance
- [ ] Each of the four sub-items fixed, or explicitly rejected with reasoning in the log

## Log
- 2026-07-07 created from production-readiness D2-D5
