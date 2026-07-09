"""
User session data model - holds all user data loaded in batch.

This model is the core of the "batch fetch + memory filter" architecture.
Load once at the start of a handler chain, filter/aggregate in Python.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict


@dataclass
class UserConfig:
    """User configuration (language, currency, limit)."""
    user_id: int
    language: str = 'en'
    currency: str = 'EUR'
    monthly_limit: Decimal = Decimal('99999999.00')
    name: Optional[str] = None


@dataclass
class Transaction:
    """Single transaction record."""
    id: int
    user_id: int
    timestamp: datetime
    transaction_type: str  # 'spending' | 'income'
    category: str
    subcategory: str
    amount: Decimal
    currency: str

    @classmethod
    def from_repo(cls, tx) -> 'Transaction':
        """Convert a repository Transaction (category_name/subcategory_name) to the domain model."""
        return cls(
            id=tx.id,
            user_id=tx.user_id,
            timestamp=tx.timestamp,
            transaction_type=tx.transaction_type,
            category=tx.category_name,
            subcategory=tx.subcategory_name,
            amount=tx.amount,
            currency=tx.currency,
        )

    @property
    def date(self) -> datetime:
        """Return date portion of timestamp."""
        return self.timestamp.date()

    @property
    def date_str(self) -> str:
        """Format: DD.MM.YYYY"""
        return self.timestamp.strftime("%d.%m.%Y")

    @property
    def iso_timestamp(self) -> str:
        """Format: YYYY-MM-DDTHH:MM:SS"""
        return self.timestamp.strftime("%Y-%m-%dT%H:%M:%S")

    def to_display_string(self) -> str:
        """Format for display in transaction lists."""
        return f"{self.id}: {self.iso_timestamp}, {self.category}, {self.subcategory}, {self.amount}, {self.currency}"


@dataclass
class UserSession:
    """
    Complete user session data - loaded once, used for all operations.

    Usage:
        session = await load_user_session(user_id, repos)
        categories = get_unique_categories(session.transactions)
        summary = calculate_summary(session.transactions, period='3m')
    """
    user_id: int
    config: UserConfig
    categories: Dict[str, List[str]] = field(default_factory=dict)  # category -> [subcategories]
    transactions: List[Transaction] = field(default_factory=list)
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata about what was loaded
    transactions_since: Optional[datetime] = None  # None = all time

    @property
    def language(self) -> str:
        return self.config.language

    @property
    def currency(self) -> str:
        return self.config.currency

    @property
    def monthly_limit(self) -> Decimal:
        return self.config.monthly_limit

    def get_subcategory_to_category_map(self) -> Dict[str, str]:
        """
        Returns inverted dict: subcategory -> category.
        Useful for auto-categorization.
        """
        result = {}
        for category, subcategories in self.categories.items():
            for subcategory in subcategories:
                result[subcategory] = category
        return result

    def category_exists(self, category_name: str) -> bool:
        """Check if category exists (pure Python, no SQL)."""
        return category_name in self.categories

    def subcategory_exists(self, category_name: str, subcategory_name: str) -> bool:
        """Check if subcategory exists (pure Python, no SQL)."""
        return (
            category_name in self.categories and
            subcategory_name in self.categories[category_name]
        )

    def find_category_for_subcategory(self, subcategory_name: str) -> Optional[str]:
        """Find which category contains this subcategory."""
        for category, subcategories in self.categories.items():
            if subcategory_name in subcategories:
                return category
        return None
