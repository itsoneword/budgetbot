# Decisions (ADR-lite)

Append-only. Format: `date — decision — why — rejected alternative`. Reference from task logs where relevant.

- 2026-01-25 — Storage = PostgreSQL with repository pattern; batch-fetch then filter-in-memory in `domain/` — one/two queries per handler, business logic testable as pure functions — rejected: SQL aggregation per view (query sprawl, untestable).
- 2026-07-07 — Task tracking = file-per-task kanban in `docs/tasks/` with generated `BOARD.md`, enforced by Claude Code hooks (`scripts/tasks.py`) — deterministic updates, per-task git history, works offline — rejected: single BACKLOG.md (no per-task history, coarse hook validation); GitHub Issues (state outside the repo, network-dependent).
- 2026-07-07 — Stop hook blocks once per session then allows (sentinel file) — deterministic nudge without nagging on every turn — rejected: always-block (fires on trivial turns); advisory-only CLAUDE.md rule (forgotten after compaction).
