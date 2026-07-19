---
id: T-045
title: Ask AI menu tap opens typed-question mode (like Add transaction)
status: todo
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner request 2026-07-19: entitled tap on the Ask AI menu button should edit the anchor into an invitation prompt ('Ask me anything about your finances, e.g. how much did I spend on beer this year?') with a Back button, and route the user's NEXT typed message to the /ask flow (no /ask prefix) — mirroring Add-transaction's typed-input pattern. Model on the existing awaiting_limit flag (settings.py handle_settings_limit) checked in the text path before transaction parsing; Back and any other menu action must clear the flag. Non-entitled path unchanged (buy offer per T-044). Builds directly on T-044's merged edit-in-place code — implement on top of main, deploy together.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
