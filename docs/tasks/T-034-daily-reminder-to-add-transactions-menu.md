---
id: T-034
title: Daily reminder to add transactions (menu + voice), per-user timezone
status: todo
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Owner request 2026-07-11: 'remind me to add transactions every day at 5 pm' — a per-user daily reminder configured from the main menu AND via the voice/AI channel (new intent). Requires per-user timezone setting (users table column + onboarding/menu setting; relates to T-014 timezone cleanup). Scheduler: reuse the T-026 JobQueue pattern (daily sweep over reminder rows, or per-user jobs). Also relevant to T-027 (AI channel managing scheduled things). Needs planning wave before implementation.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
