---
id: T-042
title: Voice STT: accented English transcribed as Russian (language misdetection on small model)
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
Owner repro 2026-07-19 (screenshot): spoke English ('Yes, but can you speak English, please'), faster-whisper small (auto-detect, infrastructure/stt/whisper_local.py:50) transcribed loose RUSSIAN translation. Known small-model failure with accented/code-switched speech. Fix candidates (planning): use _info.language_probability — below threshold retry with alternate language; per-user STT language override in Settings; WHISPER_MODEL=medium env test (CPU cost); initial_prompt bilingual hint. Interacts with T-041 context (mangled transcripts poison the interaction log).

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
