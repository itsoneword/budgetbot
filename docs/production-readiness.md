# Production-Readiness Assessment

> Target: support **1k–10k concurrent users** with high reliability. Current state: works for personal use; several blockers and gaps for that scale.
> This is a gap analysis, not a ticket list. Each item has: **what / why it matters / suggested approach**.

## Scoring summary

| Area | Status | Verdict |
|---|---|---|
| Core data layer | 🟢 Solid | Async pool, repos, indexes — fine for target scale |
| Architecture / separation of concerns | 🟢 Solid | Layered design, DI, batch-fetch pattern |
| Bot deployment topology | 🟠 Blocker | Single-replica polling won't scale; no graceful shutdown |
| Sync/CPU work in event loop | 🟠 Blocker | Charts and pandas operations block all users |
| Security & auth | 🔴 Bug | Admin check is broken; no rate limiting |
| Observability | 🟠 Gap | File logs only, no metrics/tracing/Sentry |
| Testing | 🔴 Gap | One integration script; no unit tests, no CI gating |
| Migrations | 🟠 Gap | Single raw .sql file; no framework for schema evolution |
| Backup / DR | 🟠 Gap | No automated PG backups |
| Data integrity | 🟡 Minor | Hard delete only; sentinel `99999999.00` for "no limit" |

🟢 acceptable · 🟡 minor · 🟠 blocker for scale · 🔴 ship-stopper bug

---

## 🔴 Bugs to fix immediately

### B1. Admin check is dead code (always denies)

**Where:** `src/core.py:183`, `src/handlers/admin.py:82`
```python
if user_id != "46304833":   # user_id is now int, "46304833" is str
    await update.message.reply_text("Sorry, only admin users can toggle debug mode.")
    return TRANSACTION
```

**Problem:** During the migration, `user_id` was changed from `str` to `int` everywhere, but the literal compare-target stayed as a string. `int != str` is always `True` in Python 3. **Every user — including the actual admin — is denied.** Conversely, if someone removes the check thinking it's broken, all users become admins.

**Fix:**
```python
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "46304833"))
...
if user_id != ADMIN_USER_ID:
    ...
```
Move the constant to env to avoid hardcoding it in source.

### B2. Bare `language_util` import works only because of `sys.path` manipulation

**Where:** `src/core.py:3` and a few sibling modules: `from language_util import …` (no `src.` prefix).

**Why it works today:** `run.py` does `sys.path.insert(0, src/)`.

**Why it's fragile:** Inconsistent with the rest of the codebase (`from src.handlers ...`), breaks if `run.py` is bypassed (e.g., running a script in tests, or migrating to an entry-point in `pyproject.toml`).

**Fix:** Standardize on package-qualified imports throughout. Update `run.py` to add only the project root to `sys.path` and import everything as `src.*`.

### B3. `print()` calls escape into the runtime logger

**Where:** `shared/di/bot_integration.py:29,40` and migration scripts.

**Why it matters:** `print` writes unstructured text to stdout, bypassing the logging configuration. In production these lines lose context (no timestamps, no request IDs, no level filtering) and can't be silenced.

**Fix:** Replace with `log_debug` / `logger.info`.

---

## 🟠 Blockers for 1k–10k users

### P1. Single-instance long-polling

**Today:** `application.run_polling()` in `core.py:982`. Telegram lets exactly one client poll for updates per token. There is no horizontal scaling path.

**At 10k users:**
- Long-polling itself is fine (Telegram only sends events for active users), but a single Python process becomes a hot spot for CPU work and a SPOF.
- Any handler that takes seconds (chart rendering, currency-API call, slow query) blocks **every other user** because `python-telegram-bot` runs handlers concurrently in a thread pool, but matplotlib + pandas often hold the GIL.

**Fix path (in order of effort):**
1. **Switch to webhooks** with `application.run_webhook()` behind a load balancer + multiple replicas (Telegram supports multi-replica fan-in via webhook).
2. **Move CPU work off the event loop**: wrap chart generation in `asyncio.to_thread(...)` (cheapest possible win — see P2).
3. **Add a worker queue** (e.g., RQ / arq / Celery + Redis) for chart rendering and CSV exports if step 2 isn't enough.
4. **Sticky sessions per user** are not required because all state lives in PG / `context.user_data`, but `context.user_data` is in-process — see P3.

### P2. Synchronous CPU work in async handlers

**Where:** `src/charts.py` — every chart calls matplotlib synchronously (`plt.savefig`, seaborn pivot, pandas pivot). Currency conversion uses `df.apply(axis=1)` which is row-wise Python.

**Impact:** A 200-DPI matplotlib render for a heavy user can take 1–3 seconds, during which the whole event loop pauses in CPython if those calls release the GIL inconsistently.

**Fix (lowest cost):**
```python
async def send_chart(update, context):
    ...
    image_bytes = await asyncio.to_thread(monthly_pivot_chart, session)
    await update.message.reply_photo(image_bytes)
```
This moves the CPU work to PTB's worker thread and frees the event loop. No code restructuring beyond wrapping the call sites.

For the currency `df.apply` hot path: vectorize. Build a `Series` of rates by mapping `currency_col`, then compute `df.amount / rate * target_rate` in one shot. Eliminates Python-level row iteration.

### P3. `context.user_data` is per-process and not durable

**Today:** Conversation state (current category, in-flight transaction, edit cursor) lives in `context.user_data`, which is a regular dict on the bot replica.

**Impact at scale:**
- Restart drops in-flight conversations.
- Two replicas can't share state, so users must stick to one replica.
- `detailed_transactions.py` stores filtered transaction lists in `user_data` — a power user with many transactions consumes RAM until they finish browsing.

**Fix path:**
- Use PTB's persistence backends (`PicklePersistence` for single-replica reboots; `Application(persistence=...)` with a custom Redis-backed store for multi-replica).
- Stop caching transaction lists in `user_data`; re-query on pagination using the indexes already in place.

### P4. No backoff / circuit breaker around the currency API

**Where:** `infrastructure/external/currency_service.py` calls `open.er-api.com` with a 10s timeout. On API outage, every cache-miss path takes 10s before falling back.

**At scale:** First user after the 12h cache expires triggers the fetch; concurrent users wait or thunder. If the API is down, all of them eat the timeout.

**Fix:**
- Add a single-flight lock around `_fetch_from_api` so only one request is in flight per process.
- Treat a recent fetch failure as "use cache for another N minutes" before retrying.
- Drop the 10s timeout to 3s — the API responds in <500ms when healthy.

### P5. `load_user_session` loads up to 12 months of transactions per request

**Where:** `domain/session_loader.py` — every read handler invokes this. The "batch fetch" architecture is correct, but the default window is generous.

**At 10k users with 5+ years of history per power user:** memory pressure and per-request bytes-shipped grow linearly.

**Fix:**
- Most handlers only need 2 months. Pass `transactions_months=2` explicitly where that's true (already done in `show_detailed`).
- Add `load_minimal_session` use-cases anywhere a handler doesn't need transactions at all (settings change, /help, /about).
- Consider an LRU per-user session cache with 60s TTL keyed on `(user_id, last_tx_id)` — eliminates the round-trip when the same user pages through screens.

### P6. No DB migration framework

**Today:** One `001_initial_schema.sql`, mounted by Postgres' initdb mechanism. Works for first boot, **does not run on existing databases**. Adding a column later means manual `psql` work.

**Fix:** Adopt `alembic` (works fine with asyncpg via `sqlalchemy[asyncio]` for the alembic side, while runtime stays raw asyncpg). Migrations become `alembic revision --autogenerate` + `alembic upgrade head` in CI/CD.

---

## 🟠 Operability gaps

### O1. Observability

| | Current | Needed |
|---|---|---|
| App logs | File-based (`app.log`), TimedRotatingFileHandler | Structured JSON to stdout (`structlog` is in `requirements.txt` but not wired) — let the orchestrator (Docker, K8s) collect |
| User events | CSV row to `user_log.csv` | Move to a `user_events` table; `user_log.csv` doesn't survive a container rebuild |
| Errors | Logged | Aggregate to Sentry (or similar) — at 10k users you'll never see exceptions in raw logs |
| Metrics | None | At minimum: request count, P50/P95/P99 handler latency, DB pool utilization, currency-API success rate. Prometheus + grafana, or a hosted equivalent |
| Health check | None | `GET /health` returning 200 if DB pool reachable, used by docker / k8s liveness |

### O2. CI/CD

- `.github/workflows/` exists but content unknown. At minimum:
  - Run `python3 -m py_compile` over all source (smoke test).
  - Run `scripts/test_repositories.py` against an ephemeral Postgres.
  - Build and tag Docker image on `main`.
- No automated tests beyond `test_repositories.py`. See T1 below.

### O3. Backups

- Postgres data lives in a Docker volume. **No backup automation.** A volume-corruption bug = total data loss.
- Add `pg_dump` to S3/Backblaze on a schedule (daily full + WAL streaming, or just daily full at this scale).

### O4. Postgres exposed publicly

`docker-compose.yml`:
```yaml
ports:
  - "5432:5432"  # Expose for local development; remove in production
```
Comment acknowledges it. Keep two compose files (`docker-compose.yml` for dev, `docker-compose.prod.yml` overlay) so the prod variant doesn't expose the port.

### O5. Secrets management

- `configs/config` (token) and `.env` (Postgres password) are file-based and gitignored. Fine for self-hosted single-server deployment.
- For multi-replica or staged environments, move to a secret manager (Doppler, 1Password CLI, Hashicorp Vault, or just AWS Secrets Manager / GCP Secret Manager).

---

## 🟠 Testing gaps (T)

### T1. No unit test suite

**Today:** `scripts/test_repositories.py` is an integration smoke test, not a test suite. There are no tests for `domain/filters.py`, no tests for the parser in `save_transaction.py`, no tests for currency conversion edge cases.

**Why this is dangerous at scale:** The current architecture is well-suited for testing — `domain/` is pure functions, repositories are stubbable. Skipping tests now means every refactor risks regression.

**Recommended starting set:**
1. `tests/domain/test_filters.py` — every filter and aggregation function. Pure-Python, no fixtures needed.
2. `tests/domain/test_session_loader.py` — repos mocked.
3. `tests/parsers/test_save_transaction.py` — multi-line input, ambiguous categories, edge currencies.
4. `tests/integration/test_repositories.py` — keep current integration script, run against an ephemeral PG container.

Use `pytest` + `pytest-asyncio`. Aim for `domain/` at 90%+ coverage before adding 1k users.

### T2. No load test

Before you onboard real volume, run a synthetic load test (e.g., `locust`) hitting the bot via Telegram's test environment, simulating 100/500/1000 concurrent users sending mixed transaction-add and chart-view loads. Watch DB pool saturation, P99 latency, and memory.

---

## 🟡 Data integrity / domain quality

### D1. Hard delete

`/leave` cascades a full delete via the `users` FK. There's no recovery path, no audit log, no soft delete. REFACTORING.md Phase 5.1 already calls this out.

**Fix:** Add `deleted_at TIMESTAMPTZ` to `transactions` and `users`. Filter `deleted_at IS NULL` everywhere. Add a periodic job that hard-deletes records older than N days.

### D2. `monthly_limit` sentinel

Default is `99999999.00` to signal "no limit." Should be `NULL`, with the UI/business logic treating NULL as "unlimited." The sentinel will eventually surface in some report, confusing users.

### D3. Per-language category dictionaries don't migrate

`user_categories` has a `language` column. If a user starts in English, accumulates 50 categories, then switches to Russian, **they get an empty dictionary** in the new language. Either:
- Translate on switch (UX-driven), or
- Make the dictionary language-agnostic (`language` column on transactions, not on categories).

### D4. `transaction_type VARCHAR(10)` should be an enum

Today: a `CHECK (transaction_type IN ('spending', 'income'))`. PG enum would give type safety + smaller storage. Low priority.

### D5. No timezone per user

Everything stored and rendered in UTC. A user in Bangkok seeing a transaction logged at "11pm yesterday" in their local time will see it as today's 4pm UTC. Add `timezone` to `user_configs` (default `UTC`); convert at display time.

---

## Recommended sequencing

If you want a concrete order to tackle this in:

1. **Today (1 day)** — fix B1, B2, B3 (broken admin check, import inconsistency, print→logger). Wrap chart calls in `asyncio.to_thread` (P2). Add a `health` endpoint (O1).
2. **This week** — Adopt alembic (P6). Move structlog to JSON stdout. Add Sentry. Set up daily PG backups.
3. **Before 1k users** — Tests for `domain/` (T1). Webhook mode + persistence backend (P1, P3). Single-flight currency fetch (P4). Load test (T2).
4. **Before 10k users** — Worker queue for charts/exports if needed (P1.3). Per-user session cache (P5). Per-user timezone (D5). Soft delete (D1).

---

## What you already have that's *good* and shouldn't change

A migration this big often produces architectural debt. This one didn't:

- **Layered design holds**: handlers don't talk to PG; domain doesn't talk to anything but in-memory data; infrastructure doesn't know about Telegram. This is exactly right.
- **Repository pattern is consistent**: every data access goes through one repo method. Easy to mock, easy to grep.
- **Schema is well-indexed**: the `date_trunc_month` immutable function trick is clever — keeps month-bucketed queries indexable.
- **Connection pooling is set up correctly**: asyncpg's pool with min=2/max=10 is reasonable for this workload; tune up to 20 once you're past 1k concurrent.
- **Currency conversion is decently cached**: 3-layer cache (in-memory → DB → API → fallback file) is already production-shaped.
- **DI container is minimal but real**: just enough indirection to make swapping a fake pool in tests easy, no framework astronomy.

The migration left the code in good shape. The remaining work is operational hardening, not architectural cleanup.
