"""
Telegram Stars payment audit repository (T-023).

One row per successful Stars purchase. user_id intentionally has no FK —
the refund audit must survive a /leave user-deletion cascade.
telegram_payment_charge_id is UNIQUE: record() is the idempotency gate
against Telegram redelivering a successful_payment update (INSERT ON
CONFLICT DO NOTHING -> False means "already recorded, do not re-grant").
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import asyncpg

from .base import BaseRepository


@dataclass
class AIPayment:
    """Stars payment audit row."""
    id: int
    user_id: int
    telegram_payment_charge_id: str
    invoice_payload: str
    currency: str
    amount: int
    duration_days: Optional[int]  # NULL = perpetual access was sold
    status: str  # 'paid' | 'refunded'
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    refunded_by: Optional[int] = None

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'AIPayment':
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            telegram_payment_charge_id=record['telegram_payment_charge_id'],
            invoice_payload=record['invoice_payload'],
            currency=record['currency'],
            amount=record['amount'],
            duration_days=record['duration_days'],
            status=record['status'],
            paid_at=record.get('paid_at'),
            refunded_at=record.get('refunded_at'),
            refunded_by=record.get('refunded_by'),
        )


class PaymentRepository(BaseRepository[AIPayment]):
    """Repository for the Stars payment audit trail."""

    async def record(
        self,
        user_id: int,
        telegram_payment_charge_id: str,
        invoice_payload: str,
        currency: str,
        amount: int,
        duration_days: Optional[int],
    ) -> bool:
        """Record a successful payment. Returns True if the row was inserted,
        False when the charge_id is already known (Telegram redelivery) —
        the caller must then skip re-granting the entitlement."""
        query = """
            INSERT INTO ai_payments
            (user_id, telegram_payment_charge_id, invoice_payload,
             currency, amount, duration_days)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (telegram_payment_charge_id) DO NOTHING
        """
        status = await self.execute(
            query, user_id, telegram_payment_charge_id, invoice_payload,
            currency, amount, duration_days,
        )
        return status == "INSERT 0 1"

    async def get_latest_paid(self, user_id: int) -> Optional[AIPayment]:
        """Most recent still-'paid' payment of a user (default refund target)."""
        query = """
            SELECT * FROM ai_payments
            WHERE user_id = $1 AND status = 'paid'
            ORDER BY paid_at DESC
            LIMIT 1
        """
        record = await self.fetch_one(query, user_id)
        return AIPayment.from_record(record) if record else None

    async def get_by_charge_id(self, telegram_payment_charge_id: str) -> Optional[AIPayment]:
        """Payment row by Telegram charge id (refund validation)."""
        query = "SELECT * FROM ai_payments WHERE telegram_payment_charge_id = $1"
        record = await self.fetch_one(query, telegram_payment_charge_id)
        return AIPayment.from_record(record) if record else None

    async def mark_refunded(self, telegram_payment_charge_id: str, refunded_by: int) -> bool:
        """Flip a paid row to refunded. False if unknown or already refunded."""
        query = """
            UPDATE ai_payments
            SET status = 'refunded', refunded_at = NOW(), refunded_by = $2
            WHERE telegram_payment_charge_id = $1 AND status = 'paid'
        """
        status = await self.execute(query, telegram_payment_charge_id, refunded_by)
        return status == "UPDATE 1"
