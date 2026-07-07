---
id: T-002
title: Standardize package-qualified imports
status: todo
type: refactor
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
src/core.py and siblings use bare `from language_util import ...` that only works because run.py inserts src/ into sys.path. Inconsistent with `from src.handlers ...` used elsewhere; breaks any entry point that bypasses run.py.

## Acceptance
- [ ] All intra-project imports use the src.* prefix
- [ ] run.py adds only the project root to sys.path
- [ ] Bot boots and responds to /start

## Log
- 2026-07-07 created from production-readiness B2
