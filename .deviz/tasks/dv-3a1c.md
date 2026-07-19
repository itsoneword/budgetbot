---
id: dv-3a1c
title: Agentic AI channel: tool-calling /ask (read tools) + recurring management (write tools)
status: done
priority: high
assignee: 
labels: [feature, bot]
deps: [dv-9219]
parent: 
created: 2026-07-19T14:55:32Z
updated: 2026-07-19T17:33:52Z
---

## Description

Migrated from `docs/tasks/T-051-agentic-ai-channel-tool-calling-ask-read.md`.

Combines T-027 with an agentic redesign of /ask (owner decision 2026-07-19) — supersedes T-027's approved flat-intent plan; build recurring management on the tool foundation instead of building intent plumbing twice. Today /ask is single-shot prompt stuffing: build_finance_summary packs ~18KB of pre-aggregated data, claude_agent.py runs claude-agent-sdk with tools=[] (T-018: model never touches DB). Fails on questions needing raw rows outside the fixed aggregates (last purchase of X beyond 92 days, 'all spendings over 100', specific dates) and cannot do writes at all. Design: give the SDK session custom tools. READ: query_transactions(period, category, subcategory, min/max amount, limit) — parameterized only, hard user_id scoping injected server-side, model never writes SQL. WRITE (recurring, from T-027): add_recurring(item, amount, day) / list_recurring / cancel_recurring(rule_ref) — every write still lands as an inline confirm tap (vrc_/rr_ buttons), the tool only STAGES the action; same guardrails as T-019/T-026 (validate via domain.recurring.validate_rule_input, pause-vs-delete decided by button, entitlement gate at entry). Keep the compact summary as system context so simple aggregate questions resolve in one turn without tool calls; cap tool-call rounds + total timeout for cost/latency; log per-turn usage (usage_meter landed 2026-07-19). Voice channel routes through the same session. See T-027 file for the superseded intent-based plan and its owner decisions (day default 1, buttons decide pause-vs-delete) — those UX decisions carry over.

## Acceptance Criteria

- [x] /ask answers raw-row questions the fixed aggregates can't (specific dates, amount filters, full multi-year history) via query_transactions — see dv-f0d5
- [x] Recurring rules manageable through /ask and voice; every write staged behind an inline confirm tap, never auto-applied — see dv-82c8
- [x] Simple aggregate questions still resolve in one turn (compact summary as system context); tool rounds and total time capped; per-turn usage logged — see dv-ee06
- [x] Voice channel routes through the same agent session with the same guardrails — see dv-94bd

## Notes

### Log

- 2026-07-19 created

## Comments

### @claude — 2026-07-19T15:46:14Z

Planning wave started: 3 parallel plan agents — (1) dv-ee06+dv-f0d5 foundation unit, (2) dv-82c8 write tools, (3) dv-94bd voice routing. Implementation order: foundation first, then write tools + voice in parallel worktrees.

### @claude — 2026-07-19T17:33:52Z

All four subtasks implemented, owner-verified 2026-07-19, done. Follow-ups living elsewhere: dv-2cf1 (spoken yes + conversational fallthrough, rebases on the new intent prompt), dv-2615 (dedicated LLM token).
