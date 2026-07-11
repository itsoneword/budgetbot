"""
Transaction timestamp validation (T-033). Pure logic — no I/O.

Users backfill spendings with a "dd.mm" prefix; the parser has to guess the
year. Guessing the current year turned "31.12" entered in July into a date
five months in the future, so:

- resolve_backdated_year(): if the current-year interpretation lands in the
  future, the user meant the previous year.
- clamp_future_timestamp(): safety net at the save path — no entry path may
  persist a timestamp beyond now + FUTURE_GRACE.

FUTURE_GRACE is 1 day: users ahead of UTC can legitimately produce "tomorrow"
(their today), and a transaction dated one day ahead is harmless, while
silently shifting it a year back is data corruption.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

FUTURE_GRACE = timedelta(days=1)


def _as_utc(ts: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never raise."""
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts


def resolve_backdated_year(ts: datetime, now: Optional[datetime] = None) -> datetime:
    """
    Resolve the year of a date parsed without an explicit year (dd.mm input,
    interpreted with the current year): if it is more than FUTURE_GRACE in
    the future, the user meant the previous year — roll back one year.
    """
    ts = _as_utc(ts)
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    if ts > now + FUTURE_GRACE:
        try:
            return ts.replace(year=ts.year - 1)
        except ValueError:  # 29 Feb rolled into a non-leap year
            return ts.replace(year=ts.year - 1, day=28)
    return ts


def clamp_future_timestamp(
    ts: datetime, now: Optional[datetime] = None
) -> Tuple[datetime, bool]:
    """
    Safety net for every save path: clamp timestamps more than FUTURE_GRACE
    ahead of now back to now. Returns (timestamp, was_clamped) so the caller
    can log a warning — a triggered clamp means an upstream parser misfired.
    """
    ts = _as_utc(ts)
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    if ts > now + FUTURE_GRACE:
        return now, True
    return ts, False
