"""Runtime configuration read from environment variables."""

import os

# Bot release version, shown in /about (T-031). Bump on release and note the
# designation in docs/CHANGELOG.md.
VERSION = "0.3.0"
VERSION_DATE = "11.07.2026"

# Telegram user ID allowed to run admin-only commands (/debug, /show_log_chart).
# Defaults to 0 (matches no real user) when unset, so admin commands stay locked.
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID


# AI access paywall (T-023). Price of the AI pass in Telegram Stars and its
# duration in days; AI_ACCESS_DAYS=0 sells perpetual access (entitlement
# expires_at NULL). The legacy LLM_ALLOWED_USERS env tier was removed in the
# T-023 release — access is admin + DB entitlements (src/ai_access.py) only;
# pre-deploy, every env-allowlisted user must be migrated via /grant_ai.
AI_ACCESS_PRICE_STARS = int(os.getenv("AI_ACCESS_PRICE_STARS", "100"))
AI_ACCESS_DAYS = int(os.getenv("AI_ACCESS_DAYS", "30"))


# UTC hour at which the daily recurring-transactions job runs (T-026).
RECURRING_HOUR_UTC = int(os.getenv("RECURRING_HOUR_UTC", "6"))

# Error aggregation (T-011): optional Sentry, opt-in via env. Empty DSN =
# disabled — src/observability.py then never even imports sentry_sdk.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "prod")

# Interval of the reminder sweep job (T-034): every N seconds the sweep sends
# reminders that became due since the last pass, so a reminder fires at most
# this many seconds late.
REMINDER_SWEEP_SECONDS = int(os.getenv("REMINDER_SWEEP_SECONDS", "300"))

# AI interaction-log compaction (T-041, size-based retention — owner decision
# 2026-07-13): a user whose raw ai_interactions rows exceed this many chars
# (~50k tokens) gets everything but the newest rows summarized into one
# summary row and the raw rows deleted. There is NO time-based purge.
AI_INTERACTION_COMPACT_CHARS = int(os.getenv("AI_INTERACTION_COMPACT_CHARS", "200000"))

# UTC hour of the daily compaction job.
AI_COMPACTION_HOUR_UTC = int(os.getenv("AI_COMPACTION_HOUR_UTC", "4"))
