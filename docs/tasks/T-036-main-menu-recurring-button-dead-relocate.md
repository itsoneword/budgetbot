---
id: T-036
title: Main-menu Recurring button dead; relocate into Add-transaction section
status: todo
type: bug
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Owner report 2026-07-11 (screenshot: full-width Recurring button in main menu, tap does nothing, no error logged). Diagnosis pointer: T-026 added the menu_recurring branch ONLY to src/handlers/menu.py menu_call, but src/core.py contains a duplicated copy of the menu callback logic (same duplication family as the dead code found by T-033 at core.py:608-779) — verify which function the menu conversation actually dispatches to; the receiving copy lacks the branch, so the callback falls through silently. Fix the routing (prefer deleting the core.py duplicate and routing to handlers/menu.py — aligns with T-030). UX decision by owner: move the Recurring button OUT of the main menu into the Add-transaction section/submenu since it is effectively a command link. Verify the Reminder button (T-034, planned) gets placed there too, not in main menu.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
