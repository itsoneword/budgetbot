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
