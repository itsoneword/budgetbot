"""
Tests for src/ask_agent_tools.py — ToolSpec glue for the /ask agent.

Exercises the async handler directly (no CLI, no SDK): argument coercion,
limit clamping, ValueError -> ToolInputError translation, no-match fallback.
"""
from datetime import datetime, timedelta, timezone

import pytest

from domain.ask_tools import MAX_LIMIT
from infrastructure.llm.base import ToolInputError
from src.ask_agent_tools import AgentToolContext, build_ask_toolspecs
from tests.conftest import make_session, make_tx


def _session(transactions=None, categories=None):
    return make_session(transactions=transactions, categories=categories)


def _handler(session):
    specs = build_ask_toolspecs(session)
    assert len(specs) == 1
    assert specs[0].name == "query_transactions"
    return specs[0].handler


async def test_happy_path_returns_rows_and_totals():
    session = _session(transactions=[
        make_tx(timestamp=datetime(2026, 6, 15, tzinfo=timezone.utc), amount="10"),
        make_tx(timestamp=datetime(2026, 6, 16, tzinfo=timezone.utc), amount="30"),
    ])
    text = await _handler(session)({"category": "food"})
    assert "2 transactions matched" in text
    assert "spending 40.00 EUR" in text

def test_toolspec_schema_is_the_domain_schema():
    from domain.ask_tools import QUERY_TRANSACTIONS_SCHEMA
    spec = build_ask_toolspecs(_session())[0]
    assert spec.input_schema is QUERY_TRANSACTIONS_SCHEMA

async def test_amounts_arrive_as_floats_and_are_converted_to_decimal():
    session = _session(transactions=[
        make_tx(amount="100.10"), make_tx(amount="99.90"),
    ])
    text = await _handler(session)({"min_amount": 100.1})
    assert "1 transactions matched" in text
    assert "100.10" in text

async def test_bad_amount_raises_tool_input_error():
    with pytest.raises(ToolInputError, match="min_amount"):
        await _handler(_session(transactions=[make_tx()]))({"min_amount": "lots"})

async def test_bad_period_translated_to_tool_input_error():
    with pytest.raises(ToolInputError, match="Invalid period"):
        await _handler(_session(transactions=[make_tx()]))({"period": "junk"})

async def test_bad_transaction_type_translated():
    with pytest.raises(ToolInputError, match="transaction_type"):
        await _handler(_session(transactions=[make_tx()]))({"transaction_type": "expense"})

async def test_limit_clamped_to_max():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = _session(transactions=[
        make_tx(timestamp=base + timedelta(hours=i)) for i in range(MAX_LIMIT + 50)
    ])
    text = await _handler(session)({"limit": 100000})
    # 250 matched, rows capped at MAX_LIMIT -> truncation note present
    assert f"{MAX_LIMIT} most recent rows" in text

async def test_limit_clamped_up_from_zero():
    session = _session(transactions=[make_tx()])
    text = await _handler(session)({"limit": 0})
    assert "1 transactions matched" in text

async def test_non_integer_limit_raises():
    with pytest.raises(ToolInputError, match="limit"):
        await _handler(_session(transactions=[make_tx()]))({"limit": "many"})

async def test_no_match_lists_known_categories_from_txs_and_dictionary():
    session = _session(
        transactions=[make_tx(category="food")],
        categories={"transport": ["taxi"]},
    )
    text = await _handler(session)({"category": "restaurants"})
    assert "No transactions matched" in text
    assert "food" in text and "transport" in text

async def test_empty_session_no_match_message():
    text = await _handler(_session())({})
    assert "no transactions at all" in text


def test_agent_tool_context_shape_for_write_tools():
    """dv-82c8 interface: repos/user_id/currency/language + mutable staged dict."""
    ctx = AgentToolContext(repos=object(), user_id=100, currency="EUR", language="en")
    assert ctx.staged == {}
    ctx.staged["add_recurring"] = {"item": "rent", "amount": 500, "day": 1}
    assert ctx.staged["add_recurring"]["item"] == "rent"
