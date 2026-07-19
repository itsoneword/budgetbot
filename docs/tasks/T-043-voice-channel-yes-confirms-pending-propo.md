---
id: T-043
title: Voice channel: 'yes' confirms pending proposal; graceful reply to conversational/meta messages
status: todo
type: feature
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner expectation 2026-07-19: with a pending voice-tx proposal, a spoken 'да/yes(, but...)' should tap Add; meta-requests (e.g. 'answer in English') should get a helpful reply (or route to /ask) instead of VOICE_UNKNOWN. Builds on T-041 ai_interactions context (pending proposal is visible to the classifier). Design: new confirm_pending intent honored only when an interaction with outcome=proposed exists + fallthrough intent for conversational messages routed to /ask with context. Coordinate with T-027 intent-prompt changes.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
