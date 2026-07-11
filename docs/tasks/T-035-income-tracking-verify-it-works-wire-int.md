---
id: T-035
title: Income tracking: verify it works, wire into voice/AI intents, income-vs-outcome analysis in /ask
status: todo
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Owner request 2026-07-11: income tracking exists (/income conversation, /show_income, /delete_income sharing handlers with spendings) but was never properly used — first VERIFY the whole flow works end-to-end post-PostgreSQL-migration (add, show, delete, charts treatment). Then: (1) extend the T-019 voice/text intent classifier with an add_income intent so users with irregular income can just say it ('got paid 2000 today') and it saves with the same confirm gate as spendings; (2) make sure /ask context (domain/ask_summary.py) includes income so AI can analyze income vs outcome and give suggestions — possibly a dedicated prompt hint. Notes: T-026 recurring engine already supports transaction_type=income at engine level (UI deliberately spendings-only); intent routing dispatches via synthetic Update (see DECISIONS 2026-07-09) so reusing the /income conversation may need the same pattern as voice transactions. Needs a planning wave first.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
