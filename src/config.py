"""Runtime configuration read from environment variables."""

import os

# Telegram user ID allowed to run admin-only commands (/debug, /show_log_chart).
# Defaults to 0 (matches no real user) when unset, so admin commands stay locked.
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
