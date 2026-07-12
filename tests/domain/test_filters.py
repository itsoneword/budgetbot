"""Tests for domain/filters.py — every clock pinned via reference_date."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from domain.filters import (
    calculate_daily_average,
    calculate_daily_average_per_category,
    calculate_limit_usage,
    calculate_prediction,
    calculate_summary,
    create_tx_display_mapping,
    filter_by_categories,
    filter_by_period,
    filter_by_type,
    filter_current_month,
    format_period_text,
    format_transactions_for_display,
    get_last_month_summary,
    get_period_summary,
    get_records_summary,
    get_sum_per_category,
    get_sum_per_subcategory,
    get_total,
    get_unique_categories,
    sort_by_date,
)
from tests.conftest import make_tx

REF = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)  # July: 31 days


def tx_at(days_ago: int, **overrides):
    return make_tx(timestamp=REF - timedelta(days=days_ago), **overrides)


# ==========================================
# filter_by_period
# ==========================================

class TestFilterByPeriod:
    def test_3m_window_edges(self):
        inside = tx_at(89)
        boundary = make_tx(timestamp=REF - timedelta(days=90))  # exactly 90d: >= start
        outside = tx_at(91)
        result = filter_by_period([inside, boundary, outside], "3m", reference_date=REF)
        assert result == [inside, boundary]

    def test_6m_window(self):
        inside, outside = tx_at(179), tx_at(181)
        assert filter_by_period([inside, outside], "6m", reference_date=REF) == [inside]

    def test_12m_window(self):
        inside, outside = tx_at(364), tx_at(366)
        assert filter_by_period([inside, outside], "12m", reference_date=REF) == [inside]

    def test_ytd_starts_jan_first(self):
        jan1 = make_tx(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        dec31 = make_tx(timestamp=datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc))
        assert filter_by_period([jan1, dec31], "ytd", reference_date=REF) == [jan1]

    def test_current_month_starts_month_first(self):
        jul1 = make_tx(timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc))
        jun30 = make_tx(timestamp=datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc))
        assert filter_by_period([jul1, jun30], "current_month", reference_date=REF) == [jul1]

    def test_last_month_half_open_interval(self):
        jun1 = make_tx(timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc))
        jun30 = make_tx(timestamp=datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc))
        jul1 = make_tx(timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc))
        may31 = make_tx(timestamp=datetime(2026, 5, 31, 23, 59, tzinfo=timezone.utc))
        result = filter_by_period([jun1, jun30, jul1, may31], "last_month", reference_date=REF)
        assert result == [jun1, jun30]

    def test_last_month_january_rolls_to_previous_year(self):
        ref = datetime(2026, 1, 10, tzinfo=timezone.utc)
        dec = make_tx(timestamp=datetime(2025, 12, 15, tzinfo=timezone.utc))
        nov = make_tx(timestamp=datetime(2025, 11, 30, tzinfo=timezone.utc))
        jan = make_tx(timestamp=datetime(2026, 1, 5, tzinfo=timezone.utc))
        assert filter_by_period([dec, nov, jan], "last_month", reference_date=ref) == [dec]

    def test_unknown_period_defaults_to_30_days(self):
        inside, outside = tx_at(29), tx_at(31)
        assert filter_by_period([inside, outside], "bogus", reference_date=REF) == [inside]


# ==========================================
# Simple filters
# ==========================================

def test_filter_by_categories_empty_list_returns_all():
    txs = [make_tx(category="food"), make_tx(category="rent")]
    assert filter_by_categories(txs, []) == txs


def test_filter_by_categories_filters():
    food, rent = make_tx(category="food"), make_tx(category="rent")
    assert filter_by_categories([food, rent], ["rent"]) == [rent]


def test_filter_by_type():
    spend = make_tx(transaction_type="spending")
    income = make_tx(transaction_type="income")
    assert filter_by_type([spend, income]) == [spend]
    assert filter_by_type([spend, income], "income") == [income]


def test_filter_current_month_matches_year_and_month():
    this_month = make_tx(timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc))
    last_year_same_month = make_tx(timestamp=datetime(2025, 7, 15, tzinfo=timezone.utc))
    assert filter_current_month([this_month, last_year_same_month], REF) == [this_month]


def test_sort_by_date():
    old, new = tx_at(10), tx_at(1)
    assert sort_by_date([old, new]) == [new, old]
    assert sort_by_date([old, new], descending=False) == [old, new]


# ==========================================
# Aggregations
# ==========================================

def test_get_unique_categories_sorted():
    txs = [make_tx(category="rent"), make_tx(category="food"), make_tx(category="food")]
    assert get_unique_categories(txs) == ["food", "rent"]


def test_get_total_is_decimal():
    total = get_total([make_tx(amount="1.10"), make_tx(amount="2.20")])
    assert total == Decimal("3.30")
    assert isinstance(total, Decimal)


def test_get_total_empty_is_zero_decimal():
    assert get_total([]) == Decimal("0")


def test_get_sum_per_category_sorted_descending():
    txs = [
        make_tx(category="food", amount=5),
        make_tx(category="rent", amount=100),
        make_tx(category="food", amount=10),
    ]
    result = get_sum_per_category(txs)
    assert list(result.items()) == [("rent", Decimal("100")), ("food", Decimal("15"))]


def test_get_sum_per_subcategory_filters_and_limits():
    txs = [make_tx(category="food", subcategory=f"s{i}", amount=i) for i in range(1, 9)]
    txs.append(make_tx(category="rent", subcategory="flat", amount=999))
    result = get_sum_per_subcategory(txs, category="food", limit=6)
    assert len(result) == 6
    assert "flat" not in result
    assert list(result)[0] == "s8"  # largest first


def test_calculate_summary_structure():
    txs = [
        make_tx(category="food", subcategory="coffee", amount=4),
        make_tx(category="food", subcategory="lunch", amount=6),
        make_tx(category="rent", subcategory="flat", amount=90),
    ]
    summary = calculate_summary(txs, currency="USD")
    assert summary["total"] == Decimal("100")
    assert summary["currency"] == "USD"
    assert summary["transaction_count"] == 3
    assert summary["category_sums"] == {"rent": Decimal("90"), "food": Decimal("10")}
    assert summary["subcategory_data"]["food"] == {
        "lunch": Decimal("6"), "coffee": Decimal("4")
    }


def test_calculate_summary_respects_category_filter():
    txs = [make_tx(category="food", amount=10), make_tx(category="rent", amount=90)]
    summary = calculate_summary(txs, categories=["food"])
    assert summary["total"] == Decimal("10")
    assert summary["transaction_count"] == 1
    assert list(summary["subcategory_data"]) == ["food"]


# ==========================================
# Daily averages / limits / prediction
# ==========================================

def test_calculate_daily_average_divides_by_day_of_month():
    # REF is July 15 -> divide by 15; only current-month txs count
    txs = [tx_at(1, amount=75), tx_at(2, amount=75),
           make_tx(timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc), amount=999)]
    assert calculate_daily_average(txs, reference_date=REF) == Decimal("10.00")


def test_calculate_daily_average_per_category():
    txs = [tx_at(1, category="food", amount=30), tx_at(2, category="rent", amount=150)]
    result = calculate_daily_average_per_category(txs, reference_date=REF)
    assert result == {"rent": Decimal("10.0"), "food": Decimal("2.0")}


class TestCalculateLimitUsage:
    def test_under_limit(self):
        ref = datetime(2026, 7, 10, tzinfo=timezone.utc)  # day 10 of 31
        txs = [
            make_tx(timestamp=ref - timedelta(days=1), category="food", amount=50),
            make_tx(timestamp=ref - timedelta(days=2), category="rent", amount=100),
        ]
        result = calculate_limit_usage(txs, Decimal("310"), reference_date=ref)
        # excluded rent: daily_limit = (310-100)/31, avg = (150-100)/10
        assert result["daily_limit"] == Decimal("6.77")
        assert result["current_daily_average"] == Decimal("5.00")
        assert result["exceeded"] is False
        assert result["total_spent"] == Decimal("150")
        assert result["remaining"] == Decimal("160")
        # new daily limit for remaining 21 days: (310-150)/21
        assert result["new_daily_limit"] == Decimal("7.62")

    def test_exceeded_with_recovery_days(self):
        ref = datetime(2026, 7, 10, tzinfo=timezone.utc)
        txs = [make_tx(timestamp=ref - timedelta(days=1), category="food", amount=200)]
        result = calculate_limit_usage(txs, Decimal("310"), reference_date=ref)
        assert result["exceeded"] is True
        assert result["percent_difference"] > 0
        assert result["days_zero_spending"] > 0

    def test_income_is_ignored(self):
        ref = datetime(2026, 7, 10, tzinfo=timezone.utc)
        txs = [make_tx(timestamp=ref - timedelta(days=1), transaction_type="income",
                       category="salary", amount=5000)]
        result = calculate_limit_usage(txs, Decimal("310"), reference_date=ref)
        assert result["total_spent"] == Decimal("0")

    def test_overspent_new_daily_limit_clamped_to_zero(self):
        ref = datetime(2026, 7, 10, tzinfo=timezone.utc)
        txs = [make_tx(timestamp=ref - timedelta(days=1), category="food", amount=500)]
        result = calculate_limit_usage(txs, Decimal("310"), reference_date=ref)
        assert result["new_daily_limit"] == Decimal("0")

    def test_custom_exclude_categories(self):
        ref = datetime(2026, 7, 10, tzinfo=timezone.utc)
        txs = [make_tx(timestamp=ref - timedelta(days=1), category="rent", amount=100)]
        result = calculate_limit_usage(
            txs, Decimal("310"), reference_date=ref, exclude_categories=["nothing"]
        )
        assert result["current_daily_average"] == Decimal("10.00")


def test_calculate_prediction_projects_to_month_end():
    ref = datetime(2026, 7, 10, tzinfo=timezone.utc)  # 31-day month, day 10
    txs = [make_tx(timestamp=ref - timedelta(days=1), amount=100)]
    # daily avg 10, 21 days remaining -> 100 + 210
    assert calculate_prediction(txs, reference_date=ref) == Decimal("310.00")


# ==========================================
# Period summaries
# ==========================================

class TestGetPeriodSummary:
    def test_returns_none_when_empty(self):
        assert get_period_summary([], reference_date=REF) is None

    def test_current_month_totals_exclude_rent_investing_from_daily_average(self):
        txs = [
            make_tx(timestamp=datetime(2026, 7, 5, tzinfo=timezone.utc),
                    category="food", amount=150),
            make_tx(timestamp=datetime(2026, 7, 3, tzinfo=timezone.utc),
                    category="rent", amount=300),
        ]
        result = get_period_summary(txs, "current_month", reference_date=REF)
        assert result["total"] == Decimal("450")
        assert result["sum_per_cat"] == {"rent": Decimal("300"), "food": Decimal("150")}
        # total_av_per_day excludes rent: 150 / 15 days
        assert result["total_av_per_day"] == Decimal("10.0")
        # av_per_day is per category incl. rent
        assert result["av_per_day"] == {"rent": Decimal("20.0"), "food": Decimal("10.0")}

    def test_current_month_prediction(self):
        txs = [make_tx(timestamp=datetime(2026, 7, 5, tzinfo=timezone.utc),
                       category="food", amount=150)]
        result = get_period_summary(txs, "current_month", reference_date=REF)
        # av_per_day food = 10.0; 16 days remain of 31 -> 150 + 160
        assert result["prediction"] == Decimal("310.00")

    def test_current_month_filters_type(self):
        txs = [make_tx(timestamp=datetime(2026, 7, 5, tzinfo=timezone.utc),
                       transaction_type="income", category="salary", amount=1000)]
        assert get_period_summary(txs, "current_month", "spending", REF) is None
        income = get_period_summary(txs, "current_month", "income", REF)
        assert income["total"] == Decimal("1000")

    def test_last_month_complete_period(self):
        txs = [
            make_tx(timestamp=datetime(2026, 6, 10, tzinfo=timezone.utc),
                    category="food", amount=300),
            make_tx(timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                    category="food", amount=200),
        ]
        result = get_period_summary(txs, "last_month", reference_date=REF)
        assert result["total"] == Decimal("300")
        # complete month: prediction == actual total
        assert result["prediction"] == Decimal("300")
        # comparison vs May: (300-200)/200 * 100
        assert result["comparison"] == Decimal("50.00")
        # daily average over full June (30 days)
        assert result["total_av_per_day"] == Decimal("10.0")

    def test_last_month_january_reference(self):
        ref = datetime(2026, 1, 20, tzinfo=timezone.utc)
        txs = [make_tx(timestamp=datetime(2025, 12, 10, tzinfo=timezone.utc), amount=310)]
        result = get_period_summary(txs, "last_month", reference_date=ref)
        assert result["total"] == Decimal("310")
        assert result["total_av_per_day"] == Decimal("10.0")  # 31 days in December

    def test_unsupported_period_raises(self):
        import pytest
        with pytest.raises(ValueError):
            get_period_summary([make_tx()], "3m", reference_date=REF)


def test_records_and_last_month_wrappers_delegate():
    txs = [make_tx(timestamp=datetime(2026, 7, 5, tzinfo=timezone.utc), amount=150),
           make_tx(timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc), amount=60)]
    current = get_records_summary(txs, reference_date=REF)
    last = get_last_month_summary(txs, reference_date=REF)
    assert current["total"] == Decimal("150")
    assert last["total"] == Decimal("60")


# ==========================================
# Display helpers
# ==========================================

def test_format_period_text():
    assert format_period_text("3m") == "3 months"
    assert format_period_text("nope") == "selected period"


def test_format_transactions_for_display_numbering():
    tx = make_tx(timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
                 category="food", subcategory="coffee", amount=Decimal("4.50"),
                 currency="EUR")
    lines = format_transactions_for_display([tx], start_index=5)
    assert lines == ["6. 01.07.2026 - food: coffee 4.50 EUR"]


def test_create_tx_display_mapping_pages():
    txs = [make_tx(id=i) for i in range(1, 21)]  # ids 1..20
    page0 = create_tx_display_mapping(txs, page=0, page_size=15)
    page1 = create_tx_display_mapping(txs, page=1, page_size=15)
    assert page0[1] == 1 and page0[15] == 15 and len(page0) == 15
    assert page1 == {1: 16, 2: 17, 3: 18, 4: 19, 5: 20}
