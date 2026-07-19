"""
Recurring transaction rules — pure domain logic (T-026).

This is the action-API validation layer: consumed by the manual /recurring
handlers and (T-027) the AI intent router, so the LLM never gets its own
write path. No I/O, no Telegram types.

Rule objects are duck-typed: any object with `day_of_month`, `active`,
`last_run` (Optional[date]) and `created_at` (Optional[datetime]) attributes
works (infrastructure.repositories.recurring_repository.RecurringRule).
"""
import calendar
from datetime import date
from typing import List, Optional, Tuple

MAX_AMOUNT = 10_000_000
MAX_NAME_CHARS = 60


def due_date_for(year: int, month: int, day_of_month: int) -> date:
    """The rule's due date within a given month, clamping 29-31 to month end."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day_of_month, last_day))


def is_due(rule, today: date) -> Optional[date]:
    """Return the due date the rule should post for, or None.

    Catch-up semantics: the most recent occurrence (this month's due date,
    or last month's if this month's is still in the future) is returned as
    long as it hasn't been posted yet (last_run is the idempotency cursor).
    Only one period per call — the daily job then keeps rules current, and
    a restart after downtime backfills at most the latest missed period.
    Due dates before the rule was created are never posted (a rule added on
    the 11th with day=5 first fires next month, not backdated).
    """
    if not rule.active:
        return None
    due = due_date_for(today.year, today.month, rule.day_of_month)
    if due > today:
        prev_year, prev_month = (
            (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        )
        due = due_date_for(prev_year, prev_month, rule.day_of_month)
    if rule.last_run is not None and rule.last_run >= due:
        return None
    if rule.created_at is not None and rule.created_at.date() > due:
        return None
    return due


def validate_rule_input(name: str, amount: str, day: str) -> Tuple[Optional[dict], Optional[str]]:
    """Strictly validate raw rule input (intent.py-style: any deviation rejects).

    Returns (payload, error): payload is {"name", "amount", "day"} with
    normalized values, error is one of "name" | "amount" | "day".
    """
    name = " ".join(str(name).split())
    if not name or len(name) > MAX_NAME_CHARS or name.startswith("/"):
        return None, "name"
    try:
        amount_val = float(str(amount).replace(",", "."))
    except (TypeError, ValueError):
        return None, "amount"
    if not 0 < amount_val <= MAX_AMOUNT:  # also rejects nan/inf
        return None, "amount"
    try:
        day_val = int(str(day))
    except (TypeError, ValueError):
        return None, "day"
    if not 1 <= day_val <= 31:
        return None, "day"
    return {"name": name.lower(), "amount": round(amount_val, 2), "day": day_val}, None


def match_rules(rules: List, query: str) -> List:
    """Match rules against a free-text name reference (dv-82c8 cancel flow).

    Case-insensitive. An exact (whitespace-normalized) name match
    short-circuits to just those rules — so 'rent' picks the 'rent' rule
    even when 'rent insurance' also exists. Otherwise a rule matches when
    every query token appears as a substring of its name. Empty query
    matches nothing. Never raises — callers turn 0/many matches into a
    clarification, not an error.
    """
    query = " ".join(str(query).lower().split())
    if not query:
        return []
    exact = [r for r in rules if " ".join(r.subcategory_name.lower().split()) == query]
    if exact:
        return exact
    tokens = query.split()
    return [
        r for r in rules
        if all(token in r.subcategory_name.lower() for token in tokens)
    ]


def format_amount(amount: float) -> str:
    """Render a rule amount without trailing zeros: 500.0 -> '500', 12.5 -> '12.5'.

    Used for both display copy and the re-injected '/recurring add' command,
    so the confirm message and the saved rule always show the same number.
    """
    return f"{float(amount):.2f}".rstrip("0").rstrip(".")


def format_rules_list(rules: List, paused_label: str = "paused", day_label: str = "day") -> str:
    """Render rules as numbered lines: 'name — amount CUR, day N' (+ paused mark).

    Labels are passed in by the caller (localized strings) — domain stays
    language-agnostic.
    """
    lines = []
    for i, rule in enumerate(rules, start=1):
        state = "" if rule.active else f" ({paused_label})"
        lines.append(
            f"{i}. {rule.subcategory_name} — {rule.amount} {rule.currency}, "
            f"{day_label} {rule.day_of_month}{state}"
        )
    return "\n".join(lines)
