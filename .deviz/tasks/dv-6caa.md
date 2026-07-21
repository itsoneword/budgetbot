---
id: dv-6caa
title: Deploy hardening: prod compose overlay + secrets
status: todo
priority: medium
assignee: 
labels: [backlog, ops, deploy]
deps: []
parent: 
created: 2026-07-19T14:55:41Z
updated: 2026-07-19T14:55:41Z
---

## Description

Migrated from `docs/tasks/T-012-deploy-hardening.md`.

docker-compose.yml exposes Postgres 5432 publicly (dev convenience); secrets are gitignored files. Prod needs an overlay without the port and a defined secrets story.

## Acceptance Criteria

- [ ] docker-compose.prod.yml overlay without exposed DB port
- [ ] Secrets handling documented (env injection or manager)
- [ ] deploy.sh updated for the overlay

## Notes

### Implementation plan (proposed 2026-07-21)

Design: This host is simultaneously dev and prod — the live stack (`budgetbot-postgres`, `budgetbot-container`) runs straight out of this working tree via `docker compose up -d --build` (README.md, docs/architecture.md), and `docker ps`/`ss` confirm Postgres is publicly bound **right now** (`0.0.0.0:5432->5432`); note Docker publishes ports via its own iptables chain, so a host firewall would not have protected it anyway. Postgres is the only port publisher in this repo's compose file — the bot uses long-polling and publishes nothing. Three findings shape the work: (a) an overlay cannot *remove* a `ports:` mapping by omission (compose merges lists), but Compose v2.24+ supports `!reset` and the host runs 2.40.3, so `docker-compose.prod.yml` can genuinely null the mapping; belt-and-braces, the base mapping should also shrink to `127.0.0.1:5432:5432`, which keeps every documented dev workflow working (scripts/verify_postgres.py, run-outside-Docker via `localhost:5432`) while never exposing the DB even when someone runs bare `docker compose up`. (b) Secrets today are two-tier: the shared Claude setup-token already lives in the single-source host file `/home/cleversol/.claude/service-secrets/claude-token.env` (600, T-038 / DECISIONS.md 2026-07-21), while budgetbot-specific secrets (`API_KEY`, `POSTGRES_PASSWORD`, `ADMIN_USER_ID`, `DATABASE_URL`) sit in the repo-local gitignored `./.env` (600). The T-038-consistent story is to move the budgetbot secrets to `/home/cleversol/.claude/service-secrets/budgetbot.env` — same directory, same 600-perm env-file convention, one secrets home per host, survives re-clone/`git clean -xdf` — referenced twice: `--env-file` on the compose command (compose-file `${POSTGRES_PASSWORD}` interpolation does **not** read service `env_file:` entries) and `env_file:` on the budgetbot service (container injection). (c) `deploy.sh` is a stale v1 draft (commit 517e263 "v1 draft for ref"): it references image `budgetbot_v2`, raw `docker run` without Postgres, Docker Hub multi-arch pushes, and `source .env` — none of which matches the compose deployment; it is even listed in `.gitignore` while being git-tracked. The acceptance item "deploy.sh updated for the overlay" is best met by rewriting it as a thin compose wrapper that encodes the prod file/env-file incantation so the owner never types it. No secret manager: single self-hosted box, O5 explicitly blesses env-file injection at this scale.

1. `docker-compose.yml`: change the postgres mapping to `- "127.0.0.1:5432:5432"` (comment: host-loopback for dev psql/scripts; prod overlay removes it entirely). On the budgetbot service, mark the repo-local env file optional so prod can run without it: `env_file:` entry `{path: .env, required: false}` (long syntax, Compose ≥2.24) alongside the existing absolute-path claude-token.env entry.
2. `docker-compose.prod.yml` (new, ~15 lines): overlay only — `services.postgres.ports: !reset []`, and `services.budgetbot.env_file:` adding `/home/cleversol/.claude/service-secrets/budgetbot.env`. Nothing else is duplicated; base file stays the single source for volumes/healthchecks.
3. Secrets migration (manual host step, documented in the deploy doc, not in git): copy the current `./.env` keys (`API_KEY`, `POSTGRES_PASSWORD`, `ADMIN_USER_ID` — drop `DATABASE_URL`, compose already overrides it) to `/home/cleversol/.claude/service-secrets/budgetbot.env`, `chmod 600`. Keep `./.env` in place for dev/outside-Docker runs.
4. `deploy.sh`: replace the v1 draft wholesale with a ~40-line wrapper: default action = prod deploy (`docker compose --env-file /home/cleversol/.claude/service-secrets/budgetbot.env -f docker-compose.yml -f docker-compose.prod.yml up -d --build`), preflight checks that the secrets file exists and is 600, then waits for `budgetbot-container` health = healthy (the T-011 heartbeat healthcheck, `start_period` 180s) and prints the last 20 log lines; `--dev` flag = plain `docker compose up -d --build`; `--config` flag = print the merged `docker compose ... config` for eyeballing. Remove the stale `deploy.sh` line from `.gitignore` (the file is tracked; the ignore entry is a lie).
5. Docs: README.md — replace the deploy paragraph (also fix the stale line 57 claim that AI features need "credentials mounted"; T-038 moved auth to the setup-token env file) with dev vs prod (`./deploy.sh`) commands; docs/project.md quick-start gets the same split; docs/production-readiness.md O4/O5 marked resolved with a pointer here; docs/DECISIONS.md one-liner: prod = compose overlay with `!reset` ports + all host secrets under `~/.claude/service-secrets/` (env-file injection) / rejected: secret manager (single box, overkill), Docker secrets (swarm-oriented, bot reads env).
6. Verification: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config | grep -A3 ports` shows no published port for postgres; `./deploy.sh` then `docker ps` shows no `5432->` mapping and `ss -tln | grep 5432` is empty on the host; from an external machine `nc -vz <host> 5432` times out; bot still boots: container reaches `healthy` (proves event loop + JobQueue + `SELECT 1` against postgres over the compose network), logs show `alembic upgrade head` + polling start, and a live `/about` round-trip in Telegram answers. Dev regression: `./deploy.sh --dev` re-exposes 5432 on loopback only and `python3 scripts/verify_postgres.py` still connects.

Touched: new `docker-compose.prod.yml`; modified `docker-compose.yml`, `deploy.sh` (rewrite), `.gitignore`, `README.md`, `docs/project.md`, `docs/production-readiness.md`, `docs/DECISIONS.md`; host-only (not in git) `/home/cleversol/.claude/service-secrets/budgetbot.env`. (No code, image, or migration changes — entrypoint.sh and src/config.py already read plain env vars.)

Open questions (recommended defaults):
1. Move budgetbot's own secrets to `/home/cleversol/.claude/service-secrets/budgetbot.env`, or keep them in the repo-local `./.env` and only document it? → move (consistent with the T-038 single-secrets-home decision; survives re-clone/`git clean`; `./.env` stays as the dev copy).
2. Keep a loopback `127.0.0.1:5432` binding in the base file for dev? → yes (scripts and outside-Docker runs use `localhost:5432`; loopback is unreachable externally, and prod overlay `!reset`s it anyway).
3. Rewrite deploy.sh from scratch, discarding the v1 Docker Hub / multi-arch / raw-`docker run` flows? → yes (they target a pre-compose, pre-Postgres image named `budgetbot_v2` and cannot work against today's stack; git history keeps the draft).

Risks: the sharpest edge is muscle memory — a bare `docker compose up -d` (without the overlay) still works but silently skips the prod hardening; mitigation is that the base file now binds loopback-only, so the worst case is 127.0.0.1 exposure, not public, and deploy.sh becomes the documented path. If the compose CLI on the host were ever downgraded below 2.24, `!reset` and `required: false` would parse-fail loudly at `config` time (fail-closed, acceptable; host has 2.40.3). Moving `POSTGRES_PASSWORD` interpolation to `--env-file` means running the prod overlay *without* that flag would fall back to `budgetbot_dev_pass`, which won't match the initialized `./pgdata` password — the bot then fails its healthcheck immediately rather than corrupting anything (Postgres only reads `POSTGRES_PASSWORD` at first init). Host-level listeners outside this repo (0.0.0.0:2222, netdata 19999, nginx 80/443) were observed during the port audit but belong to other services — noted so they aren't mistaken for BudgetBot's; a separate host-hardening pass may be worth its own task.

### Log

- 2026-07-07 created from production-readiness O4 + O5
- 2026-07-21 Implementation plan proposed (loopback base binding + !reset prod overlay, secrets to ~/.claude/service-secrets/budgetbot.env, deploy.sh rewritten as compose wrapper; 3 open questions batched to owner). Found: Postgres publicly bound on 0.0.0.0:5432 right now.
