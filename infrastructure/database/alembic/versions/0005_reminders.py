"""Daily reminders + per-user timezone offset (T-034)

user_configs.tz_offset_min stores the user's fixed UTC offset in minutes
(NULL = UTC), set via the one-tap "what time is it for you now" picker.
reminders holds one row per (user, kind); last_sent_on is the local-date
idempotency key claimed atomically by ReminderRepository.claim_send —
the every-5-min sweep (src/scheduler.py run_reminders) can run any number
of times without double-sending.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-12
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per call: the asyncpg dialect rejects multi-command strings.
    bind.exec_driver_sql(
        "ALTER TABLE user_configs ADD COLUMN IF NOT EXISTS tz_offset_min SMALLINT "
        "CONSTRAINT valid_tz_offset CHECK (tz_offset_min BETWEEN -720 AND 840)"
    )
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            kind VARCHAR(20) NOT NULL DEFAULT 'add_transactions',
            time_local TIME NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            last_sent_on DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, kind)
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_reminders_active "
        "ON reminders(active) WHERE active"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS reminders CASCADE")
    bind.exec_driver_sql(
        "ALTER TABLE user_configs DROP COLUMN IF EXISTS tz_offset_min"
    )
