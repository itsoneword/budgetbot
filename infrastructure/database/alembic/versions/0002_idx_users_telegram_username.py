"""Sample migration: index on users.telegram_username

Demonstrates the post-baseline migration workflow (T-005). Harmless and
mildly useful: user lookups by telegram username no longer seq-scan.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_users_telegram_username "
        "ON users(telegram_username)"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DROP INDEX IF EXISTS idx_users_telegram_username"
    )
