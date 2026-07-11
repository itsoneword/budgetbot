---
id: T-022
title: AI access control: DB-backed entitlements + admin grant/revoke
status: review
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
- [x] `ai_entitlements` table ships as alembic revision 0003 (down_revision 0002); downgrade drops it
- [x] `EntitlementRepository` (has_ai_access / grant / revoke / get / list_active) with GREATEST extension semantics; exported and wired into the DI container as `entitlements`
- [x] All 3 AI entry points gate via `src/ai_access.check_ai_access` (admin always; env allowlist fallback; else DB; fail-closed with loud log): core.py ask(), handle_text() free-text routing, handlers/voice.py
- [x] Admin commands /grant_ai user_id [days], /revoke_ai user_id, /list_ai — registered as admin_only CommandSpec rows in src/commands.py (T-021 registry); grant refuses targets missing from the users table
- [x] `is_admin()` added to src/config.py; ADMIN_USER_ID always allowed; env allowlist kept as migration fallback (removal in T-023 release)

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

Decisions: dedicated `ai_entitlements` table (not a flag on users — T-023 needs source/expiry/refund semantics, T-025 needs listing); `/grant_ai` without days = perpetual; denied users keep existing `ASK_NOT_ALLOWED` text until T-023 swaps in the Stars offer; env `LLM_ALLOWED_USERS` kept as fallback, backfilled via `/grant_ai` after deploy, removed in the T-023 release. **Ships as alembic revision 0003 (down_revision 0002) — merges after T-005 and T-021.**

1. Alembic revision `0003_ai_entitlements`: `ai_entitlements(user_id BIGINT PK REFERENCES users(user_id) ON DELETE CASCADE, source VARCHAR(20) NOT NULL DEFAULT 'admin', granted_by BIGINT NOT NULL, granted_at TIMESTAMPTZ DEFAULT NOW(), expires_at TIMESTAMPTZ /*NULL=perpetual*/, revoked_at TIMESTAMPTZ /*NULL=active*/, revoked_by BIGINT, notes TEXT, updated_at TIMESTAMPTZ DEFAULT NOW())`; reuse `update_updated_at_column()` trigger.
2. `infrastructure/repositories/entitlement_repository.py`: `AIEntitlement` dataclass + repo — `has_ai_access` (EXISTS, not revoked, not expired), `grant(user_id, granted_by, source='admin', duration_days=None)` UPSERT clearing revoked_at with extension semantics `GREATEST(COALESCE(expires,NOW()),NOW()) + interval` (T-023 contract: repeat purchase extends; T-023 writes ONLY via grant(), keeps Stars charge IDs in its own payments table), `revoke`, `get`, `list_active` (JOIN users). Export in `repositories/__init__.py`.
3. DI: `entitlements` property in `shared/di/container.py`.
4. New `src/ai_access.py`: `async check_ai_access(user_id, context) -> bool` — admin always; env-allowlist fallback; else DB via repos, fail-closed on DB error with loud log.
5. Replace 3 gate sites: `core.py` `ask()` (~800), `handle_text()` (~606), `src/handlers/voice.py:59` (+ stale docstring line 13). Voice re-enters /ask → double-check is just one extra query, fine.
6. Admin commands in `src/handlers/admin.py`: `/grant_ai <user_id> [days]` (target not in users table → "user must /start first"), `/revoke_ai <user_id>`, `/list_ai`. Use `is_admin()` from `src/config.py` (T-025 adds it; add if absent, dedupe at merge). Register as T-021 registry rows `admin_only=True`.

Files: new entitlement_repository.py, src/ai_access.py, alembic 0003; modified repositories/__init__.py, shared/di/container.py, src/core.py, src/handlers/voice.py, src/handlers/admin.py, docs/DECISIONS.md.
Risks: fail-closed = DB outage denies AI to all but admin/env users (log loudly, don't mistake for revocation bug); handlers/admin.py conflicts with T-025 (merge T-022 first, keep handlers self-contained).
- 2026-07-11 started
- 2026-07-11 alembic 0003 ai_entitlements + EntitlementRepository + DI + src/ai_access.check_ai_access; 3 gate sites swapped (ask, handle_text, voice); admin /grant_ai /revoke_ai /list_ai via T-021 registry; py_compile + import smoke OK
- 2026-07-11 verified: alembic 0001-0003 upgrade/downgrade/re-upgrade on throwaway PG; repo round-trip (perpetual/revoke/30d/extension/expiry) all pass

## Testing

### Critical
- [ ] Deploy: container start runs `alembic upgrade head` and creates `ai_entitlements` (check `\d ai_entitlements` and `alembic_version` = 0003)
- [ ] Admin (ADMIN_USER_ID) can still use /ask, voice notes and free-text routing with no grant
- [ ] Non-granted user: /ask replies ASK_NOT_ALLOWED; voice note replies ASK_NOT_ALLOWED; free text falls through to UNKNOWN_TEXT_FORMAT (no LLM call)
- [ ] `/grant_ai <uid>` (user who has done /start): reply "granted ... perpetual"; that user can immediately use /ask, voice and free-text routing
- [ ] `/revoke_ai <uid>`: access is denied again on the next /ask
- [ ] `/grant_ai <uid> 30`: reply shows expiry ~30 days out; /list_ai shows the row with @username, source and expiry
- [ ] `/grant_ai <uid> 30` again: /list_ai shows expiry extended by another 30 days (not reset)

### Important
- [ ] `/grant_ai <uid-that-never-started>`: "must /start the bot first", no row written
- [ ] `/grant_ai` with no/garbage args -> usage line; `/grant_ai <uid> 0` and negative days rejected
- [ ] `/revoke_ai <uid>` with no entitlement -> "no active AI entitlement"
- [ ] Non-admin sending /grant_ai, /revoke_ai, /list_ai gets "restricted to the bot owner"
- [ ] User in LLM_ALLOWED_USERS env (no DB row) still has AI access (fallback tier)
- [ ] Admin command menu (admin chat scope) shows grant_ai/revoke_ai/list_ai; regular users' menu does not; admin /help lists them, user /help does not
- [ ] Stop postgres briefly: non-admin /ask gets ASK_NOT_ALLOWED (fail-closed) + "failing closed" stack trace in logs; bot stays responsive; admin unaffected

### Nice-to-have
- [ ] /list_ai footer lists legacy LLM_ALLOWED_USERS ids when the env var is set
- [ ] /leave (profile deletion) cascades the ai_entitlements row (FK ON DELETE CASCADE)
- [ ] RU-language user sees Russian descriptions for the new commands in the admin menu

### Regression
- [ ] Typed transaction "coffee 4.5" still saves normally (handle_text pattern branch untouched)
- [ ] /show, /show_last, /monthly_stat unaffected
- [ ] Voice transaction confirm (vtx_yes/vtx_no) still works for a granted user
- 2026-07-11 moved to review
