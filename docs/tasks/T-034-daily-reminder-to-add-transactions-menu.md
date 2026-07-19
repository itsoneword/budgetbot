---
id: T-034
title: Daily reminder to add transactions (menu + voice), per-user timezone
status: done
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-19
---

## Context
Owner request 2026-07-11: 'remind me to add transactions every day at 5 pm' — a per-user daily reminder configured from the main menu AND via the voice/AI channel (new intent). Requires per-user timezone setting (users table column + onboarding/menu setting; relates to T-014 timezone cleanup). Scheduler: reuse the T-026 JobQueue pattern (daily sweep over reminder rows, or per-user jobs). Also relevant to T-027 (AI channel managing scheduled things). Needs planning wave before implementation.

## Acceptance
- [x] Alembic 0005 (off 0004): user_configs.tz_offset_min SMALLINT CHECK(-720..840) + reminders table (kind, time_local, active, last_sent_on, UNIQUE(user_id, kind)) with partial active index; downgrade reverses
- [x] ReminderRepository: upsert (ON CONFLICT DO UPDATE, re-activates), get_for_user, set_active, delete, get_active_with_tz (JOIN user_configs), atomic claim_send (rowcount UPDATE, last_sent_on < local_date); DI property repos.reminders
- [x] UserRepository.update_tz_offset + tz_offset_min in UserConfig; TransactionRepository.has_transaction_since(user_id, utc_start)
- [x] domain/reminders.py pure: is_due(reminder, tz_offset_min, now_utc) -> Optional[local_date], local_day_start_utc, parse_reminder_time ("HH:MM" or bare "17"), build_offset_candidates(now_utc), no I/O or Telegram types
- [x] scheduler.run_reminders: get_active_with_tz -> is_due -> claim_send FIRST -> skip-if-logged -> send in user language, Forbidden caught per user; registered run_repeating(REMINDER_SWEEP_SECONDS default 300, first=90)
- [x] /reminder: status view + preset keyboard (09/12/17/20/21 + off), args path (HH:MM | off); ^rem_ and ^tzpick_ callbacks registered BEFORE spendings_handler; lazy one-tap tz picker with pending-time stash; internal action API (set_reminder/disable_reminder/get_reminder)
- [x] Menu: reminder button (menu_reminder) in main menu + timezone button (settings_timezone) in settings keyboard, branches in handlers/menu.py
- [x] Voice: INTENT_SET_REMINDER, payload "HH:MM"|"off" strictly validated, routed via _inject_text("/reminder <payload>"); no extra gating
- [x] Registry row for /reminder; all copy in BOTH texts.py and texts_ru.py; two DECISIONS.md one-liners (sweep-vs-jobs, offset-vs-IANA) dated 2026-07-12

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
- 2026-07-12 0005 migration, ReminderRepository (upsert/claim_send), UserConfig.tz_offset_min + update_tz_offset, has_transaction_since, domain/reminders.py, DI repos.reminders
- 2026-07-12 sweep job wired (run_repeating 300s/first 90), /reminder + ^rem_/^tzpick_ before spendings_handler, menu+settings buttons, INTENT_SET_REMINDER, registry row, EN/RU copy, 2 DECISIONS lines

## Testing

Manual testing checklist (generated per .claude/instructions/post_implementation_testing.md). Note: the reminder sweep runs every 5 min, so fire-time checks are ±5 min; `REMINDER_SWEEP_SECONDS=60` speeds up testing.

### Critical — must pass before merge
- [ ] Container starts clean: `alembic upgrade head` applies 0005 (user_configs.tz_offset_min + reminders table) on the existing DB without errors
- [ ] /reminder (no tz set yet) → status "off" + preset keyboard; tap a preset → one-tap timezone picker appears; tap the time matching your clock → one message confirms both reminder time and saved UTC offset
- [ ] With tz set: /reminder 17:00 (or tap a preset) → confirm message; row visible in DB (`SELECT * FROM reminders`), `tz_offset_min` correct in user_configs
- [ ] Set a reminder 2-3 min in the future (e.g. /reminder HH:MM just ahead), don't log anything → nudge arrives within the sweep interval, in your language; `last_sent_on` = today (local)
- [ ] Skip-if-logged: set a near-future reminder, log any transaction first (e.g. "coffee 4") → NO nudge arrives, but `last_sent_on` still advances to today
- [ ] No repeat: after a fire, wait 2 more sweep cycles → no second message the same day
- [ ] /reminder off → confirmation; sweep sends nothing; /reminder shows "off" status again
- [ ] Main menu shows "⏰ Daily reminder" button and it opens the same status view; buttons work while a /menu conversation is active (rem_/tzpick_ not swallowed by the conversation fallback)
- [ ] Settings → "🕒 Time zone" opens the picker; picking with no pending reminder just saves the offset (confirm message with UTC±HH:MM)

### Important — edge cases and errors
- [ ] Set reminder for a time already past today (e.g. now-1h) → confirm message, but NO instant nudge; first fire is tomorrow
- [ ] Invalid input: /reminder 25:00, /reminder banana → invalid-time message + usage, nothing saved
- [ ] Bare hour works: /reminder 17 == 17:00; /reminder 9:30 works
- [ ] Re-set time after today's nudge already sent → no second nudge today, new time active from tomorrow
- [ ] /reminder off then a preset tap → reminder re-activates with the kept/new time (upsert re-activates)
- [ ] Voice (AI-entitled account): "remind me to add transactions at 9 pm" → routed to /reminder 21:00 flow (tz picker first if unset); "stop reminding me" → /reminder off; reminder request for an unrelated topic ("remind me to call mom") → unknown/echo, no reminder created
- [ ] Voice on a non-entitled account still gets ASK_NOT_ALLOWED (no new gating hole)
- [ ] Restart the container after setting reminders → reminders still fire (state is in DB, no re-registration)
- [ ] Block the bot from a second test account with a due reminder → sweep logs a warning, other users still get their nudges
- [ ] Russian account: /reminder texts, picker prompt, nudge text all in Russian

### Nice-to-have
- [ ] /help and the Telegram command menu list /reminder with the ⏰ description (EN + RU)
- [ ] Ambiguous far-zone labels in the picker render as "01:07 (+13)" style; all 38 buttons fit readably (4 per row)
- [ ] /reminder from the DST-note copy: TZ_SAVED mentions re-picking after clock changes

### Regression
- [ ] Recurring rules still post daily (T-026 job unaffected) and ^rr buttons still work
- [ ] Voice add-spending / add-income / show-stat / question intents still route correctly (prompt change didn't shift classifications)
- [ ] Settings → language/currency/limit/about still work with the new Time zone row present; main menu layout renders correctly with the new row
- 2026-07-12 acceptance boxes checked; verified via compileall, full src.core import (dummy config), domain/intent scratch tests, alembic history (0005 single head); DB not migrated live on purpose
- 2026-07-12 moved to review
- 2026-07-19 owner tested: reminder + adding works; logic changes requested (no skip-on-activity, multiple reminder times) -> follow-up task
- 2026-07-19 done
- 2026-07-19 changelog: Daily reminder to add transactions via menu or voice, per-user timezone
