---
id: T-034
title: Daily reminder to add transactions (menu + voice), per-user timezone
status: doing
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-12
---

## Context
Owner request 2026-07-11: 'remind me to add transactions every day at 5 pm' — a per-user daily reminder configured from the main menu AND via the voice/AI channel (new intent). Requires per-user timezone setting (users table column + onboarding/menu setting; relates to T-014 timezone cleanup). Scheduler: reuse the T-026 JobQueue pattern (daily sweep over reminder rows, or per-user jobs). Also relevant to T-027 (AI channel managing scheduled things). Needs planning wave before implementation.

## Acceptance
- [ ] Alembic 0005 (off 0004): user_configs.tz_offset_min SMALLINT CHECK(-720..840) + reminders table (kind, time_local, active, last_sent_on, UNIQUE(user_id, kind)) with partial active index; downgrade reverses
- [ ] ReminderRepository: upsert (ON CONFLICT DO UPDATE, re-activates), get_for_user, set_active, delete, get_active_with_tz (JOIN user_configs), atomic claim_send (rowcount UPDATE, last_sent_on < local_date); DI property repos.reminders
- [ ] UserRepository.update_tz_offset + tz_offset_min in UserConfig; TransactionRepository.has_transaction_since(user_id, utc_start)
- [ ] domain/reminders.py pure: is_due(reminder, tz_offset_min, now_utc) -> Optional[local_date], local_day_start_utc, parse_reminder_time ("HH:MM" or bare "17"), build_offset_candidates(now_utc), no I/O or Telegram types
- [ ] scheduler.run_reminders: get_active_with_tz -> is_due -> claim_send FIRST -> skip-if-logged -> send in user language, Forbidden caught per user; registered run_repeating(REMINDER_SWEEP_SECONDS default 300, first=90)
- [ ] /reminder: status view + preset keyboard (09/12/17/20/21 + off), args path (HH:MM | off); ^rem_ and ^tzpick_ callbacks registered BEFORE spendings_handler; lazy one-tap tz picker with pending-time stash; internal action API (set_reminder/disable_reminder/get_reminder)
- [ ] Menu: reminder button (menu_reminder) in main menu + timezone button (settings_timezone) in settings keyboard, branches in handlers/menu.py
- [ ] Voice: INTENT_SET_REMINDER, payload "HH:MM"|"off" strictly validated, routed via _inject_text("/reminder <payload>"); no extra gating
- [ ] Registry row for /reminder; all copy in BOTH texts.py and texts_ru.py; two DECISIONS.md one-liners (sweep-vs-jobs, offset-vs-IANA) dated 2026-07-12

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

Design: every-5-min sweep job (NOT per-user JobQueue jobs — those are in-memory, need restart re-registration, drop fires on downtime). DB is the only state: `reminders` table with atomic `claim_send(reminder_id, local_date)` mirroring T-026's claim_run. Timezone = fixed UTC offset minutes (`user_configs.tz_offset_min SMALLINT`, NULL=UTC) set via a one-tap picker: buttons show candidate current local times ("15:07" / "15:37" / "16:07"...) for the ~38 real offsets — user taps the one matching their clock; asked lazily on first reminder set + in Settings. No IANA list, no typing.

1. Alembic revision (0005 off 0004 — confirm head at impl time): ALTER user_configs ADD tz_offset_min SMALLINT CHECK (-720..840); CREATE reminders (id, user_id FK CASCADE, kind VARCHAR(20) DEFAULT 'add_transactions', time_local TIME, active BOOL, last_sent_on DATE, created_at, UNIQUE(user_id, kind)) + partial active index.
2. infrastructure/repositories/reminder_repository.py: upsert (ON CONFLICT DO UPDATE, re-activates), get_for_user, set_active, delete, get_active_with_tz() (JOIN user_configs), claim_send (rowcount UPDATE, last_sent_on < local_date). UserRepository: update_tz_offset + tz_offset_min in UserConfig. transaction_repository: has_transaction_since(user_id, utc_start) for skip-if-logged. DI property.
3. domain/reminders.py (pure): is_due(reminder, tz_offset_min, now_utc) -> Optional[local_date] (claim key), local_day_start_utc, parse_reminder_time ("HH:MM" or bare "17"), build_offset_candidates(now_utc).
4. src/scheduler.py run_reminders(context): get_active_with_tz → is_due → claim_send first → skip-if-logged (has_transaction_since) → send REMINDER_TEXT in user language, catch Forbidden per user. core.py: job_queue.run_repeating(interval=REMINDER_SWEEP_SECONDS default 300, first=90); config const. No catch-up job needed — repeating sweep is its own catch-up.
5. src/handlers/reminders.py (modeled on recurring.py): internal action API (set_reminder/disable_reminder/get_reminder — the T-027-style AI surface); /reminder status view + preset inline keyboard (09/12/17/20/21 as rem_set_HH:MM, rem_off); /reminder 17:00 | off args path; ^rem callback — if tz unset, stash pending time and show tzpick_ picker; ^tzpick_ callback saves offset + completes pending reminder. Register both BEFORE spendings_handler (like ^rr).
6. Menu: REMINDER_BUTTON (menu_reminder) in main menu; TIMEZONE_BUTTON (settings_timezone) in settings keyboard; branches in handlers/menu.py.
7. Voice: INTENT_SET_REMINDER, payload "HH:MM"|"off", strict regex validation; _route_intent → _inject_text("/reminder " + payload). /reminder open to all (menu feature); voice path already behind check_ai_access — no extra gating.
8. Registry row for /reminder; copy in both texts files. DECISIONS one-liners: sweep-vs-jobs, offset-vs-IANA.

Touched (COORDINATION with T-027/T-035 on domain/intent.py, voice.py, texts): new 0005 revision, reminder_repository.py, domain/reminders.py, src/handlers/reminders.py; modified repositories/__init__.py, user_repository.py, transaction_repository.py, container.py, scheduler.py, core.py, config.py, handlers/menu.py, keyboards.py, domain/intent.py, voice.py, commands.py, texts.py, texts_ru.py.

Open questions (recommended defaults):
1. Timezone UX → one-tap current-local-time offset picker; not in /start onboarding, lazy on first use.
2. Skip reminder if user already logged a transaction that local day → yes, default on, no toggle initially.
3. Default time when unspecified → 17:00 local, presets keyboard for one-tap change.
4. Extra gating for voice path → none needed (inherits check_ai_access; /reminder itself public).

Risks: DST drift (fixed offset shifts 1h twice/year — accepted v1, upgrade path to IANA column changes only is_due input; confirm message says "re-set if clocks change"); Forbidden caught per user (claim consumed = correct, no all-day retries of blocked users); ^rem registration order before spendings_handler; sweep fires up to 5 min late (irrelevant for daily nudge).

**Owner decisions 2026-07-11:** all defaults accepted (one-tap offset picker; skip-if-logged on; default 17:00; no extra voice gating). Sequencing: LAST in the intent chain (T-035 → T-027 → T-034).
- 2026-07-12 started
