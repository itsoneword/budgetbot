---
id: T-038
title: LLM auth: dedicated token for container, stop sharing host OAuth credentials
status: review
type: bug
area: infra
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-21
---

## Context
Container mounts owner's ~/.claude/.credentials.json (read-only) for claude-agent-sdk. The container CLI's OAuth refresh rotates the token server-side but cannot persist it (ro mount), and — worse — because the container *holds the refresh token and attempts refreshes*, it participates in refresh-token reuse races with the other host processes that share the same credential (owner's interactive Claude Code, Devvybot). That reuse detection has caused full logouts of the owner's Claude login ~3x in the past week. Root cause is architectural: **multiple independent clients holding & refreshing one subscription OAuth.**

Decision (owner, 2026-07-12): for the current *testing* phase we stay on the Max subscription but adopt the **int_prep access-token-only pattern**, which is the safe way to share it — a service that only ever holds the short-lived access token can never trigger a refresh race. (Long-term, once real users arrive, migrate off subscription to OpenRouter/API billing — separate task.)

**Scope correction:** the earlier "code change near zero, reads env only" estimate is wrong. budgetbot's LLM backend is `claude-agent-sdk`, which spawns the `claude` CLI and *requires the full credentials.json*. Consuming only an access token means the CLI can't be used — the backend must be **rewritten to raw HTTP** (like int_prep), authenticating with the mirrored OAuth access token and impersonating Claude Code. This is a real backend rewrite, not a config tweak.

## int_prep pattern to copy (reference, already working in that project)
- Host script `~/.claude/cv-agent-secrets/refresh-token.sh` samples only the `accessToken` out of `~/.claude/.credentials.json` and atomically writes it to `~/.claude/cv-agent-secrets/anthropic-access-token` (mode 600) every ~5 min. **Reuse the existing script — do not duplicate it.** The refresh token never leaves the host.
- Compose mounts that secrets **directory** (not a single file — atomic rename must be visible) read-only into the container, int_prep uses `/run/cv-secrets:ro`.
- `_get_token()` reads the token file **on every call** (fallback to `ANTHROPIC_AUTH_TOKEN` env), so rotation needs no restart.
- If the token starts with `sk-ant-oat` → OAuth/subscription path: requests MUST impersonate Claude Code or Anthropic 429/400s them out of the subscription pool. Required: `claude-cli` user-agent, the OAuth beta header, system prompt exactly `You are Claude Code, Anthropic's official CLI for Claude.`, and the *real* system prompt smuggled inside `<instructions>…</instructions>` in the first human message. Reference impl: int_prep `src/llm/anthropic_client.py`.

## Approach
1. New raw-HTTP Anthropic backend in `infrastructure/llm/` (e.g. `oauth_http.py`) modeled on int_prep's `anthropic_client.py`: reads access token from `$LLM_TOKEN_FILE` (default `/run/cv-secrets/anthropic-access-token`) per call, fallback `ANTHROPIC_AUTH_TOKEN`; applies the Claude-Code impersonation headers + system-prompt smuggling when token is `sk-ant-oat*`. Must set an explicit model (CLI default resolution goes away) — add `LLM_MODEL` (int_prep uses a `claude-sonnet-4-x`).
2. Point `get_llm_client()` (`infrastructure/llm/__init__.py`) at the new backend; retire/relegate `claude_agent.py` (keep behind a flag if convenient, but it must no longer be the default and the creds mount goes away).
3. docker-compose: **remove** the `~/.claude` directory mount, the `claude` binary mount, and the `entrypoint.sh` credentials-symlink step. **Add** `- /home/cleversol/.claude/cv-agent-secrets:/run/cv-secrets:ro`.
4. Preserve usage telemetry: the T-0xx `usage_meter.record(...)` hook currently reads `ResultMessage.usage` from the SDK; move it to read token usage off the new HTTP response (`response.usage`) so budgetbot keeps appearing in the host LLM digest.
5. Verify both call sites still work: `/ask` (core.py) and voice intent classification (handlers/voice.py, haiku).

## Revised approach (2026-07-21, supersedes the int_prep plan above)

Dedicated long-lived `claude setup-token` in `CLAUDE_CODE_OAUTH_TOKEN` (.env), keeping the claude-agent-sdk backend unchanged. Rationale: (a) the 07-21 incident proved the shared refresh chain is winner-takes-all — the container captured the session and logged out host Claude Code/Devvy; (b) the int_prep mirror only samples the host's access token, so the bot dies whenever the host login dies — the opposite of decoupling; (c) the raw-HTTP rewrite would now also have to reimplement the T-051 agentic MCP tool loop with Claude-Code impersonation. The setup-token is static (~1-year expiry, no refresh token, nothing to race) and is the documented headless auth for CI/Docker. Yearly manual regeneration accepted. int_prep pattern kept above as the rejected alternative; API/OpenRouter migration stays deferred until bot dev settles (owner 2026-07-21).

## Acceptance
- [x] Container authenticates via CLAUDE_CODE_OAUTH_TOKEN only: no host `~/.claude` mount, no `credentials.json` in the container, entrypoint symlink step gone
- [x] SDK+CLI verified to honor the env token in isolation (empty HOME — replicates container) before rebuild
- [ ] `/ask` (agentic tool loop) and voice intent classification work from the rebuilt container
- [x] `usage_meter` telemetry still lands (backend unchanged — regression check only)
- [ ] Host `/login` session and Devvy unaffected by bot LLM traffic (no shared refresh chain; confirm over following days)

## Testing

Container is already rebuilt and running with the new auth; in-container `complete()` verified (PONG + usage row). Remaining checks are Telegram-side and time-based.

### Critical
- [ ] /ask how much did I spend this month? — answers normally (single-shot path)
- [ ] Ask AI menu → typed question needing raw rows (e.g. "when did I last buy wine?") — agentic tool loop works over the new auth (multi-turn, longer call)
- [ ] Voice message with a transaction — intent classification (haiku) works
- [ ] Host: run /login once; confirm Claude Code and Devvy work and STAY logged in over the next days while the bot keeps making LLM calls

### Important
- [ ] docker logs: no auth errors/warnings from claude CLI spawns; "LLM query done" lines present
- [ ] user_data/llm-usage.jsonl keeps accumulating rows from real /ask traffic

### Nice-to-have
- [ ] Note token expiry (~2027-07) somewhere you'll see it — e.g. a calendar reminder to re-run `claude setup-token`

## Log
- 2026-07-12 created
- 2026-07-12 owner supplied the int_prep access-token-only pattern; scoped as a raw-HTTP backend rewrite (not a config tweak) + compose mount swap. Long-term OpenRouter/API migration deferred to a separate task. Ready for implementation.
- 2026-07-21 started
- 2026-07-21 Plan revised (owner steer 2026-07-21): dedicated setup-token via CLAUDE_CODE_OAUTH_TOKEN instead of int_prep access-token mirror — mirror keeps bot coupled to host login health, and raw-HTTP rewrite would now have to reimplement the T-051 agentic MCP tool loop. Docs verified: token static, ~1yr expiry, no rotation (nothing to race), documented headless method. Compose /host-claude mount removed, entrypoint symlink replaced with env check + defensive credential cleanup, .env slot added, isolation test script prepared. Blocked on owner: run 'claude setup-token', paste into .env
- 2026-07-21 Verified: isolation test (empty HOME) PASS; container rebuilt without /host-claude mount; in-container LLM call PASS via env token only; no credentials.json materializes after calls; usage_meter row recorded. Remaining: owner TG test of /ask+voice, multi-day no-logout confirmation
- 2026-07-21 moved to review
- 2026-07-21 Owner decision: ONE shared setup-token for all headless services, single source /home/cleversol/.claude/service-secrets/claude-token.env (600) referenced via compose env_file; token removed from project .env; container re-verified (PONG). Note: setup-tokens survive host logout (generated while host login was expired) — only account-wide revocation kills them
