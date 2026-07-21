"""Tests for domain/intent.py — strict validation of messy LLM replies."""
import json
from dataclasses import dataclass

from domain.intent import (
    CONTEXT_ANSWER_CHARS,
    CONTEXT_BLOCK_CHARS,
    CONTEXT_SUMMARY_CHARS,
    CONTEXT_TRANSCRIPT_CHARS,
    INTENT_ADD_INCOME,
    INTENT_ADD_TRANSACTION,
    INTENT_CHAT,
    INTENT_CONFIRM_PENDING,
    INTENT_QUESTION,
    INTENT_SHOW_STAT,
    INTENT_UNKNOWN,
    KNOWN_ITEMS_MAX,
    MAX_PARTIAL_CHARS,
    MAX_QUESTION_CHARS,
    build_intent_prompt,
    build_intent_system_prompt,
    find_correction_target,
    find_pending_proposal,
    format_known_items,
    format_recent_context,
    parse_intent_response,
    validate_add_payload,
)


def reply(intent, payload, **extra):
    return json.dumps({"intent": intent, "payload": payload, **extra})


@dataclass
class StubInteraction:
    """Attribute shape of InteractionRepository.AIInteraction rows."""
    transcript: str
    intent: str = "add_transaction"
    payload: str = "дом 5"
    outcome: str = "proposed"
    id: int = 1


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
    assert len(prompt) < 1300  # transcript capped at 1000 chars


class TestCorrectsPrevious:
    def test_add_transaction_true(self):
        result = parse_intent_response(
            reply("add_transaction", "дом 5", corrects_previous=True)
        )
        assert result.kind == INTENT_ADD_TRANSACTION
        assert result.corrects_previous is True

    def test_add_income_true(self):
        result = parse_intent_response(
            reply("add_income", "salary 2000", corrects_previous=True)
        )
        assert result.kind == INTENT_ADD_INCOME
        assert result.corrects_previous is True

    def test_defaults_to_false_when_absent(self):
        assert parse_intent_response(
            reply("add_transaction", "coffee 4.5")
        ).corrects_previous is False

    def test_non_boolean_values_ignored(self):
        for bad in ("true", 1, [True], {"a": 1}, None):
            result = parse_intent_response(
                reply("add_transaction", "coffee 4.5", corrects_previous=bad)
            )
            assert result.kind == INTENT_ADD_TRANSACTION
            assert result.corrects_previous is False

    def test_ignored_for_other_intents(self):
        for intent, payload in (
            ("show_stat", "show"),
            ("question", "how much?"),
            ("set_reminder", "17:00"),
        ):
            result = parse_intent_response(reply(intent, payload, corrects_previous=True))
            assert result.kind != INTENT_UNKNOWN
            assert result.corrects_previous is False

    def test_flag_does_not_bypass_payload_validation(self):
        assert parse_intent_response(
            reply("add_transaction", "/leave 5", corrects_previous=True)
        ).kind == INTENT_UNKNOWN

    def test_unknown_never_carries_flag(self):
        assert parse_intent_response(
            reply("unknown", "", corrects_previous=True)
        ).corrects_previous is False


class TestFormatRecentContext:
    def test_empty_inputs_give_empty_block(self):
        assert format_recent_context([]) == ""
        assert format_recent_context(None) == ""

    def test_numbering_one_is_most_recent(self):
        interactions = [  # newest-first, as get_recent returns
            StubInteraction("не холм дом, а дом", payload="дом 5"),
            StubInteraction("холм дом пять", payload="холм дом 5", outcome="superseded"),
        ]
        block = format_recent_context(interactions)
        assert "1. [proposed] heard: «не холм дом, а дом» -> add_transaction: дом 5" in block
        assert "2. [superseded]" in block
        assert block.index("1. [proposed]") < block.index("2. [superseded]")

    def test_transcript_capped_per_line(self):
        block = format_recent_context([StubInteraction("x" * 500)])
        assert "x" * (CONTEXT_TRANSCRIPT_CHARS + 1) not in block
        assert "x" * CONTEXT_TRANSCRIPT_CHARS in block

    def test_block_capped_total(self):
        interactions = [
            StubInteraction("x" * 400, payload="item 5") for _ in range(20)
        ]
        block = format_recent_context(interactions)
        assert len(block) <= CONTEXT_BLOCK_CHARS + 100  # + header line

    def test_intent_without_payload_has_no_colon_suffix(self):
        block = format_recent_context(
            [StubInteraction("что-то", intent="unknown", payload="", outcome="unknown")]
        )
        assert "-> unknown" in block
        assert "-> unknown:" not in block

    def test_summary_prepended_and_capped(self):
        block = format_recent_context(
            [StubInteraction("дом 5")], summary="s" * 2000
        )
        assert block.startswith("Long-term memory")
        assert "s" * CONTEXT_SUMMARY_CHARS in block
        assert "s" * (CONTEXT_SUMMARY_CHARS + 1) not in block
        # recent lines still follow the summary
        assert "1. [proposed]" in block

    def test_summary_alone_still_renders(self):
        block = format_recent_context([], summary="«холм дом» -> «дом»")
        assert "Long-term memory" in block
        assert "Recent interactions" not in block


class TestFormatKnownItems:
    def test_empty(self):
        assert format_known_items([]) == ""
        assert format_known_items(None) == ""

    def test_lists_items(self):
        block = format_known_items(["дом", "coffee", "metro"])
        assert block.startswith("User's known spending items: ")
        assert "дом, coffee, metro" in block

    def test_item_cap(self):
        block = format_known_items([f"i{n}" for n in range(100)])
        assert block.count(",") == KNOWN_ITEMS_MAX - 1

    def test_char_cap(self):
        block = format_known_items(["x" * 50 for _ in range(100)])
        assert len(block) < 700

    def test_dedupes_case_insensitively(self):
        block = format_known_items(["Coffee", "coffee", "дом"])
        assert block.count("offee") == 1


class TestFindCorrectionTarget:
    def test_exactly_one_match(self):
        candidates = [(11, "дом", 5), (12, "кофе", 4.5)]
        assert find_correction_target("дом 5", candidates) == 11

    def test_zero_matches(self):
        assert find_correction_target("дом 5", [(12, "кофе", 4.5)]) is None

    def test_many_matches_ambiguous(self):
        candidates = [(11, "дом", 5), (12, "дом", 5)]
        assert find_correction_target("дом 5", candidates) is None

    def test_amount_must_match(self):
        assert find_correction_target("дом 5", [(11, "дом", 6)]) is None

    def test_multi_item_payload_ambiguous(self):
        assert find_correction_target("дом 5, кофе 4", [(11, "дом", 5)]) is None

    def test_date_prefix_stripped(self):
        assert find_correction_target("09.07 дом 5", [(11, "дом", 5)]) == 11

    def test_garbage_payload(self):
        assert find_correction_target("", [(11, "дом", 5)]) is None
        assert find_correction_target("no amount here", [(11, "дом", 5)]) is None


def test_build_intent_prompt_appends_context_and_known_items():
    prompt = build_intent_prompt(
        "не холм дом, а дом",
        today="2026-07-13 Monday",
        context_block="Recent interactions:\n1. [proposed] heard: «холм дом пять»",
        known_items="User's known spending items: дом, кофе",
    )
    assert prompt.startswith("Today is 2026-07-13 Monday.")
    assert "Recent interactions" in prompt
    assert "known spending items" in prompt
    # the message itself stays last so the blocks read as context, not input
    assert prompt.rindex("Message to classify:") > prompt.index("known spending items")


def test_build_intent_prompt_empty_blocks_add_nothing():
    assert build_intent_prompt("coffee 4", today="2026-07-13 Monday") == (
        "Today is 2026-07-13 Monday.\nMessage to classify:\ncoffee 4"
    )


# ==========================================
# System-prompt recurring/subscription examples (dv-94bd)
# ==========================================

def test_system_prompt_routes_recurring_phrases_to_question():
    """Recurring/subscription management must classify as question (dv-94bd):
    the agent stages the rule; no new intent kind is introduced."""
    prompt = build_intent_system_prompt()
    # English + Russian recurring examples live in the question bullet
    assert "add rent 800 every month" in prompt
    assert "cancel my Netflix subscription" in prompt
    assert "каждый месяц" in prompt
    assert "отмени подписку" in prompt


def test_system_prompt_keeps_one_off_spendings_as_add_transaction():
    """Boundary guard: recurrence examples must not steal genuine one-off
    transactions — the add_transaction bullet spells out "rent 800"."""
    prompt = build_intent_system_prompt()
    add_tx_bullet = prompt.split('- "add_income"')[0]
    assert '"rent 800"' in add_tx_bullet
    assert '"аренда 800"' in add_tx_bullet
    assert "one-off" in add_tx_bullet


# ==========================================
# Spoken confirm + chat fallthrough (dv-2cf1)
# ==========================================

class TestConfirmPendingParse:
    def test_payload_always_discarded(self):
        """The LLM can never smuggle text into a confirm — the router acts
        only on the stored pending proposal."""
        intent = parse_intent_response(reply("confirm_pending", "beer 999"))
        assert intent.kind == INTENT_CONFIRM_PENDING
        assert intent.payload == ""

    def test_empty_payload_fine(self):
        assert parse_intent_response(
            reply("confirm_pending", "")
        ).kind == INTENT_CONFIRM_PENDING


class TestChatParse:
    def test_passthrough(self):
        intent = parse_intent_response(reply("chat", "answer in English please"))
        assert intent.kind == INTENT_CHAT
        assert intent.payload == "answer in English please"

    def test_truncated_and_slash_stripped(self):
        intent = parse_intent_response(reply("chat", "/" + "x" * 600))
        assert intent.kind == INTENT_CHAT
        assert not intent.payload.startswith("/")
        assert len(intent.payload) <= MAX_QUESTION_CHARS

    def test_empty_chat_unknown(self):
        assert parse_intent_response(reply("chat", "  ")).kind == INTENT_UNKNOWN


class TestFindPendingProposal:
    def test_newest_proposed_add_wins(self):
        recent = [
            StubInteraction("что-то", intent="unknown", payload="", outcome="unknown", id=3),
            StubInteraction("пиво 10", payload="пиво 10", outcome="proposed", id=2),
            StubInteraction("дом 5", payload="дом 5", outcome="proposed", id=1),
        ]
        assert find_pending_proposal(recent).id == 2

    def test_confirmed_and_routed_skipped(self):
        recent = [
            StubInteraction("пиво 10", payload="пиво 10", outcome="confirmed"),
            StubInteraction("вопрос", intent="question", payload="answer", outcome="routed"),
        ]
        assert find_pending_proposal(recent) is None

    def test_income_proposal_found(self):
        recent = [StubInteraction("зп 500", intent="add_income", payload="зп 500")]
        assert find_pending_proposal(recent).intent == "add_income"

    def test_empty(self):
        assert find_pending_proposal([]) is None
        assert find_pending_proposal(None) is None


class TestValidateAddPayload:
    def test_valid_transaction(self):
        assert validate_add_payload(INTENT_ADD_TRANSACTION, "пиво 10, дом 5")

    def test_invalid_amount_rejected(self):
        assert not validate_add_payload(INTENT_ADD_TRANSACTION, "tax unknown")

    def test_income_comma_list_rejected(self):
        assert not validate_add_payload(INTENT_ADD_INCOME, "зп 500, бонус 100")

    def test_command_injection_rejected(self):
        assert not validate_add_payload(INTENT_ADD_TRANSACTION, "/delete 5")

    def test_non_add_kinds_rejected(self):
        assert not validate_add_payload(INTENT_QUESTION, "how much?")


# ==========================================
# Partial-understanding echo (dv-8233)
# ==========================================

class TestUnknownPartial:
    def test_explicit_unknown_keeps_payload_as_partial(self):
        intent = parse_intent_response(reply("unknown", "taxes 111"))
        assert intent.kind == INTENT_UNKNOWN
        assert intent.payload == ""
        assert intent.partial == "taxes 111"

    def test_failed_add_validation_preserves_partial(self):
        intent = parse_intent_response(reply("add_transaction", "tax unknown"))
        assert intent.kind == INTENT_UNKNOWN
        assert intent.partial == "tax unknown"

    def test_failed_income_validation_preserves_partial(self):
        intent = parse_intent_response(reply("add_income", "salary soon"))
        assert intent.kind == INTENT_UNKNOWN
        assert intent.partial == "salary soon"

    def test_partial_sanitized_capped_slash_stripped(self):
        intent = parse_intent_response(reply("unknown", "/x\n\n" + "y" * 500))
        assert not intent.partial.startswith("/")
        assert "\n" not in intent.partial
        assert len(intent.partial) <= MAX_PARTIAL_CHARS

    def test_garbage_json_has_no_partial(self):
        assert parse_intent_response("not json at all").partial == ""

    def test_validated_intents_carry_no_partial(self):
        assert parse_intent_response(reply("add_transaction", "дом 5")).partial == ""
        assert parse_intent_response(reply("question", "how much?")).partial == ""


class TestQuestionRowRendering:
    def test_question_rows_labeled_as_bot_answer(self):
        block = format_recent_context(
            [
                StubInteraction(
                    "сколько налог", intent="question",
                    payload="transport>tax 111 EUR, 2026 not paid", outcome="routed",
                )
            ]
        )
        assert "user asked: «сколько налог»" in block
        assert "bot answered: «transport>tax 111 EUR, 2026 not paid»" in block

    def test_answer_capped_per_line(self):
        block = format_recent_context(
            [StubInteraction("q", intent="question", payload="a" * 900, outcome="routed")]
        )
        assert "a" * CONTEXT_ANSWER_CHARS in block
        assert "a" * (CONTEXT_ANSWER_CHARS + 1) not in block

    def test_question_without_payload_falls_back_to_plain_line(self):
        block = format_recent_context(
            [StubInteraction("q", intent="question", payload="", outcome="routed")]
        )
        assert "heard: «q» -> question" in block


def test_system_prompt_teaches_new_intents_and_referential_resolution():
    prompt = build_intent_system_prompt()
    assert '"confirm_pending"' in prompt
    assert '"chat"' in prompt
    # referential example: category words come from the shown context
    assert "transport tax 111" in prompt
    # spendings must never leak into chat
    assert "ALWAYS add_transaction, never chat" in prompt
    # unknown now asks for the partial echo
    assert "PARTIALLY understood" in prompt
