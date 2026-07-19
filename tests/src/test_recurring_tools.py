"""
Tests for src/ai_tools/recurring_tools.py — the /ask agent's recurring tools.

Core invariant: the tools NEVER write. The fake repo records every write-
capable call so any repo mutation fails the test; staging only touches
ctx.staged. Also: no rule IDs in any tool output (owner decision, T-027).
"""
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional

import pytest

from infrastructure.llm.base import ToolInputError
from src.ai_tools.recurring_tools import (
    STAGED_ADD_KEY,
    STAGED_CANCEL_KEY,
    build_recurring_tools,
)
from src.ask_agent_tools import AgentToolContext


@dataclass
class Rule:
    """Duck-typed recurring_repository.RecurringRule."""
    id: int = 777
    subcategory_name: str = "rent"
    amount: float = 500.0
    currency: str = "EUR"
    day_of_month: int = 1
    active: bool = True


class FakeRecurringRepo:
    """list_for_user works; every write-capable method records itself."""

    def __init__(self, rules=None):
        self.rules = rules or []
        self.write_calls = []

    async def list_for_user(self, user_id):
        return list(self.rules)

    async def add(self, **kwargs):
        self.write_calls.append(("add", kwargs))

    async def set_active(self, rule_id, user_id, active):
        self.write_calls.append(("set_active", rule_id, active))

    async def delete(self, rule_id, user_id):
        self.write_calls.append(("delete", rule_id))


def _ctx(rules=None):
    repo = FakeRecurringRepo(rules)
    ctx = AgentToolContext(
        repos=SimpleNamespace(recurring=repo),
        user_id=100, currency="EUR", language="en",
    )
    return ctx, repo


def _tools(ctx):
    specs = {spec.name: spec.handler for spec in build_recurring_tools(ctx)}
    assert set(specs) == {"list_recurring", "add_recurring", "cancel_recurring"}
    return specs


# ==========================================
# list_recurring
# ==========================================

async def test_list_formats_rules_without_ids():
    ctx, repo = _ctx([
        Rule(id=777, subcategory_name="rent"),
        Rule(id=888, subcategory_name="gym", active=False),
    ])
    text = await _tools(ctx)["list_recurring"]({})
    assert "rent" in text and "gym" in text
    assert "777" not in text and "888" not in text
    assert repo.write_calls == [] and ctx.staged == {}


async def test_list_empty():
    ctx, _ = _ctx()
    text = await _tools(ctx)["list_recurring"]({})
    assert "no recurring rules" in text


# ==========================================
# add_recurring — stages, never writes
# ==========================================

async def test_add_stages_and_never_writes():
    ctx, repo = _ctx()
    text = await _tools(ctx)["add_recurring"]({"item": "Rent", "amount": 500, "day": 5})
    assert ctx.staged[STAGED_ADD_KEY] == {
        "name": "rent", "amount": 500.0, "day": 5, "currency": "EUR",
    }
    assert "NOT saved" in text and "tap" in text
    assert repo.write_calls == []


async def test_add_day_defaults_to_1():
    for args in ({"item": "rent", "amount": 500},
                 {"item": "rent", "amount": 500, "day": None}):
        ctx, _ = _ctx()
        await _tools(ctx)["add_recurring"](args)
        assert ctx.staged[STAGED_ADD_KEY]["day"] == 1


async def test_add_last_wins_single_slot():
    ctx, _ = _ctx()
    handler = _tools(ctx)["add_recurring"]
    await handler({"item": "rent", "amount": 500})
    await handler({"item": "netflix", "amount": 12.99, "day": 15})
    assert ctx.staged[STAGED_ADD_KEY]["name"] == "netflix"
    assert len(ctx.staged) == 1


async def test_add_invalid_amount_is_error_and_stages_nothing():
    ctx, repo = _ctx()
    with pytest.raises(ToolInputError, match="amount"):
        await _tools(ctx)["add_recurring"]({"item": "rent", "amount": -5})
    assert ctx.staged == {} and repo.write_calls == []


async def test_add_invalid_day_is_error():
    ctx, _ = _ctx()
    with pytest.raises(ToolInputError, match="day"):
        await _tools(ctx)["add_recurring"]({"item": "rent", "amount": 5, "day": 32})
    assert ctx.staged == {}


async def test_add_missing_item_is_error():
    ctx, _ = _ctx()
    with pytest.raises(ToolInputError, match="item"):
        await _tools(ctx)["add_recurring"]({"amount": 5})
    assert ctx.staged == {}


# ==========================================
# cancel_recurring — 1 match stages; 0/many list candidates, stage nothing
# ==========================================

async def test_cancel_single_match_stages_id_and_name():
    ctx, repo = _ctx([Rule(id=42, subcategory_name="netflix subscription"),
                      Rule(id=43, subcategory_name="rent")])
    text = await _tools(ctx)["cancel_recurring"]({"rule_ref": "netflix"})
    assert ctx.staged[STAGED_CANCEL_KEY] == {"id": 42, "name": "netflix subscription"}
    assert "NOT saved" in text and "pause or delete" in text
    assert "42" not in text  # no rule IDs surfaced to the model
    assert repo.write_calls == []


async def test_cancel_zero_matches_lists_candidates_stages_nothing():
    ctx, _ = _ctx([Rule(id=1, subcategory_name="rent"),
                   Rule(id=2, subcategory_name="gym")])
    text = await _tools(ctx)["cancel_recurring"]({"rule_ref": "spotify"})
    assert ctx.staged == {}
    assert "rent" in text and "gym" in text
    assert "Ask the user" in text


async def test_cancel_many_matches_lists_candidates_stages_nothing():
    ctx, _ = _ctx([Rule(id=91, subcategory_name="netflix subscription"),
                   Rule(id=92, subcategory_name="spotify subscription")])
    text = await _tools(ctx)["cancel_recurring"]({"rule_ref": "subscription"})
    assert ctx.staged == {}
    assert "netflix subscription" in text and "spotify subscription" in text
    assert "91" not in text and "92" not in text  # no rule IDs surfaced
    assert "Ask the user" in text


async def test_cancel_exact_match_beats_substring_ambiguity():
    ctx, _ = _ctx([Rule(id=1, subcategory_name="rent"),
                   Rule(id=2, subcategory_name="rent insurance")])
    await _tools(ctx)["cancel_recurring"]({"rule_ref": "rent"})
    assert ctx.staged[STAGED_CANCEL_KEY] == {"id": 1, "name": "rent"}


async def test_cancel_no_rules_at_all():
    ctx, _ = _ctx()
    text = await _tools(ctx)["cancel_recurring"]({"rule_ref": "rent"})
    assert "no recurring rules" in text
    assert ctx.staged == {}


async def test_cancel_empty_ref_is_error():
    ctx, _ = _ctx([Rule()])
    with pytest.raises(ToolInputError, match="rule_ref"):
        await _tools(ctx)["cancel_recurring"]({})
