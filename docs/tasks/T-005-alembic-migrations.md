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

## Implementation plan (approved 2026-07-11)

Decisions: async alembic template reusing asyncpg via `sqlalchemy[asyncio]` (no new DB driver); hand-written `op.execute()` SQL (no autogenerate — no SQLAlchemy models); baseline revision executes the existing idempotent `001_initial_schema.sql` so fresh and existing DBs both just run `alembic upgrade head` (no stamp step); migrations auto-run in entrypoint on every container start; `001_initial_schema.sql` kept frozen as source of truth. T-022 (revision 0003) and T-026 (0004) chain on top — **this task merges first**.

1. `requirements.txt`: `alembic>=1.13,<2` + `sqlalchemy[asyncio]>=2.0,<3` (asyncpg already present).
2. `alembic.ini` at repo root: `script_location = infrastructure/database/alembic`, empty url. `env.py` (async template): URL from `DATABASE_URL` env / `infrastructure/database/connection.py` default, rewrite `postgresql://` → `postgresql+asyncpg://`; `target_metadata = None`. Stock `script.py.mako`.
3. `versions/0001_baseline.py`: reads and executes `001_initial_schema.sql` via `Path(__file__)`-relative path (works at /app in Docker); `downgrade()` raises NotImplementedError. Add FROZEN header comment to the .sql.
4. `versions/0002_sample.py`: harmless reversible change (`COMMENT ON TABLE migration_log`); verify `upgrade head` / `downgrade -1` against dev DB.
5. Docker: `Dockerfile` add `COPY alembic.ini /app/`; `entrypoint.sh` run `alembic upgrade head` (cd /app) before run.py (`set -e` aborts on failure); `docker-compose.yml` remove the `migrations:/docker-entrypoint-initdb.d` mount — alembic is the sole schema path incl. first boot.
6. `scripts/apply_schema.py` → 3-line stub pointing at alembic. Docs: `project.md` (add-a-feature step 1, quick start), `architecture.md` (§3 layout, §11 deploy), `DECISIONS.md` one-liner.
7. Cutover runbook: pg_dump backup FIRST (no T-007 backups exist); optional `pg_dump --schema-only` drift diff vs 001; then normal `docker compose up -d --build` — baseline no-ops, `alembic_version` created.

Risks: forgotten DSN scheme rewrite fails only inside the container (test there, not just venv); broken migration + `restart: unless-stopped` = crash loop (make alembic output loud); manual psql drift untracked (diff in runbook).
