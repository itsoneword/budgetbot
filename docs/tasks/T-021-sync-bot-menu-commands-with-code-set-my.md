---
id: T-021
title: Sync bot menu commands with code (set_my_commands on startup)
status: doing
type: feature
area: bot
priority: p2
deps: []
tags: []
blocked: 
created: 2026-07-09
updated: 2026-07-11
---

## Context
Telegram menu (getMyCommands) has 14 commands, code has 22 handlers; menu was set manually via BotFather and drifts. Add set_my_commands on startup so menu is code-driven. BLOCKED on user deciding the final command list. Missing from menu today: about, change_cat, debug, delete_income, leave, monthly_ext_stat, show_cat, show_log_chart.
Extended scope (2026-07-11, supersedes archived T-024): single registry (command, handler, EN/RU description, admin_only flag) used to (a) register handlers in core.py main(), (b) render /help (src/handlers/admin.py, texts.py + texts_ru.py), (c) set_my_commands on post_init — BotCommandScopeDefault for users, BotCommandScopeChat(ADMIN_USER_ID) with admin commands included (pairs with T-025 admin panel).

## Acceptance
- [ ] Single registry `src/commands.py` drives handler registration, /help and set_my_commands
- [ ] Default menu scope shows 19 user commands incl. /ask; /cancel and /leave hidden but in /help
- [ ] Admin chat scope (BotCommandScopeChat) adds debug + show_log_chart; failure only logs a warning
- [ ] /help differs for admin vs regular users, rendered from registry in EN and RU
- [ ] ConversationHandler entry points (leave, income, upload, start, menu, change_cat) not double-registered
- [ ] setup_container still runs in post_init (wrapped with sync_bot_commands)

## Implementation plan (approved 2026-07-11)

Decisions: user menu = all non-admin commands (~19) **including /ask** (discoverability feeds T-023 paywall; non-entitled users get denial text); `/cancel` and `/leave` excluded from menu (`in_menu=False`) but stay in /help and functional; `debug` + `show_log_chart` admin-only via `BotCommandScopeChat(ADMIN_USER_ID)`.

1. New `src/commands.py` (pure data, no PTB app import): `@dataclass(frozen=True) CommandSpec(name, handler, desc_en, desc_ru, admin_only=False, in_menu=True)`. `handler=None` marks ConversationHandler entry points (`leave`, `income`, `upload`, `start`, `menu`, `change_cat`) — listed for menu/help but NOT loop-registered (double-dispatch guard). Helpers: `menu_commands(lang, include_admin) -> list[BotCommand]`, `build_help_text(texts, is_admin)`. Descriptions ≤256 chars.
2. `src/core.py` post_init: builder takes ONE callable — wrap existing `setup_container` + new `sync_bot_commands(app)` in `on_post_init` (builder line ~862). sync: `set_my_commands` default scope EN + `language_code="ru"`; admin scope `BotCommandScopeChat(ADMIN_USER_ID)` EN+RU in try/except with logged warning ("chat not found" if admin never messaged the bot — startup must not die).
3. Replace the 17 plain `CommandHandler` registrations (core.py:867-883) with a loop over `COMMANDS` skipping `handler is None`; ConversationHandler blocks untouched.
4. Help: replace stale `HELP_TEXT` with `HELP_INTRO` in `src/texts.py`/`src/texts_ru.py`; render via `build_help_text` at all 3 call sites (`src/handlers/admin.py:28` HTML mode, `src/handlers/menu.py:187`, `src/core.py:707` plain) — generated lines must be HTML-free.
5. Append registry decision to `docs/DECISIONS.md`; T-025/T-022 later add their admin commands as registry rows.

Files: `src/commands.py` (new), `src/core.py`, `src/handlers/admin.py`, `src/handlers/menu.py`, `src/texts.py`, `src/texts_ru.py`.
Risks: Telegram clients cache menus for minutes (cosmetic); keep `handler=None` convention explicit or entry-point commands double-dispatch.
Verify: `getMyCommands` for default + admin scope; /help as admin vs non-admin; all commands still dispatch.

## Log
- 2026-07-09 created
- 2026-07-11 Owner decisions 2026-07-11: debug and show_log_chart are admin-only (admin command scope + admin help). /help must differ for admin vs regular users. Menu should balance too-many/too-few; final user-facing list still pending owner confirmation of the proposed set.
- 2026-07-11 started
- 2026-07-11 commands registry + core loop + help rendering + menu sync implemented; all consistency checks pass
