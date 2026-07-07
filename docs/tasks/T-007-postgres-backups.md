---
id: T-007
title: Automated Postgres backups
status: todo
type: ops
area: db
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Postgres data lives in a Docker volume with no backup automation — volume corruption means total loss.

## Acceptance
- [ ] Scheduled pg_dump (daily) with retention to off-box storage
- [ ] Restore procedure documented and tested once

## Log
- 2026-07-07 created from production-readiness O3
