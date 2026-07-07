# Roadmap

Milestones reference task IDs in `docs/tasks/`. Live status is in the task files and `docs/tasks/BOARD.md` — this file records direction, not state.

## M1 — Hygiene (current)

Fix the known bugs left over from the Jan 2026 PostgreSQL migration.

- T-001 Fix admin check (int vs str) — B1
- T-002 Standardize package-qualified imports — B2
- T-003 Replace print() with logger — B3

## M2 — Production hardening

From personal use to 1k+ users: performance, reliability, operability. Source analysis: `docs/production-readiness.md`.

- T-004 Chart rendering off the event loop — P2
- T-005 Alembic schema migrations — P6
- T-006 Unit tests for domain/ + CI gating — T1, O2
- T-007 Automated Postgres backups — O3
- T-008 Webhook mode + horizontal scaling — P1
- T-009 Durable conversation state — P3
- T-010 Currency API circuit breaker — P4
- T-011 Observability: structured logs, Sentry, health check — O1
- T-012 Deploy hardening: prod compose overlay, secrets — O4, O5

## M3 — Features (Phase 5 of docs/REFACTORING.md)

- T-013 Soft delete and recovery — D1
- T-014 Data-model cleanups (limit sentinel, timezone, enums, category language) — D2–D5
- T-015 CSV download/upload restore
- T-016 Analytics events table
- T-017 Web UI / API layer

## History

- 2026-01: CSV → PostgreSQL migration + layered architecture refactor (`docs/REFACTORING.md`)
- 2025: v0.2.x feature releases (inline menus, multi-transactions, charts)
