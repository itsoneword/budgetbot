"""
Daily reminders repository (T-034).

One row per (user, kind); the every-5-min sweep (src/scheduler.py
run_reminders) walks get_active_with_tz and sends due nudges. `claim_send`
is the atomic idempotency gate mirroring RecurringRepository.claim_run —
overlapping sweeps and restarts can never double-send a local date.
"""
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import List, Optional, Tuple

import asyncpg

from .base import BaseRepository

KIND_ADD_TRANSACTIONS = "add_transactions"


@dataclass
class Reminder:
    """Reminder data model (time_local is the user's wall-clock fire time)."""
    id: Optional[int]
    user_id: int
    kind: str
    time_local: time
    active: bool
    last_sent_on: Optional[date]
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'Reminder':
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            kind=record['kind'],
            time_local=record['time_local'],
            active=record['active'],
            last_sent_on=record['last_sent_on'],
            created_at=record.get('created_at'),
        )


class ReminderRepository(BaseRepository[Reminder]):
    """Reminder CRUD + the atomic send claim."""

    async def upsert(
        self, user_id: int, time_local: time, kind: str = KIND_ADD_TRANSACTIONS
    ) -> Reminder:
        """Create or update the user's reminder; re-activates a disabled one.

        last_sent_on is kept — re-setting the time after today's nudge was
        already sent must not produce a second one the same local day (the
        handler layer separately consumes today when the new time is already
        past, via domain.reminders.is_due + claim_send).
        """
        query = """
            INSERT INTO reminders (user_id, kind, time_local)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, kind) DO UPDATE SET
                time_local = EXCLUDED.time_local,
                active = TRUE
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, kind, time_local)
        return Reminder.from_record(record)

    async def get_for_user(
        self, user_id: int, kind: str = KIND_ADD_TRANSACTIONS
    ) -> Optional[Reminder]:
        query = "SELECT * FROM reminders WHERE user_id = $1 AND kind = $2"
        record = await self.fetch_one(query, user_id, kind)
        return Reminder.from_record(record) if record else None

    async def set_active(
        self, user_id: int, active: bool, kind: str = KIND_ADD_TRANSACTIONS
    ) -> bool:
        """Enable/disable without losing the configured time. True if a row changed."""
        query = "UPDATE reminders SET active = $3 WHERE user_id = $1 AND kind = $2"
        status = await self.execute(query, user_id, kind, active)
        return int(status.split()[-1]) > 0

    async def delete(self, user_id: int, kind: str = KIND_ADD_TRANSACTIONS) -> bool:
        query = "DELETE FROM reminders WHERE user_id = $1 AND kind = $2"
        status = await self.execute(query, user_id, kind)
        return int(status.split()[-1]) > 0

    async def get_active_with_tz(self) -> List[Tuple[Reminder, Optional[int]]]:
        """All active reminders joined with the owner's tz offset (NULL = UTC) —
        the sweep's work list."""
        query = """
            SELECT r.*, uc.tz_offset_min
            FROM reminders r
            LEFT JOIN user_configs uc ON uc.user_id = r.user_id
            WHERE r.active
            ORDER BY r.id
        """
        records = await self.fetch_all(query)
        return [(Reminder.from_record(r), r['tz_offset_min']) for r in records]

    async def claim_send(self, reminder_id: int, local_date: date) -> bool:
        """Atomically claim one local date for a reminder.

        Advances last_sent_on to local_date only if the reminder is active
        and that date hasn't been claimed yet. Returns True exactly once per
        (reminder, local date) no matter how many sweeps race — the caller
        must skip sending when this returns False.
        """
        query = """
            UPDATE reminders SET last_sent_on = $2
            WHERE id = $1 AND active AND (last_sent_on IS NULL OR last_sent_on < $2)
        """
        status = await self.execute(query, reminder_id, local_date)
        return int(status.split()[-1]) > 0
