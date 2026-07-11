---
id: T-021
title: Sync bot menu commands with code (set_my_commands on startup)
status: backlog
type: feature
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-09
updated: 2026-07-11
---

## Context
Telegram menu (getMyCommands) has 14 commands, code has 22 handlers; menu was set manually via BotFather and drifts. Add set_my_commands on startup so menu is code-driven. BLOCKED on user deciding the final command list. Missing from menu today: about, change_cat, debug, delete_income, leave, monthly_ext_stat, show_cat, show_log_chart.
Extended scope (2026-07-11, supersedes archived T-024): single registry (command, handler, EN/RU description, admin_only flag) used to (a) register handlers in core.py main(), (b) render /help (src/handlers/admin.py, texts.py + texts_ru.py), (c) set_my_commands on post_init — BotCommandScopeDefault for users, BotCommandScopeChat(ADMIN_USER_ID) with admin commands included (pairs with T-025 admin panel).

## Acceptance
- [ ] TODO

## Log
- 2026-07-09 created
- 2026-07-11 Owner decisions 2026-07-11: debug and show_log_chart are admin-only (admin command scope + admin help). /help must differ for admin vs regular users. Menu should balance too-many/too-few; final user-facing list still pending owner confirmation of the proposed set.
