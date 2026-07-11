---
id: T-029
title: Docs catch-up: changelog, roadmap M4, README; enforce changelog on task done
status: doing
type: docs
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Six months of shipped work (PostgreSQL migration, layered refactor, /ask, voice, T-001..T-020) is recorded only in git log and task files. README changelog stale since 0.2.3 (18.10.25); ROADMAP.md still marks M1 current and stops at T-019. Create docs/CHANGELOG.md (backfilled), add M4 milestone, refresh README feature section, and add a deterministic enforcement gate so the changelog cannot rot again.

## Acceptance
- [x] `docs/CHANGELOG.md` exists, backfilled from git history + done task files: one dated line per shipped task/release, newest first, covering at least the Jan 2026 PostgreSQL migration through T-020.
- [x] `scripts/tasks.py done` requires a `--changelog "one-line summary"` argument and itself appends the dated line to `docs/CHANGELOG.md` (hard gate — closing a task without a changelog entry is impossible). `--no-changelog` escape hatch for docs/meta tasks.
- [x] Backstop hook: the existing PostToolUse/stop hook machinery in `scripts/tasks.py` warns when a task file flips to `done` while `docs/CHANGELOG.md` is untouched in the working tree (fail-open, per existing hook design).
- [x] `docs/ROADMAP.md`: M1 no longer marked current; new "M4 — Monetization & automation (current)" milestone listing T-020..T-028; History section gains 2026-07 planning-wave line.
- [x] `README.md`: feature section rewritten to match today's bot (PostgreSQL, /ask AI Q&A, voice input, charts, multi-currency); stale in-README release notes replaced with a pointer to `docs/CHANGELOG.md` (old entries moved there, not deleted).
- [x] `CLAUDE.md` / `docs/project.md` task-workflow section documents the changelog convention in one line.

## Implementation plan (approved 2026-07-11)

Owner decision: enforcement via deterministic gate, not model memory — a skill/instruction can be forgotten after long context; `tasks.py done` refusing without `--changelog` cannot. Hook stays as fail-open backstop only.

1. Backfill: `git log --reverse --grep "T-0" --oneline` + `docs/tasks/` done files + README's old release notes → `docs/CHANGELOG.md` (sections: Unreleased / 2026-01 PostgreSQL migration / 2025 v0.2.x imported from README).
2. Extend `scripts/tasks.py done` (stdlib only, matching existing style): new required `--changelog` arg; append `- YYYY-MM-DD T-NNN: <line>` under Unreleased; `--no-changelog` flag logs "skipped (docs/meta)" to the task log instead.
3. Extend the existing `hook-post-tool-use`/`hook-stop` entrypoints: if any task file in the diff has `status: done` and CHANGELOG.md is not in the diff, emit a warning line (exit 0 always).
4. ROADMAP.md + README.md edits per acceptance. DECISIONS.md one-liner: changelog enforced in tasks.py done; rejected skill/hook-only (context rot).

Files: docs/CHANGELOG.md (new), scripts/tasks.py, docs/ROADMAP.md, README.md, CLAUDE.md or docs/project.md, docs/DECISIONS.md.
Conflicts: none with T-003/004/005/021/028 (docs + scripts/tasks.py only) — safe to run first/parallel in Batch A.

## Log
- 2026-07-11 created
- 2026-07-11 started
- 2026-07-11 docs/CHANGELOG.md created — backfilled from git log, done task files, README release notes (moved under original dates)
- 2026-07-11 tasks.py: done now requires --changelog (appends dated line under Unreleased) or --no-changelog; post-tool-use backstop warns on done task with untouched CHANGELOG; gate tested on throwaway T-030 and cleaned up
- 2026-07-11 ROADMAP M4 (current) + 2026-07 history line; README features rewritten, release notes moved to CHANGELOG; CLAUDE.md changelog convention line; DECISIONS entry
