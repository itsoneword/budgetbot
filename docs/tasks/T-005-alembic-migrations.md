---
id: T-005
title: Adopt alembic for schema migrations
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
Single 001_initial_schema.sql applied only via Postgres initdb on first boot — never runs against an existing database. Schema evolution is manual psql.

## Acceptance
- [ ] Alembic configured with the current schema as baseline revision
- [ ] A sample migration applies cleanly to the running dev DB
- [ ] README/project.md 'DB change?' step updated

## Log
- 2026-07-07 created from production-readiness P6
