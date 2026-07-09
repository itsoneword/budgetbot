---
id: T-018
title: AI Q&A over spendings (/ask)
status: done
type: feature
area: bot
priority: p2
deps: []
tags: [ai]
blocked: 
created: 2026-07-08
updated: 2026-07-09
---

## Context
Natural-language questions about the user's finances (e.g. 'how much did I spend on groceries last month?'). New handler /ask -> load_user_session + domain/filters aggregation -> compact data summary packed into prompt -> LLM answers. No text-to-SQL: per-user data is small, goes into the prompt directly; model never touches the DB. LLM client lives in infrastructure/llm/ behind a small provider-agnostic interface: initial backend uses the owner's existing Claude subscription OAuth (reference implementation from user's other projects to be provided), later swapped to OpenRouter API via config. Env-driven config, no keys in code.

## Acceptance
- [ ] TODO

## Log
- 2026-07-08 created
- 2026-07-09 started
- 2026-07-09 Implemented: infrastructure/llm/ (LLMClient ABC + ClaudeAgentClient via claude-agent-sdk, factory on LLM_BACKEND env), domain/ask_summary.py (compact prompt summary: monthly totals, category totals, month-x-category last 6mo, subcat last 92d, last 15 tx), /ask handler in core.py gated by ADMIN_USER_ID + LLM_ALLOWED_USERS env. Docker: py3.9->3.12 (SDK needs 3.10+), host claude CLI + OAuth creds mounted read-only (claude-code-telegram pattern). pydantic-settings pin relaxed (mcp conflict). Verified end-to-end in container: answers match DB exactly.
- 2026-07-09 moved to review

## Testing

### Happy Path Tests
- [ ] `/ask how much did I spend on groceries last month?` (from admin account 46304833) — returns a plain-text answer with correct amount and EUR mentioned
- [ ] `/ask сколько я потратил в мае?` with language=ru — answers in Russian
- [ ] `/ask` with no question — replies with usage example, no LLM call
- [ ] "Analyzing your data..." placeholder appears, then is edited into the answer

### Access Control
- [ ] `/ask` from a non-allowlisted account — gets the "limited testing" message, no LLM call
- [ ] Add a second ID to `LLM_ALLOWED_USERS` in .env, restart — that user can ask

### Edge Cases
- [ ] Question about data outside the 12-month window — model says data is missing rather than inventing
- [ ] Very long question (500+ chars) — no crash
- [ ] Two `/ask` requests in quick succession — both answered (each spawns its own CLI process)

### Regression
- [ ] All non-LLM commands (/show, /show_last, charts) still work after py3.9→3.12 image bump — this is the riskiest change
- [ ] Saving a transaction still works
- [ ] Container restart: bot comes up clean with CLI mounts present
- 2026-07-09 Bugfix: /ask crashed with AttributeError when the command arrived as an edited message (update.message is None on edits; PTB CommandHandler fires for both). Switched ask() to update.effective_message. Found via the T-011 error handler log — user_id and exact input were in the traceback context.
- 2026-07-09 done
- 2026-07-09 Owner confirmed /ask works in production (happy path). Remaining checklist items (edge cases, ru language, regression sweep after py3.12 bump) not individually walked — revisit if issues surface.
