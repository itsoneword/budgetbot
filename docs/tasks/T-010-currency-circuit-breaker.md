---
id: T-010
title: Currency API circuit breaker
status: todo
type: ops
area: infra
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
infrastructure/external/currency_service.py calls open.er-api.com with a 10s timeout and no single-flight: on cache expiry concurrent users thunder; on outage each cache-miss eats the timeout.

## Acceptance
- [ ] Single-flight lock around API fetch
- [ ] Recent failure extends cache validity before retry
- [ ] Timeout dropped to 3s

## Log
- 2026-07-07 created from production-readiness P4
