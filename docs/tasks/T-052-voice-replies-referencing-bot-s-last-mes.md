---
id: T-052
title: Voice replies referencing bot's last message aren't resolved (context-dependent NLU)
status: review
type: bug
area: bot
priority: p2
deps: []
tags: [ai]
blocked: 
created: 2026-07-21
updated: 2026-07-21
---

## Context
Repro (2026-07-21, screenshot): bot found two prior transport>tax payments (111 EUR: 2 Jul 2025, 1 Aug 2024) and told the user 2026's hasn't been paid yet. User's voice reply: "da, srok podoshel, dobavlyay, ya kak-to zaplatil, dumal chto ran'she ot segodnyashnego chisla" (yes it's due, add it, I think I already paid, thought it was before today's date) - a conversational confirmation referring back to the record the bot itself had just surfaced. Bot could not map it to an action and fell back to the generic "I couldn't map this to an action. You can add a spending like coffee 4.5..." message. Root cause: intent classification (domain/intent.py, see T-019) only handles fresh structured commands, not follow-up/referential replies to the bot's own previous message (pronouns, "add that one", "yes, that") - no conversational state carried into the next turn's LLM classification.

## Acceptance
- [ ] When the bot's last message showed specific records/candidates, the next voice or text turn is classified with that context available (not just the bare transcript) so referential replies ("add it", "yes, that one", "the second one") can resolve against it
- [ ] On successful context resolution, the resulting action (category/amount/date) is shown in the existing confirm/cancel flow (T-019) before saving — no silent auto-save
- [ ] On failed mapping, the fallback message echoes back what was partially understood (e.g. "Add tax payment, 111 EUR, transport>tax, date=today?") instead of only generic examples, so the user can confirm/correct in one word
- [ ] Regression: fresh structured commands ("coffee 4.5") still work unchanged when there's no relevant prior bot context

## Log
- 2026-07-21 created
- 2026-07-21 tracked on deviz board as dv-8233 (subtask of dv-3a1c agentic AI channel)
- 2026-07-21 implemented (combined with dv-2cf1): referential context resolution, partial-understanding echo, question-row context rendering, 800-char answer digest; 381 tests green
- 2026-07-21 moved to review

## Testing

### Critical
- [ ] Ask "когда я платил налог на транспорт?" -> bot answers with records; then voice "да, срок подошёл, добавляй" -> proposes a concrete transaction (category+amount from the answer, e.g. "transport tax 111") behind the normal confirm keyboard
- [ ] The resolved proposal is NOT auto-saved — Add/Cancel tap still required
- [ ] Fresh "кофе 4.5" with prior context present still proposes exactly "кофе 4.5" (no context bleed)
- [ ] Amount never invented: "добавь что-нибудь" with no amount anywhere -> unknown/partial fallback, not a proposal

### Important
- [ ] Near-miss ("налог наверное") -> "I think you meant: ..." partial echo instead of the generic unknown text
- [ ] After the partial echo, replying "да 111" (voice or text) resolves into a proposal
- [ ] Date from context: if the bot's answer named the date the record is for, the proposal carries it; user-spoken date always wins; otherwise today
- [ ] /ask answers longer than 800 chars: follow-up still resolves (digest truncation acceptable)

### Regression
- [ ] Correction flow «не X, а Y» unchanged
- [ ] show stats / reminder voice commands unchanged
- [ ] Intent classification latency still acceptable (bigger context block, haiku model)
