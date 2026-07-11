"""Runtime configuration read from environment variables."""

import os

# Bot release version, shown in /about (T-031). Bump on release and note the
# designation in docs/CHANGELOG.md.
VERSION = "0.3.0"
VERSION_DATE = "11.07.2026"

# Telegram user ID allowed to run admin-only commands (/debug, /show_log_chart).
# Defaults to 0 (matches no real user) when unset, so admin commands stay locked.
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Users allowed to use LLM-backed commands (/ask). The LLM runs on the owner's
# subscription, so this is an allowlist: ADMIN_USER_ID plus LLM_ALLOWED_USERS
# (comma-separated Telegram IDs). Empty LLM_ALLOWED_USERS = admin only.
LLM_ALLOWED_USERS = frozenset(
    int(uid) for uid in os.getenv("LLM_ALLOWED_USERS", "").split(",") if uid.strip().isdigit()
)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID


def is_llm_allowed(user_id: int) -> bool:
    """Admin + env allowlist. Since T-022 this is only the fallback tier of
    src/ai_access.check_ai_access (DB entitlements); the env allowlist is
    scheduled for removal in the T-023 release."""
    return user_id == ADMIN_USER_ID or user_id in LLM_ALLOWED_USERS


# UTC hour at which the daily recurring-transactions job runs (T-026).
RECURRING_HOUR_UTC = int(os.getenv("RECURRING_HOUR_UTC", "6"))
