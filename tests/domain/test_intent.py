"""Tests for domain/intent.py — strict validation of messy LLM replies."""
import json

from domain.intent import (
    INTENT_ADD_INCOME,
    INTENT_ADD_TRANSACTION,
    INTENT_QUESTION,
    INTENT_SHOW_STAT,
    INTENT_UNKNOWN,
    MAX_QUESTION_CHARS,
    build_intent_prompt,
    parse_intent_response,
)


def reply(intent, payload):
    return json.dumps({"intent": intent, "payload": payload})


class TestAddTransaction:
    def test_single_item(self):
        result = parse_intent_response(reply("add_transaction", "coffee 4.5"))
        assert result.kind == INTENT_ADD_TRANSACTION
        assert result.payload == "coffee 4.5"

    def test_multiple_items_comma_separated(self):
        result = parse_intent_response(reply("add_transaction", "пиво 10, продукты 8"))
        assert result.kind == INTENT_ADD_TRANSACTION
        assert result.payload == "пиво 10, продукты 8"

    def test_date_prefix_valid(self):
        result = parse_intent_response(reply("add_transaction", "09.07 beer 10"))
        assert result.kind == INTENT_ADD_TRANSACTION

    def test_date_prefix_invalid_day_or_month(self):
        assert parse_intent_response(
            reply("add_transaction", "32.07 beer 10")
        ).kind == INTENT_UNKNOWN
        assert parse_intent_response(
            reply("add_transaction", "09.13 beer 10")
        ).kind == INTENT_UNKNOWN

    def test_too_many_items(self):
        payload = ", ".join(f"item{i} 5" for i in range(6))
        assert parse_intent_response(reply("add_transaction", payload)).kind == INTENT_UNKNOWN

    def test_missing_amount(self):
        assert parse_intent_response(
            reply("add_transaction", "coffee unknown")
        ).kind == INTENT_UNKNOWN

    def test_amount_zero_or_too_large(self):
        assert parse_intent_response(reply("add_transaction", "x 0")).kind == INTENT_UNKNOWN
        assert parse_intent_response(
            reply("add_transaction", "x 10000001")
        ).kind == INTENT_UNKNOWN

    def test_leading_slash_command_injection_rejected(self):
        assert parse_intent_response(
            reply("add_transaction", "/leave 5")
        ).kind == INTENT_UNKNOWN

    def test_newlines_in_payload_collapsed(self):
        result = parse_intent_response(reply("add_transaction", "coffee\n4.5"))
        assert result.kind == INTENT_ADD_TRANSACTION
        assert result.payload == "coffee 4.5"


class TestAddIncome:
    def test_single_income(self):
        result = parse_intent_response(reply("add_income", "salary 2000"))
        assert result.kind == INTENT_ADD_INCOME
        assert result.payload == "salary 2000"

    def test_income_with_date_prefix(self):
        assert parse_intent_response(
            reply("add_income", "05.07 salary 2000")
        ).kind == INTENT_ADD_INCOME

    def test_income_comma_list_rejected(self):
        assert parse_intent_response(
            reply("add_income", "salary 2000, bonus 500")
        ).kind == INTENT_UNKNOWN

    def test_income_invalid_date(self):
        assert parse_intent_response(
            reply("add_income", "32.07 salary 2000")
        ).kind == INTENT_UNKNOWN

    def test_income_amount_bounds(self):
        assert parse_intent_response(reply("add_income", "salary 0")).kind == INTENT_UNKNOWN


class TestShowStat:
    def test_whitelisted_commands(self):
        for cmd in ("show", "show_last", "show_ext", "monthly_stat", "yearly_stat"):
            result = parse_intent_response(reply("show_stat", cmd))
            assert result.kind == INTENT_SHOW_STAT
            assert result.payload == cmd

    def test_non_whitelisted_command_rejected(self):
        assert parse_intent_response(reply("show_stat", "drop_tables")).kind == INTENT_UNKNOWN


class TestQuestion:
    def test_question_passthrough(self):
        result = parse_intent_response(reply("question", "how much on food?"))
        assert result.kind == INTENT_QUESTION
        assert result.payload == "how much on food?"

    def test_question_truncated(self):
        result = parse_intent_response(reply("question", "x" * 600))
        assert len(result.payload) == MAX_QUESTION_CHARS

    def test_question_leading_slash_stripped(self):
        result = parse_intent_response(reply("question", "/help me"))
        assert result.payload == "help me"

    def test_empty_question_unknown(self):
        assert parse_intent_response(reply("question", "///")).kind == INTENT_UNKNOWN


class TestMalformedReplies:
    def test_markdown_fenced_json(self):
        raw = '```json\n{"intent": "show_stat", "payload": "show"}\n```'
        assert parse_intent_response(raw).kind == INTENT_SHOW_STAT

    def test_surrounding_prose(self):
        raw = 'Sure! Here is the classification: {"intent": "question", "payload": "hi"} Hope it helps.'
        result = parse_intent_response(raw)
        assert result.kind == INTENT_QUESTION
        assert result.payload == "hi"

    def test_no_json_at_all(self):
        assert parse_intent_response("I cannot classify this").kind == INTENT_UNKNOWN

    def test_broken_json(self):
        assert parse_intent_response('{"intent": "question", ').kind == INTENT_UNKNOWN

    def test_json_but_not_a_dict(self):
        assert parse_intent_response("[1, 2, 3]").kind == INTENT_UNKNOWN

    def test_unknown_intent_name(self):
        assert parse_intent_response(reply("delete_everything", "x")).kind == INTENT_UNKNOWN

    def test_non_string_payload_coerced_to_empty(self):
        raw = json.dumps({"intent": "question", "payload": 42})
        assert parse_intent_response(raw).kind == INTENT_UNKNOWN

    def test_explicit_unknown(self):
        result = parse_intent_response(reply("unknown", ""))
        assert result.kind == INTENT_UNKNOWN
        assert result.payload == ""


def test_build_intent_prompt_includes_date_and_truncates():
    prompt = build_intent_prompt("x" * 2000, today="2026-07-11 Friday")
    assert prompt.startswith("Today is 2026-07-11 Friday.")
    assert len(prompt) < 1200  # transcript capped at 1000 chars
