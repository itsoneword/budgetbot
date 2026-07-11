---
id: T-023
title: Paywall: buy AI access via Telegram Stars
status: todo
type: feature
area: bot
priority: p1
deps: [T-022]
tags: [ai, monetization]
blocked: 
created: 2026-07-11
updated: 2026-07-11
---

## Context
Users without AI entitlement get an offer instead of ASK_NOT_ALLOWED: inline button -> Telegram native payments in Stars (XTR, no provider token needed for digital goods): send_invoice, PreCheckoutQueryHandler, successful_payment handler writes the entitlement (T-022) with period end. Decide pricing/duration with owner before implementing. Handle: repeat purchase extends expiry; refund command per Telegram policy (refundStarPayment); receipts in both languages (texts.py + texts_ru.py). Security: entitlement written ONLY from successful_payment update, never from callback data.

## Acceptance
- [ ] TODO

## Log
- 2026-07-11 created

## Implementation plan (planned 2026-07-11, pre-approval)

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
