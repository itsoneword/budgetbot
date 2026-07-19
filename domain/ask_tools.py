"""
Pure logic for the /ask agent's read tool: query_transactions.

Filters the in-memory transaction list the ask flow already loads (full
history, see T-049) — no SQL surface the model can influence; user scoping is
structural because the list is per-session. Totals are computed over ALL
matches before truncation, so "sum of spendings over 100" is answerable even
when only the newest rows are shown.

No I/O, no Telegram types. `now` is injectable for tests.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from domain.models.user_session import Transaction

DEFAULT_LIMIT = 20
MAX_LIMIT = 200
MAX_OUTPUT_CHARS = 8192  # hard cap on formatted tool output

_PRESETS = ("3m", "6m", "12m", "ytd", "current_month", "last_month", "all")

# JSON Schema handed to the model verbatim (SDK passes through full schemas).
QUERY_TRANSACTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "period": {
            "type": "string",
            "description": (
                "Time period: 'YYYY' (year), 'YYYY-MM' (month), 'YYYY-MM-DD' "
                "(single day), 'YYYY-MM-DD..YYYY-MM-DD' (inclusive range), or "
                "a preset: 3m, 6m, 12m, ytd, current_month, last_month, all. "
                "Omit for all time."
            ),
        },
        "category": {
            "type": "string",
            "description": "Filter by category name (case-insensitive exact match).",
        },
        "subcategory": {
            "type": "string",
            "description": "Filter by subcategory name (case-insensitive exact match).",
        },
        "transaction_type": {
            "type": "string",
            "enum": ["spending", "income"],
            "description": "Only spendings or only incomes. Omit for both.",
        },
        "min_amount": {
            "type": "number",
            "description": "Only transactions with amount >= this value.",
        },
        "max_amount": {
            "type": "number",
            "description": "Only transactions with amount <= this value.",
        },
        "limit": {
            "type": "integer",
            "description": (
                f"Max rows returned, newest first (default {DEFAULT_LIMIT}, "
                f"max {MAX_LIMIT}). Counts and totals always cover ALL matches "
                "regardless of limit."
            ),
        },
    },
    "required": [],
}


@dataclass
class QueryResult:
    """Rows are newest-first and truncated to limit; totals cover all matches."""
    rows: List[Transaction]
    total_matches: int
    total_spending: Decimal
    total_income: Decimal


def parse_period(
    period: str, now: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse a period string into a [start, end) UTC datetime window.

    Either bound may be None (open). Raises ValueError with a model-readable
    message on unknown formats. Preset semantics match domain.filters
    .filter_by_period (90/180/365-day windows, calendar ytd/months).
    """
    now = now or datetime.now(timezone.utc)
    p = (period or "").strip()

    if p == "all":
        return None, None
    if p == "3m":
        return now - timedelta(days=90), None
    if p == "6m":
        return now - timedelta(days=180), None
    if p == "12m":
        return now - timedelta(days=365), None
    if p == "ytd":
        return datetime(now.year, 1, 1, tzinfo=timezone.utc), None
    if p == "current_month":
        return datetime(now.year, now.month, 1, tzinfo=timezone.utc), None
    if p == "last_month":
        if now.month == 1:
            start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
        else:
            start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        return start, datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    invalid = ValueError(
        f"Invalid period '{period}'. Use 'YYYY', 'YYYY-MM', 'YYYY-MM-DD', "
        f"'YYYY-MM-DD..YYYY-MM-DD', or one of: {', '.join(_PRESETS)}."
    )
    if ".." in p:
        start_s, end_s = (s.strip() for s in p.split("..", 1))
        try:
            start = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise invalid
        if end < start:
            raise ValueError(f"Period end {end_s} is before start {start_s}.")
        return start, end + timedelta(days=1)  # inclusive end date
    if len(p) == 4 and p.isdigit():
        year = int(p)
        return (
            datetime(year, 1, 1, tzinfo=timezone.utc),
            datetime(year + 1, 1, 1, tzinfo=timezone.utc),
        )
    if len(p) == 7:
        try:
            start = datetime.strptime(p, "%Y-%m").replace(tzinfo=timezone.utc)
        except ValueError:
            raise invalid
        if start.month == 12:
            return start, datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
        return start, datetime(start.year, start.month + 1, 1, tzinfo=timezone.utc)
    if len(p) == 10:
        try:
            start = datetime.strptime(p, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise invalid
        return start, start + timedelta(days=1)
    raise invalid


def query_transactions(
    transactions: List[Transaction],
    period: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    limit: int = DEFAULT_LIMIT,
    now: Optional[datetime] = None,
) -> QueryResult:
    """Filter the transaction list; return newest-first rows + full-match totals.

    Raises ValueError (model-readable) on bad period / transaction_type / limit.
    """
    if transaction_type is not None and transaction_type not in ("spending", "income"):
        raise ValueError(
            f"Invalid transaction_type '{transaction_type}': use 'spending' or 'income'."
        )
    if limit < 1:
        raise ValueError("limit must be >= 1")

    start = end = None
    if period is not None:
        start, end = parse_period(period, now=now)

    cat = category.strip().lower() if category else None
    sub = subcategory.strip().lower() if subcategory else None

    matches = []
    for tx in transactions:
        if start is not None and tx.timestamp < start:
            continue
        if end is not None and tx.timestamp >= end:
            continue
        if transaction_type is not None and tx.transaction_type != transaction_type:
            continue
        if cat is not None and (tx.category or "").strip().lower() != cat:
            continue
        if sub is not None and (tx.subcategory or "").strip().lower() != sub:
            continue
        if min_amount is not None and tx.amount < min_amount:
            continue
        if max_amount is not None and tx.amount > max_amount:
            continue
        matches.append(tx)

    matches.sort(key=lambda t: t.timestamp, reverse=True)
    total_spending = sum(
        (t.amount for t in matches if t.transaction_type == "spending"), Decimal(0)
    )
    total_income = sum(
        (t.amount for t in matches if t.transaction_type == "income"), Decimal(0)
    )
    return QueryResult(
        rows=matches[:limit],
        total_matches=len(matches),
        total_spending=total_spending,
        total_income=total_income,
    )


def format_query_result(result: QueryResult, currency: str) -> str:
    """Render a QueryResult as compact model-readable text, capped at 8KB."""
    header = (
        f"{result.total_matches} transactions matched. Totals over ALL matches: "
        f"spending {result.total_spending:.2f} {currency}, "
        f"income {result.total_income:.2f} {currency}."
    )
    lines = [header]
    if result.total_matches > len(result.rows):
        lines.append(
            f"Showing the {len(result.rows)} most recent rows; "
            "the totals above already cover every match."
        )
    for tx in result.rows:
        lines.append(
            f"{tx.timestamp.strftime('%Y-%m-%d')} {tx.transaction_type} "
            f"{tx.category} > {tx.subcategory}: {tx.amount:.2f}"
        )

    out: List[str] = []
    size = 0
    note = "\n[output truncated at 8KB — narrow the filters or lower the limit]"
    for line in lines:
        if size + len(line) + 1 > MAX_OUTPUT_CHARS - len(note):
            out.append(note.lstrip("\n"))
            break
        out.append(line)
        size += len(line) + 1
    return "\n".join(out)


def format_no_match(known_categories: List[str]) -> str:
    """Zero-match reply that lets the model self-correct spellings in one round."""
    if known_categories:
        return (
            "No transactions matched these filters. "
            f"Known categories: {', '.join(sorted(known_categories))}. "
            "Check the category/subcategory spelling or widen the period/amount filters."
        )
    return "No transactions matched these filters, and the user has no transactions at all."
