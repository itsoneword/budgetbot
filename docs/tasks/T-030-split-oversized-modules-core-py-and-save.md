---
id: T-030
title: Split oversized modules: core.py and save_transaction.py
status: backlog
type: refactor
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
core.py (1056 lines) is a god module (handlers + wiring + business logic) and was the merge-conflict hotspot of the 2026-07 wave; save_transaction.py is 1251 lines. Move core.py handlers into src/handlers/, keep main() as pure wiring; split save_transaction.py flow into cohesive pieces. MUST wait until after Batch B (T-022/T-026/T-025) merges — their approved plans reference current core.py structure.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
