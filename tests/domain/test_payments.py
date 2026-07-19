"""Tests for the AI-access invoice payload codec (T-023, domain/payments.py).

The payload is the source of truth for what a payment grants: a stale
invoice paid after a config change must grant what it advertised, and the
pre-checkout gate must reject anything that doesn't parse.
"""
import pytest

from domain.payments import AIPurchaseTerms, encode_ai_payload, parse_ai_payload


class TestEncode:
    def test_days(self):
        assert encode_ai_payload(30) == "ai:30"

    def test_one_day(self):
        assert encode_ai_payload(1) == "ai:1"

    def test_perpetual_none(self):
        assert encode_ai_payload(None) == "ai:perp"

    def test_perpetual_zero(self):
        # AI_ACCESS_DAYS=0 means "sell perpetual access".
        assert encode_ai_payload(0) == "ai:perp"

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            encode_ai_payload(-5)


class TestParse:
    def test_days(self):
        assert parse_ai_payload("ai:30") == AIPurchaseTerms(duration_days=30)

    def test_perpetual(self):
        assert parse_ai_payload("ai:perp") == AIPurchaseTerms(duration_days=None)

    def test_roundtrip(self):
        for days in (None, 1, 30, 365):
            assert parse_ai_payload(encode_ai_payload(days)) == AIPurchaseTerms(
                duration_days=days
            )

    @pytest.mark.parametrize(
        "payload",
        [
            "",                # empty
            "ai:",             # no terms
            "ai:0",            # zero-day pass was never sold
            "ai:-3",           # negative
            "ai:30.5",         # not an int
            "ai:thirty",       # garbage terms
            "AI:30",           # wrong case prefix
            "other:30",        # foreign product payload
            "30",              # missing prefix
            "ai:perpetual",    # wrong perpetual marker
        ],
    )
    def test_invalid_payloads_return_none(self, payload):
        assert parse_ai_payload(payload) is None

    def test_non_string_returns_none(self):
        assert parse_ai_payload(None) is None
