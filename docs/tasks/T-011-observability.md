---
id: T-011
title: Observability: structured logs, Sentry, health check
status: todo
type: ops
area: obs
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
File logs only (app.log + user_log.csv); structlog is in requirements but unwired; no error aggregation; no liveness signal for Docker.

## Acceptance
- [ ] structlog JSON to stdout wired through src/logger
- [ ] Sentry (or equivalent) receives handler exceptions
- [ ] Health endpoint returns 200 when DB pool reachable; wired into docker-compose healthcheck

## Log
- 2026-07-07 created from production-readiness O1
