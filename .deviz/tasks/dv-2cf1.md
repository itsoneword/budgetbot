---
id: dv-2cf1
title: Voice channel: 'yes' confirms pending proposal; graceful reply to conversational messages
status: done
priority: medium
assignee: claude
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T14:55:32Z
updated: 2026-07-21T13:05:00Z
---

## Description

Migrated from `docs/tasks/T-043-voice-channel-yes-confirms-pending-propo.md`.

Owner expectation 2026-07-19: with a pending voice-tx proposal, a spoken 'да/yes(, but...)' should tap Add; meta-requests (e.g. 'answer in English') should get a helpful reply (or route to /ask) instead of VOICE_UNKNOWN. Builds on T-041 ai_interactions context (pending proposal is visible to the classifier). Design: new confirm_pending intent honored only when an interaction with outcome=proposed exists + fallthrough intent for conversational messages routed to /ask with context. Coordinate with T-027 intent-prompt changes.

## Acceptance Criteria

- [ ] TODO

## Notes

### Log

- 2026-07-19 created

## Comments

### @claude — 2026-07-21T11:12:28Z

Owner decisions 2026-07-21: combined implementation with dv-8233 on one branch (single coherent intent-prompt ladder). Chat scope: ALL conversational/meta voice messages route to /ask agent session (entitlement-gated). Bare yes with nothing pending: canned no-LLM reply. 'Yes but X' re-proposes (existing T-041 policy). Precedence: correction > confirm_pending > referential add > chat > unknown.

### @claude — 2026-07-21T11:24:11Z

Implemented (combined branch with dv-8233, commit follows): confirm_pending + chat intents in domain/intent.py; _confirm_pending_by_voice in voice.py acts only on the durable [proposed] row (LLM payload discarded), strips the stale Add/Cancel keyboard, income saves via save_income_text; chat routes to answer_ask_question with the recent-conversation block. Canned VOICE_NOTHING_PENDING when nothing pending. 381 tests green. Manual checklist appended to docs/tasks/T-043 (## Testing).
- 2026-07-21 owner tested voice flows on prod (c0fa7d2) — confirm/chat/referential working
