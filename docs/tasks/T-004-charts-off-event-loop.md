---
id: T-004
title: Move chart rendering off the event loop
status: todo
type: refactor
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
src/charts.py runs matplotlib/seaborn/pandas synchronously inside async handlers; a 1-3s render blocks every other user. Currency conversion uses row-wise df.apply.

## Acceptance
- [ ] Chart generation call sites wrapped in asyncio.to_thread
- [ ] Currency conversion vectorized (no df.apply(axis=1))
- [ ] All three chart commands render correctly

## Log
- 2026-07-07 created from production-readiness P2

## Implementation plan (approved 2026-07-11)

Decisions: `asyncio.to_thread` + module-level render RLock (matches existing to_thread precedent in currency_service/whisper_local; no process pool — DataFrames would need pickling, BytesIO doesn't cross processes, renders are 1-3s). **Approved: delete the copy-pasted `show_log_chart` body inside `delete_records` (core.py:468-500)** — no early return, so it currently renders two admin usage charts on EVERY delete and sends them to whoever deleted a record; it's a bug, not a feature.

1. `src/charts.py`: `matplotlib.use("Agg")` BEFORE the pyplot import (line 7); `_render_lock = threading.RLock()` + `@_serialized_render` decorator on all 6 render functions — RLock because `make_yearly_pie_chart` calls `make_yearly_comparison_chart` (charts.py:606). pyplot's global figure registry is not thread-safe; the lock serializes renders while the event loop stays free.
2. `src/handlers/charts.py`: wrap in `asyncio.to_thread` — `monthly_pivot_chart` + `monthly_line_chart` (lines 36-37, KEEP SEQUENTIAL: both mutate the shared `data` frame in place, no gather without `.copy()`), `monthly_ext_pivot_chart` (67), `make_yearly_pie_chart` (91).
3. `src/handlers/admin.py:94-97`: wrap both `generate_usage_summary_chart` calls (log parse + render blocks too).
4. `src/core.py`: delete the orphaned block after `delete_records` (function should end at line 466); drop now-unused chart imports (lines 38-43).
5. `infrastructure/external/currency_service.py` `convert_dataframe` (262-296): replace row-wise `df.apply(axis=1)` with a per-unique-currency factor map (factor via existing `Decimal` `convert(1, c, to)` — preserves via-USD semantics + missing-rate default); `df[result] = amount * currency.map(factors)`. Delete dead `float_rates` local (charts.py:77).

Files: src/charts.py, src/handlers/charts.py, src/handlers/admin.py, src/core.py, infrastructure/external/currency_service.py.
Verify: /monthly_stat, /monthly_ext_stat, /yearly_stat, menu chart buttons, admin /show_log_chart; a delete no longer emits usage charts; converted amounts match pre-change output for a mixed-currency user.
Risks: don't parallelize the two monthly renders (shared frame); pinning Agg is required insurance against backend auto-detection.
