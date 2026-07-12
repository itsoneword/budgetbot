"""Async tests for domain/session_loader.py against hand-written FakeRepos."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from domain.models.user_session import UserSession
from domain.session_loader import (
    load_minimal_session,
    load_user_session,
    refresh_transactions,
)
from tests.conftest import FakeRepos, RepoConfig, make_repo_tx, make_session


def window_start_dates(months: int):
    """Acceptable start_date values around 'now' (call may straddle midnight)."""
    return {
        (datetime.now(timezone.utc) - timedelta(days=months * 30)).date(),
        (datetime.now(timezone.utc) - timedelta(days=months * 30, seconds=5)).date(),
    }


async def test_config_mapped_from_repo_row():
    repos = FakeRepos(config=RepoConfig(
        user_id=7, language="ru", currency="USD",
        monthly_limit=Decimal("1500"), name="Alice",
    ))
    session = await load_user_session(7, repos)
    assert session.config.language == "ru"
    assert session.config.currency == "USD"
    assert session.config.monthly_limit == Decimal("1500")
    assert session.config.name == "Alice"
    assert repos.users.calls == [("get_config", 7)]


async def test_missing_config_falls_back_to_defaults():
    repos = FakeRepos(config=None)
    session = await load_user_session(7, repos)
    assert session.config.user_id == 7
    assert session.config.language == "en"
    assert session.config.currency == "EUR"


async def test_categories_loaded_with_config_language():
    repos = FakeRepos(
        config=RepoConfig(user_id=7, language="ru"),
        dictionary={"food": ["coffee"]},
    )
    session = await load_user_session(7, repos)
    assert session.categories == {"food": ["coffee"]}
    assert repos.categories.calls == [("get_dictionary", 7, "ru")]


async def test_transactions_converted_from_repo_rows():
    row = make_repo_tx(id=1, category_name="food", subcategory_name="coffee",
                       amount=Decimal("4.50"))
    repos = FakeRepos(tx_rows=[row])
    session = await load_user_session(7, repos)
    assert len(session.transactions) == 1
    tx = session.transactions[0]
    assert (tx.category, tx.subcategory, tx.amount) == ("food", "coffee", Decimal("4.50"))


async def test_months_window_and_type_passed_to_date_range_query():
    repos = FakeRepos()
    session = await load_user_session(
        7, repos, transactions_months=6, transaction_type="income"
    )
    method, user_id, start_date, end_date, tx_type = repos.transactions.calls[0]
    assert method == "get_by_date_range"
    assert user_id == 7
    assert start_date in window_start_dates(6)
    assert end_date == date(2099, 12, 31)
    assert tx_type == "income"
    assert session.transactions_since is not None


async def test_zero_months_falls_back_to_get_latest_all_time():
    repos = FakeRepos()
    session = await load_user_session(7, repos, transactions_months=0)
    assert repos.transactions.calls == [("get_latest", 7, 10000, None)]
    assert session.transactions_since is None


async def test_load_transactions_false_skips_transaction_queries():
    repos = FakeRepos(tx_rows=[make_repo_tx()])
    session = await load_user_session(7, repos, load_transactions=False)
    assert session.transactions == []
    assert session.transactions_since is None
    assert repos.transactions.calls == []


async def test_load_minimal_session_skips_transactions():
    repos = FakeRepos(tx_rows=[make_repo_tx()])
    session = await load_minimal_session(7, repos)
    assert isinstance(session, UserSession)
    assert session.transactions == []
    assert repos.transactions.calls == []


async def test_refresh_transactions_keeps_config_and_categories():
    old_session = make_session(user_id=7, categories={"food": ["coffee"]})
    row = make_repo_tx(category_name="rent", subcategory_name="flat")
    repos = FakeRepos(tx_rows=[row])

    refreshed = await refresh_transactions(old_session, repos, months=1,
                                           transaction_type="spending")
    assert refreshed.config is old_session.config
    assert refreshed.categories is old_session.categories
    assert [tx.category for tx in refreshed.transactions] == ["rent"]
    method, user_id, start_date, _end, tx_type = repos.transactions.calls[0]
    assert (method, user_id, tx_type) == ("get_by_date_range", 7, "spending")
    assert start_date in window_start_dates(1)
    # config/user repos untouched on refresh
    assert repos.users.calls == []
