---
id: T-051
title: Agentic AI channel: tool-calling /ask (read tools) + recurring management (write tools)
status: doing
type: feature
area: bot
priority: p1
deps: [T-026]
tags: [ai, recurring, agentic]
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Combines T-027 with an agentic redesign of /ask (owner decision 2026-07-19) — supersedes T-027's approved flat-intent plan; build recurring management on the tool foundation instead of building intent plumbing twice. Today /ask is single-shot prompt stuffing: build_finance_summary packs ~18KB of pre-aggregated data, claude_agent.py runs claude-agent-sdk with tools=[] (T-018: model never touches DB). Fails on questions needing raw rows outside the fixed aggregates (last purchase of X beyond 92 days, 'all spendings over 100', specific dates) and cannot do writes at all. Design: give the SDK session custom tools. READ: query_transactions(period, category, subcategory, min/max amount, limit) — parameterized only, hard user_id scoping injected server-side, model never writes SQL. WRITE (recurring, from T-027): add_recurring(item, amount, day) / list_recurring / cancel_recurring(rule_ref) — every write still lands as an inline confirm tap (vrc_/rr_ buttons), the tool only STAGES the action; same guardrails as T-019/T-026 (validate via domain.recurring.validate_rule_input, pause-vs-delete decided by button, entitlement gate at entry). Keep the compact summary as system context so simple aggregate questions resolve in one turn without tool calls; cap tool-call rounds + total timeout for cost/latency; log per-turn usage (usage_meter landed 2026-07-19). Voice channel routes through the same session. See T-027 file for the superseded intent-based plan and its owner decisions (day default 1, buttons decide pause-vs-delete) — those UX decisions carry over.

## Acceptance
- [ ] TODO

## Log
- 2026-07-19 created
- 2026-07-19 started
- 2026-07-19 Foundation + wave 2 implemented via deviz board (dv-ee06/dv-f0d5/dv-82c8/dv-94bd): tool-calling ask session with query_transactions read tool, staged recurring write tools behind vrc_/rr_ confirms, voice routed through agent session with channel tags. 348 tests green, container deployed. Task detail now tracked on deviz board (board-ff8aeb03).
