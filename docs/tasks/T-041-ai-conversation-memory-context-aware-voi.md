---
id: T-041
title: AI conversation memory: context-aware voice/ask channel with correction handling
status: todo
type: feature
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-12
---

## Context
Owner request 2026-07-12 (screenshot repro): voice pipeline is stateless — Whisper misheard 'дом' as 'холм дом', bot proposed the wrong transaction, and the user's follow-up voice correction ('не холм дом, а дом') hit the intent classifier with zero context and fell to VOICE_UNKNOWN. Every /ask and voice message starts from scratch. Wanted, modeled on the owner's Devvybot memory system (/home/cleversol/Devvybot/devvy_bot: src/storage/memory_repository.py — tiered facts, pinned+FTS retrieval, soft supersede; docs/plans/agent-memory-system.md — evaluator extraction at token intervals, rolling summary compaction): (1) persist AI-channel interactions per user (transcript, detected intent+payload, proposed/confirmed/cancelled outcome) in Postgres — NOT SQLite, we already run Postgres, owner explicitly OK with skipping SQLite; (2) feed recent interaction window into intent classification so corrections and follow-ups resolve ('not X, I meant Y' should edit/redo the previous action, pending confirmations should be referenceable); (3) ASR disambiguation: bias transcript interpretation with the user's category dictionary + past corrections so холм/дом-type mishears map to real categories; (4) longer-term per-user memory with summarization/compaction (Devi evaluator pattern) — likely v2, scope split is a planning decision. Relates to T-027 (AI recurring channel — same intent prompt), T-018//ask, T-019/voice. Needs planning wave: read Devvybot implementation + budgetbot voice/intent pipeline, propose schema + retention/privacy policy + v1/v2 split.

## Acceptance
- [ ] TODO

## Log
- 2026-07-12 created
