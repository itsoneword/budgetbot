---
id: T-031
title: Fix /about panel: stale version, raw limit sentinel, dead settings buttons
status: done
type: bug
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-11
updated: 2026-07-19
---

## Context
All pre-existing (verified 2026-07-11): (1) version string hardcoded in texts.ABOUT (src/texts.py:111, texts_ru equivalent) says 0.2.3/18.10.25 — replace with a single VERSION constant sourced from one place and bump on release (consider wiring to CHANGELOG). (2) monthly limit displays raw 99999999 sentinel — show 'no limit' when sentinel (full sentinel cleanup stays in T-014). (3) settings keyboard buttons attached by /about do nothing — callbacks only routed inside the menu conversation states; either register a standalone CallbackQueryHandler for settings_* actions or reuse the menu path. Workaround exists (menu->settings). Run AFTER Batch B merges (texts/core.py overlap).

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created
- 2026-07-11 new finding from owner test: /about greets 'Hello, None!' — users.username/config.name never populated; fall back to update.effective_user.first_name. Also limit renders as float 4000.0 — format as int/currency
- 2026-07-11 started
- 2026-07-11 Root cause of dead buttons: create_settings_keyboard emitted change_* callback_data handled nowhere (settings handling only knows settings_*). Fixed to settings_*; in-conversation the existing menu_callback fallback now routes them with proper state transitions. Standalone ^settings_/^lang_/^cur_ handlers added AFTER spendings_handler (deviation from before-placement: before would swallow settings_* mid-conversation and break the SETTINGS_* state transitions the menu path needs); awaiting_limit flag now consumed by handle_text for out-of-conversation limit entry
- 2026-07-11 VERSION/VERSION_DATE constants in src/config.py (0.3.0 / 11.07.2026); ABOUT texts take placeholders; name falls back to Telegram first_name; limit renders via format_monthly_limit (sentinel -> localized 'no limit', no trailing .0); CHANGELOG Unreleased + project.md version row updated. core.py 608-779 is unreachable legacy menu_call copy inside handle_text (references undefined _handle_settings_about) — left alone, flagged
- 2026-07-11 moved to review

## Testing

### Critical
- [ ] /about shows "Current version is 0.3.0 from 11.07.2026" (EN) / "Текущая версия 0.3.0 от 11.07.2026" (RU)
- [ ] /about greets with the Telegram first name (no more "Hello, None!")
- [ ] /about with sentinel limit shows "no limit" / "без лимита"; with limit 4000 shows "4000" (no .0); with 4000.5 shows "4000.50"
- [ ] /about buttons work after normal usage (active conversation): change language -> language keyboard -> pick -> saved; same for currency; change limit -> type number -> saved
- [ ] Menu -> Settings path still works end-to-end (language, currency, limit, about) — regression for the fallback routing

### Important
- [ ] /about buttons work in a FRESH chat (no prior /start or transaction this session, e.g. right after bot restart): language/currency/limit flows complete via the standalone handlers
- [ ] Limit flow via /about in fresh chat: prompt -> type "abc" -> "Invalid limit" -> type "4000" -> saved (flag retained on invalid input)
- [ ] After limit prompt, sending an ordinary transaction text instead: it is treated as limit input once (known trade-off) — verify the flag clears and the next message behaves normally
- [ ] Settings-about button inside menu (settings_about) shows the same updated version/limit/name rendering

### Regression
- [ ] Voice confirm buttons (vtx_) and recurring buttons (rr) still work
- [ ] /start onboarding language/currency selection unaffected (conversation states claim lang_/cur_ first)
- [ ] Transaction category selection (cat_ buttons) unaffected
- 2026-07-19 done
- 2026-07-19 changelog: /about panel: correct version, readable limit, working settings buttons
