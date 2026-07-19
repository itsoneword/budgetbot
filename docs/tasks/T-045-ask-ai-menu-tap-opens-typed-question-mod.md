---
id: T-045
title: Ask AI menu tap opens typed-question mode (like Add transaction)
status: review
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner request 2026-07-19: entitled tap on the Ask AI menu button should edit the anchor into an invitation prompt ('Ask me anything about your finances, e.g. how much did I spend on beer this year?') with a Back button, and route the user's NEXT typed message to the /ask flow (no /ask prefix) — mirroring Add-transaction's typed-input pattern. Model on the existing awaiting_limit flag (settings.py handle_settings_limit) checked in the text path before transaction parsing; Back and any other menu action must clear the flag. Non-entitled path unchanged (buy offer per T-044). Builds directly on T-044's merged edit-in-place code — implement on top of main, deploy together.

## Acceptance
- [x] ASK_AI_PROMPT text exists in both src/texts.py and src/texts_ru.py
- [x] Entitled menu_ask_ai tap edits the anchor to ASK_AI_PROMPT + Back and sets awaiting_ask; non-entitled path unchanged
- [x] Next typed message with awaiting_ask set is routed into the /ask answer flow (shared helper, entitlement re-checked, interaction logged on channel 'ask')
- [x] awaiting_ask cleared by Back / any menu tap (pop at top of menu_call) and by a voice message
- [x] /ask command behavior unchanged (delegates to the shared helper)
- [x] Unit tests cover the new paths; full suite green

## Log
- 2026-07-19 created
- 2026-07-19 started

## Testing

Manual testing checklist: Ask AI typed-question mode (T-045)

### Critical
- [ ] Entitled user taps 🤖 Ask AI in the menu → anchor edits to the "Ask me anything about your finances…" prompt with a Back button (no new message)
- [ ] Typing a question next (e.g. "how much did I spend on food this month?") → "Analyzing…" then an AI answer; no /ask prefix needed
- [ ] Tapping Back from the prompt returns to the main menu; typing a transaction afterwards (e.g. "coffee 3.5") parses as a transaction, NOT as a question
- [ ] Non-entitled user taps Ask AI → Stars offer with Buy + Back, exactly as before T-045; their next typed text is NOT swallowed
- [ ] /ask <question> command works unchanged (usage hint on empty /ask, answer on a real question)
- [ ] RU language user sees the Russian prompt text

### Important
- [ ] After the prompt, sending a VOICE message routes by intent as usual, and a typed transaction after that still parses as a transaction (flag did not leak)
- [ ] After the prompt, tapping any other menu button (e.g. via a second /menu) works and cancels the mode — the next typed text is not treated as a question
- [ ] Asking a question with zero transactions → "no data" message, no crash
- [ ] Entitlement revoked between tap and typed question → Stars offer, not an answer
- [ ] The Q&A appears in ai_interactions (channel 'ask') so a voice follow-up ("а за июнь?") classifies against it — same as /ask (T-041 parity)

### Nice-to-have
- [ ] Double-tapping the Ask AI button does not error (edit-not-modified swallowed)
- [ ] LLM failure during the answer → friendly ASK_ERROR text, bot stays responsive
- 2026-07-19 ASK_AI_PROMPT texts; menu_ask_ai arms awaiting_ask; core.answer_ask_question helper shared by /ask and typed path; flag cleared in menu_call top + voice entry; 8 unit tests, suite 250 green
- 2026-07-19 moved to review
