"""Tests for domain/export.py — CSV column order is a re-import contract."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO

from domain.export import CSV_HEADER, render_transactions_csv
from tests.conftest import make_tx


def parse(csv_text):
    return list(csv.reader(StringIO(csv_text)))


def test_header_is_legacy_columns_plus_transaction_type():
    assert CSV_HEADER == [
        "id", "timestamp", "category", "subcategory",
        "amount", "currency", "user_id", "transaction_type",
    ]
    rows = parse(render_transactions_csv([]))
    assert rows == [CSV_HEADER]


def test_row_values_and_column_order():
    tx = make_tx(
        id=7,
        user_id=42,
        timestamp=datetime(2026, 3, 5, 14, 30, 15, tzinfo=timezone.utc),
        category="food",
        subcategory="coffee",
        amount=Decimal("4.50"),
        currency="EUR",
        transaction_type="spending",
    )
    rows = parse(render_transactions_csv([tx]))
    assert rows[1] == [
        "7", "2026-03-05T14:30:15", "food", "coffee", "4.50", "EUR", "42", "spending"
    ]


def test_rows_sorted_ascending_by_timestamp():
    newer = make_tx(id=2, timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc))
    older = make_tx(id=1, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    rows = parse(render_transactions_csv([newer, older]))
    assert [r[0] for r in rows[1:]] == ["1", "2"]


def test_fields_with_commas_survive_roundtrip():
    tx = make_tx(subcategory="coffee, beans")
    rows = parse(render_transactions_csv([tx]))
    assert rows[1][3] == "coffee, beans"


def test_income_type_column():
    tx = make_tx(transaction_type="income", category="salary")
    rows = parse(render_transactions_csv([tx]))
    assert rows[1][-1] == "income"
