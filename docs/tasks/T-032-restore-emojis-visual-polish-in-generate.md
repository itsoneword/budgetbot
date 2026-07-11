---
id: T-032
title: Restore emojis/visual polish in generated /help and menu command descriptions
status: todo
type: feature
area: bot
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
T-021's generated help is deliberately HTML-free (one call site renders HTML, two plain) but lost the old HELP_TEXT emojis. Add emojis to CommandSpec descriptions in src/commands.py (safe in BotCommand descriptions and plain text; e.g. chart commands get a chart emoji) and light section structure to build_help_text, EN+RU. Owner feedback 2026-07-11: menu descriptions ('comments') should carry emojis where visually meaningful, not necessarily all. Run AFTER Batch B merges (commands.py/texts overlap).

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
