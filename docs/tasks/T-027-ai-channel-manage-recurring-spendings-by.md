---
id: T-027
title: AI channel: manage recurring spendings by voice//ask
status: todo
type: feature
area: bot
priority: p1
deps: [T-026]
tags: [ai, recurring]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Extend domain/intent.py with recurring intents on top of the T-026 action API: add_recurring (payload: item, amount, day-of-month — strictly validated like add_transaction), list_recurring, cancel_recurring (payload: rule reference from a shown list, never free-form). Same guardrails as T-019: enum + validated payload, every write behind an inline confirm tap, is_llm_allowed/entitlement gate. Target UX: voice 'remember I pay 800 for the apartment every month on the 1st' -> confirm dialog -> rule created -> transactions appear automatically; 'what are my recurring payments' -> list.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
