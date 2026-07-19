---
id: dv-ee06
title: Agent session plumbing: tool loop, round/timeout caps, summary context, usage logging
status: todo
priority: high
assignee: 
labels: [feature, bot]
deps: []
parent: dv-3a1c
created: 2026-07-19T15:31:19Z
updated: 2026-07-19T15:31:19Z
---

## Description

claude-agent-sdk session with custom tools replacing tools=[]. Keep compact finance summary as system context so simple aggregate questions resolve in one turn without tool calls. Cap tool-call rounds + total timeout for cost/latency; log per-turn usage via usage_meter.

## Acceptance Criteria

## Notes

## Comments
