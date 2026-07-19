---
id: dv-ee06
title: Agent session plumbing: tool loop, round/timeout caps, summary context, usage logging
status: done
priority: high
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T15:31:19Z
updated: 2026-07-19T17:32:56Z
---

## Description

claude-agent-sdk session with custom tools replacing tools=[]. Keep compact finance summary as system context so simple aggregate questions resolve in one turn without tool calls. Cap tool-call rounds + total timeout for cost/latency; log per-turn usage via usage_meter.

## Acceptance Criteria

## Notes

## Notes

### Implementation plan (plan agent, 2026-07-19)

Verified against installed claude-agent-sdk 0.1.81: @tool + create_sdk_mcp_server + ClaudeAgentOptions(mcp_servers, allowed_tools=["mcp__finance__<tool>"], tools=[] disables built-ins). query() with string prompt DOES support SDK MCP servers in 0.1.81 (README stale; fallback = ClaudeSDKClient runner; pin SDK version). max_turns caps tool rounds; AssistantMessage.usage + .model feed usage_meter.record per turn (ResultMessage cumulative only as fallback — avoid double count).

1. infrastructure/llm/base.py: ToolSpec dataclass (name, description, input_schema, async handler->str), ToolInputError (message surfaced to model as is_error result), non-abstract complete_with_tools default raising LLMError. complete() untouched (voice/scheduler call sites preserved). Tools passed per call, never stored — get_llm_client() is lru_cached/shared.
2. infrastructure/llm/claude_agent.py: shared runner; complete_with_tools wraps ToolSpecs into SDK tools (ToolInputError -> is_error; unexpected exceptions -> generic "tool failed", never leak internals), permission_mode="dontAsk", DEFAULT_MAX_TOOL_TURNS=8 (env ASK_MAX_TOOL_TURNS), 120s wall clock kept (env ASK_TIMEOUT_SECONDS). On max-turns/budget exhaustion with usable text: return accumulated text, don't raise; LLMError only when nothing usable.
3. domain/ask_summary.py: build_ask_system_prompt(language, tools_enabled=False) — when True, append guidance: answer from summary when it suffices (keeps simple questions one-turn/zero tools); call query_transactions only for raw rows/filters; at most a few calls.
4. src/core.py answer_ask_question: ~4 lines — complete_with_tools(prompt, system(tools_enabled=True), tools=build_ask_toolspecs(session)). Entitlement gate, empty-data early return, thinking message, interaction log unchanged.

Sizing: rows default 20 / cap 200 / ~8KB formatted cap / counts+totals always over full match set pre-truncation.

Defaults accepted: per-turn usage JSONL rows (row count != ask count); 20/200/8KB limits; in-memory filter over session (no SQL surface at all) instead of new repo method.

Risks: SDK upgrade regressing query()-MCP path; max_turns too low truncates (graceful text return, tune from logs); usage double-count (check host report once after deploy); 10k-row get_latest cap inherited from summary path (accepted).

## Comments

### @claude — 2026-07-19T16:39:55Z

Session plumbing landed: ToolSpec/ToolInputError + complete_with_tools default in llm/base.py; claude_agent.py shared _run loop with per-turn usage recording (ResultMessage fallback only), SDK MCP finance server, dontAsk, max_turns env-capped, graceful partial-text return on turn exhaustion; build_ask_system_prompt tools_enabled flag; core.py answer_ask_question switched to complete_with_tools. AgentToolContext shape defined in src/ask_agent_tools.py for dv-82c8.

### @claude — 2026-07-19T16:46:23Z

Foundation committed (d848341), 310 tests green. Container rebuilding for owner manual verification. Wave 2 (dv-82c8 + dv-94bd) starting in parallel worktrees.

### @claude — 2026-07-19T17:25:56Z

VERIFY (owner): 1) latency of a simple question comparable to before. 2) adversarial: /ask list every transaction one by one -> stops at turn cap with usable partial answer, not ASK_ERROR. 3) user_data/llm-usage.jsonl: one row per model turn on a multi-tool question, totals not doubled.

### @itsoneword — 2026-07-19T17:32:34Z

seems to be working . and working pretty good even for complex tasks:
Всего по категории alcohol найдено 266 транзакций на общую сумму 2778.50 EUR — это слишком много для одного сообщения в чате.

Вот помесячные итоги (все — категория alcohol, субкатегории: beer, wine, alco, cocktails):

2023-05: 129, 06: 261, 07: 68, 08: 185, 09: 124, 10: 169, 11: 146, 12: 100
2024-01: 47, 02: 163, 03: 101, 04: 103, 05: 62, 06: 121, 07: 73.5, 08: 35, 09: 49, 10: 74, 11: 52, 12: 25
2025-01: 55, 02: 12, 04: 23, 05: 7, 06: 20, 07: 18, 08: 52, 09: 70, 10: 55, 11: 62, 12: 50
2026-02: 12, 04: 34, 05: 69, 06: 114, 07: 38

Итого: 2778.50 EUR

Если нужен полный построчный список — скажи период (например «последние 3 месяца» или «2026»), и я выведу все строки с датами и субкатегориями.
...!
