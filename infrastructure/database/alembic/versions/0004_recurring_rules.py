"""Recurring transaction rules table (T-026)

recurring_rules holds user-defined monthly rules; the daily scheduler
materializes due rules into normal transactions. last_run stores the due
date of the last posted period and is the idempotency key (claim_run).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-11
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per call: the asyncpg dialect rejects multi-command strings.
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS recurring_rules (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            transaction_type VARCHAR(10) NOT NULL DEFAULT 'spending'
                CONSTRAINT valid_recurring_type CHECK (transaction_type IN ('spending', 'income')),
            category_name TEXT NOT NULL,
            subcategory_name TEXT NOT NULL,
            amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
            currency CHAR(3) NOT NULL,
            day_of_month SMALLINT NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            last_run DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_recurring_rules_active "
        "ON recurring_rules(active) WHERE active"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS recurring_rules CASCADE")
