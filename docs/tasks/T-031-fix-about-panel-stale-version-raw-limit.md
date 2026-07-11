---
id: T-031
title: Fix /about panel: stale version, raw limit sentinel, dead settings buttons
status: todo
type: bug
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
All pre-existing (verified 2026-07-11): (1) version string hardcoded in texts.ABOUT (src/texts.py:111, texts_ru equivalent) says 0.2.3/18.10.25 — replace with a single VERSION constant sourced from one place and bump on release (consider wiring to CHANGELOG). (2) monthly limit displays raw 99999999 sentinel — show 'no limit' when sentinel (full sentinel cleanup stays in T-014). (3) settings keyboard buttons attached by /about do nothing — callbacks only routed inside the menu conversation states; either register a standalone CallbackQueryHandler for settings_* actions or reuse the menu path. Workaround exists (menu->settings). Run AFTER Batch B merges (texts/core.py overlap).

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
- 2026-07-11 new finding from owner test: /about greets 'Hello, None!' — users.username/config.name never populated; fall back to update.effective_user.first_name. Also limit renders as float 4000.0 — format as int/currency
