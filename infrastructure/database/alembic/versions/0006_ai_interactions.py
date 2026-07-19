"""AI conversation memory: per-user interaction log (T-041)

ai_interactions persists every voice//ask exchange (transcript, detected
intent + payload, outcome lifecycle) so the intent classifier can see recent
context and resolve corrections ("не X, а Y"). Rows are size-compacted by
src/scheduler.run_interaction_compaction into a summary row
(channel='system', intent='summary') — no time-based purge (owner decision
2026-07-13).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-13
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per call: the asyncpg dialect rejects multi-command strings.
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ai_interactions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            channel VARCHAR(10) NOT NULL,
            transcript TEXT NOT NULL,
            intent VARCHAR(30) NOT NULL,
            payload TEXT NOT NULL DEFAULT '',
            outcome VARCHAR(12) NOT NULL DEFAULT 'proposed'
                CONSTRAINT valid_outcome CHECK (outcome IN
                    ('proposed', 'confirmed', 'cancelled', 'routed',
                     'unknown', 'superseded')),
            tx_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_ai_interactions_user_recent "
        "ON ai_interactions(user_id, id DESC)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS ai_interactions CASCADE")
