---
id: dv-cf4a
title: Paywall: buy AI access via Telegram Stars
status: done
priority: high
assignee: 
labels: [feature, bot]
deps: [dv-4a4a]
parent: 
created: 2026-07-19T15:01:13Z
updated: 2026-07-19T15:01:13Z
---

## Description

Migrated from `docs/tasks/T-023-paywall-buy-ai-access-via-telegram-stars.md`.

Users without AI entitlement get an offer instead of ASK_NOT_ALLOWED: inline button -> Telegram native payments in Stars (XTR, no provider token needed for digital goods): send_invoice, PreCheckoutQueryHandler, successful_payment handler writes the entitlement (T-022) with period end. Decide pricing/duration with owner before implementing. Handle: repeat purchase extends expiry; refund command per Telegram policy (refundStarPayment); receipts in both languages (texts.py + texts_ru.py). Security: entitlement written ONLY from successful_payment update, never from callback data.

## Acceptance Criteria

- [x] Alembic revision 0007 `ai_payments`: audit table with user_id WITHOUT FK (refund audit survives /leave cascade), telegram_payment_charge_id UNIQUE; single head on top of 0006
- [x] PaymentRepository (record ON CONFLICT DO NOTHING -> False on redelivery, get_latest_paid, get_by_charge_id, mark_refunded), exported + `repos.payments` DI property
- [x] Config: AI_ACCESS_PRICE_STARS (default 100), AI_ACCESS_DAYS (default 30; 0 = perpetual)
- [x] Copy in BOTH texts.py + texts_ru.py: offer, buy button, invoice title/description, receipts ({expiry}/perpetual), BUY_AI_ALREADY, PAY_PRECHECKOUT_FAILED, ASK_AI_BUTTON, AI_HOWTO
- [x] Stateless src/handlers/payments.py: send_ai_offer (via effective_message — works from message AND callback contexts), invoice with payload-encoded sold terms (domain/payments.py 'ai:30'/'ai:perp'), /buy_ai (entitled -> BUY_AI_ALREADY + invoice anyway), buy_ai callback, precheckout (validation only, NO DB), successful_payment = the ONLY grant point (record first; grant only if inserted; CRITICAL log with charge_id on any failure), /refund_ai USER_ID [charge_id] -> refund_star_payment + mark_refunded + revoke
- [x] Registry rows: buy_ai next to ask, refund_ai admin_only; import guard passes (no <>& chars)
- [x] core.py wiring BEFORE spendings_handler: CallbackQueryHandler(^buy_ai$), PreCheckoutQueryHandler, MessageHandler(filters.SUCCESSFUL_PAYMENT)
- [x] Denial -> offer at both gate sites (core.py ask(), voice.py handle_voice); silent free-text fallthrough left silent; ASK_NOT_ALLOWED removed
- [x] Step 9 code side: LLM_ALLOWED_USERS env tier removed from config.py/ai_access.py/list_ai footer (pre-deploy /grant_ai migration = owner action, see Testing)
- [x] Amendment: ASK_AI_BUTTON full-width TOP row in create_main_menu_keyboard (callback_data="menu_ask_ai"); menu_call branch: entitled -> AI_HOWTO + return to menu, else send_ai_offer
- [x] Domain payload codec tests added; full suite green (231 passed); `import src.core` OK with stub config; alembic single head 0007

## Notes

### Log

- 2026-07-11 created

### Implementation plan (approved 2026-07-11)

Verified against installed PTB v22.6: send_invoice(currency="XTR", provider_token omitted, exactly one LabeledPrice), PreCheckoutQueryHandler, filters.SUCCESSFUL_PAYMENT, Bot.refund_star_payment(user_id, telegram_payment_charge_id). Persist charge_id for refunds.

1. Alembic revision `ai_payments` (rev-id = head at implementation time, pattern-copy 0003): id BIGSERIAL PK, user_id BIGINT (NO FK — refund audit must survive /leave cascade), telegram_payment_charge_id TEXT UNIQUE (refund key + idempotency), invoice_payload TEXT ('ai:30'/'ai:perp' — terms as sold), currency 'XTR', amount INTEGER (Stars), duration_days (NULL=perpetual), status 'paid'|'refunded', paid_at, refunded_at, refunded_by; index (user_id, paid_at DESC).
2. payment_repository.py: record(...) INSERT ON CONFLICT (charge_id) DO NOTHING → False on redelivery (skip re-grant); get_latest_paid(user_id); mark_refunded(charge_id, by). Export + DI property (entitlements pattern).
3. src/config.py (pricing parked → env-parameterized): AI_ACCESS_PRICE_STARS (default 100), AI_ACCESS_DAYS (default 30; 0 → None = perpetual, flows into grant(duration_days=None) with zero code change).
4. Copy both texts files: BUY_AI_OFFER (replaces denial), BUY_AI_BUTTON/TITLE(≤32ch)/DESCRIPTION, BUY_AI_RECEIPT_DAYS {expiry}, BUY_AI_RECEIPT_PERPETUAL, BUY_AI_ALREADY (buying extends), PAY_PRECHECKOUT_FAILED.
5. New src/handlers/payments.py — STATELESS (no user_data; survives restart mid-flow): send_ai_offer (inline Buy button callback_data="buy_ai"); _send_invoice (payload encodes sold terms so stale invoices grant what was advertised); buy_ai command (already-entitled → BUY_AI_ALREADY + invoice anyway, repeat extends via GREATEST); buy_ai_callback; precheckout (validate payload prefix + XTR, answer ok — NO DB writes, must answer <10s); successful_payment — THE ONLY place purchase grants: payments.record() first; if inserted → entitlements.grant(source='purchase', duration_days from payload) + receipt with expires_at; if not inserted (redelivery) → receipt only; try/except logging CRITICAL with charge_id (money taken + grant failed must be findable → manual /grant_ai); refund_ai admin command: /refund_ai USER_ID [charge_id] (default latest paid) → bot.refund_star_payment → mark_refunded + entitlements.revoke, report both.
6. Registry rows (no <>& — import guard): buy_ai (next to ask), refund_ai (admin_only).
7. core.py wiring BEFORE spendings_handler (menu_callback fallback swallows callbacks): CallbackQueryHandler(^buy_ai$), PreCheckoutQueryHandler, MessageHandler(filters.SUCCESSFUL_PAYMENT). Handlers imported into core globals via handlers/__init__.py.
8. Denial → offer at both gate sites: core.py ask() (~791) and voice.py handle_voice (~61). Leave the silent free-text fallthrough (core.py:594) silent — no spam.
9. Release step (last, reversible): /grant_ai each LLM_ALLOWED_USERS user, then remove env tier from config.py/ai_access.py/list_ai footer.

Touched: new revision + payment_repository.py + handlers/payments.py; modified repositories/__init__.py, container.py, config.py, handlers/__init__.py, commands.py, core.py, voice.py, admin.py (step 9), texts.py, texts_ru.py, DECISIONS.md.

Open questions (recommended defaults):
1. Price → 100 Stars (~$1.3-2), env-overridable without deploy.
2. Model → 30-day pass (LLM cost is recurring; GREATEST stacking built for this). Perpetual = AI_ACCESS_DAYS=0, one env var away.
3. Refund policy → refund revokes entirely; admin re-grants remainder manually in stacked cases; advertise 7-day goodwill window.

Risks: duplicate successful_payment delivery (handled: UNIQUE charge_id, insert-first); crash between record and grant (narrow; CRITICAL log + manual /grant_ai; shared transaction not worth breaking repo pattern); refund-after-stacking is blunt revoke-all (documented in refund reply); pre-checkout is I/O-free so 10s deadline safe; config change with pending invoices handled by payload-encoded terms.

**Owner decisions 2026-07-11:** 100 Stars / 30-day pass (AI_ACCESS_PRICE_STARS=100, AI_ACCESS_DAYS=30); refund revokes all access (manual re-grant of remainder in stacked cases). All planner defaults accepted.

### Amendment (2026-07-12): main-menu "Ask AI" funnel

Owner addition 2026-07-12: a prominent main-menu button becomes the paywall's primary funnel. No entitlement → the step-5 offer; entitled → a how-to message. Reuses `send_ai_offer` — no new payment surface, no security change (button never grants; purchase still flows exclusively invoice → `successful_payment`).

10. Texts (fold into step 4's copy pass, both `src/texts.py` + `src/texts_ru.py`): `ASK_AI_BUTTON` ("🤖 Ask AI" / "🤖 Спросить ИИ"), `AI_HOWTO` (entitled-user info: send a voice message, or `/ask <question>`; EN/RU).
11. `src/keyboards.py` `create_main_menu_keyboard`: new full-width TOP row (prominent per owner) above Add/Show — `InlineKeyboardButton(texts.ASK_AI_BUTTON, callback_data="menu_ask_ai")`. The `menu_` prefix rides the existing `^menu_` CallbackQueryHandler (core.py:808) and the menu_callback fallback — core.py untouched.
12. `src/handlers/menu.py` `menu_call`: new `menu_ask_ai` branch (place with the other main-menu-navigation branches, T-036 pattern). `await query.answer()`; `check_ai_access(user_id, context)` (src/ai_access.py) → entitled: `edit_message_text(texts.AI_HOWTO)` then `_return_to_main_menu(query, texts)` (menu_help pattern); not entitled: `await send_ai_offer(update, context)` then `return await _return_to_main_menu(query, texts)`. **Contract note for step 5:** `send_ai_offer` must send via `update.effective_message.reply_text` (NOT `update.message`) so it serves both message contexts (step 8's ask/voice denial sites) and this callback context.

Touched (append to step list): src/keyboards.py, src/handlers/menu.py (both new to the Touched list; texts files already listed).

Open question (recommended default): exact label/placement → "🤖 Ask AI" as a full-width top row (highest-visibility slot; existing six buttons keep their 3×2 layout below). Alternative if owner objects to a 4-row menu: pair it half-width next to Help.

Risks: none new — `menu_ask_ai` from a stale keyboard rendered outside TRANSACTION state is caught by the menu_callback fallback (same as every existing `menu_*` button); `check_ai_access` is fail-closed, so a DB error shows the offer rather than granting — acceptable (paying while entitled just extends via GREATEST, step 5).
- 2026-07-12 Plan amendment: main-menu Ask AI funnel button (steps 10-12) — reuses send_ai_offer; effective_message contract note for step 5
- 2026-07-19 started
- 2026-07-19 Implemented all 12 plan steps: 0007 ai_payments revision, PaymentRepository+DI, config pricing, texts EN/RU, stateless payments handlers (invoice/precheckout/successful_payment sole grant point/refund_ai), registry rows, core.py wiring, denial->offer at ask+voice, env tier removed, menu Ask-AI funnel; suite 231 green, import check OK, alembic single head

### Testing

#### PRE-DEPLOY — OWNER ACTION REQUIRED (before this code goes live)
- [ ] **Migrate the env allowlist BEFORE deploying this build.** The LLM_ALLOWED_USERS env tier is REMOVED in this code — any user relying on it loses AI access the moment this deploys. On the CURRENTLY RUNNING (old) bot, run `/grant_ai USER_ID` (or `/grant_ai USER_ID 30` for a timed pass) for EVERY user id currently in LLM_ALLOWED_USERS, and verify with `/list_ai` that each now holds a DB entitlement. Only then deploy. (Reversible: if anything goes wrong, re-adding LLM_ALLOWED_USERS to the old image restores the old behavior.)
- [ ] After deploy: `alembic upgrade head` ran on container start (check logs for revision 0007); `\d ai_payments` shows the table with the UNIQUE constraint on telegram_payment_charge_id and NO FK on user_id.
- [ ] After deploy: remove LLM_ALLOWED_USERS from the deployment env/compose file (it is dead config now).

#### Critical — real purchase flow (needs a real 100-Star balance)
- [ ] As a NON-entitled, non-admin user: `/ask test` shows the Stars offer (price 100, 30 days) with the Buy button — not the old denial text, no dead end.
- [ ] As the same user: send a voice note — same offer appears.
- [ ] Tap Buy: a Telegram Stars invoice appears (title/description in the user's language, 100 XTR, one price row). `/buy_ai` produces the same invoice directly.
- [ ] Pay the invoice (real 100 Stars): receipt arrives with an expiry date ~30 days out (UTC); `/ask test` now answers; voice notes now work; admin `/list_ai` shows the user with source=purchase and the expiry.
- [ ] DB audit: `SELECT * FROM ai_payments` has one 'paid' row with the charge id, payload 'ai:30', amount 100, currency XTR.
- [ ] Repeat purchase while entitled: `/buy_ai` first replies BUY_AI_ALREADY, still sends the invoice; paying again EXTENDS expiry (~60 days from first purchase, GREATEST semantics) — it must never shorten.
- [ ] Redelivery idempotency (reasoning check, hard to trigger live): the grant runs ONLY when payments.record() actually inserts; a redelivered successful_payment update hits the UNIQUE charge_id, record() returns False, and the handler sends a receipt WITHOUT re-granting. Verify the code path once by manually re-inserting the same charge id is rejected: second `INSERT ... ON CONFLICT DO NOTHING` reports INSERT 0 0.
- [ ] Refund flow: admin `/refund_ai USER_ID` refunds the latest paid charge — Stars return to the buyer, ai_payments row flips to 'refunded' with refunded_by, `/list_ai` no longer lists the user, and their next `/ask` shows the offer again. Reply text mentions revoke-all + manual /grant_ai for remainders.
- [ ] Ask AI menu button — NOT entitled: /menu shows the full-width top "🤖 Ask AI" row; tapping it sends the offer and returns to the main menu (menu keeps working afterwards).
- [ ] Ask AI menu button — entitled (or admin): tapping it shows AI_HOWTO, then returns to the main menu.

#### Important
- [ ] Pre-checkout failure path: with a pending unpaid invoice, restart the bot, then pay — payment still completes (handlers are stateless; payload carries the sold terms). If Telegram ever sends a non-'ai:' payload, the pre-checkout is declined with PAY_PRECHECKOUT_FAILED.
- [ ] `/refund_ai` edge cases: unknown user id -> "no refundable payment"; explicit charge id of another user -> rejected; refunding an already-refunded charge -> "already refunded"; non-admin caller -> restricted message.
- [ ] Russian-language user sees RU copy end-to-end: offer, invoice title/description, receipt, AI_HOWTO, Ask-AI button label.
- [ ] Grant-failure audit trail (reasoning check): if entitlements.grant() throws after record(), the log contains a CRITICAL line with the charge_id and the /grant_ai instruction, and the user sees ERROR_PROCESSING_REQUEST — money is never silently lost.
- [ ] Free-text fallthrough stays silent: a non-entitled user typing random text (no amount pattern) gets UNKNOWN_TEXT_FORMAT, NOT the paywall offer (no spam).
- [ ] `/help` and the command menu show /buy_ai for everyone and /refund_ai only in the admin scope.

#### Regression
- [ ] Menu still 5 rows and all previous buttons work (add/show/edit/reminder/settings/help); mid-conversation menu_ask_ai from a stale keyboard doesn't crash (menu_callback fallback catches it).
- [ ] Admin retains AI access with no entitlement row (is_admin tier).
- [ ] /grant_ai, /revoke_ai, /list_ai still work; /list_ai no longer prints the env-allowlist footer.
- [ ] vtx_/vinc_/rr/rem_ inline buttons still work (handler ordering unchanged around the new payment handlers).
- 2026-07-19 moved to review
- 2026-07-19 done
- 2026-07-19 changelog: AI paywall via Telegram Stars: /buy_ai, offer-on-denial, Ask-AI menu funnel, /refund_ai — purchase flow owner-verified live
- 2026-07-19 Owner verified live purchase: 100 Stars, receipt with expiry 2026-08-18, entitled how-to shown. Refund path (/refund_ai) implemented + reviewed but not yet exercised live
