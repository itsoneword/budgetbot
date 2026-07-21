"""Multiple reminder times per user (dv-ff5f)

Reminder v2: a user may keep several daily reminder times (e.g. midday +
evening). The per-row sweep, is_due and claim_send already handle N rows
independently — the only schema change is swapping the one-per-user
UNIQUE (user_id, kind) for UNIQUE (user_id, kind, time_local). Each row
keeps its own last_sent_on local-date idempotency cursor.

Downgrade is lossy by design: it dedupes to the lowest-id row per
(user_id, kind) before restoring the old constraint.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-21
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per call: the asyncpg dialect rejects multi-command strings.
    bind.exec_driver_sql(
        "ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_user_id_kind_key"
    )
    bind.exec_driver_sql(
        "ALTER TABLE reminders ADD CONSTRAINT reminders_user_kind_time_key "
        "UNIQUE (user_id, kind, time_local)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Keep only the lowest-id row per (user_id, kind) so the old one-per-user
    # constraint can be restored (lossy — downgrades are for emergencies).
    bind.exec_driver_sql(
        "DELETE FROM reminders r USING reminders keep "
        "WHERE keep.user_id = r.user_id AND keep.kind = r.kind AND keep.id < r.id"
    )
    bind.exec_driver_sql(
        "ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_user_kind_time_key"
    )
    bind.exec_driver_sql(
        "ALTER TABLE reminders ADD CONSTRAINT reminders_user_id_kind_key "
        "UNIQUE (user_id, kind)"
    )
