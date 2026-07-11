---
id: T-035
title: Income tracking: verify it works, wire into voice/AI intents, income-vs-outcome analysis in /ask
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
Owner request 2026-07-11: income tracking exists (/income conversation, /show_income, /delete_income sharing handlers with spendings) but was never properly used — first VERIFY the whole flow works end-to-end post-PostgreSQL-migration (add, show, delete, charts treatment). Then: (1) extend the T-019 voice/text intent classifier with an add_income intent so users with irregular income can just say it ('got paid 2000 today') and it saves with the same confirm gate as spendings; (2) make sure /ask context (domain/ask_summary.py) includes income so AI can analyze income vs outcome and give suggestions — possibly a dedicated prompt hint. Notes: T-026 recurring engine already supports transaction_type=income at engine level (UI deliberately spendings-only); intent routing dispatches via synthetic Update (see DECISIONS 2026-07-09) so reusing the /income conversation may need the same pattern as voice transactions. Needs a planning wave first.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created

## Implementation plan (planned 2026-07-11, pre-approval)

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
