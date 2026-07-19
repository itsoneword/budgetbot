---
id: T-039
title: Chart handlers reference undefined texts.NO_DATA (latent AttributeError on empty-data path)
status: done
type: bug
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-19
---

## Context
Found during T-010: src/handlers/charts.py references texts.NO_DATA but neither src/texts.py nor src/texts_ru.py defines it — the empty-charts path raises AttributeError instead of a friendly message. Define the constant in both files (EN/RU) and verify every texts.* reference in handlers resolves (cheap guard: a unit test iterating referenced attrs).

## Acceptance
- [ ] TODO

## Log
- 2026-07-12 created
- 2026-07-19 done
- 2026-07-19 changelog: Defined missing chart texts (NO_DATA + 3 more) in both languages — fixed with T-044
