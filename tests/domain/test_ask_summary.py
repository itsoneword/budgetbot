"""
Tests for domain/ask_summary.py.

Asserts key figures/months are present, not full-string snapshots (copy churns).
build_finance_summary computes its recent-days cutoff from the real clock, so
recent-section fixtures use now-relative timestamps.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from domain.ask_summary import build_ask_system_prompt, build_finance_summary
from domain.models.user_session import UserConfig
from tests.conftest import make_session, make_tx


def test_summary_headline_counts_and_currency():
    session = make_session(
        transactions=[
            make_tx(transaction_type="spending"),
            make_tx(transaction_type="income", category="salary"),
        ],
        config=UserConfig(user_id=100, currency="USD"),
    )
    text = build_finance_summary(session)
    assert "Currency: USD" in text
    assert "Transactions loaded: 1 spendings, 1 incomes" in text


def test_monthly_limit_shown_only_when_real():
    limited = make_session(config=UserConfig(user_id=1, monthly_limit=Decimal("1500")))
    unlimited = make_session(config=UserConfig(user_id=1))  # default sentinel 99999999
    assert "Monthly spending limit: 1500" in build_finance_summary(limited)
    assert "Monthly spending limit" not in build_finance_summary(unlimited)


def test_monthly_totals_spend_and_income():
    session = make_session(transactions=[
        make_tx(timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc), amount="100.50"),
        make_tx(timestamp=datetime(2026, 5, 20, tzinfo=timezone.utc), amount="49.50"),
        make_tx(timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
                transaction_type="income", category="salary", amount=2000),
    ])
    text = build_finance_summary(session)
    assert "  2026-05: 150.00 / 0.00" in text
    assert "  2026-06: 0.00 / 2000.00" in text


def test_category_totals_and_income_section():
    session = make_session(transactions=[
        make_tx(category="food", amount=30),
        make_tx(category="rent", amount=500),
        make_tx(transaction_type="income", category="salary", amount=2000),
    ])
    text = build_finance_summary(session)
    assert "  rent: 500.00" in text
    assert "  food: 30.00" in text
    assert "Income per category (whole period):" in text
    assert "  salary: 2000.00" in text


def test_income_section_absent_without_incomes():
    text = build_finance_summary(make_session(transactions=[make_tx()]))
    assert "Income per category" not in text


def test_per_month_per_category_block():
    session = make_session(transactions=[
        make_tx(timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
                category="food", amount=42),
    ])
    text = build_finance_summary(session)
    assert "  2026-06 food: 42.00" in text


def test_per_month_per_category_covers_whole_period():
    """T-049: the breakdown is no longer capped at the last 6 months."""
    session = make_session(transactions=[
        make_tx(timestamp=datetime(2023, 3, 5, tzinfo=timezone.utc),
                category="alcohol", amount=15),
        make_tx(timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
                category="food", amount=42),
    ])
    text = build_finance_summary(session)
    assert "  2023-03 alcohol: 15.00" in text
    assert "  2026-06 food: 42.00" in text


def test_recent_subcategory_detail_uses_real_clock():
    now = datetime.now(timezone.utc)
    session = make_session(transactions=[
        make_tx(timestamp=now - timedelta(days=5), category="food",
                subcategory="coffee", amount=7),
    ])
    text = build_finance_summary(session)
    assert "  food > coffee: 7.00" in text


def test_most_recent_transactions_listed():
    ts = datetime(2026, 6, 15, tzinfo=timezone.utc)
    session = make_session(transactions=[
        make_tx(timestamp=ts, category="food", subcategory="coffee", amount="4.50"),
    ])
    text = build_finance_summary(session)
    assert "  2026-06-15 spending food > coffee: 4.50" in text


def test_data_covers_since_line():
    since = datetime(2025, 7, 1, tzinfo=timezone.utc)
    session = make_session(transactions_since=since)
    assert "Data covers since: 2025-07-01" in build_finance_summary(session)


def test_data_covers_since_derived_from_oldest_tx_on_full_history():
    """T-049: full-history load has transactions_since=None — derive from data."""
    session = make_session(
        transactions=[
            make_tx(timestamp=datetime(2023, 2, 1, tzinfo=timezone.utc)),
            make_tx(timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc)),
        ],
        transactions_since=None,
    )
    assert "Data covers since: 2023-02-01" in build_finance_summary(session)


def test_ask_system_prompt_language():
    assert build_ask_system_prompt("ru").endswith("Answer in Russian.")
    assert build_ask_system_prompt("en").endswith("Answer in English.")


def test_ask_system_prompt_without_tools_has_no_tool_guidance():
    assert "query_transactions" not in build_ask_system_prompt("en")


def test_ask_system_prompt_with_tools_appends_guidance():
    prompt = build_ask_system_prompt("en", tools_enabled=True)
    assert "query_transactions" in prompt
    # summary-first guidance keeps simple aggregate questions zero-tool
    assert "summary" in prompt
    assert prompt.endswith("Answer in English.")


def test_ask_system_prompt_tools_flag_keeps_language_note_ru():
    assert build_ask_system_prompt("ru", tools_enabled=True).endswith("Answer in Russian.")
