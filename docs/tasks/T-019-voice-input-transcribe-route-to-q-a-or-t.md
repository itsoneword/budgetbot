---
id: T-019
title: Voice input: transcribe + route to Q&A or transaction entry
status: backlog
type: feature
area: bot
priority: p2
deps: [T-018]
tags: [ai]
blocked: 
created: 2026-07-08
updated: 2026-07-08
---

## Context
Telegram voice messages (OGG/Opus) downloaded via bot API, transcribed locally with faster-whisper (no external STT; adds ~1GB model weight to the Docker image - consider a separate image layer or volume). LLM classifies transcript intent: question -> T-018 /ask pipeline; spending phrase ('coffee 4.50') -> parsed into a structured transaction shown for user confirmation before saving. Depends on T-018 for the LLM client and prompt plumbing.

## Acceptance
- [ ] TODO

## Log
- 2026-07-08 created
