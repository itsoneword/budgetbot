---
id: T-046
title: awaiting_ask intercepted too late: typed question after Ask AI tap hits transaction parser
status: review
type: bug
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner repro 2026-07-19 (screenshot): tap Ask AI -> prompt shows correctly (T-045), but the typed question gets 'You need to enter an amount...' — the transaction parser answered, not the AI. Diagnosis: T-045 put the awaiting_ask intercept in core.py handle_text (~:637, next to awaiting_limit), but inside the active spendings ConversationHandler the TRANSACTION state maps typed text to the transaction-entry callback, so handle_text's intercept never runs in exactly the state menu_ask_ai returns. Fix options (pick at impl): (a) check user_data.pop('awaiting_ask') at the TOP of the transaction-state text callback (the handler that produced the error message — find it via that texts key TRANSACTION_ERROR_TEXT) and route to answer_ask_question (core.py:676, already extracted and tested); (b) dedicated ASK_INPUT conversation state returned by menu_ask_ai with its own MessageHandler + fallbacks (cleaner state machine, more wiring — mirrors how Add-transaction states work); (c) verify where awaiting_limit actually gets intercepted — if it works in-conversation today, mirror THAT exact placement. Check both in-conversation and expired-conversation paths (stale prompt after restart: flag set, conversation dead — handle_text intercept may then be the one that fires, so keep both or unify). Tests exist in tests/src/test_menu_nav.py exercising handle_text routing — extend to the real conversation-state callback. All T-045 plumbing (flag arming, defensive clears, answer_ask_question, texts) is correct and stays.

## Acceptance
- [x] Typing a question right after the Ask AI menu tap (inside an active conversation) reaches the /ask flow, not the transaction amount parser
- [x] Back from the prompt (or any menu tap) exits question mode; later typed text is parsed normally
- [x] Stale-prompt path preserved: with no active conversation, the awaiting_ask flag still routes via handle_text
- [x] Unit tests cover the new state routing (menu_ask_ai return state, ASK_INPUT callback, stale-flag fallback)

## Log
- 2026-07-19 created
- 2026-07-19 started
- 2026-07-19 Implemented option (b): new ASK_INPUT conversation state (states.py 34->35) returned by entitled menu_ask_ai; handle_ask_input in core.py answers via answer_ask_question, falls back to handle_text on stale flag; awaiting_ask flag kept for out-of-conversation path; 3 tests added/extended, 252 green
- 2026-07-19 moved to review

## Testing

The T-045 checklist item "typed question after menu tap" is the repro this fixes — retest it first.

### Critical
- [ ] /menu → Ask AI (entitled account) → type a question immediately: AI answer arrives, NOT "You need to enter an amount…"
- [ ] Same, then type a transaction ("bread 5") right after the answer: saved as a spending (question mode consumed exactly one message)
- [ ] /menu → Ask AI → tap Back → type "bread 5": parsed as a transaction, no AI call
- [ ] /ask beer spend this month — command path unchanged

### Important
- [ ] /menu → Ask AI → tap a DIFFERENT old menu button (not Back) → type text: not treated as a question
- [ ] Stale prompt: /menu → Ask AI, restart the bot, then type the question: still routed to the AI (handle_text fallback path)
- [ ] Non-entitled account: Ask AI shows the Stars offer; typing text afterwards is parsed normally, never as a question

### Nice-to-have
- [ ] Voice message while the question prompt is open: voice channel handles it; a typed message after that is parsed normally
- [ ] /cancel or /menu while the prompt is open: no stuck question mode
