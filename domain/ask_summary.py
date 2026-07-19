"""
Build a compact text summary of a user's finances for LLM Q&A (/ask).

Pure functions over UserSession — no I/O, no Telegram types. The summary is
packed into the LLM prompt directly (per-user data is small), so it must stay
compact: monthly and per-category totals for the whole loaded period, plus a
recent category/subcategory breakdown.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from domain.models.user_session import UserSession, Transaction

RECENT_DAYS = 92  # ~3 months of subcategory-level detail


def _month_key(tx: Transaction) -> str:
    return tx.timestamp.strftime("%Y-%m")


def build_finance_summary(session: UserSession) -> str:
    """Render the user's transactions as a compact plain-text summary."""
    spendings = [t for t in session.transactions if t.transaction_type == "spending"]
    incomes = [t for t in session.transactions if t.transaction_type == "income"]

    lines: List[str] = []
    lines.append(f"Currency: {session.currency}")
    if session.config.monthly_limit and session.config.monthly_limit < Decimal("99999999"):
        lines.append(f"Monthly spending limit: {session.config.monthly_limit}")
    lines.append(f"Transactions loaded: {len(spendings)} spendings, {len(incomes)} incomes")
    # Full-history loads (T-049) have no explicit window — derive the start
    # from the data so the model states its coverage correctly.
    since = session.transactions_since
    if since is None and session.transactions:
        since = min(t.timestamp for t in session.transactions)
    if since:
        lines.append(f"Data covers since: {since.date().isoformat()}")

    # Monthly totals (spending and income)
    monthly_spend: dict = defaultdict(Decimal)
    monthly_income: dict = defaultdict(Decimal)
    for t in spendings:
        monthly_spend[_month_key(t)] += t.amount
    for t in incomes:
        monthly_income[_month_key(t)] += t.amount

    lines.append("\nMonthly totals (month: spent / income):")
    for month in sorted(set(monthly_spend) | set(monthly_income)):
        lines.append(
            f"  {month}: {monthly_spend.get(month, Decimal(0)):.2f}"
            f" / {monthly_income.get(month, Decimal(0)):.2f}"
        )

    # Per-category totals over the whole period
    cat_totals: dict = defaultdict(Decimal)
    for t in spendings:
        cat_totals[t.category] += t.amount
    lines.append("\nSpending per category (whole period):")
    for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
        lines.append(f"  {cat}: {total:.2f}")

    # Income per category over the whole period (T-035) — income volume is
    # tiny next to spendings, so the prompt-size cost is negligible.
    if incomes:
        income_totals: dict = defaultdict(Decimal)
        for t in incomes:
            income_totals[t.category] += t.amount
        lines.append("\nIncome per category (whole period):")
        for cat, total in sorted(income_totals.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {total:.2f}")

    # Per-month per-category totals over the whole period — needed for
    # questions like "how much did I spend on X last month?" or "which month
    # was my max on X in 2024?" (T-049). Size is months x active categories,
    # ~25 chars a line — even multi-year histories stay a few KB.
    month_cat: dict = defaultdict(Decimal)
    for t in spendings:
        month_cat[(_month_key(t), t.category)] += t.amount
    if month_cat:
        lines.append("\nPer-category totals by month (whole period):")
        for (month, cat), total in sorted(month_cat.items()):
            lines.append(f"  {month} {cat}: {total:.2f}")

    # Recent detail: category>subcategory for the last ~3 months
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    recent = [t for t in spendings if t.timestamp >= cutoff]
    if recent:
        subcat_totals: dict = defaultdict(Decimal)
        for t in recent:
            subcat_totals[(t.category, t.subcategory)] += t.amount
        lines.append(f"\nRecent {RECENT_DAYS} days, category > subcategory:")
        for (cat, sub), total in sorted(subcat_totals.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat} > {sub}: {total:.2f}")

    # Last few transactions verbatim — lets the model answer "when did I last..."
    last = sorted(session.transactions, key=lambda t: t.timestamp, reverse=True)[:15]
    if last:
        lines.append("\nMost recent transactions (date, type, category, subcategory, amount):")
        for t in last:
            lines.append(
                f"  {t.timestamp.strftime('%Y-%m-%d')} {t.transaction_type}"
                f" {t.category} > {t.subcategory}: {t.amount:.2f}"
            )

    return "\n".join(lines)


def build_ask_system_prompt(language: str) -> str:
    """System prompt for the /ask Q&A call."""
    lang_note = (
        "Answer in Russian." if language == "ru" else "Answer in English."
    )
    return (
        "You are a personal finance assistant inside a Telegram budget bot. "
        "You are given a summary of the user's own spending and income data, "
        "then their question. Answer using only the provided data; if the data "
        "is insufficient, say what is missing. The data contains both income "
        "and spending — compare them when relevant (savings rate, income vs "
        "outcome, suggestions). You are read-only: you cannot add, edit or "
        "delete records. If the user asks you to record something, say so and "
        "point them to the working paths: /income (e.g. /income salary 2000) "
        "for income, plain text like 'coffee 4.5' or a voice message for "
        "spendings. Be concise — a few short "
        "sentences or a small list; this is a chat message, not a report. "
        "Round amounts sensibly and always mention the currency. "
        "Write plain text only — no markdown, no asterisks, no headers. "
        + lang_note
    )
