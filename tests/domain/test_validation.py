"""Tests for domain/validation.py — the T-033 regression surface."""
from datetime import datetime, timedelta, timezone

from domain.validation import FUTURE_GRACE, clamp_future_timestamp, resolve_backdated_year

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)


class TestResolveBackdatedYear:
    def test_past_date_unchanged(self):
        ts = datetime(2026, 3, 1, tzinfo=timezone.utc)
        assert resolve_backdated_year(ts, now=NOW) == ts

    def test_dec_31_entered_in_july_rolls_back_a_year(self):
        ts = datetime(2026, 12, 31, tzinfo=timezone.utc)
        assert resolve_backdated_year(ts, now=NOW) == datetime(
            2025, 12, 31, tzinfo=timezone.utc
        )

    def test_tomorrow_within_grace_unchanged(self):
        ts = NOW + timedelta(hours=20)
        assert resolve_backdated_year(ts, now=NOW) == ts

    def test_just_beyond_grace_rolls_back(self):
        ts = NOW + FUTURE_GRACE + timedelta(seconds=1)
        assert resolve_backdated_year(ts, now=NOW).year == NOW.year - 1

    def test_feb_29_rolling_into_non_leap_year_clamps_to_28(self):
        # 29 Feb 2028 seen from mid-2027 rolls back into non-leap 2027
        now = datetime(2027, 7, 1, tzinfo=timezone.utc)
        ts = datetime(2028, 2, 29, tzinfo=timezone.utc)
        assert resolve_backdated_year(ts, now=now) == datetime(
            2027, 2, 28, tzinfo=timezone.utc
        )

    def test_naive_input_treated_as_utc(self):
        ts = datetime(2026, 12, 31)  # naive
        result = resolve_backdated_year(ts, now=NOW)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025


class TestClampFutureTimestamp:
    def test_past_timestamp_untouched(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert clamp_future_timestamp(ts, now=NOW) == (ts, False)

    def test_within_grace_untouched(self):
        ts = NOW + timedelta(hours=23)
        assert clamp_future_timestamp(ts, now=NOW) == (ts, False)

    def test_beyond_grace_clamped_to_now(self):
        ts = NOW + timedelta(days=400)
        assert clamp_future_timestamp(ts, now=NOW) == (NOW, True)

    def test_naive_input_treated_as_utc(self):
        ts = datetime(2027, 7, 10)  # naive, one year ahead
        clamped, was_clamped = clamp_future_timestamp(ts, now=NOW)
        assert was_clamped is True
        assert clamped == NOW
