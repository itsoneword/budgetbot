"""
Daily reminders repository (T-034, multi-time dv-ff5f).

One row per (user, kind, time) — a user may keep several daily reminder
times; the every-5-min sweep (src/scheduler.py run_reminders) walks
get_active_with_tz and sends due nudges per row. `claim_send` is the atomic
idempotency gate mirroring RecurringRepository.claim_run — overlapping
sweeps and restarts can never double-send a (row, local date).
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

    async def add_time(
        self, user_id: int, time_local: time, kind: str = KIND_ADD_TRANSACTIONS
    ) -> Reminder:
        """Add one reminder time; re-adding an existing one re-activates it.

        last_sent_on is kept — re-adding a time after today's nudge was
        already sent must not produce a second one the same local day (the
        handler layer separately consumes today when the new time is already
        past, via domain.reminders.is_due + claim_send).
        """
        query = """
            INSERT INTO reminders (user_id, kind, time_local)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, kind, time_local) DO UPDATE SET
                active = TRUE
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, kind, time_local)
        return Reminder.from_record(record)

    async def get_all_for_user(
        self, user_id: int, kind: str = KIND_ADD_TRANSACTIONS
    ) -> List[Reminder]:
        """All reminder rows (active or not) for the user, ordered by time."""
        query = (
            "SELECT * FROM reminders WHERE user_id = $1 AND kind = $2 "
            "ORDER BY time_local"
        )
        records = await self.fetch_all(query, user_id, kind)
        return [Reminder.from_record(r) for r in records]

    async def remove_time(
        self, user_id: int, time_local: time, kind: str = KIND_ADD_TRANSACTIONS
    ) -> bool:
        """Delete one reminder time. True if a row was removed."""
        query = (
            "DELETE FROM reminders "
            "WHERE user_id = $1 AND kind = $2 AND time_local = $3"
        )
        status = await self.execute(query, user_id, kind, time_local)
        return int(status.split()[-1]) > 0

    async def set_active(
        self, user_id: int, active: bool, kind: str = KIND_ADD_TRANSACTIONS
    ) -> bool:
        """Enable/disable ALL of the user's times without losing them.
        True if any row changed."""
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
