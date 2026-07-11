---
id: T-022
title: AI access control: DB-backed entitlements + admin grant/revoke
status: todo
type: feature
area: db
priority: p1
deps: []
tags: [ai, monetization]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Replace the env-var allowlist (src/config.py is_llm_allowed: ADMIN_USER_ID + LLM_ALLOWED_USERS) with a per-user entitlement stored in PostgreSQL (users table flag or ai_access table with granted_by/granted_at/expires_at). All AI entry points consult it: /ask (core.py), voice + free-text intent routing (src/handlers/voice.py). Admin commands to grant/revoke/list access. Keep ADMIN_USER_ID always allowed. Env allowlist stays as fallback during migration, then removed. This is the prerequisite for the paywall (separate task): a purchase just writes an entitlement row with expiry.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
