---
id: T-027
title: AI channel: manage recurring spendings by voice//ask
status: todo
type: feature
area: bot
priority: p1
deps: [T-026]
tags: [ai, recurring]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Extend domain/intent.py with recurring intents on top of the T-026 action API: add_recurring (payload: item, amount, day-of-month — strictly validated like add_transaction), list_recurring, cancel_recurring (payload: rule reference from a shown list, never free-form). Same guardrails as T-019: enum + validated payload, every write behind an inline confirm tap, is_llm_allowed/entitlement gate. Target UX: voice 'remember I pay 800 for the apartment every month on the 1st' -> confirm dialog -> rule created -> transactions appear automatically; 'what are my recurring payments' -> list.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created

## Implementation plan (planned 2026-07-11, pre-approval)

Design: three flat intents — add_recurring, list_recurring, cancel_recurring (matches existing flat enum + one-string-payload Intent shape). Pause-vs-delete is decided by which button the user taps at confirm time, never by the LLM. All writes ride the T-026 action API: add via injected `/recurring add <payload>` after a vrc_yes confirm tap; pause/delete via the existing rr_* callback buttons (already the confirm gate).

1. domain/intent.py: INTENT_ADD_RECURRING / INTENT_LIST_RECURRING / INTENT_CANCEL_RECURRING. parse_intent_response: add payload "<name> <amount> <day>" (last-two-tokens split, same as /recurring add), validate via domain.recurring.validate_rule_input, reject leading "/"; list forces empty payload; cancel payload = rule reference words (MAX_NAME_CHARS cap, never an ID). build_intent_system_prompt: EN/RU examples + explicit disambiguation line (recurrence words → add_recurring, plain amount → add_transaction).
2. domain/recurring.py: pure match_rules(rules, query) — case-insensitive token/substring match on subcategory_name.
3. src/handlers/voice.py _route_intent: list → _inject_text("/recurring"); add → store payload in user_data["voice_rec_text"], vrc_yes/vrc_no confirm keyboard (mirror vtx_), on yes inject "/recurring add <payload>"; cancel → list_rules + match_rules: exactly one match → "Stop '{name}'?" with rr_pause_{id} / rr_delc_{id} / rr_back buttons (land in existing handle_recurring_callback); zero/many → rules view with "which one?" header. New handle_voice_recurring_confirmation.
4. src/core.py: CallbackQueryHandler(handle_voice_recurring_confirmation, pattern="^vrc_") registered next to vtx_ (before spendings_handler).
5. texts.py + texts_ru.py: VOICE_CONFIRM_RECURRING, RECURRING_AI_STOP_CONFIRM, RECURRING_AI_WHICH_RULE (reuse existing pause/delete/back button labels); no parse_mode (user text).
6. No migration needed. Gating confirmed: both intent entry points (voice.py:60, core.py:594 free-text) already call check_ai_access — new intents inherit T-022 gate with zero code; vrc_ confirm needs no re-check.

Touched: domain/intent.py, domain/recurring.py, src/handlers/voice.py, src/core.py, texts.py, texts_ru.py.
COORDINATION: T-027/T-034/T-035 all edit domain/intent.py (monolithic prompt string) and voice.py:_route_intent — do NOT run as parallel worktrees on those files. Either sequence (T-027 first — deps done) or refactor the prompt into an intent registry (name, description, validator) first to make them append-only parallelizable.

Open questions (recommended defaults):
1. Day not stated ("pay rent monthly") → default day 1, shown explicitly in the confirm dialog (LLM instructed: no day → 1).
2. "Stop/cancel" → LLM never chooses pause vs delete; confirm message offers both buttons.
3. Voice resume ("turn rent back on") → out of scope; list_recurring + resume button covers it.

Risks: classifier accuracy regression as prompt grows (add contrast examples, watch "Intent routed" logs); transcription/language name mismatches degrade safely to full-list fallback; rule names ending in digits are ambiguous but consistent with /recurring add; stale pending confirm overwritten by second voice note (same accepted vtx_ behavior).
