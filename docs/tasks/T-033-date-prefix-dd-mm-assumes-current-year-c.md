---
id: T-033
title: Date prefix dd.mm assumes current year, creates future-dated transactions
status: done
type: bug
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-19
---

## Context
Verified 2026-07-11: tx 3532 (31.12, user 49560859) and 4164 (26.12, user 497754687) entered on 2026-07-09 via dd.mm prefix got year 2026 -> dated 5+ months in the future (surfaced as impossible 'last activity 2026-12-31' in /admin_users). Fix in the T-019 date-prefix parsing (text + voice paths): if the parsed dd.mm date is in the future, roll back one year. Add the same guard for full dd.mm.yy input if present. One-off data fix for the two rows applied separately. Consider a domain-level guard so no entry path can write timestamp > now + 1 day.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
- 2026-07-11 one-off data fix applied: tx 3532/4164 shifted back one year (2026-12 -> 2025-12); parser fix still open
- 2026-07-11 started
- 2026-07-11 Fix: domain/validation.py (resolve_backdated_year + clamp_future_timestamp, pure); _parse_date_to_utc rolls future dd.mm back one year; income path parses dd.mm explicitly (dateutil was discarding the month) and returns datetime (str default crashed repo .tzinfo); _save_transaction_to_db now honors parsed timestamp (was silently dropping it — dd.mm on spendings never persisted); clamp at TransactionRepository.save covers all write paths with warning log
- 2026-07-11 Tomorrow semantics: 1-day grace — dd.mm up to now+1d kept in current year (users ahead of UTC produce 'tomorrow' legitimately; 1 day future is harmless vs shifting a same-day entry back a year). Beyond grace -> previous year. Save-path clamp uses same grace. 18/18 scratchpad checks pass
- 2026-07-11 moved to review

## Testing

### Critical
- [ ] Text entry `31.12 groceries 49` (in July) saves with date 31.12 of the PREVIOUS year — verify via /show or /show_last
- [ ] Text entry with a recent past date, e.g. `01.07 coffee 4`, saves dated 01.07 of the CURRENT year
- [ ] Plain entry without date prefix (`coffee 4`) still saves dated today
- [ ] Voice note "yesterday beer 10" -> confirm -> transaction dated yesterday (voice injects the same text path)
- [ ] /income `31.12 500` saves income dated 31 December of the previous year (was: 31st of the current month — dateutil bug)
- [ ] /income `salary 500` (no date) saves dated now and does NOT error (was: string timestamp could crash the repo save)

### Important
- [ ] Entry dated tomorrow (`12.07 x 5` on 11.07) keeps the current year (1-day grace for users ahead of UTC)
- [ ] Entry dated day-after-tomorrow (`13.07 x 5` on 11.07) rolls back to previous year
- [ ] /income `31.12.26 bonus 500` (explicit future year): saved clamped to now, warning in logs ("Future timestamp clamped")
- [ ] Invalid date prefix (`99.99 x 5`) falls back to today's date, no crash
- [ ] Multi-line/comma input `31.12 beer 5, coffee 3`: first item backdated, second dated today

### Regression
- [ ] Category-selection flow (short format `coffee 4` -> pick category) still saves correctly
- [ ] Recurring transactions (scheduler) still post on their due date, not clamped
- [ ] /show monthly stats include the backdated transaction in the correct (previous-year) month
- 2026-07-19 done
- 2026-07-19 changelog: dd.mm date prefix resolves to most recent past date instead of future-dating
