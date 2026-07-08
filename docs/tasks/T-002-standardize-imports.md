---
id: T-002
title: Standardize package-qualified imports
status: review
type: refactor
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-08
---

## Context
src/core.py and siblings use bare `from language_util import ...` that only works because run.py inserts src/ into sys.path. Inconsistent with `from src.handlers ...` used elsewhere; breaks any entry point that bypasses run.py.

## Acceptance
- [x] All intra-project imports use the src.* prefix
- [x] run.py adds only the project root to sys.path
- [ ] Bot boots and responds to /start (boot verified; /start pending manual check)

## Log
- 2026-07-07 created from production-readiness B2
- 2026-07-08 started
- 2026-07-08 Rewrote all bare intra-project imports to src.* in 15 files incl. indented function-level ones; language_util importlib strings now src.texts/src.texts_ru; run.py only inserts project root; image rebuilt, bot boots and polls
- 2026-07-08 moved to review

## Testing

Behavior-preserving refactor — the goal is confirming nothing broke, with extra attention on the two riskiest changes: dynamic texts loading (`importlib.import_module("src.texts*")`) and the dual-instance fix for save_transaction.

### Critical
- [ ] /start responds (fresh user onboarding keyboard, or normal reply for existing user)
- [ ] Language switch to Russian works and bot replies in Russian (exercises dynamic src.texts_ru import); switch back to English works
- [ ] Save a spending transaction end-to-end (category → subcategory → amount → confirm) — exercises src.save_transaction
- [ ] /menu opens and Edit transactions → recent entries list works (exercises function-level detailed_transactions imports)

### Important
- [ ] Charts render (/menu → charts or /show_chart equivalents)
- [ ] /debug from admin still works (regression on T-001, core.py imports changed)
- [ ] /help and about display texts correctly

### Nice-to-have
- [ ] No ImportError/ModuleNotFoundError anywhere in `docker compose logs budgetbot` after exercising the flows above
