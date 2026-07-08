---
id: T-018
title: AI Q&A over spendings (/ask)
status: backlog
type: feature
area: bot
priority: p2
deps: []
tags: [ai]
blocked: 
created: 2026-07-08
updated: 2026-07-08
---

## Context
Natural-language questions about the user's finances (e.g. 'how much did I spend on groceries last month?'). New handler /ask -> load_user_session + domain/filters aggregation -> compact data summary packed into prompt -> LLM answers. No text-to-SQL: per-user data is small, goes into the prompt directly; model never touches the DB. LLM client lives in infrastructure/llm/ behind a small provider-agnostic interface: initial backend uses the owner's existing Claude subscription OAuth (reference implementation from user's other projects to be provided), later swapped to OpenRouter API via config. Env-driven config, no keys in code.

## Acceptance
- [ ] TODO

## Log
- 2026-07-08 created
