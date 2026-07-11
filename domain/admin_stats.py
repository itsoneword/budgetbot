"""
Admin usage statistics - pure functions, no I/O, no Telegram types (T-025).

Consumes UsageRecords parsed from global_log.txt (src/usage_log.py) and
row aggregates from the DB (passed in as plain values). All datetimes here
are naive local time for log records; DB created_at comparisons take
timezone-aware datetimes — callers must pass a matching `now` for each.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Sequence

# Handler names (as logged by log_user_interaction) that hit the LLM.
AI_FUNCTIONS = frozenset({"ask", "handle_voice"})

TELEGRAM_MESSAGE_LIMIT = 4096


@dataclass
class AdminStats:
    """Usage stats over log records. DAU/WAU/MAU use fixed 1/7/30-day windows."""
    window_days: int
    total_events: int
    dau: int
    wau: int
    mau: int
    ai_total: int
    ai_counts: Dict[str, int] = field(default_factory=dict)  # handler -> count
    wau_labels: List[str] = field(default_factory=list)  # active last 7d, display strings


def _label(name: str, username: str) -> str:
    display_name = name if name and name != "None" else "Unknown"
    display_username = f"@{username}" if username and username != "None" else "(no username)"
    return f"{display_name} {display_username}"


def compute_usage_stats(
    records: Sequence,
    now: datetime,
    window_days: int = 30,
) -> AdminStats:
    """
    Compute DAU/WAU/MAU (distinct users in the last 1/7/30 days), total events
    and per-AI-function counts within `window_days`.

    `records` are UsageRecords (or anything with .timestamp/.user_id/.name/
    .username/.handler). Records newer than `now` are ignored.
    """
    day_cut = now - timedelta(days=1)
    week_cut = now - timedelta(days=7)
    month_cut = now - timedelta(days=30)
    window_cut = now - timedelta(days=window_days)

    dau_ids, wau_ids, mau_ids = set(), set(), set()
    labels: Dict[str, str] = {}
    ai_counts: Dict[str, int] = {}
    total_events = 0

    for r in records:
        if r.timestamp > now:
            continue
        if r.timestamp >= window_cut:
            total_events += 1
            if r.handler in AI_FUNCTIONS:
                ai_counts[r.handler] = ai_counts.get(r.handler, 0) + 1
        if r.timestamp >= month_cut:
            mau_ids.add(r.user_id)
        if r.timestamp >= week_cut:
            wau_ids.add(r.user_id)
            labels[r.user_id] = _label(r.name, r.username)
        if r.timestamp >= day_cut:
            dau_ids.add(r.user_id)

    return AdminStats(
        window_days=window_days,
        total_events=total_events,
        dau=len(dau_ids),
        wau=len(wau_ids),
        mau=len(mau_ids),
        ai_total=sum(ai_counts.values()),
        ai_counts=dict(sorted(ai_counts.items(), key=lambda kv: -kv[1])),
        wau_labels=sorted(labels.values(), key=str.lower),
    )


def count_new_users(created_ats: Sequence[datetime], now: datetime, days: int) -> int:
    """Count creation timestamps within the last `days`. `now` must match tz-awareness."""
    cutoff = now - timedelta(days=days)
    return sum(1 for created in created_ats if created is not None and cutoff <= created <= now)


def format_admin_stats(
    stats: AdminStats,
    total_users: int,
    total_transactions: int,
    new_users_7d: int,
    new_users_30d: int,
) -> str:
    """Render /admin_stats reply (plain text, admin-facing, EN only)."""
    lines = [
        f"Usage stats — last {stats.window_days} days",
        f"Events logged: {stats.total_events}",
        f"DAU: {stats.dau} | WAU: {stats.wau} | MAU: {stats.mau}",
        f"New users: {new_users_7d} (7d) / {new_users_30d} (30d)",
        f"Total users: {total_users} | Total transactions: {total_transactions}",
        f"AI calls: {stats.ai_total}",
    ]
    for handler, count in stats.ai_counts.items():
        lines.append(f"  {handler}: {count}")
    if stats.wau_labels:
        lines.append("Active last 7 days:")
        for label in stats.wau_labels:
            lines.append(f"  {label}")
    return "\n".join(lines)


def format_user_activity_lines(rows: Sequence, name_fallbacks: dict = None) -> List[str]:
    """
    Render /admin_users lines from repository UserActivity rows
    (.user_id/.username/.telegram_username/.tx_count/.last_tx_at).
    Rows arrive sorted by last activity desc (SQL ORDER BY).

    name_fallbacks maps user_id -> (name, tg_username) harvested from the
    usage log, used when the users table columns are NULL (they are never
    populated by onboarding as of T-025).
    """
    fallbacks = name_fallbacks or {}
    lines = []
    for row in rows:
        fb_name, fb_tg = fallbacks.get(row.user_id, (None, None))
        last = row.last_tx_at.strftime("%Y-%m-%d") if row.last_tx_at else "never"
        tg = row.telegram_username or fb_tg
        username = f"@{tg}" if tg else "-"
        name = row.username or fb_name or "-"
        lines.append(f"{row.user_id} | {username} | {name} | tx: {row.tx_count} | last: {last}")
    return lines


def latest_names_by_user(records: Sequence) -> dict:
    """
    Map int user_id -> (name, telegram_username) from UsageRecords, keeping
    the most recent non-empty values per user (records are chronological).
    UsageRecord.user_id is a string parsed from the log; non-numeric ids are
    skipped. 'None' strings are log artifacts of absent values.
    """
    names = {}
    for r in records:
        try:
            uid = int(r.user_id)
        except (TypeError, ValueError):
            continue
        name = r.name if r.name and r.name != "None" else None
        tg = r.username if r.username and r.username != "None" else None
        prev_name, prev_tg = names.get(uid, (None, None))
        names[uid] = (name or prev_name, tg or prev_tg)
    return names


def chunk_lines(lines: Sequence[str], limit: int = TELEGRAM_MESSAGE_LIMIT) -> List[str]:
    """
    Pack lines into messages of at most `limit` chars (Telegram cap),
    joining with newlines and never splitting a line across messages.
    A single line longer than `limit` is truncated.
    """
    chunks: List[str] = []
    current = ""
    for line in lines:
        if len(line) > limit:
            line = line[:limit]
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
