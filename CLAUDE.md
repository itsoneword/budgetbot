# BudgetBot

Telegram bot for personal finance tracking. Python + python-telegram-bot (async), PostgreSQL via asyncpg, Docker Compose. Layered: `src/` (handlers) → `domain/` (pure logic) → `infrastructure/` (repositories, DB, external APIs); `shared/` (DI container, utils). Entry point: `run.py`.

## Start here

- A task-board brief is injected at session start (SessionStart hook). Full board: `docs/tasks/BOARD.md`. Pick work with `python3 scripts/tasks.py next`.
- Direction and milestones: `docs/ROADMAP.md`. Architecture deep-dive: `docs/architecture.md`. Conventions and how-to-add-a-feature: `docs/project.md`.
- Cross-task decisions go to `docs/DECISIONS.md` as an appended dated one-liner: decision / why / rejected alternative.

## Task workflow (enforced by hooks in .claude/settings.json)

- Tasks are files `docs/tasks/T-NNN-slug.md` managed by `python3 scripts/tasks.py` (`new` / `start` / `log` / `review` / `done` / `next` / `board` / `validate` / `archive`).
- `BOARD.md` is generated — never edit it by hand. On a merge conflict in it: take either side, then run `python3 scripts/tasks.py board`.
- Log progress when an acceptance checkbox flips, not only at session end: `python3 scripts/tasks.py log T-NNN "what changed"`. This bounds context loss from interrupted sessions.
- `review` status means: generate a manual-testing checklist per `.claude/instructions/post_implementation_testing.md` and append it under a `## Testing` section in the task file.
- Commit messages for task work: `T-NNN: subject`. Find a task's commits with `git log --grep T-NNN`.
- Closing a task requires a changelog line: `done T-NNN --changelog "one-line summary"` appends it to `docs/CHANGELOG.md` under Unreleased (`--no-changelog` only for docs/meta tasks).

## Code conventions (details in docs/project.md)

- All handlers are async; repository calls must be awaited. User IDs are `int` — never stringify.
- No file I/O in handlers — all persistent state goes through `infrastructure/repositories/`.
- Load user data once per handler via `load_user_session()` (domain/session_loader.py), then filter in memory with `domain/filters.py`. Don't sprinkle repo queries through a handler.
- Business logic lives in `domain/` as pure functions — no I/O, no Telegram types.
- User-facing copy goes to both `src/texts.py` and `src/texts_ru.py`.
