---
id: T-038
title: LLM auth: dedicated token for container, stop sharing host OAuth credentials
status: todo
type: bug
area: infra
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-12
updated: 2026-07-12
---

## Context
Container mounts owner's ~/.claude/.credentials.json (read-only) for claude-agent-sdk; the container CLI's OAuth refresh rotates the token server-side but cannot persist it, invalidating the host's copy and killing the owner's local Claude login. Fix: dedicated token via env (candidate: claude setup-token -> CLAUDE_CODE_OAUTH_TOKEN, or ANTHROPIC_API_KEY = API billing), drop the credentials mount from docker-compose. Owner to supply the int_perp project's rotating-token pattern before implementation. Code change near zero (infrastructure/llm/claude_agent.py reads env only); mostly compose/env.

## Acceptance
- [ ] TODO

## Log
- 2026-07-12 created
