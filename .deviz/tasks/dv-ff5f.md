---
id: dv-ff5f
title: Reminder v2: always remind, support multiple reminder times per day
status: review
priority: medium
assignee: claude
labels: [feature, bot]
deps: []
parent: 
created: 2026-07-19T14:55:32Z
updated: 2026-07-21T14:35:00Z
---

## Description

Migrated from `docs/tasks/T-047-reminder-v2-always-remind-no-skip-when-t.md`.

Owner feedback 2026-07-19 after testing T-034: (1) do NOT skip the reminder even if the user already added transactions that day — remind regardless; (2) allow more than one reminder option/time per user (e.g. midday + evening). Touches domain/reminders.py, reminder scheduler, reminder settings menu.

## Acceptance Criteria

- [x] Reminder fires even when the user already logged transactions that day (skip-if-logged removed, copy promise removed in EN+RU)
- [x] A user can have multiple active reminder times per day (add/remove/list from the menu; `/reminder HH:MM` adds)
- [x] `/reminder off` (and voice "off") disables all times; times survive re-enable
- [x] Each time fires at most once per local day (per-row last_sent_on idempotency), covered by tests

## Notes

### Implementation plan (proposed 2026-07-21)

Design: T-034's schema already almost supports multiple times — `reminders` is a per-row table (`id, user_id, kind, time_local, active, last_sent_on`) whose sweep (`src/scheduler.py run_reminders`) iterates rows independently, and `domain/reminders.py is_due` + `ReminderRepository.claim_send` are already per-row with `last_sent_on` as a per-row local-date idempotency cursor. The only thing forcing "one reminder per user" is the `UNIQUE (user_id, kind)` constraint (migration 0005) plus the `upsert`/`get_for_user` singular repo API and the singular handler layer (`src/handlers/reminders.py`). So change (2) is a constraint swap + API pluralization, not a redesign: replace the unique key with `UNIQUE (user_id, kind, time_local)` and each row fires once per local day on its own cursor — no domain or claim logic changes at all. Change (1) is a deletion: the skip-if-logged block in `run_reminders` (the `local_day_start_utc` + `transactions.has_transaction_since` check, scheduler lines 129–131) goes away; both helpers then have no remaining callers (`local_day_start_utc` is only imported by the scheduler; `has_transaction_since` was added by T-034 for exactly this) and should be removed as dead code. The internal action API keeps its shape so the voice channel is untouched: the LLM intent still injects `/reminder <HH:MM|off>`, which now means "add this time" / "turn all off" — additive semantics fit the owner's "midday + evening" ask. A cap (recommended 3 active times) is enforced in the handler layer, not the schema. Copy in both languages currently promises "If you've already logged something that day, I'll stay quiet" (`REMINDER_STATUS_OFF`, `REMINDER_SET`) — that promise must be deleted, not just the behavior.

1. Migration `infrastructure/database/alembic/versions/0008_reminders_multi.py` (revision "0008", down_revision "0007"): `ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_user_id_kind_key` then `ADD CONSTRAINT reminders_user_kind_time_key UNIQUE (user_id, kind, time_local)` — one `exec_driver_sql` per statement (asyncpg dialect rejects multi-command strings, per 0005's comment). Existing rows migrate as-is. Downgrade: delete all but the lowest-id row per (user_id, kind), then restore the old constraint.
2. `infrastructure/repositories/reminder_repository.py`: replace `upsert` with `add_time(user_id, time_local, kind)` — `INSERT ... ON CONFLICT (user_id, kind, time_local) DO UPDATE SET active = TRUE` (re-adding a disabled time re-activates it; keeps `last_sent_on` so a re-add after today's send can't double-fire, same rationale as v1's upsert). Replace `get_for_user` with `get_all_for_user(user_id, kind) -> List[Reminder]` (ordered by `time_local`). Add `remove_time(user_id, time_local, kind) -> bool` (DELETE one row). Keep `set_active` (already `WHERE user_id AND kind`, now naturally affects all rows — that is the "all off" switch), `get_active_with_tz` and `claim_send` unchanged. Update the module docstring ("one row per (user, kind, time)").
3. `src/scheduler.py run_reminders`: delete the skip-if-logged block and the `local_day_start_utc` import; update the docstring (always reminds — owner decision 2026-07-19). No other sweep changes — per-row `is_due`/`claim_send` already handles N rows per user.
4. Dead-code removal: `local_day_start_utc` from `domain/reminders.py` (and its docstring mention of "skip-if-logged window"); `has_transaction_since` from `infrastructure/repositories/transaction_repository.py` (verify no other caller with grep at implementation time). Add `MAX_REMINDER_TIMES = 3` to `domain/reminders.py`.
5. `src/handlers/reminders.py`: action API becomes plural-aware — `set_reminder` → `add_reminder_time(repos, user_id, time_local, tz_offset_min)` (same consume-today-if-past logic via `is_due` + `claim_send`, now on the returned row), `get_reminder` → `get_reminders(...) -> List[Reminder]`, `disable_reminder` unchanged (all off), new `remove_reminder_time(repos, user_id, time_local)`. `reminder_command`: `/reminder HH:MM` adds (rejecting with `REMINDER_LIMIT_REACHED` when the user already has `MAX_REMINDER_TIMES` active times and this one isn't among them); `/reminder off` disables all; no-args shows the list view. `build_reminder_view(reminders: List[Reminder], texts, back_cb)`: status line listing all active times; preset rows unchanged (`rem_set_HH:MM` now means add); one removal button per active time (`🔕 HH:MM`, callback `rem_del_HH:MM` — time-keyed like `rem_set_`, no ids in callback data); keep the all-off button when anything is active. `handle_reminder_callback`: handle `rem_del_`, and after any mutation re-render the list view in place (edit_message to `build_reminder_view`) instead of a terminal confirmation, so managing multiple times doesn't require reopening the menu. The tz-picker flow (`_PENDING_TIME_KEY`, `handle_tzpick_callback`) is untouched except calling the renamed `add_reminder_time`.
6. Call sites: `src/handlers/menu.py` `menu_reminder` branch (~line 320) switches to `get_reminders` + the plural `build_reminder_view`; `src/core.py` imports unchanged in shape (`^rem_` pattern already covers `rem_del_`). `src/commands.py` /reminder description: mention multiple times.
7. Copy in **both** `src/texts.py` and `src/texts_ru.py`: rewrite `REMINDER_STATUS_OFF`, `REMINDER_SET` (drop the "I'll stay quiet" promise), replace `REMINDER_STATUS_ACTIVE` with a list form (`REMINDER_STATUS_LIST` with a `{times}` join), add `REMINDER_TIME_REMOVED`, `REMINDER_LIMIT_REACHED`, `REMINDER_REMOVE_BTN` label prefix; update `REMINDER_USAGE`. Keep `REMINDER_TEXT` (the nudge itself) HTML-free as noted in texts.py.
8. Tests: new `tests/domain/test_reminders.py` (none exists today despite T-034): `parse_reminder_time` valid/invalid, `is_due` due/not-due/already-sent/inactive, and two same-user reminders firing independently on their own `last_sent_on` cursors on one local date. Add a `docs/DECISIONS.md` one-liner: reminders always fire regardless of logged transactions (owner 2026-07-19) / rejected: skip-if-logged (v1 behavior). Then the review-stage manual-testing checklist covers: two times same day both fire, re-adding an existing time doesn't duplicate, off kills all, voice "remind me at 12" adds alongside an existing 17:00.

Touched: new `infrastructure/database/alembic/versions/0008_reminders_multi.py`, `tests/domain/test_reminders.py`; modified `infrastructure/repositories/reminder_repository.py`, `infrastructure/repositories/transaction_repository.py`, `domain/reminders.py`, `src/scheduler.py`, `src/handlers/reminders.py`, `src/handlers/menu.py`, `src/commands.py`, `src/texts.py`, `src/texts_ru.py`, `docs/DECISIONS.md`. (No changes to `src/core.py` handler registration, `domain/intent.py`, or the voice path — the `/reminder <HH:MM|off>` injection contract is preserved.)

Open questions (recommended defaults):
1. Max active reminder times per user → 3 (covers "midday + evening" with slack; handler-enforced, trivially raised later).
2. Menu UX for removal → one `🔕 HH:MM` button per active time on the same view (tap to remove, view re-renders in place); presets always add.
3. `/reminder off` and the voice "off" intent turn off ALL times → yes (deactivate, keep rows, so times survive a re-enable; simplest contract for the LLM channel).
4. Delete the now-dead `has_transaction_since` + `local_day_start_utc` → yes (no other callers; keeping them would silently invite the skip behavior back).

Risks: voice "change my reminder to 18:00" now *adds* 18:00 next to the old time instead of replacing it — accepted as inherent to additive semantics (the cap bounds the damage; the list view makes it visible), but worth watching in owner testing; the migration downgrade is lossy (dedupes to one time per user) — acceptable, downgrades are for emergencies; `rem_del_HH:MM` callback data assumes the rendered time round-trips through `parse_reminder_time` — it does (`format_reminder_time` output is always `HH:MM`); re-rendering the same view after a tap can hit Telegram's "message is not modified" error if state didn't change — `menu.py`'s `_safe_edit` pattern already handles this, reuse it or guard in the handler; the per-row `last_sent_on` cursor means adding a second time that is already past "today" consumes today for that row only (existing v1 behavior per row), so no surprise double-nudge on setup day.

## Testing

Manual testing checklist (reminder v2: always remind, multiple times):

### Critical
- [ ] Two times same day both fire: set `/reminder` times 5 min and 10 min ahead (sweep runs every 5 min) — both nudges arrive, one each, at their own times
- [ ] Reminder fires even after logging: add a transaction, wait for a reminder time to pass — the nudge still arrives (no skip)
- [ ] Re-adding an existing time doesn't duplicate: tap the same preset twice / `/reminder 17:00` twice — list still shows 17:00 once, no error, no double nudge that day
- [ ] `/reminder off` (typed and via voice "stop reminding me") kills all times; menu shows the off state; re-adding any time via preset re-activates and previous times reappear active after their rows' `set_active` re-enable path (add one time back — only re-added times fire)
- [ ] Voice "remind me at 12" ADDS 12:00 alongside an existing 17:00 (list shows both) — does not replace
- [ ] Migration: deploy applies 0008 cleanly on the existing DB; pre-existing single reminders still fire at their time

### Important
- [ ] 🔕 HH:MM removal button removes exactly that time and the view re-renders in place (list + buttons update without reopening the menu)
- [ ] 4th time rejected: with 3 active times, `/reminder 08:00` and a preset tap both show the limit message (preset tap keeps the view usable)
- [ ] Off-state copy (EN and RU) no longer promises "I'll stay quiet if you've logged" anywhere (/reminder view, set confirmation)
- [ ] First-ever `/reminder 17:00` with no timezone still routes through the tz picker and completes the pending time after the pick
- [ ] Double-tapping the same button doesn't trip an error ("message is not modified" swallowed)
- [ ] Menu → Daily reminder path shows the list view with a working Back button, and Back survives an add/remove re-render

### Nice-to-have
- [ ] Status line lists multiple times sorted ascending (09:00, 12:00, 17:00)
- [ ] /help command description mentions multiple times (EN + RU)
- [ ] Removal of the last time flips the view to the off text in the same edit

### Log

- 2026-07-19 created
- 2026-07-21 Implementation plan proposed (constraint swap to UNIQUE(user_id, kind, time_local), plural repo/handler API, skip-if-logged deleted with its dead helpers, 4 open questions batched to owner)
- 2026-07-21 Implemented: migration 0008 (UNIQUE user_id+kind+time_local, lossy dedupe downgrade), repo pluralized (add_time/get_all_for_user/remove_time), scheduler skip-if-logged deleted with dead helpers (has_transaction_since, local_day_start_utc), handler layer add/remove/list with MAX_REMINDER_TIMES=3 cap and in-place re-render (🔕 HH:MM buttons), EN+RU copy rewritten (quiet-day promise dropped), tests/domain/test_reminders.py added (402 tests green), DECISIONS.md line appended. Status → review.
