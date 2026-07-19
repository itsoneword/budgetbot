---
id: T-044
title: Menu UX: edit-in-place navigation, stop stacking new messages on submenu actions
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
Owner repro 2026-07-19 (screenshot, Ask AI button): tapping a main-menu item leaves the old menu message in place, sends the response as a NEW message (buy offer), then sends a THIRD 'Returning to main menu' message with a duplicate keyboard — 3 stacked messages per tap. Wanted: Telegram-native edit-in-place — the tapped menu message edits into the submenu/response with a Back button, Back edits it back to the main menu; no new messages, no 'Returning to main menu' text. Scope: audit ALL menu_call branches (handlers/menu.py) for which edit vs send; the Ask AI branch (T-023 amendment used send_ai_offer + _return_to_main_menu) is the worst case but the pattern is likely systemic. Constraint: flows that must send something new (invoice, charts, transaction entry prompts that expect typed input) stay as sends but should not ALSO re-send the menu.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
