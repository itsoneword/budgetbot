"""
Shared test factories and hand-written fakes (no mock library).

make_tx / make_session build domain models with sane defaults; FakeRepos
mimics the shared.di RepositoryContainer surface that domain code touches
(repos.users.get_config, repos.categories.get_dictionary /
find_category_by_subcategory / add_subcategory, repos.transactions
.get_by_date_range / .get_latest). Async methods return canned data and
record their calls for assertions.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest

from domain.models.user_session import Transaction, UserConfig, UserSession

_TX_ID = iter(range(1, 1_000_000))


def make_tx(**overrides) -> Transaction:
    """Transaction with sane defaults: Decimal amount, tz-aware UTC timestamp."""
    defaults = dict(
        id=next(_TX_ID),
        user_id=100,
        timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
        transaction_type="spending",
        category="food",
        subcategory="coffee",
        amount=Decimal("10"),
        currency="EUR",
    )
    defaults.update(overrides)
    if not isinstance(defaults["amount"], Decimal):
        defaults["amount"] = Decimal(str(defaults["amount"]))
    return Transaction(**defaults)


def make_session(
    transactions=None,
    config: Optional[UserConfig] = None,
    categories=None,
    user_id: int = 100,
    transactions_since: Optional[datetime] = None,
) -> UserSession:
    return UserSession(
        user_id=user_id,
        config=config or UserConfig(user_id=user_id),
        categories=categories or {},
        transactions=transactions or [],
        transactions_since=transactions_since,
    )


# ==========================================
# Repo-side canned rows
# ==========================================

@dataclass
class RepoConfig:
    """Row shape returned by UserRepository.get_config."""
    user_id: int
    language: str = "en"
    currency: str = "EUR"
    monthly_limit: Decimal = Decimal("99999999.00")
    name: Optional[str] = None


@dataclass
class RepoTx:
    """Row shape returned by TransactionRepository (category_name/subcategory_name)."""
    id: int
    user_id: int
    timestamp: datetime
    transaction_type: str
    category_name: str
    subcategory_name: str
    amount: Decimal
    currency: str


def make_repo_tx(**overrides) -> RepoTx:
    defaults = dict(
        id=next(_TX_ID),
        user_id=100,
        timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
        transaction_type="spending",
        category_name="food",
        subcategory_name="coffee",
        amount=Decimal("10"),
        currency="EUR",
    )
    defaults.update(overrides)
    if not isinstance(defaults["amount"], Decimal):
        defaults["amount"] = Decimal(str(defaults["amount"]))
    return RepoTx(**defaults)


# ==========================================
# Fakes (plain classes, call-recording)
# ==========================================

class FakeUserRepo:
    def __init__(self, config: Optional[RepoConfig] = None):
        self.config = config
        self.calls = []

    async def get_config(self, user_id: int):
        self.calls.append(("get_config", user_id))
        return self.config


class FakeCategoryRepo:
    def __init__(self, dictionary=None, subcategory_map=None):
        # dictionary: {category: [subcategories]}
        # subcategory_map: {subcategory: [categories]} for find_category_by_subcategory
        self.dictionary = dictionary or {}
        self.subcategory_map = subcategory_map or {}
        self.calls = []

    async def get_dictionary(self, user_id: int, language: str):
        self.calls.append(("get_dictionary", user_id, language))
        return self.dictionary

    async def find_category_by_subcategory(self, user_id: int, subcategory: str, language: str):
        self.calls.append(("find_category_by_subcategory", user_id, subcategory, language))
        return self.subcategory_map.get(subcategory, [])

    async def add_subcategory(self, user_id: int, category: str, subcategory: str, language: str):
        self.calls.append(("add_subcategory", user_id, category, subcategory, language))


class FakeTransactionRepo:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    async def get_by_date_range(self, user_id, start_date, end_date, transaction_type=None):
        self.calls.append(("get_by_date_range", user_id, start_date, end_date, transaction_type))
        return self.rows

    async def get_latest(self, user_id, limit, transaction_type=None):
        self.calls.append(("get_latest", user_id, limit, transaction_type))
        return self.rows


class FakeRepos:
    """Duck-typed stand-in for shared.di.container.Container."""

    def __init__(self, config=None, dictionary=None, subcategory_map=None, tx_rows=None):
        self.users = FakeUserRepo(config)
        self.categories = FakeCategoryRepo(dictionary, subcategory_map)
        self.transactions = FakeTransactionRepo(tx_rows)


@pytest.fixture
def fake_repos():
    return FakeRepos()
