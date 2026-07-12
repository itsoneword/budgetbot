"""Optional error aggregation via Sentry (T-011).

Opt-in through the SENTRY_DSN env var. Without a DSN, init_sentry() returns
False without ever importing sentry_sdk — zero overhead, the bot ships dark
until the owner creates a Sentry project and sets the DSN.

With a DSN, LoggingIntegration hooks the stdlib logging module: every
logging.error(..., exc_info=...) — including core.py's global_error_handler
and per-item logger.exception() calls inside JobQueue jobs — becomes a Sentry
event, INFO+ lines become breadcrumbs. No explicit capture_exception calls
anywhere in the codebase.
"""

import logging

from src.config import SENTRY_DSN, SENTRY_ENVIRONMENT, VERSION

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """Initialize Sentry if SENTRY_DSN is set; return True when enabled."""
    if not SENTRY_DSN:
        logger.info("Sentry disabled (no SENTRY_DSN)")
        return False

    # Lazy import: only pay for the SDK when a DSN is configured.
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=f"budgetbot@{VERSION}",
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    logger.info("Sentry enabled (environment=%s)", SENTRY_ENVIRONMENT)
    return True
