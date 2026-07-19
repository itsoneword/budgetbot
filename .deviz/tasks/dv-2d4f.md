---
id: dv-2d4f
title: Sync bot menu commands with code (set_my_commands on startup)
status: done
priority: medium
assignee: 
labels: [feature, bot]
deps: []
parent: 
created: 2026-07-19T15:01:13Z
updated: 2026-07-19T15:01:13Z
---

## Description

Migrated from `docs/tasks/T-021-sync-bot-menu-commands-with-code-set-my.md`.

Telegram menu (getMyCommands) has 14 commands, code has 22 handlers; menu was set manually via BotFather and drifts. Add set_my_commands on startup so menu is code-driven. BLOCKED on user deciding the final command list. Missing from menu today: about, change_cat, debug, delete_income, leave, monthly_ext_stat, show_cat, show_log_chart.
Extended scope (2026-07-11, supersedes archived T-024): single registry (command, handler, EN/RU description, admin_only flag) used to (a) register handlers in core.py main(), (b) render /help (src/handlers/admin.py, texts.py + texts_ru.py), (c) set_my_commands on post_init — BotCommandScopeDefault for users, BotCommandScopeChat(ADMIN_USER_ID) with admin commands included (pairs with T-025 admin panel).

## Acceptance Criteria

- [x] Single registry `src/commands.py` drives handler registration, /help and set_my_commands
- [x] Default menu scope shows 19 user commands incl. /ask; /cancel and /leave hidden but in /help
- [x] Admin chat scope (BotCommandScopeChat) adds debug + show_log_chart; failure only logs a warning
- [x] /help differs for admin vs regular users, rendered from registry in EN and RU
- [x] ConversationHandler entry points (leave, income, upload, start, menu, change_cat) not double-registered
- [x] setup_container still runs in post_init (wrapped with sync_bot_commands)

## Notes

### Implementation plan (approved 2026-07-11)

Decisions: user menu = all non-admin commands (~19) **including /ask** (discoverability feeds T-023 paywall; non-entitled users get denial text); `/cancel` and `/leave` excluded from menu (`in_menu=False`) but stay in /help and functional; `debug` + `show_log_chart` admin-only via `BotCommandScopeChat(ADMIN_USER_ID)`.

1. New `src/commands.py` (pure data, no PTB app import): `@dataclass(frozen=True) CommandSpec(name, handler, desc_en, desc_ru, admin_only=False, in_menu=True)`. `handler=None` marks ConversationHandler entry points (`leave`, `income`, `upload`, `start`, `menu`, `change_cat`) — listed for menu/help but NOT loop-registered (double-dispatch guard). Helpers: `menu_commands(lang, include_admin) -> list[BotCommand]`, `build_help_text(texts, is_admin)`. Descriptions ≤256 chars.
2. `src/core.py` post_init: builder takes ONE callable — wrap existing `setup_container` + new `sync_bot_commands(app)` in `on_post_init` (builder line ~862). sync: `set_my_commands` default scope EN + `language_code="ru"`; admin scope `BotCommandScopeChat(ADMIN_USER_ID)` EN+RU in try/except with logged warning ("chat not found" if admin never messaged the bot — startup must not die).
3. Replace the 17 plain `CommandHandler` registrations (core.py:867-883) with a loop over `COMMANDS` skipping `handler is None`; ConversationHandler blocks untouched.
4. Help: replace stale `HELP_TEXT` with `HELP_INTRO` in `src/texts.py`/`src/texts_ru.py`; render via `build_help_text` at all 3 call sites (`src/handlers/admin.py:28` HTML mode, `src/handlers/menu.py:187`, `src/core.py:707` plain) — generated lines must be HTML-free.
5. Append registry decision to `docs/DECISIONS.md`; T-025/T-022 later add their admin commands as registry rows.

Files: `src/commands.py` (new), `src/core.py`, `src/handlers/admin.py`, `src/handlers/menu.py`, `src/texts.py`, `src/texts_ru.py`.
Risks: Telegram clients cache menus for minutes (cosmetic); keep `handler=None` convention explicit or entry-point commands double-dispatch.
Verify: `getMyCommands` for default + admin scope; /help as admin vs non-admin; all commands still dispatch.

### Testing

#### Critical
- [ ] Bot starts cleanly: post_init logs "[OK] Database container initialized" AND "Synced 19 user commands to the default menu scope"
- [ ] getMyCommands (or the client menu button) shows exactly 19 commands for a regular user; /cancel, /leave, /debug, /show_log_chart absent
- [ ] In the admin chat, the menu additionally shows /debug and /show_log_chart (21 total)
- [ ] Telegram client with RU interface language shows Russian descriptions in the menu
- [ ] /help as regular user: 21 lines (19 menu + /cancel + /leave), no /debug or /show_log_chart, no visible HTML tags
- [ ] /help as admin: same list plus /debug and /show_log_chart at the end
- [ ] /help in RU profile language renders Russian intro + descriptions
- [ ] Each ConversationHandler entry point fires exactly ONCE per message: /start, /menu, /change_cat, /income, /upload, /leave (watch for duplicate replies = double dispatch)
- [ ] Plain commands still dispatch: /show, /show_last, /show_ext, /delete, /ask, /download, /about, /cancel

#### Important
- [ ] Menu > Help button (menu_help callback) renders the same generated help text without HTML errors, then returns to main menu (both call sites: core.py menu_call and handlers/menu.py)
- [ ] Startup with ADMIN_USER_ID pointing to a chat that never messaged the bot: only a warning in logs, bot keeps running
- [ ] Startup with ADMIN_USER_ID=0/unset: admin scope skipped, no error
- [ ] /debug and /show_log_chart still work for admin and still refuse non-admin users (runtime gate unchanged)

#### Nice-to-have
- [ ] Menu updates visible without reinstalling the client (Telegram caches command lists for a few minutes)
- [ ] Command descriptions read well truncated in the compact client menu

### Log

- 2026-07-09 created
- 2026-07-11 Owner decisions 2026-07-11: debug and show_log_chart are admin-only (admin command scope + admin help). /help must differ for admin vs regular users. Menu should balance too-many/too-few; final user-facing list still pending owner confirmation of the proposed set.
- 2026-07-11 started
- 2026-07-11 commands registry + core loop + help rendering + menu sync implemented; all consistency checks pass
- 2026-07-11 moved to review
- 2026-07-11 acceptance boxes checked (static verification); Testing checklist appended; moved to review
- 2026-07-19 done
- 2026-07-19 changelog: Bot menu commands synced from code registry on startup (21 commands)
