---
id: T-043
title: Voice channel: 'yes' confirms pending proposal; graceful reply to conversational/meta messages
status: review
type: feature
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-21
---

## Context
Owner expectation 2026-07-19: with a pending voice-tx proposal, a spoken 'да/yes(, but...)' should tap Add; meta-requests (e.g. 'answer in English') should get a helpful reply (or route to /ask) instead of VOICE_UNKNOWN. Builds on T-041 ai_interactions context (pending proposal is visible to the classifier). Design: new confirm_pending intent honored only when an interaction with outcome=proposed exists + fallthrough intent for conversational messages routed to /ask with context. Coordinate with T-027 intent-prompt changes.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
- 2026-07-21 implemented (combined with T-052/dv-8233): confirm_pending + chat intents, spoken yes taps Add, conversational messages route to /ask with context; 381 tests green
- 2026-07-21 moved to review

## Testing

### Critical
- [ ] Voice "пиво 10" -> confirm keyboard appears; then voice "да" -> transaction saved, keyboard stripped from the old message, "Adding: пиво 10" shown
- [ ] Spoken confirm of a pending INCOME proposal saves via the income path (shows in income stats, not spendings)
- [ ] Voice "да" with nothing pending -> "Nothing is waiting for confirmation" (instant, no LLM delay)
- [ ] After a spoken confirm, tapping the old Add button does nothing harmful (no double-save)
- [ ] Voice "ответь по-английски" after an /ask answer -> the agent re-answers in English (not VOICE_UNKNOWN)
- [ ] Plain "пиво 10" by voice still proposes a transaction (not chat/confirm)

### Important
- [ ] "да, но 6" with a pending "пиво 10" -> re-proposes пиво 6 with a fresh keyboard (correction path unchanged)
- [ ] Bot restart between proposal and spoken "да" -> still confirms from the durable row
- [ ] "спасибо" / "what can you do?" -> friendly agent reply, not the unknown fallback
- [ ] RU and EN texts both render (VOICE_NOTHING_PENDING, VOICE_TX_CONFIRMED_VOICE)

### Regression
- [ ] Tap-based vtx_yes / vinc_yes confirm flows unchanged
- [ ] Voice questions ("сколько я трачу на пиво") still answered via /ask
- [ ] Typed transactions and /show_last unaffected
