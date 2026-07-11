"""Runtime configuration read from environment variables."""

import os

# Telegram user ID allowed to run admin-only commands (/debug, /show_log_chart).
# Defaults to 0 (matches no real user) when unset, so admin commands stay locked.
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Users allowed to use LLM-backed commands (/ask). The LLM runs on the owner's
# subscription, so this is an allowlist: ADMIN_USER_ID plus LLM_ALLOWED_USERS
# (comma-separated Telegram IDs). Empty LLM_ALLOWED_USERS = admin only.
LLM_ALLOWED_USERS = frozenset(
    int(uid) for uid in os.getenv("LLM_ALLOWED_USERS", "").split(",") if uid.strip().isdigit()
)


def is_llm_allowed(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID or user_id in LLM_ALLOWED_USERS


# UTC hour at which the daily recurring-transactions job runs (T-026).
RECURRING_HOUR_UTC = int(os.getenv("RECURRING_HOUR_UTC", "6"))
