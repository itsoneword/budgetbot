"""Tests for domain/recurring.py — bugs here double-post money."""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from domain.recurring import (
    due_date_for,
    format_amount,
    format_rules_list,
    is_due,
    match_rules,
    validate_rule_input,
)


@dataclass
class Rule:
    """Duck-typed rule matching recurring_repository.RecurringRule."""
    day_of_month: int = 5
    active: bool = True
    last_run: Optional[date] = None
    created_at: Optional[datetime] = datetime(2025, 1, 1, tzinfo=timezone.utc)
    subcategory_name: str = "rent"
    amount: float = 500.0
    currency: str = "EUR"


class TestDueDateFor:
    def test_normal_day(self):
        assert due_date_for(2026, 7, 15) == date(2026, 7, 15)

    def test_day_31_clamped_in_february(self):
        assert due_date_for(2026, 2, 31) == date(2026, 2, 28)

    def test_day_31_clamped_in_leap_february(self):
        assert due_date_for(2028, 2, 31) == date(2028, 2, 29)

    def test_day_31_clamped_in_30_day_month(self):
        assert due_date_for(2026, 6, 31) == date(2026, 6, 30)


class TestIsDue:
    def test_inactive_rule_never_due(self):
        assert is_due(Rule(active=False), date(2026, 7, 10)) is None

    def test_due_this_month_not_yet_run(self):
        assert is_due(Rule(day_of_month=5), date(2026, 7, 10)) == date(2026, 7, 5)

    def test_due_date_still_future_falls_back_to_previous_month(self):
        assert is_due(Rule(day_of_month=20), date(2026, 7, 10)) == date(2026, 6, 20)

    def test_january_falls_back_to_december_previous_year(self):
        assert is_due(Rule(day_of_month=20), date(2026, 1, 10)) == date(2025, 12, 20)

    def test_already_run_is_idempotent(self):
        rule = Rule(day_of_month=5, last_run=date(2026, 7, 5))
        assert is_due(rule, date(2026, 7, 10)) is None

    def test_last_run_before_due_still_fires(self):
        rule = Rule(day_of_month=5, last_run=date(2026, 6, 5))
        assert is_due(rule, date(2026, 7, 10)) == date(2026, 7, 5)

    def test_created_after_due_date_never_backfills(self):
        # Rule added on the 11th with day=5 first fires next month
        rule = Rule(day_of_month=5, created_at=datetime(2026, 7, 11, tzinfo=timezone.utc))
        assert is_due(rule, date(2026, 7, 11)) is None

    def test_day_31_rule_in_30_day_month(self):
        assert is_due(Rule(day_of_month=31), date(2026, 6, 30)) == date(2026, 6, 30)


class TestValidateRuleInput:
    def test_valid_input_normalized(self):
        payload, error = validate_rule_input("  Gym  Membership ", "49,99", "15")
        assert error is None
        assert payload == {"name": "gym membership", "amount": 49.99, "day": 15}

    def test_name_empty(self):
        assert validate_rule_input("   ", "10", "1") == (None, "name")

    def test_name_too_long(self):
        assert validate_rule_input("x" * 61, "10", "1") == (None, "name")

    def test_name_command_injection_rejected(self):
        assert validate_rule_input("/leave", "10", "1") == (None, "name")

    def test_amount_not_numeric(self):
        assert validate_rule_input("rent", "ten", "1") == (None, "amount")

    def test_amount_zero_or_negative(self):
        assert validate_rule_input("rent", "0", "1") == (None, "amount")
        assert validate_rule_input("rent", "-5", "1") == (None, "amount")

    def test_amount_above_max(self):
        assert validate_rule_input("rent", "10000001", "1") == (None, "amount")

    def test_amount_nan_and_inf_rejected(self):
        assert validate_rule_input("rent", "nan", "1") == (None, "amount")
        assert validate_rule_input("rent", "inf", "1") == (None, "amount")

    def test_day_not_int(self):
        assert validate_rule_input("rent", "10", "first") == (None, "day")
        assert validate_rule_input("rent", "10", "1.5") == (None, "day")

    def test_day_out_of_range(self):
        assert validate_rule_input("rent", "10", "0") == (None, "day")
        assert validate_rule_input("rent", "10", "32") == (None, "day")

    def test_day_31_accepted(self):
        payload, error = validate_rule_input("rent", "10", "31")
        assert error is None and payload["day"] == 31


class TestMatchRules:
    def _rules(self):
        return [
            Rule(subcategory_name="rent"),
            Rule(subcategory_name="rent insurance"),
            Rule(subcategory_name="netflix subscription"),
            Rule(subcategory_name="spotify subscription"),
        ]

    def test_exact_match_short_circuits_over_substring_hits(self):
        matches = match_rules(self._rules(), "rent")
        assert [r.subcategory_name for r in matches] == ["rent"]

    def test_exact_match_case_and_whitespace_insensitive(self):
        matches = match_rules(self._rules(), "  Rent   Insurance ")
        assert [r.subcategory_name for r in matches] == ["rent insurance"]

    def test_single_token_substring_match(self):
        matches = match_rules(self._rules(), "netflix")
        assert [r.subcategory_name for r in matches] == ["netflix subscription"]

    def test_all_tokens_must_match(self):
        matches = match_rules(self._rules(), "netflix subscription monthly")
        assert matches == []

    def test_partial_word_substring_matches(self):
        matches = match_rules(self._rules(), "sub")
        assert [r.subcategory_name for r in matches] == [
            "netflix subscription", "spotify subscription",
        ]

    def test_zero_matches(self):
        assert match_rules(self._rules(), "gym") == []

    def test_empty_and_whitespace_query_match_nothing(self):
        assert match_rules(self._rules(), "") == []
        assert match_rules(self._rules(), "   ") == []

    def test_empty_rules(self):
        assert match_rules([], "rent") == []


def test_format_amount_drops_trailing_zeros():
    assert format_amount(500.0) == "500"
    assert format_amount(49.99) == "49.99"
    assert format_amount(12.5) == "12.5"
    assert format_amount(1234567.89) == "1234567.89"


def test_format_rules_list_numbering_and_paused_mark():
    rules = [
        Rule(subcategory_name="rent", amount=500, currency="EUR", day_of_month=1),
        Rule(subcategory_name="gym", amount=30, currency="USD", day_of_month=15,
             active=False),
    ]
    text = format_rules_list(rules, paused_label="paused", day_label="day")
    assert text == (
        "1. rent — 500 EUR, day 1\n"
        "2. gym — 30 USD, day 15 (paused)"
    )
