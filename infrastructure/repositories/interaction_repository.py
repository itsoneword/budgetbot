"""
AI interaction log repository (T-041).

One row per voice//ask exchange: transcript, detected intent + payload and an
outcome lifecycle (proposed/confirmed/cancelled/routed/unknown/superseded).
The voice router injects the newest rows into the intent prompt so
corrections ("не X, а Y") resolve against real context. Retention is
size-based (owner decision 2026-07-13): src/scheduler.py compacts oversized
users into one summary row (channel='system', intent='summary') and deletes
the raw rows — there is no time-based purge.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

import asyncpg

from .base import BaseRepository

# Per-message guardrail (amended step 8a): one runaway transcript must not
# dominate the size budget; anything longer carries no classification value.
MAX_STORED_CHARS = 2000

# channel value reserved for compaction summaries — excluded from the
# recent-context window and never re-compacted as a raw row.
SUMMARY_CHANNEL = "system"
SUMMARY_INTENT = "summary"


@dataclass
class AIInteraction:
    """AI interaction data model."""
    id: Optional[int]
    user_id: int
    channel: str  # 'voice' | 'text' | 'ask' | 'system'
    transcript: str
    intent: str
    payload: str
    outcome: str  # proposed|confirmed|cancelled|routed|unknown|superseded
    tx_id: Optional[int] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'AIInteraction':
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            channel=record['channel'],
            transcript=record['transcript'],
            intent=record['intent'],
            payload=record['payload'],
            outcome=record['outcome'],
            tx_id=record['tx_id'],
            created_at=record.get('created_at'),
        )


class InteractionRepository(BaseRepository[AIInteraction]):
    """CRUD for the per-user AI interaction log."""

    async def add(
        self,
        user_id: int,
        channel: str,
        transcript: str,
        intent: str,
        payload: str = "",
        outcome: str = "proposed",
    ) -> int:
        """Insert one interaction row and return its id.

        transcript/payload are truncated at MAX_STORED_CHARS each (amended
        step 8a guardrail)."""
        query = """
            INSERT INTO ai_interactions
            (user_id, channel, transcript, intent, payload, outcome)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        return await self.fetch_val(
            query,
            user_id,
            channel,
            transcript[:MAX_STORED_CHARS],
            intent,
            payload[:MAX_STORED_CHARS],
            outcome,
        )

    async def get_recent(self, user_id: int, n: int) -> List[AIInteraction]:
        """Newest-first non-summary rows — the intent-prompt context window."""
        query = """
            SELECT * FROM ai_interactions
            WHERE user_id = $1 AND channel != $2
            ORDER BY id DESC
            LIMIT $3
        """
        records = await self.fetch_all(query, user_id, SUMMARY_CHANNEL, n)
        return [AIInteraction.from_record(r) for r in records]

    async def set_outcome(
        self,
        interaction_id: int,
        user_id: int,
        outcome: str,
        tx_id: Optional[int] = None,
    ) -> bool:
        """Advance one interaction's outcome (user_id guards cross-user access)."""
        query = """
            UPDATE ai_interactions SET outcome = $3, tx_id = COALESCE($4, tx_id)
            WHERE id = $1 AND user_id = $2
        """
        status = await self.execute(query, interaction_id, user_id, outcome, tx_id)
        return int(status.split()[-1]) > 0

    # ------------------------------------------------------------------
    # Compaction support (amended step 8 — size-based, no time purge)
    # ------------------------------------------------------------------

    async def get_users_over_size(self, threshold_chars: int) -> List[int]:
        """user_ids whose non-summary rows exceed threshold_chars in total."""
        query = """
            SELECT user_id FROM ai_interactions
            WHERE channel != $1
            GROUP BY user_id
            HAVING SUM(LENGTH(transcript) + LENGTH(payload)) > $2
        """
        records = await self.fetch_all(query, SUMMARY_CHANNEL, threshold_chars)
        return [r['user_id'] for r in records]

    async def get_all_for_user(self, user_id: int) -> List[AIInteraction]:
        """All non-summary rows of one user, oldest first (compaction input)."""
        query = """
            SELECT * FROM ai_interactions
            WHERE user_id = $1 AND channel != $2
            ORDER BY id
        """
        records = await self.fetch_all(query, user_id, SUMMARY_CHANNEL)
        return [AIInteraction.from_record(r) for r in records]

    async def get_latest_summary(self, user_id: int) -> Optional[AIInteraction]:
        """The user's newest compaction summary row, if any."""
        query = """
            SELECT * FROM ai_interactions
            WHERE user_id = $1 AND channel = $2
            ORDER BY id DESC
            LIMIT 1
        """
        record = await self.fetch_one(query, user_id, SUMMARY_CHANNEL)
        return AIInteraction.from_record(record) if record else None

    async def delete_by_ids(self, user_id: int, ids: Sequence[int]) -> int:
        """Delete specific rows (compacted raw rows / folded old summary)."""
        if not ids:
            return 0
        query = """
            DELETE FROM ai_interactions
            WHERE user_id = $1 AND id = ANY($2::bigint[])
        """
        status = await self.execute(query, user_id, list(ids))
        return int(status.split()[-1])
