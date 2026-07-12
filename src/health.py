"""Liveness heartbeat for the Docker healthcheck (T-011).

A JobQueue job proves the three things that can die silently in a polling
bot — event loop alive, JobQueue running, DB reachable — in one signal:
every run executes SELECT 1 on the asyncpg pool and touches HEARTBEAT_FILE.
The docker-compose healthcheck execs a one-line mtime check (file younger
than 180s = healthy); no HTTP server, no new port.

NOTE: touching HEARTBEAT_FILE is a deliberate exception to the project's
no-file-I/O-outside-repositories rule. It is a liveness probe written to the
container's /tmp, not user state — Docker's healthcheck can only observe the
filesystem of a process it cannot call into.
"""

import logging
from pathlib import Path

from shared.di import get_repos

logger = logging.getLogger(__name__)

HEARTBEAT_FILE = "/tmp/budgetbot-heartbeat"


async def heartbeat(context) -> None:
    """Touch HEARTBEAT_FILE only if the DB pool answers SELECT 1."""
    try:
        await get_repos(context).pool.fetchval("SELECT 1")
    except Exception:
        # Deliberately do NOT touch the file: its mtime goes stale and the
        # container flips unhealthy. The ERROR line becomes a Sentry event
        # when Sentry is enabled.
        logger.error("Heartbeat failed: DB unreachable", exc_info=True)
        return
    Path(HEARTBEAT_FILE).touch()
