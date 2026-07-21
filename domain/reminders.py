"""
Daily reminders — pure domain logic (T-034). No I/O, no Telegram types.

Timezone model: a fixed UTC offset in minutes (user_configs.tz_offset_min,
NULL = UTC). Deliberately not IANA zones — the offset is captured by the
one-tap "what time is it for you now" picker (build_offset_candidates) and
a fixed offset drifts 1h across DST changes, which is accepted for a daily
nudge (the confirm copy tells users to re-pick when clocks change). Upgrade
path: switch the column to an IANA name and only is_due's offset input
changes.

Reminder objects are duck-typed: anything with `active`, `time_local`
(datetime.time) and `last_sent_on` (Optional[date]) attributes works
(infrastructure.repositories.reminder_repository.Reminder).
"""
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple

# CHECK constraint bounds on user_configs.tz_offset_min (UTC-12:00..UTC+14:00).
TZ_OFFSET_MIN = -720
TZ_OFFSET_MAX = 840

# Every UTC offset observed in the real world (minutes) — drives the one-tap
# picker and validates tzpick_ callback payloads.
REAL_UTC_OFFSETS_MIN: Tuple[int, ...] = (
    -720, -660, -600, -570, -540, -480, -420, -360, -300, -240, -210, -180,
    -120, -60, 0, 60, 120, 180, 210, 240, 270, 300, 330, 345, 360, 390, 420,
    480, 525, 540, 570, 600, 630, 660, 720, 765, 780, 840,
)

# Owner decision 2026-07-11: default reminder time when none specified.
DEFAULT_REMINDER_TIME = time(17, 0)

# dv-ff5f: max active reminder times per user (handler-enforced, not schema).
MAX_REMINDER_TIMES = 3

_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?$")


def parse_reminder_time(raw: str) -> Optional[time]:
    """Parse "HH:MM" or a bare hour ("17") into a time; None when invalid."""
    match = _TIME_RE.match(str(raw).strip())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour, minute)


def format_reminder_time(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def format_utc_offset(offset_min: int) -> str:
    """-330 -> '-05:30', 0 -> '+00:00' (rendered after 'UTC' in copy)."""
    sign = "-" if offset_min < 0 else "+"
    return f"{sign}{abs(offset_min) // 60:02d}:{abs(offset_min) % 60:02d}"


def local_now(now_utc: datetime, tz_offset_min: Optional[int]) -> datetime:
    """The user's local wall clock as a naive datetime (offset applied)."""
    return (now_utc.astimezone(timezone.utc) + timedelta(minutes=tz_offset_min or 0)).replace(
        tzinfo=None
    )


def is_due(reminder, tz_offset_min: Optional[int], now_utc: datetime) -> Optional[date]:
    """Return the local date the reminder should fire for, or None.

    Due when the user's local wall clock has passed time_local and nothing
    was sent for that local date yet (last_sent_on is the idempotency
    cursor — the caller must claim it atomically before sending). A day the
    bot slept through entirely is skipped, never sent late at 3am: once the
    local date rolls over, the missed date can no longer be returned.
    """
    if not reminder.active:
        return None
    local = local_now(now_utc, tz_offset_min)
    if local.time() < reminder.time_local:
        return None
    local_date = local.date()
    if reminder.last_sent_on is not None and reminder.last_sent_on >= local_date:
        return None
    return local_date


def build_offset_candidates(now_utc: datetime) -> List[Tuple[int, str]]:
    """(offset_min, current local time 'HH:MM') for every real UTC offset.

    The picker shows these as buttons — the user taps whichever matches
    their clock, which pins the offset without lists or typing. Offsets 24h
    apart (e.g. UTC-11 vs UTC+13) share a wall-clock time, so those few
    labels additionally carry the offset ("01:07 (+13)") to stay unambiguous;
    every other zone gets a clean time label.
    """
    labels = [
        (offset, format_reminder_time(local_now(now_utc, offset).time()))
        for offset in REAL_UTC_OFFSETS_MIN
    ]
    counts = {}
    for _, label in labels:
        counts[label] = counts.get(label, 0) + 1

    def _disambiguated(offset: int, label: str) -> str:
        if counts[label] == 1:
            return label
        suffix = format_utc_offset(offset)
        if suffix.endswith(":00"):
            suffix = suffix[:-3]
        return f"{label} ({suffix})"

    return [(offset, _disambiguated(offset, label)) for offset, label in labels]
