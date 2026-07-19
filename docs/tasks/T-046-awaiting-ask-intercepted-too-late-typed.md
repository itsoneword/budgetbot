---
id: T-046
title: awaiting_ask intercepted too late: typed question after Ask AI tap hits transaction parser
status: todo
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
- [ ] TODO

## Log
- 2026-07-19 created
