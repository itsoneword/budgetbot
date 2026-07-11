"""Baseline: full initial schema from 001_initial_schema.sql

The SQL file is idempotent (IF NOT EXISTS / OR REPLACE / DROP TRIGGER IF
EXISTS throughout), so this revision applies cleanly both to a fresh empty
database and to an existing database that already carries the schema —
in the latter case every statement no-ops and alembic just records the
revision in alembic_version.

Revision ID: 0001
Revises:
Create Date: 2026-07-11
"""
from pathlib import Path
from typing import List

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_SCHEMA_FILE = Path(__file__).resolve().parents[2] / "migrations" / "001_initial_schema.sql"


def _split_statements(sql: str) -> List[str]:
    """Split a SQL script on ';', respecting $$-quoted function bodies.

    Needed because the asyncpg dialect sends each command as a single
    prepared statement — multi-command strings are rejected by the driver.
    """
    statements: List[str] = []
    buf: List[str] = []
    in_dollar = False
    i = 0
    while i < len(sql):
        if sql.startswith("$$", i):
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        ch = sql[i]
        if ch == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    statements.append("".join(buf))
    # Drop fragments that are empty or comment-only.
    result = []
    for stmt in statements:
        stripped = stmt.strip()
        lines = [ln.strip() for ln in stripped.splitlines()]
        if stripped and not all(ln == "" or ln.startswith("--") for ln in lines):
            result.append(stripped)
    return result


def upgrade() -> None:
    bind = op.get_bind()
    sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    for statement in _split_statements(sql):
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    bind = op.get_bind()
    for statement in (
        "DROP TABLE IF EXISTS migration_log CASCADE",
        "DROP TABLE IF EXISTS exchange_rates CASCADE",
        "DROP TABLE IF EXISTS transactions CASCADE",
        "DROP TABLE IF EXISTS user_categories CASCADE",
        "DROP TABLE IF EXISTS user_configs CASCADE",
        "DROP TABLE IF EXISTS users CASCADE",
        "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE",
        "DROP FUNCTION IF EXISTS date_trunc_month(TIMESTAMPTZ) CASCADE",
    ):
        bind.exec_driver_sql(statement)
