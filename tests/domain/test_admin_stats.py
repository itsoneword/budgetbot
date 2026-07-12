"""Tests for domain/admin_stats.py."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.admin_stats import (
    AdminStats,
    chunk_lines,
    compute_usage_stats,
    count_new_users,
    format_admin_stats,
    format_user_activity_lines,
    latest_names_by_user,
)

NOW = datetime(2026, 7, 10, 12, 0)  # naive local time, like log records


@dataclass
class Record:
    """Duck-typed UsageRecord."""
    timestamp: datetime
    user_id: str = "1"
    name: str = "Alice"
    username: str = "alice"
    handler: str = "menu"


def rec(hours_ago=0, days_ago=0, **overrides):
    return Record(timestamp=NOW - timedelta(days=days_ago, hours=hours_ago), **overrides)


class TestComputeUsageStats:
    def test_dau_wau_mau_windows(self):
        records = [
            rec(hours_ago=2, user_id="1"),               # today -> DAU+WAU+MAU
            rec(days_ago=3, user_id="2", name="Bob", username="bob"),  # WAU+MAU
            rec(days_ago=20, user_id="3"),                # MAU only
            rec(days_ago=40, user_id="4"),                # outside all windows
        ]
        stats = compute_usage_stats(records, NOW)
        assert (stats.dau, stats.wau, stats.mau) == (1, 2, 3)
        assert stats.total_events == 3  # 40d-old record outside 30d window

    def test_future_records_ignored(self):
        records = [Record(timestamp=NOW + timedelta(hours=1))]
        stats = compute_usage_stats(records, NOW)
        assert stats.total_events == 0 and stats.mau == 0

    def test_ai_counts_sorted_descending(self):
        records = (
            [rec(hours_ago=1, handler="ask")] * 1
            + [rec(hours_ago=1, handler="handle_voice")] * 3
            + [rec(hours_ago=1, handler="menu")] * 5
        )
        stats = compute_usage_stats(records, NOW)
        assert stats.ai_total == 4
        assert list(stats.ai_counts.items()) == [("handle_voice", 3), ("ask", 1)]

    def test_wau_labels_deduped_and_sorted_case_insensitively(self):
        records = [
            rec(days_ago=1, user_id="1", name="zoe", username="zzz"),
            rec(days_ago=2, user_id="2", name="Bob", username="bob"),
            rec(days_ago=3, user_id="1", name="zoe", username="zzz"),
        ]
        stats = compute_usage_stats(records, NOW)
        assert stats.wau_labels == ["Bob @bob", "zoe @zzz"]

    def test_missing_name_and_username_labels(self):
        records = [rec(days_ago=1, user_id="1", name="None", username="None")]
        stats = compute_usage_stats(records, NOW)
        assert stats.wau_labels == ["Unknown (no username)"]


def test_count_new_users():
    created = [NOW - timedelta(days=2), NOW - timedelta(days=10), None,
               NOW + timedelta(days=1)]  # future creation excluded
    assert count_new_users(created, NOW, days=7) == 1
    assert count_new_users(created, NOW, days=30) == 2


def test_format_admin_stats_renders_all_sections():
    stats = AdminStats(
        window_days=30, total_events=10, dau=1, wau=2, mau=3,
        ai_total=4, ai_counts={"ask": 4}, wau_labels=["Alice @alice"],
    )
    text = format_admin_stats(stats, total_users=9, total_transactions=100,
                              new_users_7d=1, new_users_30d=2)
    assert "DAU: 1 | WAU: 2 | MAU: 3" in text
    assert "New users: 1 (7d) / 2 (30d)" in text
    assert "Total users: 9 | Total transactions: 100" in text
    assert "  ask: 4" in text
    assert "  Alice @alice" in text


def test_format_user_activity_lines_with_fallbacks():
    @dataclass
    class Row:
        user_id: int
        username: str
        telegram_username: str
        tx_count: int
        last_tx_at: datetime

    rows = [Row(user_id=1, username=None, telegram_username=None,
                tx_count=5, last_tx_at=datetime(2026, 7, 1))]
    lines = format_user_activity_lines(rows, {1: ("Alice", "alice")})
    assert lines == ["1 | @alice | Alice | tx: 5 | last: 2026-07-01"]

    lines = format_user_activity_lines(rows)  # no fallbacks
    assert lines == ["1 | - | - | tx: 5 | last: 2026-07-01"]


class TestLatestNamesByUser:
    def test_latest_non_empty_values_win(self):
        records = [
            rec(user_id="1", name="Old", username="old_handle"),
            rec(user_id="1", name="New", username="None"),
        ]
        assert latest_names_by_user(records) == {1: ("New", "old_handle")}

    def test_non_numeric_ids_skipped(self):
        records = [rec(user_id="not-a-number"), rec(user_id=None)]
        assert latest_names_by_user(records) == {}


class TestChunkLines:
    def test_short_lines_single_chunk(self):
        assert chunk_lines(["a", "b"], limit=100) == ["a\nb"]

    def test_split_at_limit_without_breaking_lines(self):
        chunks = chunk_lines(["aaaa", "bbbb", "cccc"], limit=9)
        assert chunks == ["aaaa\nbbbb", "cccc"]  # "aaaa\nbbbb" is exactly 9 chars

    def test_line_longer_than_limit_truncated(self):
        assert chunk_lines(["x" * 20], limit=10) == ["x" * 10]

    def test_empty_input(self):
        assert chunk_lines([]) == []
