"""
Recurring transaction rules repository (T-026).

Stores user-defined monthly rules; the daily scheduler (src/scheduler.py)
materializes due rules into normal transactions. `claim_run` is the atomic
idempotency gate — restarts and overlapping runs can never double-post.
"""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

import asyncpg

from .base import BaseRepository


@dataclass
class RecurringRule:
    """Recurring rule data model."""
    id: Optional[int]
    user_id: int
    transaction_type: str  # 'spending' | 'income'
    category_name: str
    subcategory_name: str
    amount: Decimal
    currency: str
    day_of_month: int
    active: bool
    last_run: Optional[date]
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'RecurringRule':
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            transaction_type=record['transaction_type'],
            category_name=record['category_name'],
            subcategory_name=record['subcategory_name'],
            amount=record['amount'],
            currency=record['currency'],
            day_of_month=record['day_of_month'],
            active=record['active'],
            last_run=record['last_run'],
            created_at=record.get('created_at'),
        )


class RecurringRepository(BaseRepository[RecurringRule]):
    """Repository for recurring rule CRUD + the atomic run claim."""

    async def add(
        self,
        user_id: int,
        category_name: str,
        subcategory_name: str,
        amount: float,
        currency: str,
        day_of_month: int,
        transaction_type: str = 'spending',
    ) -> RecurringRule:
        """Insert a new active rule and return it."""
        query = """
            INSERT INTO recurring_rules
            (user_id, transaction_type, category_name, subcategory_name,
             amount, currency, day_of_month)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        record = await self.fetch_one(
            query,
            user_id,
            transaction_type,
            category_name,
            subcategory_name,
            Decimal(str(amount)),
            currency.upper()[:3],
            day_of_month,
        )
        return RecurringRule.from_record(record)

    async def list_for_user(self, user_id: int) -> List[RecurringRule]:
        """All rules of one user (active and paused), oldest first."""
        query = "SELECT * FROM recurring_rules WHERE user_id = $1 ORDER BY id"
        records = await self.fetch_all(query, user_id)
        return [RecurringRule.from_record(r) for r in records]

    async def get_by_id(self, rule_id: int, user_id: int) -> Optional[RecurringRule]:
        """One rule, scoped to its owner (user_id guards cross-user access)."""
        query = "SELECT * FROM recurring_rules WHERE id = $1 AND user_id = $2"
        record = await self.fetch_one(query, rule_id, user_id)
        return RecurringRule.from_record(record) if record else None

    async def set_active(self, rule_id: int, user_id: int, active: bool) -> bool:
        """Pause/resume a rule. Returns True if a row changed."""
        query = """
            UPDATE recurring_rules SET active = $3
            WHERE id = $1 AND user_id = $2
        """
        status = await self.execute(query, rule_id, user_id, active)
        return int(status.split()[-1]) > 0

    async def delete(self, rule_id: int, user_id: int) -> bool:
        """Delete a rule. Returns True if a row was removed."""
        query = "DELETE FROM recurring_rules WHERE id = $1 AND user_id = $2"
        status = await self.execute(query, rule_id, user_id)
        return int(status.split()[-1]) > 0

    async def get_active(self) -> List[RecurringRule]:
        """All active rules across users — the scheduler's work list."""
        query = "SELECT * FROM recurring_rules WHERE active ORDER BY id"
        records = await self.fetch_all(query)
        return [RecurringRule.from_record(r) for r in records]

    async def claim_run(self, rule_id: int, due_date: date) -> bool:
        """Atomically claim one posting period for a rule.

        Advances last_run to due_date only if the rule is active and hasn't
        posted this period yet. Returns True exactly once per (rule, period),
        no matter how many concurrent or restarted runs race for it — the
        caller must skip posting when this returns False.
        """
        query = """
            UPDATE recurring_rules SET last_run = $2
            WHERE id = $1 AND active AND (last_run IS NULL OR last_run < $2)
        """
        status = await self.execute(query, rule_id, due_date)
        return int(status.split()[-1]) > 0
