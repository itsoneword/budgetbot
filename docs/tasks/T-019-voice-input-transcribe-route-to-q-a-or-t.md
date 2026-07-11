---
id: T-019
title: Voice input: transcribe + route to Q&A or transaction entry
status: review
type: feature
area: bot
priority: p2
deps: [T-018]
tags: [ai]
blocked: 
created: 2026-07-08
updated: 2026-07-11
---

## Context
Telegram voice messages (OGG/Opus) downloaded via bot API, transcribed locally with faster-whisper (no external STT; adds ~1GB model weight to the Docker image - consider a separate image layer or volume). LLM classifies transcript intent: question -> T-018 /ask pipeline; spending phrase ('coffee 4.50') -> parsed into a structured transaction shown for user confirmation before saving. Depends on T-018 for the LLM client and prompt plumbing.

## Acceptance
- [x] Voice note → local faster-whisper transcription (small model, CPU int8, weights from host HF cache mounted via compose)
- [x] LLM classifies transcript into add_transaction / show_stat / question / unknown; output strictly validated in domain/intent.py (enum + payload regex/whitelist)
- [x] add_transaction: transcript + parsed "item amount" shown with confirm/cancel buttons; nothing saved without a tap
- [x] show_stat: dispatches only whitelisted commands (show, show_last, show_ext, monthly_stat, yearly_stat)
- [x] question: routed into the /ask pipeline
- [x] Free text that doesn't match the transaction pattern also intent-routed (allowed users only)
- [x] Guardrails: is_llm_allowed() gate, voice ≤120s, transcript ≤1000 chars, no leading-"/" payloads, amount sanity cap
- [ ] Manually tested in Telegram (see Testing)

## Testing

### Critical
- [ ] Voice "coffee four fifty" → confirm dialog "coffee 4.5" → ✅ Add → transaction saved, visible in /show_last
- [ ] Confirm dialog ❌ Cancel → nothing saved
- [ ] Voice "show my last transactions" → /show_last output appears
- [ ] Voice "how much did I spend on food this month" → /ask answer appears
- [ ] Typed free text "bought coffee for five euros" (no trailing number) → same confirm flow
- [ ] Typed "coffee 5" still saves via the old direct path (no LLM involved)
- [ ] Voice from a non-allowlisted user → ASK_NOT_ALLOWED, nothing transcribed
- [ ] Russian voice note works for both transaction and question intents

### Important
- [ ] Voice note >120s → VOICE_TOO_LONG, no download/transcription
- [ ] Silent/noise-only voice note → VOICE_NO_SPEECH
- [ ] Gibberish/unrelated voice → VOICE_UNKNOWN with transcript echoed
- [ ] First voice message after container rebuild loads model from mounted cache (no re-download; check logs for "Loading whisper model")
- [ ] Confirm tap while a /menu conversation is open still works (vtx_ callback not swallowed)
- [ ] LLM down/timeout during classification → VOICE_UNKNOWN-style graceful reply, bot stays responsive

### Regression
- [ ] /ask still works as a typed command
- [ ] Multi-line/comma text transactions still work
- [ ] Menu buttons (menu_callback fallback) still respond normally

## Log
- 2026-07-08 created
- 2026-07-09 Prereq T-018 is done: LLM client at infrastructure/llm/ (get_llm_client), /ask pipeline in core.py. Open decisions for voice: (a) faster-whisper model size + weights in image vs volume (~150MB small / ~1GB large, CPU-only VPS), (b) owner suggestion: optionally ship intent-routing on TEXT messages first, audio second. Intent routing = LLM call classifying transcript -> /ask pipeline or parsed transaction with confirm buttons.
- 2026-07-09 started
- 2026-07-09 Implemented: infrastructure/stt (faster-whisper small via host HF cache mount), domain/intent.py (strict enum+payload validation), src/handlers/voice.py (voice handler, free-text routing, vtx_ confirm, synthetic-update injection via process_update), LLM_INTENT_MODEL=haiku default. Offline tests pass; whisper smoke-tested.
- 2026-07-09 moved to review
- 2026-07-09 Deployed to prod: image rebuilt with faster-whisper, HF cache mount verified in container, in-container transcription smoke test passed (model loads from host cache, no download). Awaiting manual Telegram testing.
- 2026-07-11 Fixed root cause of intent routing always returning unknown: single-file bind mount of .credentials.json pinned a deleted inode after host token refresh -> expired OAuth broke ALL LLM calls. Now mount ~/.claude dir ro at /host-claude + entrypoint symlink. Also hardened intent prompt for STT-garbled commands. Verified in container: garbled RU transcripts now classify correctly.
- 2026-07-11 Extended intent schema: comma-separated multi-transactions (max 5) and optional dd.mm date prefix per item, resolved from today's date passed into the prompt. Validator checks each item + date sanity. Verified in prod container with the exact failing phrase.
