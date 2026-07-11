#!/usr/bin/env python3
"""
DEPRECATED (T-005): schema is now managed by alembic.

This script used to apply infrastructure/database/migrations/001_initial_schema.sql
directly. That SQL file is retained only as the source for the alembic baseline
revision (0001). Do not apply it by hand.

To apply migrations:
    DATABASE_URL=postgresql://... alembic upgrade head

To add a schema change:
    alembic revision -m "short_slug" --rev-id NNNN   # then edit the new file
    alembic upgrade head

In Docker the bot container runs `alembic upgrade head` on every start
(entrypoint.sh), so a plain `docker compose up` migrates automatically.
"""
import sys

sys.stderr.write(__doc__ + "\n")
sys.exit(1)
