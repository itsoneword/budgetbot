---
id: T-028
title: Fix /download: export transactions from PostgreSQL, not stale user_data CSV
status: todo
type: bug
area: bot
priority: p1
deps: []
tags: [db]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
download_spendings (src/core.py:511) sends user_data/{id}/spendings_{id}.csv — a frozen pre-migration file; everything added since the PostgreSQL migration is missing from the export. Fix: load transactions via repositories (load_user_session or repos.transactions), render CSV in memory (or scratch temp), send as document. Also fixes convention violations: file I/O in a handler + blocking open() on the event loop. Mind /download vs admin export overlap (T-025) — same CSV renderer should serve both.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created

## Implementation plan (approved 2026-07-11)

Decision: CSV = legacy 7 columns in order (`id,timestamp,category,subcategory,amount,currency,user_id`) + `transaction_type` appended — migration parser ignores extras, and the explicit column removes the income-heuristic dependency for future T-015 restore.

1. New `domain/export.py` (pure): `render_transactions_csv(transactions) -> str` via `csv.writer` over `StringIO`; sort ascending by timestamp (repo returns DESC); use `tx.iso_timestamp` (already emits legacy `YYYY-MM-DDTHH:MM:SS`). Docstring: T-015 restore and T-025 `/admin_export` consume this format.
2. Rewrite `download_spendings` (`src/core.py:511`) in place: `repos = get_repos(context)`; `session = await load_user_session(user_id, repos, transactions_months=None)` (None skips the 12-month window → `get_latest(limit=10000)` = all tx); empty → `texts.RECORDS_NOT_FOUND_TEXT` (exists in both texts files); else `send_document(BytesIO(csv_str.encode("utf-8")), filename=f"spendings_{user_id}.csv")`. Removes stale-path read, blocking `open()`, and the handler file-I/O violation.
3. Do NOT touch `start_upload`/`receive_document` (T-015 scope). DECISIONS.md one-liner on the format.

Files: `domain/export.py` (new), `src/core.py` (~511–521 + imports), docs.
Risks: >10k tx silently truncated by get_latest limit (comment it); `str(Decimal)` scale variance (26.0 vs 26.00) — harmless to the tolerant importer.
