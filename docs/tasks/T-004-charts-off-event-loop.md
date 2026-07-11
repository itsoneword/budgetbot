---
id: T-004
title: Move chart rendering off the event loop
status: review
type: refactor
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-11
---

## Context
src/charts.py runs matplotlib/seaborn/pandas synchronously inside async handlers; a 1-3s render blocks every other user. Currency conversion uses row-wise df.apply.

## Acceptance
- [x] Chart generation call sites wrapped in asyncio.to_thread
- [x] Currency conversion vectorized (no df.apply(axis=1))
- [ ] All three chart commands render correctly (needs manual verification — see Testing)

## Log
- 2026-07-07 created from production-readiness P2
- 2026-07-11 started
- 2026-07-11 Agg backend + RLock-serialized renders in charts.py; all chart call sites (handlers/charts.py, handlers/admin.py) via asyncio.to_thread; convert_dataframe vectorized (per-currency Decimal factor, verified allclose 1e-12 vs old row-wise); deleted live-but-orphaned show_log_chart copy from core.py delete_records + unused chart imports
- 2026-07-11 moved to review

## Testing

Automated (done): py_compile on all 5 touched files; scratchpad equivalence test — vectorized convert_dataframe vs old row-wise on 5000 mixed-currency rows incl. missing-rate currency, allclose rtol=1e-12 for EUR/USD/RSD/unknown targets (max rel diff 3.7e-16); off-main-thread render harness — monthly_pivot_chart and make_yearly_pie_chart (2 years, exercises RLock re-entry into make_yearly_comparison_chart) produced valid PNGs via asyncio.to_thread on Agg.

### Critical
- [ ] /monthly_chart (send_chart) sends pivot heatmap + stacked area chart, values look sane
- [ ] /monthly_ext_chart (send_ext_chart) sends subcategory heatmap
- [ ] /yearly_chart (send_yearly_piechart) sends pie chart(s); with >1 year of data also two comparison bar charts
- [ ] /delete <id> deletes the record and replies with confirmation only — no usage-summary charts are sent afterwards (orphaned block removed)
- [ ] Mixed-currency user: converted totals in charts match pre-change values

### Important
- [ ] Bot stays responsive during a chart render: send /monthly_chart, immediately send a text transaction from another account — it should be processed without waiting for the render
- [ ] Two users request charts simultaneously — both receive correct, non-corrupted images (lock serialization)
- [ ] User with no transactions gets NO_DATA / NO_YEARLY_DATA message, no crash
- [ ] Admin /show_log_chart sends both usage summaries (30d + 1y)
- [ ] /delete with non-numeric arg replies INVALID_RECORD_NUM; /delete for missing id replies NOT_ENOUGH_RECORDS

### Nice-to-have
- [ ] Currency with no stored rate falls back to 1.0 conversion (unchanged behavior)
- [ ] /delete_income path behaves same as /delete
