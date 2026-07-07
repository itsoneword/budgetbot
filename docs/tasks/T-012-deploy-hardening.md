---
id: T-012
title: Deploy hardening: prod compose overlay + secrets
status: backlog
type: ops
area: deploy
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
docker-compose.yml exposes Postgres 5432 publicly (dev convenience); secrets are gitignored files. Prod needs an overlay without the port and a defined secrets story.

## Acceptance
- [ ] docker-compose.prod.yml overlay without exposed DB port
- [ ] Secrets handling documented (env injection or manager)
- [ ] deploy.sh updated for the overlay

## Log
- 2026-07-07 created from production-readiness O4 + O5
