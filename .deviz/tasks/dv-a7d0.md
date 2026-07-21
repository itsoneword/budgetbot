---
id: dv-a7d0
title: Epic: horizontal scaling — durable shared state, then webhook mode
status: todo
priority: medium
assignee:
labels: [backlog, feature, deploy]
deps: []
parent:
created: 2026-07-21T11:40:47Z
updated: 2026-07-21T11:40:47Z
---

## Description

Groups dv-86de (durable conversation state) and dv-8a83 (webhook mode + LB replicas) into one architectural change in two phases: webhook-behind-LB is pointless without shared state, and dv-8a83 already depends on dv-86de. Phase 1: move context.user_data off the in-process dict to a durable shared store. Phase 2: run_polling -> webhook behind a load balancer with replicas. Board-restructure decision 2026-07-21.

## Acceptance Criteria

## Notes
