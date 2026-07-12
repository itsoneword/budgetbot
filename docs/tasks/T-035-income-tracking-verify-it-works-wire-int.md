---
id: T-035
title: Income tracking: verify it works, wire into voice/AI intents, income-vs-outcome analysis in /ask
status: review
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
Owner request 2026-07-11: income tracking exists (/income conversation, /show_income, /delete_income sharing handlers with spendings) but was never properly used — first VERIFY the whole flow works end-to-end post-PostgreSQL-migration (add, show, delete, charts treatment). Then: (1) extend the T-019 voice/text intent classifier with an add_income intent so users with irregular income can just say it ('got paid 2000 today') and it saves with the same confirm gate as spendings; (2) make sure /ask context (domain/ask_summary.py) includes income so AI can analyze income vs outcome and give suggestions — possibly a dedicated prompt hint. Notes: T-026 recurring engine already supports transaction_type=income at engine level (UI deliberately spendings-only); intent routing dispatches via synthetic Update (see DECISIONS 2026-07-09) so reusing the /income conversation may need the same pattern as voice transactions. Needs a planning wave first.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

### Phase 0 — audit findings (verified in code; income IS broken)
1. /income CRASHES on save for its most common inputs ("salary 2000", "2000"): process_income_input (src/save_transaction.py:63-95) returns timestamp as a STRING when no date given; TransactionRepository.save does ts.tzinfo → AttributeError. Classic post-migration stale type.
2. Future-dated income: parse(parts[0], dayfirst=True) defaults to current year — same T-033 bug class.
3. /delete_income ignores transaction_type: delete_records (core.py:447-476) deletes by raw ID for both commands (default record_id=1!) — /delete_income can delete a SPENDING. /show_last hardcodes spending (core.py:417) so income IDs are undiscoverable.
4. Latent PTB v22 crash: menu.py:128 mutates immutable Message (.text = "/show_income"); unreachable only because the Income-stats button is commented out (keyboards.py:178). Plus a dead duplicate block in handle_text (core.py:608-660) — delete.
5. records is None branch replies via update.message (None from callbacks) and returns None instead of a state (records.py:52,156).
6. Verified OK: save_income writes type correctly; charts/detailed/limit calc all filter to spending; /download exports income with type column; recurring engine income-capable.

### Phase 1 — fix defects
save_transaction.py: datetime return + shared past-date-rollback helper (T-033 adopts it). core.py: type-aware delete_records (no-arg → delete latest of that type + echo; ID → verify type matches command), delete dead handle_text block. records.py: tx_type param on show_records, effective_message guards, extract save_income_text(update, context, text) — the single write path Phase 2 reuses. menu.py: replace .text mutation with tx_type call; keyboards.py: re-enable Income-stats button. Fix INCOME_HELP copy both languages.

### Phase 2 — add_income intent
domain/intent.py: INTENT_ADD_INCOME, payload "<source> <amount>" (optional dd.mm prefix), _TX_ITEM_RE validation, ONE item only (no comma lists); prompt: "user reports receiving money; never invent an amount". voice.py: distinct user_data key voice_income_text + distinct callbacks vinc_yes/vinc_no (cross-talk guard vs pending spending confirm); on confirm call save_income_text() DIRECTLY (do NOT _inject_text — plain text would save as spending, /income would double-message). Register ^vinc_ before spendings_handler (core.py:1046 ordering). VOICE_CONFIRM_INCOME copy (must clearly say "income"), both languages.

### Phase 3 — /ask income context
domain/ask_summary.py: add income-per-category section (mirror of spending block, lines 51-57; negligible prompt-size cost); one system-prompt sentence: data contains both income and spending — compare when relevant (savings rate, suggestions). ask() itself already loads all types.

Touched: save_transaction.py, handlers/records.py, core.py, handlers/menu.py, keyboards.py, domain/intent.py, handlers/voice.py, domain/ask_summary.py, texts.py, texts_ru.py. COORDINATION: intent.py + voice.py + texts overlap with T-027/T-034 — do not run parallel on those files.

Open questions (recommended defaults):
1. Income categories → free-form with "salary" fallback, no subcategory, zero migration.
2. Re-enable Income-stats menu button → yes (its crash is fixed in Phase 1).
3. /delete_income no-arg → delete latest income + echo it; ID form stays, type-checked.
4. T-033 sequencing → ship the shared year-rollback helper here; T-033 adopts it (note in T-033).
5. Typed "got paid 2000" (trailing-number text) hits the transaction regex BEFORE intent routing and saves as spending — out of scope; log as known limitation.

Risks: confirm-gate cross-talk (mitigated by vinc_ separation); delete_records blast radius (/delete must keep exact behavior); classifier ambiguity contained by confirm gate; income "prediction" line in get_period_summary is meaningless for lumpy income (optionally suppress); no test infra (T-006 todo) — domain changes are pure, unit-test if T-006 lands first.

**Owner decisions 2026-07-11:** all defaults accepted (free-form income categories with salary fallback; Income-stats button re-enabled; /delete_income no-arg deletes latest income). Sequencing: FIRST in the intent chain (T-035 → T-027 → T-034). ADJUSTMENT: T-033's parser fix is being implemented in parallel and lands first — Phase 1 must REUSE T-033's year-rollback helper (check what it shipped) instead of creating a new one.

**Adjustment after T-033 landed (2026-07-11):** T-033 already fixed Phase 0 defects #1 (process_income_input now always returns a datetime — the /income save crash) and #2 (dd.mm year rollback via new domain/validation.py resolve_backdated_year + clamp_future_timestamp in TransactionRepository.save). Phase 1 shrinks accordingly: reuse domain/validation.py, do NOT re-fix those. T-033 also found the unreachable legacy block in handle_text is core.py:608-779 (larger than planned ~608-660) — delete the whole block. Note: dd.mm prefixes on spendings were parsed but silently DROPPED before T-033 (_save_transaction_to_db ignored the parsed timestamp — now honored); income dd.mm previously recorded wrong MONTHS too (dateutil default-month bug, fixed).

**Owner-reported UX gaps (2026-07-11 evening, add to scope):**
- `/income trading 300` with inline args silently ignores the args and prints INCOME_HELP — the conversation only accepts input as the NEXT message. Fix: the /income entry point must parse context.args and save directly when present (reuse save_income_text from Phase 1), falling back to the conversational prompt only when called bare. Mirror the /recurring add args pattern.
- `/ask add 300 eur income from trading` → AI correctly refuses (read-only by design), but the refusal should point users at the working paths: mention /income and (once shipped) plain-text/voice entry. Update the ask system prompt's refusal guidance in Phase 3.
- Verify the two-step flow (/income → next-message "trading 300") actually saves post-T-033 — owner stopped at the help text, so the happy path is still UNVERIFIED on live.
- 2026-07-11 owner test: /income inline args ignored (help shown instead of saving); /ask write-refusal should redirect; two-step flow still unverified live
- 2026-07-11 owner verified on live: two-step /income flow saves correctly post-T-033 — remaining income work is inline args, delete_income type-safety, intent + /ask context
- 2026-07-12 started
- 2026-07-12 root-caused owner screenshot: /income trading 300 fell through active income conversation to spendings regex entry (no ~COMMAND filter), saved as spending cat=/income; DB row 4739
- 2026-07-12 Phase 1-3 implemented: /income inline args + shared save_income_text, ~COMMAND on spendings regex entry + income allow_reentry (root cause of spending-mislog), type-aware /delete vs /delete_income, dead 174-line block removed from core.py, Income-stats button re-enabled with immutable-safe tx_type param, add_income voice/text intent with vinc_ confirm gate, /ask income section + write-refusal redirect; DB rows 4739/8140 repaired; deployed

## Testing

### Income entry — happy paths
- [ ] `/income trading 300` (inline args) saves immediately: "💵 Income saved: trading, 300.0 EUR (date)" — no help text, no conversation left open
- [ ] `/income` bare → help text → next message `salary 2000` saves as income
- [ ] `/income 11.07 trading 300` (dd.mm prefix) saves with 11 July date
- [ ] `/income 500` (amount only) saves with category "salary"
- [ ] Repeated `/income` while the prompt is pending re-shows the help (re-entry) instead of doing nothing
- [ ] `/income trading 300` sent TWICE in a row: second one saves a second income — must NOT save a spending with category "/income" (the original bug)

### Regression: spendings still work
- [ ] Plain text `coffee 4.5` still saves a spending
- [ ] `31.12 coffee 4` backdated spending still works
- [ ] Multi-line / comma spendings still work

### Delete type-safety
- [ ] `/delete_income` (no arg) deletes the LATEST INCOME and echoes its details
- [ ] `/delete` (no arg) deletes the LATEST SPENDING and echoes its details
- [ ] `/delete_income <id-of-a-spending>` refuses with the type-mismatch message
- [ ] `/delete <id-of-an-income>` refuses with the type-mismatch message
- [ ] `/delete abc` → invalid-number message

### Voice / free-text income intent
- [ ] Voice "получил доход 300 от трейдинга" → 💵 income confirm keyboard (must say ДОХОД/INCOME) → ✅ saves an INCOME (check /show_income)
- [ ] Voice spending "кофе 5" still shows the spending confirm and saves a spending
- [ ] Income confirm ❌ cancels, nothing saved
- [ ] Typed free text "got paid 2000 by client today" (no trailing-number pattern, e.g. with trailing words) routes to income confirm
- [ ] Pending spending confirm + pending income confirm at once: each button saves its own thing (no cross-talk)

### Menu & stats
- [ ] Menu → Show transactions → "💵 Income stats" button appears and shows income summary (was commented out; also crashed on immutable Message before)
- [ ] /show_income shows income summary incl. the repaired 300 EUR trading entry under July
- [ ] /show_ext no longer lists a "/income" spending category (row 4739 converted to income, category dict cleaned)

### /ask income context
- [ ] `/ask покажи доход и расход за последний месяц` now reports the 300 EUR as INCOME, no "logged as spending" note
- [ ] `/ask add 300 eur income from trading` refusal now points to /income and text/voice entry
- 2026-07-12 moved to review
