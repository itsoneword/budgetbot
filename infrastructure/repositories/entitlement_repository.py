"""
AI entitlement repository (T-022).

DB-backed per-user AI access replacing the LLM_ALLOWED_USERS env allowlist.
One row per user: NULL expires_at = perpetual, NULL revoked_at = active.
T-023 contract: a Stars purchase writes ONLY via grant(source='purchase',
duration_days=N) — a repeat purchase extends the remaining time
(GREATEST(expires_at, NOW()) + interval), it never shortens it.
"""
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
import asyncpg

from .base import BaseRepository


@dataclass
class AIEntitlement:
    """AI entitlement data model. telegram_username is only populated by
    list_active() (JOIN users); plain reads leave it None."""
    user_id: int
    source: str = 'admin'
    granted_by: int = 0
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # NULL = perpetual
    revoked_at: Optional[datetime] = None  # NULL = active
    revoked_by: Optional[int] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    telegram_username: Optional[str] = None

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'AIEntitlement':
        return cls(
            user_id=record['user_id'],
            source=record.get('source', 'admin'),
            granted_by=record.get('granted_by', 0),
            granted_at=record.get('granted_at'),
            expires_at=record.get('expires_at'),
            revoked_at=record.get('revoked_at'),
            revoked_by=record.get('revoked_by'),
            notes=record.get('notes'),
            updated_at=record.get('updated_at'),
            telegram_username=record.get('telegram_username'),
        )


class EntitlementRepository(BaseRepository[AIEntitlement]):
    """Repository for AI access entitlements."""

    async def has_ai_access(self, user_id: int) -> bool:
        """True if the user has an active (not revoked, not expired) entitlement."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM ai_entitlements
                WHERE user_id = $1
                  AND revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
            )
        """
        return await self.fetch_val(query, user_id)

    async def grant(
        self,
        user_id: int,
        granted_by: int,
        source: str = 'admin',
        duration_days: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AIEntitlement:
        """Grant or extend AI access. Clears any revocation.

        duration_days=None -> perpetual (expires_at NULL). With a duration,
        an existing unexpired entitlement is extended from its current
        expiry, an expired one from NOW() (GREATEST semantics).
        """
        query = """
            INSERT INTO ai_entitlements (user_id, source, granted_by, expires_at, notes)
            VALUES (
                $1, $2, $3,
                CASE WHEN $4::int IS NULL THEN NULL
                     ELSE NOW() + make_interval(days => $4) END,
                $5
            )
            ON CONFLICT (user_id) DO UPDATE SET
                source = EXCLUDED.source,
                granted_by = EXCLUDED.granted_by,
                granted_at = NOW(),
                expires_at = CASE
                    WHEN $4::int IS NULL THEN NULL
                    ELSE GREATEST(COALESCE(ai_entitlements.expires_at, NOW()), NOW())
                         + make_interval(days => $4)
                END,
                revoked_at = NULL,
                revoked_by = NULL,
                notes = COALESCE(EXCLUDED.notes, ai_entitlements.notes),
                updated_at = NOW()
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, source, granted_by, duration_days, notes)
        return AIEntitlement.from_record(record)

    async def revoke(self, user_id: int, revoked_by: int) -> bool:
        """Revoke an active entitlement. False if there was none to revoke."""
        query = """
            UPDATE ai_entitlements
            SET revoked_at = NOW(), revoked_by = $2, updated_at = NOW()
            WHERE user_id = $1 AND revoked_at IS NULL
        """
        result = await self.execute(query, user_id, revoked_by)
        return result == "UPDATE 1"

    async def get(self, user_id: int) -> Optional[AIEntitlement]:
        """Get the entitlement row (active or not) for a user."""
        query = "SELECT * FROM ai_entitlements WHERE user_id = $1"
        record = await self.fetch_one(query, user_id)
        return AIEntitlement.from_record(record) if record else None

    async def list_active(self) -> List[AIEntitlement]:
        """All active entitlements with the user's telegram username."""
        query = """
            SELECT e.*, u.telegram_username
            FROM ai_entitlements e
            JOIN users u ON u.user_id = e.user_id
            WHERE e.revoked_at IS NULL
              AND (e.expires_at IS NULL OR e.expires_at > NOW())
            ORDER BY e.granted_at
        """
        records = await self.fetch_all(query)
        return [AIEntitlement.from_record(r) for r in records]
