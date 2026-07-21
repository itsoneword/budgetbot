"""
Parser tests for src/save_transaction.py (acceptance: multi-line/ambiguous input).

These functions call datetime.now() internally, so the clock is frozen with
freezegun instead of passing a reference date. Frozen mid-year so both the
"date in the past of this year" and "backdated into last year" branches are
exercised deterministically.
"""
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from src.save_transaction import (
    _parse_date_to_utc,
    _parse_income_date,
    process_income_input,
    process_transaction_input_async,
)
from tests.conftest import FakeRepos

FROZEN = "2026-07-10 12:00:00"
FROZEN_NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)


# ==========================================
# process_income_input
# ==========================================

@freeze_time(FROZEN)
class TestProcessIncomeInput:
    def test_amount_only_defaults_to_now_and_salary(self):
        timestamp, category = process_income_input(1, ["1000"])
        assert timestamp == FROZEN_NOW
        assert category == "salary"

    def test_two_parts_date_amount(self):
        timestamp, category = process_income_input(1, ["05.07", "1000"])
        assert timestamp == datetime(2026, 7, 5, tzinfo=timezone.utc)
        assert category == "salary"

    def test_two_parts_category_amount(self):
        timestamp, category = process_income_input(1, ["freelance", "1000"])
        assert timestamp == FROZEN_NOW
        assert category == "freelance"

    def test_three_parts_date_category_amount(self):
        timestamp, category = process_income_input(1, ["05.07", "bonus", "1000"])
        assert timestamp == datetime(2026, 7, 5, tzinfo=timezone.utc)
        assert category == "bonus"

    def test_three_parts_no_date_uses_first_as_category(self):
        timestamp, category = process_income_input(1, ["sidegig", "extra", "1000"])
        assert timestamp == FROZEN_NOW
        assert category == "sidegig"

    def test_backdated_ddmm_rolls_into_previous_year(self):
        # "31.12" entered in July means last December, not next (T-033)
        timestamp, _ = process_income_input(1, ["31.12", "1000"])
        assert timestamp == datetime(2025, 12, 31, tzinfo=timezone.utc)

    def test_date_shaped_garbage_propagates_value_error(self):
        # 29.02 in the frozen non-leap 2026: the ValueError from
        # _parse_income_date must reach the caller — the token is never
        # silently reinterpreted as a category (dv-5465)
        with pytest.raises(ValueError):
            process_income_input(1, ["29.02", "1000"])


# ==========================================
# _parse_income_date
# ==========================================

@freeze_time(FROZEN)
class TestParseIncomeDate:
    def test_ddmm_past_this_year(self):
        assert _parse_income_date("05.07") == datetime(2026, 7, 5, tzinfo=timezone.utc)

    def test_ddmm_future_rolls_back_a_year(self):
        assert _parse_income_date("31.12") == datetime(2025, 12, 31, tzinfo=timezone.utc)

    def test_explicit_future_year_left_alone(self):
        # Explicit years bypass the backdating heuristic (clamped at save path)
        parsed = _parse_income_date("15.03.2027")
        assert parsed == datetime(2027, 3, 15, tzinfo=timezone.utc)

    def test_explicit_past_year(self):
        assert _parse_income_date("15.03.2024") == datetime(2024, 3, 15, tzinfo=timezone.utc)

    def test_non_date_token_returns_none(self):
        assert _parse_income_date("salary") is None

    def test_ddmm_shaped_garbage_rejected(self):
        # "99.99" is date-shaped but not a valid date: rejected outright —
        # the old dateutil fallback read "99" as year 1999 (dv-5465)
        with pytest.raises(ValueError):
            _parse_income_date("99.99")

    def test_feb_29_in_non_leap_year_rejected(self):
        # Frozen 2026 is not a leap year: 29.02 must error, not be
        # reinterpreted as day 29 of the current month (dv-5465)
        with pytest.raises(ValueError):
            _parse_income_date("29.02")

    @freeze_time("2024-07-10 12:00:00")
    def test_feb_29_valid_in_leap_year(self):
        assert _parse_income_date("29.02") == datetime(
            2024, 2, 29, tzinfo=timezone.utc
        )

    def test_two_digit_year_rejected(self):
        # Only dd.mm.yyyy carries an explicit year; "24" is ambiguous
        with pytest.raises(ValueError):
            _parse_income_date("15.03.24")

    def test_one_digit_year_garbage_rejected(self):
        # Date-shaped with a bogus year — dateutil used to read 2001-01-01
        with pytest.raises(ValueError):
            _parse_income_date("1.1.1")

    def test_bare_year_is_not_a_date(self):
        # dateutil freebie dropped: INCOME_HELP advertises dd.mm only, and
        # "2024" is a plausible amount/category (dv-5465)
        assert _parse_income_date("2024") is None

    def test_bare_day_is_not_a_date(self):
        assert _parse_income_date("12") is None

    def test_slash_separated_is_not_a_date(self):
        assert _parse_income_date("05/07") is None


# ==========================================
# _parse_date_to_utc
# ==========================================

@freeze_time(FROZEN)
class TestParseDateToUtc:
    def test_past_ddmm_keeps_current_year(self):
        assert _parse_date_to_utc("05.07") == "2026-07-05T00:00:00"

    def test_future_ddmm_rolls_back_a_year(self):
        assert _parse_date_to_utc("31.12") == "2025-12-31T00:00:00"

    def test_invalid_input_raises(self):
        with pytest.raises(ValueError):
            _parse_date_to_utc("notadate")


# ==========================================
# process_transaction_input_async
# ==========================================

def repos_with(subcategory_map=None):
    return FakeRepos(subcategory_map=subcategory_map or {})


@freeze_time(FROZEN)
class TestProcessTransactionInputAsync:
    async def test_short_format_known_subcategory(self):
        repos = repos_with({"coffee": ["food"]})
        timestamp, category, subcategory, unknown = await process_transaction_input_async(
            1, ["coffee", "4.5"], repos
        )
        assert timestamp == "2026-07-10T12:00:00"
        assert (category, subcategory, unknown) == ("food", "coffee", False)

    async def test_short_format_unknown_subcategory_defaults_to_other(self):
        repos = repos_with()
        _, category, subcategory, unknown = await process_transaction_input_async(
            1, ["mystery", "9"], repos
        )
        assert (category, subcategory, unknown) == ("other", "mystery", True)

    async def test_date_subcategory_amount(self):
        repos = repos_with({"coffee": ["food"]})
        timestamp, category, subcategory, unknown = await process_transaction_input_async(
            1, ["05.07", "coffee", "4.5"], repos
        )
        assert timestamp == "2026-07-05T00:00:00"
        assert (category, subcategory, unknown) == ("food", "coffee", False)

    async def test_backdated_date_prefix_rolls_into_previous_year(self):
        repos = repos_with({"coffee": ["food"]})
        timestamp, _, _, _ = await process_transaction_input_async(
            1, ["31.12", "coffee", "4.5"], repos
        )
        assert timestamp == "2025-12-31T00:00:00"

    async def test_category_subcategory_amount_registers_mapping(self):
        repos = repos_with()
        timestamp, category, subcategory, unknown = await process_transaction_input_async(
            1, ["food", "coffee", "4.5"], repos, language="en"
        )
        assert timestamp == "2026-07-10T12:00:00"
        assert (category, subcategory, unknown) == ("food", "coffee", False)
        assert ("add_subcategory", 1, "food", "coffee", "en") in repos.categories.calls

    async def test_date_category_subcategory_amount(self):
        repos = repos_with()
        timestamp, category, subcategory, unknown = await process_transaction_input_async(
            1, ["05.07", "food", "coffee", "4.5"], repos
        )
        assert timestamp == "2026-07-05T00:00:00"
        assert (category, subcategory, unknown) == ("food", "coffee", False)

    async def test_invalid_date_like_prefix_falls_back_to_now(self):
        # "99.99" starts and ends with a digit but isn't a date: parse fails,
        # timestamp stays "now", token is treated as the subcategory slot
        repos = repos_with({"coffee": ["food"]})
        timestamp, category, subcategory, _ = await process_transaction_input_async(
            1, ["99.99", "coffee", "4.5"], repos
        )
        assert timestamp == "2026-07-10T12:00:00"
        assert (category, subcategory) == ("food", "coffee")

    async def test_string_user_id_coerced_to_int(self):
        repos = repos_with({"coffee": ["food"]})
        await process_transaction_input_async("1", ["coffee", "4.5"], repos, "en")
        assert repos.categories.calls == [
            ("find_category_by_subcategory", 1, "coffee", "en")
        ]
