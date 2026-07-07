---
id: T-008
title: Webhook mode + horizontal scaling path
status: backlog
type: feature
area: deploy
priority: p2
deps: [T-009]
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
run_polling() in core.py is single-instance by Telegram's design: SPOF and no scale-out. Webhooks behind a load balancer allow replicas; requires durable shared state first (T-009).

## Acceptance
- [ ] run_webhook behind reverse proxy works in prod
- [ ] Multi-replica topology documented

## Log
- 2026-07-07 created from production-readiness P1
