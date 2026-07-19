---
id: T-041
title: AI conversation memory: context-aware voice/ask channel with correction handling
status: review
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-13
---

## Context
Owner request 2026-07-12 (screenshot repro): voice pipeline is stateless — Whisper misheard 'дом' as 'холм дом', bot proposed the wrong transaction, and the user's follow-up voice correction ('не холм дом, а дом') hit the intent classifier with zero context and fell to VOICE_UNKNOWN. Every /ask and voice message starts from scratch. Wanted, modeled on the owner's Devvybot memory system (/home/cleversol/Devvybot/devvy_bot: src/storage/memory_repository.py — tiered facts, pinned+FTS retrieval, soft supersede; docs/plans/agent-memory-system.md — evaluator extraction at token intervals, rolling summary compaction): (1) persist AI-channel interactions per user (transcript, detected intent+payload, proposed/confirmed/cancelled outcome) in Postgres — NOT SQLite, we already run Postgres, owner explicitly OK with skipping SQLite; (2) feed recent interaction window into intent classification so corrections and follow-ups resolve ('not X, I meant Y' should edit/redo the previous action, pending confirmations should be referenceable); (3) ASR disambiguation: bias transcript interpretation with the user's category dictionary + past corrections so холм/дом-type mishears map to real categories; (4) longer-term per-user memory with summarization/compaction (Devi evaluator pattern) — likely v2, scope split is a planning decision. Relates to T-027 (AI recurring channel — same intent prompt), T-018//ask, T-019/voice. Needs planning wave: read Devvybot implementation + budgetbot voice/intent pipeline, propose schema + retention/privacy policy + v1/v2 split.

## Acceptance
- [ ] Screenshot repro fixed: after a proposed/confirmed voice transaction, a voice correction ("не X, а Y") replaces the pending proposal or offers "Replace old → new?" for a saved one — never falls to VOICE_UNKNOWN
- [x] ai_interactions table (alembic 0006+) persists every voice//ask exchange with outcome lifecycle (proposed/confirmed/cancelled/routed/unknown/superseded)
- [x] Intent prompt receives last-N context + user's known-items dictionary; mishears snap to real categories
- [x] Size-based compaction job (~50k tokens/user: summarize + extract key facts incl. correction pairs, delete raw rows, keep summary; per-message char guardrail); domain-level unit tests for new pure functions

## Log
- 2026-07-12 created

## Implementation plan (proposed 2026-07-12)

Design: fix the screenshot failure with a short **per-user interaction log in Postgres** (`ai_interactions`: transcript, intent, payload, outcome, optional tx link) injected into the existing single intent call — no second LLM call, no agent loop. Corrections are handled by **context-aware re-parse, NOT a new intent kind**: the classifier sees the last N=3 interactions and re-emits a normal `add_transaction`/`add_income` with a new boolean JSON field `"corrects_previous": true`; the router branches on the *previous interaction's outcome* — pending proposal → replace the confirm; already confirmed → "Replace X with Y?" confirm that deletes the old row and re-injects the corrected text through the normal save pipeline (category resolution for free). A new-intent-kind alternative ("correct_last") was rejected: it would need its own payload grammar and duplicate validation, while re-parse reuses `_TX_ITEM_RE` and every existing guardrail unchanged. ASR disambiguation: the intent prompt today contains NO user vocabulary (verified — `build_intent_prompt` is date+transcript only); inject the user's flattened category dictionary (capped) as "known items" so холм/дом-type mishears snap to real categories. Recent-context and dictionary blocks are built by **separate pure functions appended in `build_intent_prompt`** — the system-prompt intent list stays a single string T-027 extends independently (append-only seam, no conflict). Long-term memory (Devvybot evaluator/facts/rolling summary) is an explicit v2 slice with schema sketched below — not built in v1. N=3 because corrections reference the immediately previous action and each entry is ~100 tokens; 3 entries + a ~40-item dictionary adds ~400–500 tokens to a Haiku call (negligible at 72 users) while keeping classifier drift risk low.

1. Alembic revision 0006 (off whatever head is at impl time; 0005 today) in `infrastructure/database/alembic/versions/0006_ai_interactions.py`: `CREATE TABLE ai_interactions (id BIGSERIAL PK, user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, channel VARCHAR(10) NOT NULL — 'voice'|'text'|'ask', transcript TEXT NOT NULL, intent VARCHAR(30) NOT NULL, payload TEXT NOT NULL DEFAULT '', outcome VARCHAR(12) NOT NULL DEFAULT 'proposed' CHECK IN (proposed, confirmed, cancelled, routed, unknown, superseded), tx_id BIGINT NULL, created_at TIMESTAMPTZ DEFAULT NOW())` + index `(user_id, id DESC)`; one `exec_driver_sql` per statement (asyncpg dialect); downgrade drops the table.
2. `infrastructure/repositories/interaction_repository.py` (model on `recurring_repository.py`): `AIInteraction` dataclass + `InteractionRepository` with `add(user_id, channel, transcript, intent, payload) -> id`, `get_recent(user_id, n)`, `set_outcome(interaction_id, user_id, outcome, tx_id=None)` (rowcount-guarded), `purge_older_than(days) -> int`. Register in `repositories/__init__.py` and `shared/di/container.py` as `repos.interactions`.
3. `domain/intent.py` (pure, COORDINATION seam for T-027): `Intent` gains `corrects_previous: bool = False`; `parse_intent_response` accepts the optional JSON field, honored ONLY for `add_transaction`/`add_income` (ignored elsewhere — still collapses garbage to unknown). New pure builders: `format_recent_context(interactions)` — numbered "[outcome] heard: «transcript» → intent payload" lines, each transcript capped ~200 chars, block capped ~1200 chars; `format_known_items(subcategories)` — comma list capped ~40 items/~600 chars. `build_intent_prompt(transcript, today, context_block="", known_items="")` appends both blocks; system prompt gets two additions: (a) mishear-bias line "prefer a phonetically close known item over a literal mishear", (b) correction rule "if the message corrects the previous interaction shown in context («не X, а Y», "not X, I meant Y"), re-emit the FULL corrected intent and set corrects_previous true" + one RU/EN contrast example each.
4. `src/handlers/voice.py` `_classify(text)` → `_classify(user_id, text, context)`: load `repos.interactions.get_recent(user_id, 3)` and `repos.categories.get_dictionary(user_id, language)` (flatten subcategories), pass through the new builders; failures degrade to empty blocks, never block classification.
5. `src/handlers/voice.py` `_route_intent`: after classification, `repos.interactions.add(...)` for EVERY message including unknown (a failed turn must still be visible as context to the next one); stash `voice_tx_interaction_id` / `voice_income_interaction_id` in `user_data` next to the payload keys. `handle_voice_tx_confirmation` / `handle_voice_income_confirmation`: pop the id, `set_outcome(confirmed|cancelled)`. Stat/reminder/question routes → `set_outcome('routed')` immediately.
6. Correction branch in `_route_intent` (when `intent.corrects_previous` and a previous add_* interaction exists): previous outcome `proposed` → `set_outcome(old, 'superseded')`, overwrite the pending `user_data` key, send a fresh confirm keyboard; previous outcome `confirmed` → find the saved row via `repos.transactions.get_latest(user_id, 5)` matched on amount+item words from the recorded payload — exactly one match: stash its tx id + corrected text, show "Replace {old} → {new}?" keyboard (`vfix_yes`/`vfix_no`, new `handle_voice_fix_confirmation`: `repos.transactions.delete(tx_id)` then `_inject_text(corrected_text)`); zero/many matches, or `corrects_previous` with no usable previous: fall back to the normal new-transaction confirm (never guess). Register `^vfix_` in `core.py` next to `vtx_` (before spendings_handler).
7. `/ask` (`src/core.py` `ask()`, ~line 654): after a successful answer, `repos.interactions.add(user_id, 'ask', question, 'question', answer[:300], outcome='routed')` — so a voice follow-up ("а за июнь?") classifies against the asked question. No context injection into the ask *answer* prompt in v1 (open question 4).
8. Retention (AMENDED per owner 2026-07-13 — size-based, NOT time-based; no 30-day purge): keep all conversations until compaction. (a) Per-message guardrail: truncate stored transcript/payload at 2000 chars each on insert. (b) `src/scheduler.py` `run_interaction_compaction(context)` daily job: for each user whose non-summary rows exceed AI_INTERACTION_COMPACT_CHARS total (default 200_000 chars ≈ 50k tokens, `src/config.py`), summarize all but the newest 20 rows via `get_llm_client("haiku")` — the summary must extract key durable things: confirmed ASR-correction pairs («холм дом»→«дом»), recurring phrasings/preferences, notable Q&A topics — insert one summary row (`channel='system'`, `intent='summary'`, `outcome='routed'`), then DELETE the summarized raw rows. Summaries are never auto-deleted; repeat compactions fold the previous summary row into the new one (hierarchical). LLM failure → skip user, retry next day, log error. (c) `format_recent_context` additionally prepends the user's latest summary row (capped ~800 chars) when present — so learned correction pairs persist into the intent prompt beyond the N=3 window, pulling the most valuable slice of v2 forward.
9. Copy in BOTH `src/texts.py` and `src/texts_ru.py`: `VOICE_CONFIRM_FIX` (old→new), `VOICE_FIX_DONE`, `VOICE_FIX_CANCELLED`, `VOICE_FIX_NOT_FOUND`. Two `docs/DECISIONS.md` one-liners: re-parse-vs-correction-intent; delete+re-add-vs-UPDATE for corrected transactions (re-add reuses category resolution; UPDATE would bypass it).
10. Tests (`tests/`, pure domain only): `parse_intent_response` with/without `corrects_previous` per intent kind, `format_recent_context` caps/ordering, `format_known_items` cap; pin clocks per convention.

**v2 slice (separate task, schema sketch only — Devvybot patterns adapted to Postgres):** `ai_memory_facts (id, user_id, tier 'pinned'|'general', kind 'asr_correction'|'preference'|'summary', content TEXT, status 'active'|'superseded', source, created_at, updated_at)` + `tsvector` GIN index — Postgres FTS replaces Devvybot's SQLite FTS5, `MemoryRetriever`-style pinned-always + FTS-with-recency-fill selection, soft supersede kept. Evaluator: a daily batch job (not Devvybot's 50k-token interval — a finance bot's turns are tiny) runs a small model over the day's `ai_interactions` per active user, extracting durable facts — confirmed correction pairs («холм дом»→«дом») as pinned `asr_correction` facts injected into the intent prompt, plus preference/summary facts with rolling compaction of superseded rows. v1's schema needs no change for v2 to land.

Touched (COORDINATION with T-027 on `domain/intent.py` + `voice.py` — sequence, do not run as parallel worktrees): new `0006_ai_interactions.py`, `infrastructure/repositories/interaction_repository.py`; modified `repositories/__init__.py`, `shared/di/container.py`, `domain/intent.py`, `src/handlers/voice.py`, `src/core.py`, `src/scheduler.py`, `src/config.py`, `src/texts.py`, `src/texts_ru.py`, `docs/DECISIONS.md`, tests.

Open questions (recommended defaults):
1. Raw transcript retention → OWNER OVERRIDE 2026-07-13: no time purge; size-based compaction at ~50k tokens/user (summarize + extract key facts, delete raw), per-message char cap. See amended step 8.
2. Recent-interaction window N injected into the intent prompt → 3.
3. Correction of an already-confirmed transaction = delete + re-inject (not in-place UPDATE) → yes.
4. Also inject recent context into the /ask answer prompt (ask-channel follow-ups) → no (v2).
5. Known-items dictionary cap in the prompt → 40.
6. Record /ask Q&A rows in ai_interactions in v1 → yes.

**Owner decisions 2026-07-13:** retention = size-based compaction, NOT time-based (override of planner's 30-day default): store all conversations, per-message char guardrail, summarize-and-delete at ~50k tokens/user with key-fact extraction (amended step 8; latest summary feeds the intent prompt). All other defaults accepted (N=3 window; delete+re-add for confirmed-tx corrections; /ask answers single-shot in v1; 40-item dictionary cap; /ask Q&A logged). Implement immediately — only unblocked p1 feature; T-027 rebases on it later.

What v1 does NOT do (ranked by likelihood someone assumes it does):
1. No long-term facts/summaries/evaluator/compaction — the whole Devvybot fact tier is v2.
2. No learned ASR-correction pairs persisting beyond the N=3 window (v2 pinned facts).
3. No multi-turn /ask conversation — ask answers stay single-shot.
4. No correction of transactions saved via *typed* quick-add or menu edits — only voice/free-text-routed ones in the interaction log.
5. No FTS/semantic retrieval — v1 context is pure recency.
6. No /memory-style inspection command.

Risks: classifier regression as the prompt grows (T-034's regression checklist already covers intent routing — re-run it; watch "Intent routed" logs; contrast examples mandatory); `corrects_previous` misfiring on messages that merely *mention* the previous item (gated: ignored unless a previous add_* interaction exists, and fallback is a normal confirm — worst case one extra tap, never a silent edit); stale confirm keyboard after a proposal is superseded by a correction (old buttons act on the NEW payload since `user_data` was overwritten — same accepted vtx_ overwrite behavior as T-027, noted in testing); `get_latest` match ambiguity for delete+re-add (two identical recent amounts → falls back to propose-new, never deletes ambiguously); privacy — voice transcripts now persist server-side 30 days (owner sign-off required, question 1); T-027/T-041 both edit the intent prompt and `_route_intent` — sequence them, the context seam itself is append-only.
- 2026-07-12 Implementation plan proposed: ai_interactions log + context-aware re-parse (corrects_previous flag), known-items ASR bias, 30-day purge; Devi facts/evaluator sketched as v2. 6 open questions pending owner
- 2026-07-13 Owner decisions: size-based compaction instead of 30-day purge (summarize+extract at ~50k tokens/user, keep summaries, delete raw); other defaults accepted; implementation starting
- 2026-07-13 started
- 2026-07-13 alembic 0006 ai_interactions + InteractionRepository + DI wiring; repo pattern from recurring_repository
- 2026-07-13 context-aware intent prompt (corrects_previous, recent-context + known-items blocks), voice correction flow (supersede pending / vfix Replace keyboard), interaction logging incl. unknown, /ask Q&A rows, vfix_ registration, EN/RU copy
- 2026-07-13 size-based compaction: domain/memory.py pure logic, run_interaction_compaction daily job, AI_INTERACTION_COMPACT_CHARS config; 40 new domain tests (212 total green); 3 DECISIONS one-liners

## Testing

Manual checklist (unit suite green: 212 passed; alembic single head 0006; `import src.core` OK). Needs a running bot with DB migrated to 0006 and an AI-entitled user.

### Critical — screenshot repro end-to-end
- [ ] Voice add with a mishear: say a spending so Whisper mishears the item (e.g. «дом пять» heard as «холм дом пять») → confirm keyboard appears, row logged in ai_interactions with outcome=proposed
- [ ] While the proposal is pending, voice-correct it («не холм дом, а дом») → a FRESH confirm keyboard with the corrected payload appears (not VOICE_UNKNOWN); old row becomes superseded; tapping ✅ saves only the corrected transaction
- [ ] Confirm a voice transaction (✅), then voice-correct it → "Replace {old} → {new}?" (vfix keyboard); ✅ deletes the old saved row and saves the corrected one (check /show_last: exactly one row, the corrected item, correct category resolution); interaction outcomes: old=superseded, new=confirmed
- [ ] vfix ❌ keeps the saved record untouched (VOICE_FIX_CANCELLED; /show_last unchanged; new interaction=cancelled)
- [ ] Known-items snap: with «дом» in the user's category dictionary, a voice message misheard as «холм» maps to «дом» in the proposed payload
- [ ] Russian repro from the screenshot verbatim: «не холм дом, а дом» after a wrong proposal never falls to VOICE_UNKNOWN

### Critical — interaction log lifecycle
- [ ] Every voice/free-text message writes a row: add_* → proposed; stat/reminder/question → routed; gibberish → unknown (check table directly)
- [ ] vtx_yes/vtx_no and vinc_yes/vinc_no set confirmed/cancelled on the right row
- [ ] /ask logs a row (channel=ask, intent=question, payload=answer prefix, outcome=routed); a voice follow-up («а за июнь?») classifies against the asked question (context visible in the intent, not VOICE_UNKNOWN)

### Critical — compaction job on a seeded oversized user
- [ ] Seed >200k chars of ai_interactions rows (or lower AI_INTERACTION_COMPACT_CHARS) for one user, trigger run_interaction_compaction (restart with AI_COMPACTION_HOUR_UTC near now, or call the job in a REPL) → all but the newest 20 raw rows deleted, one channel='system' intent='summary' row inserted containing correction pairs
- [ ] Second compaction folds the previous summary row (old summary deleted, one summary remains)
- [ ] With a summary row present, the next voice classification still works (summary block prepended, no crash)

### Important — edge/error handling
- [ ] Correction when the previous add was CANCELLED → falls back to a normal new-transaction confirm (no Replace keyboard, nothing deleted)
- [ ] Correction when two identical recent amounts match (e.g. two «дом 5» saved) → falls back to normal confirm, never deletes ambiguously
- [ ] Correction of an income proposal/confirmed income goes through the income path (saved as income, not spending)
- [ ] DB down / interactions table missing: voice classification still answers (context degrades to empty blocks, error logged, no user-facing crash)
- [ ] Transcript >2000 chars stores truncated, doesn't break inserts
- [ ] Stale keyboard: after a correction supersedes a pending proposal, tapping the OLD keyboard's ✅ acts on the NEW payload (accepted overwrite behavior — verify no crash/duplicate)

### Regression (T-034 intent checklist re-run)
- [ ] Plain voice spending, income, «покажи статистику», reminder set/off, /ask question all still route correctly with the grown prompt (watch "Intent routed" logs)
- [ ] Typed quick-add («кофе 4.5») and menu flows unaffected
- [ ] Recurring rules + reminder jobs still fire (scheduler untouched paths)
- 2026-07-13 moved to review
