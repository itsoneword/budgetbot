---
id: dv-3ace
title: Currency API circuit breaker
status: review
priority: medium
assignee: 
labels: [ops, infra]
deps: []
parent: 
created: 2026-07-19T14:55:25Z
updated: 2026-07-19T14:55:25Z
---

## Description

Migrated from `docs/tasks/T-010-currency-circuit-breaker.md`.

infrastructure/external/currency_service.py calls open.er-api.com with a 10s timeout and no single-flight: on cache expiry concurrent users thunder; on outage each cache-miss eats the timeout.

## Acceptance Criteria

- [x] Single-flight lock around API fetch
- [x] Recent failure extends cache validity before retry
- [x] Timeout dropped to 3s

## Notes

### Log

- 2026-07-07 created from production-readiness P4

### Implementation plan (proposed 2026-07-12)

Design: `infrastructure/external/currency_service.py` has exactly one runtime call site — `src/charts.py:load_chart_data()` → `repos.currency.get_rates()`, feeding the three chart handlers in `src/handlers/charts.py`. Failures never reach users as errors today (fallback chain: memory cache 12h → DB `exchange_rates` → API → stale DB → `configs/currency_defaults.json`); the cost is latency and herding — every cache-expired request independently eats the API timeout, concurrently. Two findings change the shape of the work: (a) **aiohttp is not installed** — the "primary" async branch dead-ends at `ImportError` on line 157 and the live fetch is actually `requests` (transitive dep via yfinance) in `asyncio.to_thread` with `timeout=10`; (b) `_update_memory_cache()` stamps `_cache_time = now` even when caching *stale* DB rates, so after one degraded serve the service won't retry the API for 12h — an accidental, unbounded version of "extend cache validity". The plan: one small reusable in-memory breaker in `shared/utils/`, single-flight lock inside CurrencyService, one honest httpx fetch at 3s, and explicit data-age tracking (`rates_as_of`) so degradation is bounded and visible (stale-note caption on charts). open.er-api.com documents no rate limit in our code; publicly it's a keyless free endpoint that refreshes ~daily and asks clients to cache — so serving stale for minutes-to-hours is materially harmless. Breaker state is in-memory: T-008 (webhook/multi-replica) is backlog with an unmet dep (T-009), and the DB rates table is already the cross-process cache layer, so per-process breakers stay correct there anyway.

1. `shared/utils/circuit_breaker.py` (new, ~40 lines): `CircuitBreaker(failure_threshold=2, cooldown_seconds=900, clock=time.monotonic)` — pure sync state machine, no I/O, no decorators. API: `allow() -> bool` (side-effect-free: True when closed or cooldown elapsed — half-open probe), `record_success()` (reset), `record_failure()` (increment; at threshold, open with cooldown). Concurrent-probe safety comes from the caller's single-flight lock, not from the breaker. Export from `shared/utils/__init__.py`.
2. Replace the dual fetch in `infrastructure/external/currency_service.py`: delete `_fetch_from_api_sync` and the aiohttp/ImportError dance; one async `_fetch_from_api()` using `httpx.AsyncClient` (httpx 0.28 already ships with python-telegram-bot 22) with `timeout=3`. Keep the `result == "success"` validation and `_build_rates_from_api()` unchanged. [acceptance: timeout 3s]
3. Single-flight + breaker in `get_rates()`: add `self._flight_lock = asyncio.Lock()` and `self._breaker = CircuitBreaker(...)` in `__init__`. Flow: memory-cache fresh → return; else `async with self._flight_lock:` re-check memory cache (followers ride the leader's fetch), load DB, DB fresh → return; else if `breaker.allow()` fetch API → on success `record_success` + save/cache, on failure/exception `record_failure` and fall through to stale (DB rows → expired memory cache → `_get_default_rates()`). While the breaker is open, `get_rates()` serves the stale cache without touching the API — the cooldown *is* the "recent failure extends cache validity" window, replacing today's accidental 12h freeze. [acceptance: single-flight; failure extends validity]
4. Staleness tracking in the same file: replace the dual role of `_cache_time` with `_rates_as_of: Optional[datetime]` = API fetch time on success, `min(last_updated)` when serving DB rows, `None` for config defaults; TTL checks (`_is_cache_valid`, `_is_db_cache_valid`) key off data age, not cache-write time (fixes the stale-marked-fresh bug). Add `rates_age() -> Optional[timedelta]` for callers. Constants stay class attrs (`CACHE_TTL_HOURS = 12`, `API_TIMEOUT_SECONDS = 3`, breaker params) — no `src.config` import into infrastructure.
5. Age indicator: in `src/handlers/charts.py` (all three handlers), after `load_chart_data()` check `repos.currency.rates_age()`; if older than 48h, set `caption=texts.RATES_STALE_NOTE.format(hours=...)` on the first `InputMediaPhoto` / `send_photo` (no signature change to `load_chart_data`). Copy `RATES_STALE_NOTE` in both `src/texts.py` and `src/texts_ru.py`.
6. Tests: `tests/shared/test_circuit_breaker.py` — the breaker is pure with an injectable clock (closed→open at threshold, half-open after cooldown, reopen on probe failure, reset on success). Plain pytest, no async needed; becomes the first tenant of the T-006 harness. Add a `docs/DECISIONS.md` one-liner: breaker = in-memory per process, DB rates table is the shared layer / rejected: DB-backed breaker state (T-008 not started, needless writes).

Touched: new `shared/utils/circuit_breaker.py`, `tests/shared/test_circuit_breaker.py`; modified `infrastructure/external/currency_service.py`, `shared/utils/__init__.py`, `src/handlers/charts.py`, `src/texts.py`, `src/texts_ru.py`, `docs/DECISIONS.md`. (No DB migration, no config file changes, no requirements change — httpx is already present via PTB.)

Open questions (recommended defaults):
1. Drop the dead aiohttp branch + `requests` fallback for a single httpx fetch → yes (requests is only a transitive yfinance dep; httpx is a pinned PTB dependency).
2. Breaker tuning → threshold 2 failures, cooldown 15 min (rates update ~daily upstream; a 15-min blackout is invisible).
3. Stale-caption threshold → 48h (12h TTL + daily upstream refresh means <48h staleness is normal operation, not worth alarming users).
4. Breaker location → `shared/utils/circuit_breaker.py` (shared is the stated utils home; llm/stt clients can adopt it later).
5. Seed the pytest file now even though T-006 (harness+CI) is still todo → yes (pure module, runs standalone with bare pytest).

**Owner decisions 2026-07-12:** all planner defaults accepted (drop aiohttp/requests paths for httpx; 2-failure/15-min breaker; 48h stale caption; breaker in shared/utils; seed pytest file now).

Risks: the flight lock is held across the 3s fetch, serializing all `get_rates()` callers during a fetch — bounded at 3s and followers then hit warm cache, acceptable; `convert()` silently defaults missing rates to 1.0 (wrong conversions rather than errors) — pre-existing, out of scope, worth a follow-up task; the unused module-level `get_currency_service` singleton bypasses the DI container — left alone, but the breaker must live on the container instance (it does, single `CurrencyService` per process); per-process breaker under a future T-008 multi-replica topology means each replica probes independently — harmless (DB cache is shared; N replicas = N probes per cooldown), noted so T-008 doesn't rediscover it; `_get_default_rates()` does blocking file I/O on the event loop — pre-existing, tiny file, untouched.
- 2026-07-12 Implementation plan proposed (shared CircuitBreaker util, single-flight lock, httpx 3s fetch, rates_as_of staleness fix); found 2 pre-existing bugs (dead aiohttp branch, stale-marked-fresh cache)
- 2026-07-12 started
- 2026-07-12 Implemented: shared CircuitBreaker (2 fail/15min, injectable clock) + single-flight lock + httpx 3s fetch replacing dead aiohttp/requests paths; _rates_as_of data-age tracking + rates_age(); 48h stale caption on all 3 chart handlers (EN+RU); 8 breaker unit tests green; live API fetch verified (USDEUR 0.8755), 5 concurrent calls -> 1 fetch, breaker opens after 2 failures and still serves defaults

### Testing

Automated (already run, green): `pytest tests/shared/test_circuit_breaker.py` (8 tests); live script verified fresh API fetch, single-flight (5 concurrent get_rates -> 1 fetch), breaker opening after 2 failures while still returning a rates dict.

#### Critical
- [ ] /chart renders both monthly charts normally (fresh rates, no caption) — entry: chart command/menu
- [ ] /ext_chart and yearly piechart render normally with converted amounts matching user currency
- [ ] Charts still render when DB `exchange_rates` table is empty AND network is blocked (config-defaults path; converted amounts use fallback rates, no crash, no user-facing error)
- [ ] With network blocked (e.g. `docker network disconnect` or hosts-file block of open.er-api.com) and DB rates older than 12h: first two chart requests each add ~3s max (not 10s), third request is fast (breaker open, no API attempt)

#### Important
- [ ] Stale caption path: set `exchange_rates.last_updated` to 3 days ago (`UPDATE exchange_rates SET last_updated = now() - interval '3 days'`), block network, restart bot; chart arrives with the "rates are Nh old" caption on the first photo, in the user's language (check EN and RU users)
- [ ] After breaker cooldown (15 min) with network restored: next chart request refreshes rates and the stale caption disappears
- [ ] Two users requesting charts simultaneously right after bot restart: both get charts, only one API call in logs (single-flight)

#### Nice-to-have
- [ ] Log lines: "Fetched fresh exchange rates from API" on success; "Error fetching exchange rates from API" on blocked network; no tracebacks
- [ ] Regression: /show_last, stats and detailed reports (other currency consumers, if any) unaffected — only charts call get_rates()
- 2026-07-12 moved to review
