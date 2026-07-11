---
id: T-005
title: Adopt alembic for schema migrations
status: doing
type: ops
area: db
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-11
---

## Context
Single 001_initial_schema.sql applied only via Postgres initdb on first boot — never runs against an existing database. Schema evolution is manual psql.

## Acceptance
- [x] Alembic configured with the current schema as baseline revision
- [x] A sample migration applies cleanly to the running dev DB (verified against throwaway PG15 container; production application is the cutover runbook below — owner-run)
- [x] README/project.md 'DB change?' step updated

## Log
- 2026-07-07 created from production-readiness P6
- 2026-07-11 started
- 2026-07-11 alembic scaffold (async asyncpg env.py, baseline 0001 from idempotent SQL, sample 0002); entrypoint runs upgrade head; initdb.d mount removed; apply_schema.py stubbed; verified fresh-DB, existing-DB, downgrade, scheme-rewrite against throwaway pg15
