---
id: dv-2cf1
title: Voice channel: 'yes' confirms pending proposal; graceful reply to conversational messages
status: todo
priority: medium
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T14:55:32Z
updated: 2026-07-21T10:56:56Z
---

## Description

Migrated from `docs/tasks/T-043-voice-channel-yes-confirms-pending-propo.md`.

Owner expectation 2026-07-19: with a pending voice-tx proposal, a spoken 'да/yes(, but...)' should tap Add; meta-requests (e.g. 'answer in English') should get a helpful reply (or route to /ask) instead of VOICE_UNKNOWN. Builds on T-041 ai_interactions context (pending proposal is visible to the classifier). Design: new confirm_pending intent honored only when an interaction with outcome=proposed exists + fallthrough intent for conversational messages routed to /ask with context. Coordinate with T-027 intent-prompt changes.

## Acceptance Criteria

- [ ] TODO

## Notes

### Log

- 2026-07-19 created
