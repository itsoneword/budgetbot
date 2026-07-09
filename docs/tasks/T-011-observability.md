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
updated: 2026-07-09
---

## Context
File logs only (app.log + user_log.csv); structlog is in requirements but unwired; no error aggregation; no liveness signal for Docker.

## Acceptance
- [ ] structlog JSON to stdout wired through src/logger
- [ ] Sentry (or equivalent) receives handler exceptions
- [ ] Health endpoint returns 200 when DB pool reachable; wired into docker-compose healthcheck

## Log
- 2026-07-07 created from production-readiness O1
- 2026-07-09 Scope narrowed per owner 2026-07-09: proper logging + PTB error handler only. NO in-bot owner notifications — external devops agent will watch logs and report. Sentry optional/deferred.
- 2026-07-09 Added global PTB error handler (core.py): logs full traceback + user_id/input/callback context to app.log and stdout, replies with localized ERROR_PROCESSING_REQUEST. 'No error handlers registered' warning gone. Remaining scope: structured logs, health check.
