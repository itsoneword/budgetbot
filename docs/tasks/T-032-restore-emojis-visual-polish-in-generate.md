---
id: T-032
title: Restore emojis/visual polish in generated /help and menu command descriptions
status: done
type: feature
area: bot
priority: p3
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-19
---

## Context
T-021's generated help is deliberately HTML-free (one call site renders HTML, two plain) but lost the old HELP_TEXT emojis. Add emojis to CommandSpec descriptions in src/commands.py (safe in BotCommand descriptions and plain text; e.g. chart commands get a chart emoji) and light section structure to build_help_text, EN+RU. Owner feedback 2026-07-11: menu descriptions ('comments') should carry emojis where visually meaningful, not necessarily all. Run AFTER Batch B merges (commands.py/texts overlap).

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
- 2026-07-11 started
- 2026-07-11 Emojis added to 16 command descriptions (EN+RU identically); CommandSpec gains section field + HELP_SECTIONS (Tracking/Stats/Settings/Admin, admin_only always maps to admin section); build_help_text groups by section with blank line + emoji title, still plain-text/HTML-free; import guard extended: 256-char cap + unknown-section check; HELP_INTRO refreshed both languages (typed-entry example incl. dd.mm backdating, dropped 'Available commands:' trailer). All 4 variants render, guard passes, max 2217 chars
- 2026-07-11 moved to review

## Testing

### Critical
- [ ] /help (regular user, EN): sections 💸 Tracking / 📊 Stats / ⚙️ Settings render with emojis, no raw HTML or entities visible
- [ ] /help (admin): additionally shows 🛠 Admin section with all 8 admin commands
- [ ] /help in RU: same structure with Учёт/Статистика/Настройки/Админ titles
- [ ] menu -> Help button (plain-text render path) shows the same structured text without artifacts
- [ ] Bot restarts cleanly: import-time guard passes, sync_bot_commands syncs the menu (check startup log "Synced 20 user commands")

### Important
- [ ] Telegram command menu (the / picker) shows emoji-prefixed descriptions in EN and RU scopes
- [ ] Admin chat scope menu includes admin commands (28 entries)
- [ ] No description truncated in the Telegram menu (all under 256 chars)

### Regression
- [ ] /help via voice/free-text routing still renders
- [ ] Commands themselves still dispatch (registry loop registration unchanged — spot-check /show, /about)
- 2026-07-19 done
- 2026-07-19 changelog: Restored emoji/visual polish in /help and menu descriptions
