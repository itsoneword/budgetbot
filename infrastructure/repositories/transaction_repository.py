"""
Transaction repository for database operations on transactions.
Replaces file_ops.py and pandas_ops.py transaction-related functions.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, date
from decimal import Decimal
from dataclasses import dataclass
import asyncpg

from .base import BaseRepository


@dataclass
class Transaction:
    """Transaction data model."""
    id: Optional[int]
    user_id: int
    timestamp: datetime
    transaction_type: str  # 'spending' | 'income'
    category_name: str
    subcategory_name: str
    amount: Decimal
    currency: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'Transaction':
        """Create Transaction from database record."""
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            timestamp=record['timestamp'],
            transaction_type=record['transaction_type'],
            category_name=record['category_name'],
            subcategory_name=record['subcategory_name'],
            amount=record['amount'],
            currency=record['currency'],
            created_at=record.get('created_at'),
        )


@dataclass
class UserActivity:
    """Per-user activity aggregate for /admin_users and /admin_stats (T-025)."""
    user_id: int
    username: Optional[str]
    telegram_username: Optional[str]
    created_at: Optional[datetime]
    tx_count: int
    last_tx_at: Optional[datetime]


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for transaction CRUD operations."""
    
    # ==========================================
    # CREATE
    # ==========================================
    
    async def save(self, transaction: Transaction) -> int:
        """
        Save a new transaction and return its ID.
        Replaces: file_ops.save_user_transaction
        """
        query = """
            INSERT INTO transactions 
            (user_id, timestamp, transaction_type, category_name, subcategory_name, amount, currency)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        # Ensure timestamp is timezone-aware
        ts = transaction.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        
        return await self.fetch_val(
            query,
            transaction.user_id,
            ts,
            transaction.transaction_type,
            transaction.category_name,
            transaction.subcategory_name,
            transaction.amount,
            transaction.currency,
        )
    
    async def save_spending(
        self,
        user_id: int,
        category: str,
        subcategory: str,
        amount: float,
        currency: str,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """Convenience method for saving a spending transaction."""
        tx = Transaction(
            id=None,
            user_id=user_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            transaction_type='spending',
            category_name=category,
            subcategory_name=subcategory,
            amount=Decimal(str(amount)),
            currency=currency.upper()[:3],
        )
        return await self.save(tx)
    
    async def save_income(
        self,
        user_id: int,
        category: str,
        subcategory: str,
        amount: float,
        currency: str,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """Convenience method for saving an income transaction."""
        tx = Transaction(
            id=None,
            user_id=user_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            transaction_type='income',
            category_name=category,
            subcategory_name=subcategory,
            amount=Decimal(str(amount)),
            currency=currency.upper()[:3],
        )
        return await self.save(tx)
    
    # ==========================================
    # READ
    # ==========================================
    
    async def get_by_id(self, transaction_id: int, user_id: int) -> Optional[Transaction]:
        """Get a single transaction by ID (with user verification)."""
        query = """
            SELECT * FROM transactions 
            WHERE id = $1 AND user_id = $2
        """
        record = await self.fetch_one(query, transaction_id, user_id)
        return Transaction.from_record(record) if record else None
    
    # NOTE: get_current_month, get_last_month removed - use domain/filters.py instead

    async def get_by_date_range(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        transaction_type: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Transaction]:
        """Get transactions within a date range with optional filters."""
        conditions = ["user_id = $1", "timestamp >= $2", "timestamp < $3"]
        params: List[Any] = [user_id, start_date, end_date]
        
        if transaction_type:
            params.append(transaction_type)
            conditions.append(f"transaction_type = ${len(params)}")
        
        if categories:
            params.append(categories)
            conditions.append(f"category_name = ANY(${len(params)})")
        
        query = f"""
            SELECT * FROM transactions
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
        """
        records = await self.fetch_all(query, *params)
        return [Transaction.from_record(r) for r in records]
    
    async def get_latest(
        self,
        user_id: int,
        limit: int = 10,
        transaction_type: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Get the most recent transactions.
        Replaces: file_ops.get_latest_records
        """
        if transaction_type:
            query = """
                SELECT * FROM transactions
                WHERE user_id = $1 AND transaction_type = $2
                ORDER BY timestamp DESC
                LIMIT $3
            """
            records = await self.fetch_all(query, user_id, transaction_type, limit)
        else:
            query = """
                SELECT * FROM transactions
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """
            records = await self.fetch_all(query, user_id, limit)
        
        return [Transaction.from_record(r) for r in records]
    
    # ==========================================
    # AGGREGATIONS - REMOVED
    # ==========================================
    # All aggregation methods moved to domain/filters.py:
    # - get_monthly_summary -> get_sum_per_category()
    # - get_monthly_total -> get_total()
    # - get_daily_average -> calculate_daily_average()
    # - get_daily_average_per_category -> calculate_daily_average_per_category()
    # - get_records_data -> get_records_summary()
    # - calculate_limit_usage_detailed -> calculate_limit_usage()
    # - calculate_limit_usage -> calculate_limit_usage()
    #
    # Use: load_user_session() + filter functions instead of SQL aggregations

    # ==========================================
    # UPDATE
    # ==========================================
    
    async def update(
        self,
        transaction_id: int,
        user_id: int,
        **fields,
    ) -> bool:
        """Update specific fields of a transaction."""
        if not fields:
            return False
        
        allowed_fields = {
            'timestamp', 'category_name', 'subcategory_name', 
            'amount', 'currency', 'transaction_type'
        }
        
        updates = []
        params = []
        param_idx = 1
        
        for field, value in fields.items():
            if field not in allowed_fields:
                continue
            params.append(value)
            updates.append(f"{field} = ${param_idx}")
            param_idx += 1
        
        if not updates:
            return False
        
        params.extend([transaction_id, user_id])
        query = f"""
            UPDATE transactions 
            SET {', '.join(updates)}
            WHERE id = ${param_idx} AND user_id = ${param_idx + 1}
        """
        
        result = await self.execute(query, *params)
        return result == "UPDATE 1"
    
    # ==========================================
    # DELETE
    # ==========================================
    
    async def delete(self, transaction_id: int, user_id: int) -> bool:
        """
        Delete a transaction by ID.
        Replaces: file_ops.delete_record
        """
        query = """
            DELETE FROM transactions 
            WHERE id = $1 AND user_id = $2
        """
        result = await self.execute(query, transaction_id, user_id)
        return result == "DELETE 1"
    
    async def delete_all_for_user(self, user_id: int) -> int:
        """Delete all transactions for a user (for CSV upload replacement)."""
        query = "DELETE FROM transactions WHERE user_id = $1"
        result = await self.execute(query, user_id)
        # Parse "DELETE X" to get count
        return int(result.split()[-1]) if result else 0
    
    # ==========================================
    # UTILITY
    # ==========================================
    
    async def get_activity_by_user(self) -> List[UserActivity]:
        """
        All users with transaction count and last transaction time,
        most recently active first (T-025 /admin_users, /admin_stats).
        """
        query = """
            SELECT u.user_id, u.username, u.telegram_username, u.created_at,
                   COUNT(t.id) AS tx_count, MAX(t.timestamp) AS last_tx_at
            FROM users u
            LEFT JOIN transactions t ON t.user_id = u.user_id
            GROUP BY u.user_id, u.username, u.telegram_username, u.created_at
            ORDER BY last_tx_at DESC NULLS LAST, u.user_id
        """
        records = await self.fetch_all(query)
        return [
            UserActivity(
                user_id=r['user_id'],
                username=r['username'],
                telegram_username=r['telegram_username'],
                created_at=r['created_at'],
                tx_count=r['tx_count'],
                last_tx_at=r['last_tx_at'],
            )
            for r in records
        ]

    async def count_for_user(self, user_id: int) -> int:
        """Count total transactions for a user."""
        query = "SELECT COUNT(*) FROM transactions WHERE user_id = $1"
        return await self.fetch_val(query, user_id)
    
    async def get_frequent_categories(
        self,
        user_id: int,
        limit: int = 5,
    ) -> List[str]:
        """
        Get most frequently used categories.
        Replaces: file_ops.get_frequently_used_categories
        """
        query = """
            SELECT category_name, COUNT(*) as cnt
            FROM transactions
            WHERE user_id = $1
            GROUP BY category_name
            ORDER BY cnt DESC
            LIMIT $2
        """
        records = await self.fetch_all(query, user_id, limit)
        return [r['category_name'] for r in records]
    
    async def get_recent_amounts(
        self,
        user_id: int,
        category: str,
        subcategory: str,
        limit: int = 3,
    ) -> List[Decimal]:
        """
        Get recent amounts for a category/subcategory combination.
        Replaces: file_ops.get_recent_amounts
        """
        query = """
            SELECT amount FROM transactions
            WHERE user_id = $1 
              AND category_name = $2 
              AND subcategory_name = $3
            ORDER BY timestamp DESC
            LIMIT $4
        """
        records = await self.fetch_all(query, user_id, category, subcategory, limit)
        return [r['amount'] for r in records]
