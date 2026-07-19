---
id: dv-94bd
title: Voice channel routes through the same agent session
status: done
priority: medium
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T15:31:19Z
updated: 2026-07-19T17:32:58Z
---

## Description

Voice questions get the same read/write tools as typed /ask; keep T-019 guardrails. Related: dv-2cf1 ('yes' confirms pending proposal).

## Acceptance Criteria

## Notes

## Notes

### Implementation plan (plan agent, 2026-07-19)

Key insight: voice questions already funnel into answer_ask_question (src/core.py:689) via synthetic "/ask" injection — once dv-ee06 lands, voice gets the agent session almost free. Thin routing/UX layer.

1. src/handlers/voice.py + src/core.py: add channel="ask" param to answer_ask_question, thread into repos.interactions.add and usage logging; INTENT_QUESTION branch calls answer_ask_question(..., channel="voice") directly instead of _inject_text("/ask ..."). OWNER DECISION 2026-07-19: keep transcript echo + separate answer message (two messages), do NOT merge into one edited status message. Injection for show_stat/set_reminder/transactions unchanged.
2. domain/intent.py: extend `question` intent examples so recurring/subscription phrases ("add rent 800 every month", "cancel Netflix") classify as question -> agent stages via dv-82c8 vrc_ buttons. No new intent kind. Agent receives classifier payload (not verbatim transcript) — default accepted.
3. Keep haiku intent triage as-is ("coffee 4.50" must not pay agent cost); only `question` reaches the agent. INTENT_UNKNOWN dead-end stays — fallthrough-to-agent belongs to dv-2cf1.

Coordination: land dv-94bd BEFORE dv-2cf1 (both edit build_intent_system_prompt; dv-2cf1 rebases). Agent-staged writes must log ai_interactions outcome=proposed so dv-2cf1 spoken-yes can see them; dv-2cf1 decides if spoken-yes covers vrc_.

Risks: STT-garbled text staging wrong rules (contained: stage-only + confirm shows what saves); latency (triage keeps most voice off agent; ee06 caps); question-intent examples could steal "rent 800" one-off tx — test boundary phrases both ways.

Tests: voice raw-row question -> query_transactions answer; voice "add rent 800 every month" -> vrc_ confirm; one-turn summary answer latency; channel="voice" in ai_interactions; T-019 regressions (vtx_ flow, /show_last, paywall, LLM-down, vfix_).

## Comments

### @claude — 2026-07-19T16:58:14Z

Implemented in worktree commit 67545bf: answer_ask_question channel param, voice INTENT_QUESTION calls agent directly (transcript echo kept, two messages), recurring/subscription prompt examples + one-off boundary. 317 tests green.

### @claude — 2026-07-19T17:08:10Z

Merged to main, 317 tests green. Voice + typed free-text questions now call the agent session directly with channel tags (voice/text). Needs container rebuild + manual voice test — will batch with dv-82c8 merge. Deviation: typed free-text questions also route direct (channel=text), behaviorally identical, better telemetry.

### @claude — 2026-07-19T17:25:56Z

VERIFY (owner): 1) voice question -> transcript echo + agent answer (two messages, as decided). 2) voice add rent 800 every month -> vrc_ confirm flow. 3) BOUNDARY: plain rent 800 (typed and voice) still parses as one-off transaction, NOT recurring. 4) voice coffee 4.50 -> normal vtx_ confirm, no agent session. 5) ai_interactions rows show channel=voice / text correctly.

### @itsoneword — 2026-07-19T17:32:48Z

seems to be working.
