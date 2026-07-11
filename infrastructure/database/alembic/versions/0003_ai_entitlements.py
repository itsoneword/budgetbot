"""AI entitlements table (T-022)

Per-user AI access grants replacing the LLM_ALLOWED_USERS env allowlist.
One row per user (PK = user_id): NULL expires_at = perpetual, NULL
revoked_at = active. T-023 (Stars paywall) writes rows via
EntitlementRepository.grant() with source='purchase'.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ai_entitlements (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            source VARCHAR(20) NOT NULL DEFAULT 'admin',
            granted_by BIGINT NOT NULL,
            granted_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            revoked_by BIGINT,
            notes TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    # Reuse the shared updated_at trigger function from the baseline schema.
    bind.exec_driver_sql(
        "DROP TRIGGER IF EXISTS update_ai_entitlements_updated_at ON ai_entitlements"
    )
    bind.exec_driver_sql(
        """
        CREATE TRIGGER update_ai_entitlements_updated_at
            BEFORE UPDATE ON ai_entitlements
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS ai_entitlements CASCADE")
