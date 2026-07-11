"""
Usage-log parsing shared by admin charts and /admin_stats (T-025).

Lifted from the inline parsing block in src/charts.py
generate_usage_summary_chart. Each relevant line of global_log.txt looks like:

    2026-07-11 10:00:00,123 - UserID: 12345, Name, tg_username, handler_name

(written by src.logger.log_user_interaction).
"""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from src.logger import LogConfig


@dataclass(frozen=True)
class UsageRecord:
    timestamp: datetime
    user_id: str
    name: str
    username: str
    handler: str


def parse_usage_log(
    days: Optional[int] = None,
    log_path: Optional[str] = None,
) -> List[UsageRecord]:
    """
    Parse the user-interaction log into UsageRecords.

    days=N keeps only records from the last N days; None keeps everything.
    A missing log file yields [] (the file starts fresh per deploy volume).
    Malformed lines are skipped silently, matching the old inline parser.
    """
    if log_path is None:
        log_path = os.path.join(LogConfig.LOG_DIR, LogConfig.USER_LOG_FILE)
    if not os.path.exists(log_path):
        return []

    cutoff = datetime.now() - timedelta(days=days) if days is not None else None
    records: List[UsageRecord] = []
    with open(log_path, "r") as log_file:
        for line in log_file:
            line = line.strip()
            if not line:
                continue
            try:
                timestamp_str, remainder = line.split(" - ", 1)
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            except ValueError:
                continue

            if "UserID:" not in remainder:
                continue
            details = remainder.split("UserID:", 1)[1].strip()
            parts = [part.strip() for part in details.split(",")]
            if len(parts) < 4:
                continue

            if cutoff is not None and timestamp < cutoff:
                continue

            user_id, name, username, handler = parts[:4]
            records.append(UsageRecord(timestamp, user_id, name, username, handler))
    return records
