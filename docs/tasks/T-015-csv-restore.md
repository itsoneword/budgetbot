---
id: T-015
title: CSV download/upload restore
status: backlog
type: feature
area: bot
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-07
updated: 2026-07-07
---

## Context
Bulk-edit flow: download transactions as CSV, edit externally, re-upload. Upload has been disabled since the PostgreSQL migration.

## Acceptance
- [ ] /download exports the user's transactions as CSV
- [ ] /upload validates and restores, with clear error reporting

## Log
- 2026-07-07 created from REFACTORING Phase 5.2
