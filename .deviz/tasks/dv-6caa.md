---
id: dv-6caa
title: Deploy hardening: prod compose overlay + secrets
status: todo
priority: medium
assignee: 
labels: [backlog, ops, deploy]
deps: []
parent: 
created: 2026-07-19T14:55:41Z
updated: 2026-07-19T14:55:41Z
---

## Description

Migrated from `docs/tasks/T-012-deploy-hardening.md`.

docker-compose.yml exposes Postgres 5432 publicly (dev convenience); secrets are gitignored files. Prod needs an overlay without the port and a defined secrets story.

## Acceptance Criteria

- [ ] docker-compose.prod.yml overlay without exposed DB port
- [ ] Secrets handling documented (env injection or manager)
- [ ] deploy.sh updated for the overlay

## Notes

### Log

- 2026-07-07 created from production-readiness O4 + O5
