---
id: T-025
title: Admin panel commands: user data export + activity monitoring
status: todo
type: feature
area: bot
priority: p2
deps: []
tags: [admin]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Admin-only capabilities exist in code but are invisible in the bot (only show_log_chart and toggle_debug are gated to ADMIN_USER_ID today). Add admin commands, all gated by ADMIN_USER_ID: /admin_users (list users with last-activity, tx counts — data already logged via log_user_interaction), /admin_export <user_id> (download a user's transactions like /download does for self), /admin_stats (DAU/WAU, new users, AI usage counts). Surface them in the admin-scoped command menu + help section (depends loosely on the command registry task). No new data collection — only expose what repositories already store.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
