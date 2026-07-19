"""
Tests for domain/ask_tools.py — the /ask agent's query_transactions read tool.

Everything is pure: `now` is injected everywhere the clock matters, so no
fixture depends on the real date.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from domain.ask_tools import (
    DEFAULT_LIMIT,
    MAX_OUTPUT_CHARS,
    QUERY_TRANSACTIONS_SCHEMA,
    format_no_match,
    format_query_result,
    parse_period,
    query_transactions,
)
from tests.conftest import make_tx

NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


# ==========================================
# parse_period
# ==========================================

def test_parse_period_year():
    start, end = parse_period("2024", now=NOW)
    assert start == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert end == datetime(2025, 1, 1, tzinfo=timezone.utc)

def test_parse_period_month():
    start, end = parse_period("2025-11", now=NOW)
    assert start == datetime(2025, 11, 1, tzinfo=timezone.utc)
    assert end == datetime(2025, 12, 1, tzinfo=timezone.utc)

def test_parse_period_december_rolls_year():
    start, end = parse_period("2025-12", now=NOW)
    assert end == datetime(2026, 1, 1, tzinfo=timezone.utc)

def test_parse_period_single_day():
    start, end = parse_period("2026-03-05", now=NOW)
    assert start == datetime(2026, 3, 5, tzinfo=timezone.utc)
    assert end == datetime(2026, 3, 6, tzinfo=timezone.utc)

def test_parse_period_range_end_inclusive():
    start, end = parse_period("2026-01-10..2026-01-20", now=NOW)
    assert start == datetime(2026, 1, 10, tzinfo=timezone.utc)
    # end date itself must be included -> exclusive bound is the next day
    assert end == datetime(2026, 1, 21, tzinfo=timezone.utc)

def test_parse_period_range_end_before_start():
    with pytest.raises(ValueError, match="before start"):
        parse_period("2026-02-01..2026-01-01", now=NOW)

@pytest.mark.parametrize("preset,days", [("3m", 90), ("6m", 180), ("12m", 365)])
def test_parse_period_rolling_presets_match_filter_by_period(preset, days):
    start, end = parse_period(preset, now=NOW)
    assert start == NOW - timedelta(days=days)
    assert end is None

def test_parse_period_ytd_and_current_month():
    assert parse_period("ytd", now=NOW) == (datetime(2026, 1, 1, tzinfo=timezone.utc), None)
    assert parse_period("current_month", now=NOW) == (
        datetime(2026, 7, 1, tzinfo=timezone.utc), None
    )

def test_parse_period_last_month():
    start, end = parse_period("last_month", now=NOW)
    assert start == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 1, tzinfo=timezone.utc)

def test_parse_period_last_month_january_rolls_year():
    jan = datetime(2026, 1, 5, tzinfo=timezone.utc)
    start, end = parse_period("last_month", now=jan)
    assert start == datetime(2025, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 1, 1, tzinfo=timezone.utc)

def test_parse_period_all_is_unbounded():
    assert parse_period("all", now=NOW) == (None, None)

@pytest.mark.parametrize("bad", ["nope", "2026-13", "2026-02-30", "20261", "..", "2026-01-01..x"])
def test_parse_period_invalid_is_model_readable(bad):
    with pytest.raises(ValueError, match="Invalid period|before start"):
        parse_period(bad, now=NOW)


# ==========================================
# query_transactions filtering
# ==========================================

def _fixture():
    return [
        make_tx(timestamp=datetime(2024, 5, 1, tzinfo=timezone.utc),
                category="Food", subcategory="Coffee", amount="3.50"),
        make_tx(timestamp=datetime(2025, 6, 2, tzinfo=timezone.utc),
                category="food", subcategory="groceries", amount="120"),
        make_tx(timestamp=datetime(2026, 6, 3, tzinfo=timezone.utc),
                category="transport", subcategory="taxi", amount="45"),
        make_tx(timestamp=datetime(2026, 7, 4, tzinfo=timezone.utc),
                transaction_type="income", category="salary", subcategory="job",
                amount="2000"),
        make_tx(timestamp=datetime(2026, 7, 10, tzinfo=timezone.utc),
                category="food", subcategory="coffee", amount="4.50"),
    ]

def test_no_filters_matches_everything_newest_first():
    res = query_transactions(_fixture(), now=NOW)
    assert res.total_matches == 5
    assert [t.timestamp.year for t in res.rows] == [2026, 2026, 2026, 2025, 2024]
    assert res.rows[0].subcategory == "coffee"

def test_category_filter_is_case_insensitive():
    res = query_transactions(_fixture(), category="FOOD", now=NOW)
    assert res.total_matches == 3
    assert all(t.category.lower() == "food" for t in res.rows)

def test_subcategory_filter_is_case_insensitive():
    res = query_transactions(_fixture(), subcategory="Coffee", now=NOW)
    assert res.total_matches == 2

def test_transaction_type_filter():
    res = query_transactions(_fixture(), transaction_type="income", now=NOW)
    assert res.total_matches == 1
    assert res.total_income == Decimal("2000")
    assert res.total_spending == Decimal("0")

def test_invalid_transaction_type_raises():
    with pytest.raises(ValueError, match="transaction_type"):
        query_transactions(_fixture(), transaction_type="expense", now=NOW)

def test_amount_bounds_are_inclusive():
    res = query_transactions(_fixture(), min_amount=Decimal("45"),
                             max_amount=Decimal("120"), now=NOW)
    assert res.total_matches == 2  # 45 taxi + 120 groceries, both boundary values

def test_combined_filters():
    res = query_transactions(_fixture(), period="2026", category="food",
                             min_amount=Decimal("1"), now=NOW)
    assert res.total_matches == 1
    assert res.rows[0].amount == Decimal("4.50")

def test_period_boundaries_start_inclusive_end_exclusive():
    txs = [
        make_tx(timestamp=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)),
        make_tx(timestamp=datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)),
    ]
    res = query_transactions(txs, period="2026-06", now=NOW)
    assert res.total_matches == 1
    assert res.rows[0].timestamp.month == 6

def test_bad_period_propagates_value_error():
    with pytest.raises(ValueError, match="Invalid period"):
        query_transactions(_fixture(), period="junk", now=NOW)

def test_empty_transaction_list_fresh_account():
    res = query_transactions([], period="12m", category="food", now=NOW)
    assert res.total_matches == 0
    assert res.rows == []
    assert res.total_spending == Decimal("0")
    assert res.total_income == Decimal("0")

def test_limit_truncates_rows_but_totals_cover_all_matches():
    txs = [
        make_tx(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                amount="10")
        for i in range(30)
    ]
    res = query_transactions(txs, limit=5, now=NOW)
    assert len(res.rows) == 5
    assert res.total_matches == 30
    assert res.total_spending == Decimal("300")
    # newest first even after truncation
    assert res.rows[0].timestamp > res.rows[-1].timestamp

def test_default_limit_is_20():
    txs = [
        make_tx(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i))
        for i in range(25)
    ]
    res = query_transactions(txs, now=NOW)
    assert len(res.rows) == DEFAULT_LIMIT

def test_limit_below_one_raises():
    with pytest.raises(ValueError, match="limit"):
        query_transactions(_fixture(), limit=0, now=NOW)


# ==========================================
# formatting
# ==========================================

def test_format_query_result_header_and_rows():
    res = query_transactions(_fixture(), now=NOW)
    text = format_query_result(res, "EUR")
    assert "5 transactions matched" in text
    assert "spending 173.00 EUR" in text
    assert "income 2000.00 EUR" in text
    assert "2026-07-10 spending food > coffee: 4.50" in text

def test_format_query_result_notes_truncation_of_rows():
    txs = [
        make_tx(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i))
        for i in range(30)
    ]
    res = query_transactions(txs, limit=3, now=NOW)
    text = format_query_result(res, "EUR")
    assert "30 transactions matched" in text
    assert "3 most recent rows" in text

def test_format_query_result_caps_output_at_8kb():
    txs = [
        make_tx(timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i),
                category="some-category-name", subcategory="some-subcategory-name")
        for i in range(500)
    ]
    res = query_transactions(txs, limit=500, now=NOW)  # limit clamping is adapter-side
    text = format_query_result(res, "EUR")
    assert len(text) <= MAX_OUTPUT_CHARS
    assert "truncated at 8KB" in text

def test_format_no_match_lists_known_categories_sorted():
    text = format_no_match(["transport", "food"])
    assert "No transactions matched" in text
    assert "food, transport" in text

def test_format_no_match_without_categories():
    text = format_no_match([])
    assert "no transactions at all" in text


# ==========================================
# schema sanity
# ==========================================

def test_schema_is_full_json_schema_with_optional_params():
    assert QUERY_TRANSACTIONS_SCHEMA["type"] == "object"
    assert QUERY_TRANSACTIONS_SCHEMA["required"] == []
    assert set(QUERY_TRANSACTIONS_SCHEMA["properties"]) == {
        "period", "category", "subcategory", "transaction_type",
        "min_amount", "max_amount", "limit",
    }
