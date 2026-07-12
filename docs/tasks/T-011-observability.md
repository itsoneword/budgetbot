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
updated: 2026-07-12
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

## Implementation plan (proposed 2026-07-12)

Design: keep every existing `logging.getLogger(__name__)` call site untouched — structured JSON happens at the formatter layer. `setup_logging()` swaps the stdout handler's formatter for `structlog.stdlib.ProcessorFormatter` (JSONRenderer + `foreign_pre_chain` of TimeStamper(iso, utc), add_log_level, logger name, `ExtraAdder`, exc_info rendering), so all stdlib log records — handlers, repos, scheduler jobs — emit one JSON object per line to stdout with zero call-site rewrites; `app.log` stays human-readable text for eyeballing. Sentry is opt-in via `SENTRY_DSN` env: no DSN → the module never even imports `sentry_sdk` (zero overhead); with DSN → `LoggingIntegration` (INFO→breadcrumbs, ERROR→events) means the existing `global_error_handler`'s `logging.error(..., exc_info=...)` AND per-item `logger.exception(...)` inside JobQueue jobs (T-026 recurring, T-034's coming reminder sweep) all become Sentry events with no explicit `capture_exception` calls; PTB already routes uncaught job exceptions to `global_error_handler` (`update=None`), so nothing new can vanish. Health: no HTTP server exists and polling needs none — a JobQueue heartbeat job runs `SELECT 1` on the pool every 60s and touches `/tmp/budgetbot-heartbeat`; the Docker healthcheck execs a one-line python mtime check (file younger than 180s = healthy). This proves event loop alive + JobQueue running + DB reachable in one signal — exactly the three things that can die silently in a polling bot.

1. `src/logger.py`: in `setup_logging()`, replace the stdout handler's formatter with `structlog.stdlib.ProcessorFormatter(processor=JSONRenderer(), foreign_pre_chain=[merge_contextvars, add_log_level, TimeStamper(fmt="iso", utc=True), stdlib.add_logger_name, stdlib.ExtraAdder()])`; raise its non-debug level WARNING→INFO (stdout is now the primary sink for `docker logs` / the devops watcher); keep `DebugFilter`; call `structlog.configure(logger_factory=stdlib.LoggerFactory(), wrapper_class=stdlib.BoundLogger, ...)` once so future structlog-native calls share the same handlers. Handler-clearing already makes repeated `setup_logging` (the `/debug` toggle) idempotent — preserve that.
2. Same file: fix the T-003 follow-up rotation bug — `TimedRotatingFileHandler(when="m", interval=10, backupCount=5)` (~50 min retention) → `when="D", backupCount=7`.
3. `src/config.py`: add `SENTRY_DSN = os.getenv("SENTRY_DSN", "")` and `SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "prod")` following the existing env-const pattern; `requirements.txt`: add `sentry-sdk~=2.0` (no extras — the stdlib LoggingIntegration is built in).
4. New `src/observability.py`: `init_sentry() -> bool` — `if not SENTRY_DSN: logger.info("Sentry disabled (no DSN)"); return False`; lazy `import sentry_sdk` inside the branch; `sentry_sdk.init(dsn, environment=SENTRY_ENVIRONMENT, release=f"budgetbot@{VERSION}", integrations=[LoggingIntegration(level=INFO, event_level=ERROR)], send_default_pii=False, traces_sample_rate=0.0)`. Call it first thing in `core.py main()`.
5. `src/core.py global_error_handler`: pass the already-collected context as structured fields — `logging.error("Unhandled exception", exc_info=context.error, extra={"user_id": ..., "user_input": ..., "callback": ..., "job": context.job.name if context.job else None})` — so `ExtraAdder` surfaces them as JSON keys and Sentry as event extras (the f-string interpolation stays for app.log readability or is dropped; fields are the source of truth). This is the only call-site edit in the task.
6. New `src/health.py`: `HEARTBEAT_FILE = "/tmp/budgetbot-heartbeat"`; `async def heartbeat(context): await get_repos(context).pool.fetchval("SELECT 1")` then `Path(HEARTBEAT_FILE).touch()`; on exception `logger.error("Heartbeat failed: DB unreachable", exc_info=True)` and do NOT touch (stale file → unhealthy; the log line → Sentry). Module docstring notes this is a deliberate exception to the no-file-I/O rule (liveness probe, tmpfs, not user state). Register in `main()` next to the T-026 jobs: `job_queue.run_repeating(heartbeat, interval=60, first=10, name="heartbeat")`.
7. `docker-compose.yml` budgetbot service: `healthcheck: test: ["CMD", "python3", "-c", "import os,sys,time; sys.exit(0 if time.time()-os.stat('/tmp/budgetbot-heartbeat').st_mtime < 180 else 1)"], interval: 60s, timeout: 10s, retries: 3, start_period: 180s` (start_period covers alembic upgrade + slow first boot). Missing file raises → exit 1 → unhealthy, correct during crash loops.
8. Docs: `docs/architecture.md` logging section (~line 185) — describe the three sinks post-change, delete the "structlog unwired" note; `docs/DECISIONS.md` one-liners: (a) JSON logs via ProcessorFormatter at the handler, call sites stay stdlib — rejected: structlog-native rewrite of every module; (b) healthcheck = heartbeat file from a JobQueue job — rejected: embedded HTTP server (new port + dep for a single-process polling bot with no other HTTP surface). Amend the task's stale acceptance line ("Health endpoint returns 200") to the heartbeat wording. README `.env` docs: mention `SENTRY_DSN` optional.

Touched files: src/logger.py, src/config.py, src/core.py, src/observability.py (new), src/health.py (new), docker-compose.yml, requirements.txt, docs/architecture.md, docs/DECISIONS.md, README.md.

Open questions (recommended defaults):
1. Replace the "health endpoint returns 200" acceptance with heartbeat-file + exec healthcheck (no HTTP server) → yes.
2. stdout stays JSON even when `/debug` toggles verbose mode (parsers never break; humans read app.log) → yes.
3. Fix app.log rotation here to daily/7-day retention (closes the T-003 follow-up) → yes.
4. Sentry event threshold ERROR, warnings only as breadcrumbs → yes.
5. Auto-restart on unhealthy (Docker doesn't do this natively; needs autoheal or systemd) → defer to T-012 deploy hardening.
6. Actually create a Sentry project/DSN now, or ship dark until the owner makes one → ship dark.

Risks: `restart: unless-stopped` ignores health status — unhealthy is a visible signal (`docker ps`, deploy checks), not a self-heal, hence Q5; heartbeat proves loop+JobQueue+DB but not Telegram connectivity (a dead getUpdates keeps the container "healthy" — accepted, PTB retry logs + Sentry cover it); anything blocking the event loop >180s flips unhealthy — that is signal, not noise, but verify chart generation (T-004 still open) stays well under it; `LoggingIntegration` will Sentry-fy every pre-existing `logger.error` including expected ones (e.g. `/ask` LLM failures) — acceptable noise at this scale, tune with `ignore_logger` later; T-034's sweep must keep the per-item `logger.exception` pattern (a bare `except: pass` would still vanish — call this out in its review); stdout volume grows (WARNING→INFO at ~72 users: trivial); `setup_logging` runs at core.py import time before `main()` — Sentry init lands in `main()` after it, so the handful of import-time log lines predate Sentry (fine, they're INFO).
- 2026-07-12 Implementation plan proposed (JSON stdout via ProcessorFormatter, env-gated Sentry, heartbeat-file healthcheck); 6 open questions pending owner batch
