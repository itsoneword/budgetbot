"""Telegram Stars payments audit table (T-023)

ai_payments records every successful Stars purchase of AI access. user_id has
NO foreign key on purpose: the refund audit trail must survive a /leave
delete-cascade of the user row. telegram_payment_charge_id is UNIQUE — it is
both the refund key (Bot.refund_star_payment) and the idempotency guard
against Telegram redelivering a successful_payment update.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-19
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per call: the asyncpg dialect rejects multi-command strings.
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ai_payments (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            telegram_payment_charge_id TEXT NOT NULL UNIQUE,
            invoice_payload TEXT NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'XTR',
            amount INTEGER NOT NULL,
            duration_days INTEGER,
            status VARCHAR(10) NOT NULL DEFAULT 'paid'
                CONSTRAINT valid_payment_status CHECK (status IN ('paid', 'refunded')),
            paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            refunded_at TIMESTAMPTZ,
            refunded_by BIGINT
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_ai_payments_user_paid "
        "ON ai_payments(user_id, paid_at DESC)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS ai_payments CASCADE")
