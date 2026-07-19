---
id: T-044
title: Menu UX: edit-in-place navigation, stop stacking new messages on submenu actions
status: todo
type: bug
area: bot
priority: p1
deps: []
tags: []
blocked: 
created: 2026-07-19
updated: 2026-07-19
---

## Context
Owner repro 2026-07-19 (screenshot, Ask AI button): tapping a main-menu item leaves the old menu message in place, sends the response as a NEW message (buy offer), then sends a THIRD 'Returning to main menu' message with a duplicate keyboard — 3 stacked messages per tap. Wanted: Telegram-native edit-in-place — the tapped menu message edits into the submenu/response with a Back button, Back edits it back to the main menu; no new messages, no 'Returning to main menu' text. Scope: audit ALL menu_call branches (handlers/menu.py) for which edit vs send; the Ask AI branch (T-023 amendment used send_ai_offer + _return_to_main_menu) is the worst case but the pattern is likely systemic. Constraint: flows that must send something new (invoice, charts, transaction entry prompts that expect typed input) stay as sends but should not ALSO re-send the menu.

## Acceptance
- [ ] Every main-menu tap mutates the tapped message only (edit-in-place); no "Returning to main menu." duplicates anywhere
- [ ] Ask AI, Help, About, summaries, detailed stats render as edits of the anchor with a Back button; Back restores the menu in place (incl. on stale keyboards outside a conversation)
- [ ] Media/invoice/typed-input flows send what they must but never re-send the menu; charts callback-context crash (update.message None) fixed
- [ ] Dead-end submenus (recurring, reminder, tz picker via menu) gain Back rows; command paths unchanged

## Log
- 2026-07-19 created

## Implementation plan (approved 2026-07-19, from research agent — recommended defaults accepted)

### Repro reconstruction (verified in code)

The Ask-AI 3-message stack (`src/handlers/menu.py:235-246`, non-entitled path): (1) `menu_ask_ai` never edits the tapped message — old main menu stays live; (2) `send_ai_offer` (`payments.py:42-53`) replies via `effective_message` → offer arrives as a NEW message; (3) `_return_to_main_menu` (`menu.py:360-369`) sends "Returning to main menu." + duplicate keyboard. Entitled path stacks 2. Systemic: every `_return_to_main_menu` caller stacks because the helper sends instead of edits.

Branch audit — STACK (bad): show_monthly_summary / show_last_month_summary / show_income_stats (3-4 msgs: stale "Loading…" edit + records send via `records.py:98` + possible LIMIT_EXCEEDED + menu), show_extended_stats / show_last_month_extended_stats (`core.py:286` send), show_monthly_charts / show_yearly_charts (stale "Generating…" + media + menu; PLUS latent crash: `charts.py:71,125,148,152` use `update.message.reply_text` — None in callback context), menu_ask_ai, menu_help, settings_about, cancel_transaction (sleep(1) + new menu). CLEAN (already edit-in-place): menu_add_transaction, menu_add_income, menu_add_spending, menu_show_transactions, menu_recurring, menu_reminder, menu_settings, back_to_main_menu, settings_* leaves, edit_* branches, show_last_transactions. Caveats: menu_recurring/menu_reminder/settings_timezone views are dead ends (no Back row); `detailed_transactions.py:60-62` double-edit overwrites NO_CATEGORIES_FOUND instantly. Routing confirmed: all taps land in menu_call (core.py:855-858 in-conversation, :967 fallback, :1023 ^settings_). The correct pattern to generalize: menu_show_transactions + back_to_transactions_menu (`detailed_transactions.py:461-472`).

### Design

One navigation anchor: the tapped menu message. Every `menu_call` branch either (a) edits the anchor into the submenu/response with a Back button (→ back_to_main_menu, or → menu_settings for settings leaves), or (b) for flows that must send something new — media groups, Stars invoices, typed-input prompts — edits the anchor into a minimal state and never re-sends the menu. Text responses (summaries, detailed stats, help, about, AI how-to, AI offer) become edits of the anchor; media flows edit the anchor back to the main menu after sending, so exactly one menu keyboard exists at all times. `_return_to_main_menu` is deleted. All edits go through `_safe_edit` (swallows Telegram "Message is not modified" BadRequest — double-tap protection). `send_ai_offer`'s effective_message contract for /ask and voice-denial message contexts is preserved via an extracted `(text, keyboard)` builder both paths share.

### Steps

1. `src/handlers/menu.py`: add `_safe_edit(query, text, **kwargs)` (ignore BadRequest containing "not modified", re-raise others) and `_edit_to_main_menu(query, texts)` (edits anchor to MAIN_MENU_TEXT + main-menu keyboard, returns TRANSACTION). Delete `_return_to_main_menu`. Single `query.answer()` at top of `menu_call`; remove scattered per-branch answers.
2. `src/handlers/menu.py`: add `_back_kb(texts, cb="back_to_main_menu")` one-row InlineKeyboardMarkup with `texts.BACK_BUTTON`.
3. `src/handlers/records.py`: extract `build_records_report(update, context, tx_type) -> str | None` from `show_records` (records text + LIMIT_EXCEEDED block appended when applicable; None when no records). `show_records` delegates — command path unchanged.
4. `menu.py` show_monthly_summary/show_last_month_summary/show_income_stats: drop Loading-edit-then-send-then-menu; `_safe_edit(query, text or RECORDS_NOT_FOUND_TEXT, reply_markup=_back_kb, parse_mode=HTML)`. If len(text) > 4096 → fall back to send + `_edit_to_main_menu` (no duplicate menu).
5. `src/core.py`: extract `build_detailed_report(update, context, period) -> str` from `show_detailed` (command path keeps sending). `menu.py` show_extended_stats/show_last_month_extended_stats: edit anchor + _back_kb, same 4096 fallback.
6. `menu.py` show_monthly_charts/show_yearly_charts: keep edit-to-"Generating…", keep media send, replace `_return_to_main_menu` with `_edit_to_main_menu` (menu ends up above photos — accepted default). `charts.py:71,99,125,148,152`: `update.message.reply_text` → `update.effective_message.reply_text` (fixes callback crash); chart senders return True if media sent; menu branch edits anchor to NO_DATA text + Back on empty.
7. `src/handlers/payments.py`: extract `build_ai_offer(texts, include_back=False) -> (text, InlineKeyboardMarkup)` (Buy row; + Back row when include_back). `send_ai_offer` uses it (no back), keeps `effective_message.reply_text` — /ask and voice-denial contexts unchanged.
8. `menu.py` menu_ask_ai: entitled → `_safe_edit(AI_HOWTO, _back_kb)`; non-entitled → `_safe_edit(*build_ai_offer(texts, include_back=True))`. No offer send, no menu re-send. Buy tap still → buy_ai_callback → invoice as new message (unavoidable); anchor keeps Back.
9. `menu.py` menu_help: edit anchor to help text + _back_kb. settings_about: edit to ABOUT + `_back_kb(cb="menu_settings")` (Back returns to Settings — accepted default).
10. `menu.py` cancel_transaction: single `_safe_edit` to TRANSACTION_CANCELED + "\n\n" + MAIN_MENU_TEXT with main-menu keyboard; delete sleep(1), reply_text, unused asyncio import.
11. Dead ends: `recurring.py build_rules_view`, `reminders.py build_reminder_view`/`build_tz_keyboard` gain optional `back_cb: str | None = None` appending a Back row; menu passes back_to_main_menu (tz picker: menu_settings); command paths unchanged.
12. `core.py` after spendings_handler (next to ^settings_ at :1023): `CallbackQueryHandler(menu_call, pattern="^back_to_main_menu$")` — Back works on stale keyboards outside conversations.
13. `src/detailed_transactions.py:60-62`: merge double-edit — one edit with NO_CATEGORIES_FOUND + "\n\n" + SHOW_TRANSACTIONS_MENU_TEXT + transactions keyboard.
14. texts/texts_ru: remove now-unused BACK_TO_MAIN_MENU. Also add Back rows to typed-input prompts (menu_add_income, settings_change_limit, edit_add_remove_category) — fallback already routes back_to_main_menu safely (accepted default).
15. Tests: `_safe_edit` swallow behavior, `build_ai_offer` back-row flag, `build_records_report` None/limit-append; manual checklist: every button tap mutates only the tapped message (plus photos/invoice where applicable), Back restores in place, /ask + voice denial still reply with the offer.

Touched: src/handlers/menu.py (main rework), src/handlers/payments.py, src/handlers/records.py, src/handlers/charts.py, src/core.py, src/handlers/recurring.py, src/handlers/reminders.py, src/detailed_transactions.py, src/texts.py, src/texts_ru.py.

Risks: same-content edits raise BadRequest "not modified" on double-tap — `_safe_edit` must wrap every edit or the global error handler fires per tap; 4096-char edit overflow → fallback-to-send paths (steps 4/5); never edit a media message into text (not currently possible — keep it that way); stale keyboards self-heal via edits but require the step-12 global back handler; send_ai_offer reply contract for /ask + voice must be regression-tested; menu_ask_ai still never grants — Buy → invoice → successful_payment untouched.
- 2026-07-19 Research complete: 10 stacking branches + charts callback crash + 3 dead-end submenus mapped; edit-in-place plan approved with defaults
