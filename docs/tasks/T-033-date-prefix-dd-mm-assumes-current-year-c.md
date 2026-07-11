---
id: T-033
title: Date prefix dd.mm assumes current year, creates future-dated transactions
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
Verified 2026-07-11: tx 3532 (31.12, user 49560859) and 4164 (26.12, user 497754687) entered on 2026-07-09 via dd.mm prefix got year 2026 -> dated 5+ months in the future (surfaced as impossible 'last activity 2026-12-31' in /admin_users). Fix in the T-019 date-prefix parsing (text + voice paths): if the parsed dd.mm date is in the future, roll back one year. Add the same guard for full dd.mm.yy input if present. One-off data fix for the two rows applied separately. Consider a domain-level guard so no entry path can write timestamp > now + 1 day.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
