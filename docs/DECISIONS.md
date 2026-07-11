# Decisions (ADR-lite)

Append-only. Format: `date — decision — why — rejected alternative`. Reference from task logs where relevant.

- 2026-01-25 — Storage = PostgreSQL with repository pattern; batch-fetch then filter-in-memory in `domain/` — one/two queries per handler, business logic testable as pure functions — rejected: SQL aggregation per view (query sprawl, untestable).
- 2026-07-07 — Task tracking = file-per-task kanban in `docs/tasks/` with generated `BOARD.md`, enforced by Claude Code hooks (`scripts/tasks.py`) — deterministic updates, per-task git history, works offline — rejected: single BACKLOG.md (no per-task history, coarse hook validation); GitHub Issues (state outside the repo, network-dependent).
- 2026-07-07 — Stop hook blocks once per session then allows (sentinel file) — deterministic nudge without nagging on every turn — rejected: always-block (fires on trivial turns); advisory-only CLAUDE.md rule (forgotten after compaction).
- 2026-07-08 — AI Q&A ships as prompt-packed context (load_user_session + domain/filters summary into the LLM prompt), not text-to-SQL — per-user data is tiny and the model must not touch the DB — rejected: LLM-generated SQL (injection risk, needless complexity).
- 2026-07-08 — LLM access via provider-agnostic client in infrastructure/llm/: subscription OAuth now, OpenRouter later via config — owner already pays for a subscription and wants test runs before committing to a paid API — rejected: hardcoding one provider's SDK.
- 2026-07-08 — Voice transcription via local faster-whisper, not a cloud STT — privacy and zero per-minute cost outweigh the ~1GB image growth for a personal bot — rejected: OpenAI Whisper API (second vendor + key).
- 2026-07-09: Postgres data on ./pgdata bind mount instead of named docker volume / why: survives `down -v`, visible, one backup surface / rejected: named volume (invisible, deletable by flag).
- 2026-07-09: LLM backend = claude-agent-sdk spawning host-mounted claude CLI (subscription OAuth, credentials ro) / why: zero API cost for tests, pattern proven in claude-code-telegram / rejected: raw OAuth token against API (fragile), OpenRouter now (paid; deferred to config swap).
- 2026-07-09: Docker image python 3.9 -> 3.12 / why: claude-agent-sdk requires 3.10+ / rejected: separate LLM sidecar container (more moving parts).
- 2026-07-09: /ask gated by ADMIN_USER_ID + LLM_ALLOWED_USERS env allowlist / why: LLM runs on owner's personal subscription / rejected: open to all 72 users.

- 2026-07-09: Voice/text intent routing dispatches by synthetic Update injected through application.process_update (LLM output reduced to enum + validated payload) / reuses all existing handlers, gating and conversation states; PTB v22 Message objects are immutable so mutating .text (as core.py menu_call does) crashes / rejected: calling handlers directly (show_records reads message.text -> None on voice) and duplicating the save flow.
- 2026-07-11: Recurring transactions (T-026/T-027) built code-first as an internal action API (domain + repo) consumed by both manual handlers and the AI intent router / keeps single write path, LLM only selects validated intents / rejected: letting the LLM call scheduling directly via its own tools.
- 2026-07-11: New DB tables ship as alembic revisions with T-005 landing first (T-022=0003, T-026=0004 chained). Why: two tasks both claimed 002_*.sql (collision) and raw SQL re-creates the untracked-migration drift T-005 exists to fix. Rejected: shipping raw SQL now + converting later.
