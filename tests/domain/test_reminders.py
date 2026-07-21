"""Tests for domain/reminders.py — bugs here spam users or eat their nudges."""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Optional

from domain.reminders import (
    MAX_REMINDER_TIMES,
    format_reminder_time,
    is_due,
    parse_reminder_time,
)


@dataclass
class Reminder:
    """Duck-typed reminder matching reminder_repository.Reminder."""
    time_local: time = time(17, 0)
    active: bool = True
    last_sent_on: Optional[date] = None


def _utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


class TestParseReminderTime:
    def test_full_form(self):
        assert parse_reminder_time("17:00") == time(17, 0)

    def test_single_digit_hour_with_minutes(self):
        assert parse_reminder_time("9:30") == time(9, 30)

    def test_bare_hour(self):
        assert parse_reminder_time("17") == time(17, 0)

    def test_strips_whitespace(self):
        assert parse_reminder_time("  12:15 ") == time(12, 15)

    def test_midnight(self):
        assert parse_reminder_time("0:00") == time(0, 0)

    def test_hour_out_of_range(self):
        assert parse_reminder_time("24:00") is None

    def test_minute_out_of_range(self):
        assert parse_reminder_time("17:60") is None

    def test_garbage(self):
        assert parse_reminder_time("evening") is None

    def test_empty(self):
        assert parse_reminder_time("") is None

    def test_negative(self):
        assert parse_reminder_time("-5:00") is None

    def test_format_round_trips_through_parse(self):
        # rem_del_HH:MM callback data relies on this round-trip.
        for t in (time(0, 0), time(9, 5), time(23, 59)):
            assert parse_reminder_time(format_reminder_time(t)) == t


class TestIsDue:
    def test_due_when_local_time_passed(self):
        r = Reminder(time_local=time(17, 0))
        assert is_due(r, 0, _utc(2026, 7, 21, 17, 30)) == date(2026, 7, 21)

    def test_not_due_before_local_time(self):
        r = Reminder(time_local=time(17, 0))
        assert is_due(r, 0, _utc(2026, 7, 21, 16, 59)) is None

    def test_not_due_when_already_sent_today(self):
        r = Reminder(time_local=time(17, 0), last_sent_on=date(2026, 7, 21))
        assert is_due(r, 0, _utc(2026, 7, 21, 18, 0)) is None

    def test_due_again_next_day(self):
        r = Reminder(time_local=time(17, 0), last_sent_on=date(2026, 7, 20))
        assert is_due(r, 0, _utc(2026, 7, 21, 17, 0)) == date(2026, 7, 21)

    def test_not_due_when_inactive(self):
        r = Reminder(time_local=time(17, 0), active=False)
        assert is_due(r, 0, _utc(2026, 7, 21, 18, 0)) is None

    def test_tz_offset_shifts_local_clock(self):
        # 15:30 UTC at +120 is 17:30 local — due; at 0 it is not.
        r = Reminder(time_local=time(17, 0))
        assert is_due(r, 120, _utc(2026, 7, 21, 15, 30)) == date(2026, 7, 21)
        assert is_due(r, 0, _utc(2026, 7, 21, 15, 30)) is None

    def test_tz_offset_shifts_local_date(self):
        # 23:00 UTC at +180 is 02:00 the NEXT local day.
        r = Reminder(time_local=time(1, 0))
        assert is_due(r, 180, _utc(2026, 7, 21, 23, 0)) == date(2026, 7, 22)

    def test_none_offset_means_utc(self):
        r = Reminder(time_local=time(17, 0))
        assert is_due(r, None, _utc(2026, 7, 21, 17, 0)) == date(2026, 7, 21)


class TestMultipleTimesIndependentCursors:
    """dv-ff5f: two same-user rows fire independently, once each per day."""

    def test_two_times_fire_independently_same_day(self):
        morning = Reminder(time_local=time(9, 0))
        evening = Reminder(time_local=time(18, 0))

        # 12:00 local: morning due, evening not yet.
        noon = _utc(2026, 7, 21, 12, 0)
        assert is_due(morning, 0, noon) == date(2026, 7, 21)
        assert is_due(evening, 0, noon) is None

        # Claim the morning send (what claim_send does on its row only).
        morning.last_sent_on = date(2026, 7, 21)
        assert is_due(morning, 0, noon) is None

        # 19:00 local: evening fires despite the morning's claim.
        later = _utc(2026, 7, 21, 19, 0)
        assert is_due(morning, 0, later) is None
        assert is_due(evening, 0, later) == date(2026, 7, 21)

        evening.last_sent_on = date(2026, 7, 21)
        assert is_due(evening, 0, later) is None

        # Next day both are due again.
        tomorrow = _utc(2026, 7, 22, 20, 0)
        assert is_due(morning, 0, tomorrow) == date(2026, 7, 22)
        assert is_due(evening, 0, tomorrow) == date(2026, 7, 22)

    def test_cap_constant(self):
        assert MAX_REMINDER_TIMES == 3
