"""
CSV export rendering - pure functions, no I/O.

Format: legacy 7 columns in legacy order (id, timestamp, category,
subcategory, amount, currency, user_id) plus `transaction_type` appended.
The migration importer (scripts/migrate_csv_to_postgres.py) ignores extra
columns, and the explicit type column removes the income-heuristic
dependency for a future restore path.

Consumers: /download (src/core.py), T-015 CSV restore, T-025 /admin_export.
"""
import csv
from io import StringIO
from typing import List

from domain.models.user_session import Transaction

CSV_HEADER = [
    "id",
    "timestamp",
    "category",
    "subcategory",
    "amount",
    "currency",
    "user_id",
    "transaction_type",
]


def render_transactions_csv(transactions: List[Transaction]) -> str:
    """
    Render transactions as a CSV string (legacy columns + transaction_type).

    Rows are sorted ascending by timestamp (repositories return DESC).
    """
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for tx in sorted(transactions, key=lambda t: t.timestamp):
        writer.writerow([
            tx.id,
            tx.iso_timestamp,
            tx.category,
            tx.subcategory,
            tx.amount,
            tx.currency,
            tx.user_id,
            tx.transaction_type,
        ])
    return buffer.getvalue()
