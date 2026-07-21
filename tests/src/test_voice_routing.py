"""dv-94bd: voice/free-text questions call answer_ask_question directly.

Covers: the INTENT_QUESTION branch of _route_intent (transcript echo kept as
its own message, classifier payload — not the verbatim transcript — handed to
the agent, originating channel threaded through), non-question intents still
dispatching via _inject_text, and answer_ask_question logging the interaction
row under the caller's channel.
"""
from types import SimpleNamespace

import pytest

import src.handlers.voice as voice
import src.texts as texts_en
from domain.intent import (
    INTENT_CHAT,
    INTENT_CONFIRM_PENDING,
    INTENT_QUESTION,
    INTENT_SHOW_STAT,
    INTENT_UNKNOWN,
    Intent,
)


@pytest.fixture(scope="module")
def core(tmp_path_factory):
    """Import src.core once, from a cwd with a stubbed configs/config.

    Same pattern as tests/src/test_menu_nav.py — src/core.py reads
    configs/config at import time; cached in sys.modules afterwards.
    """
    import os
    import sys

    if "src.core" not in sys.modules:
        tmp = tmp_path_factory.mktemp("coreimport")
        (tmp / "configs").mkdir()
        (tmp / "configs" / "config").write_text("[TELEGRAM]\nTOKEN = 123:dummy\n")
        (tmp / "user_data").mkdir()  # src.logger opens user_data/app.log
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            import src.core  # noqa: F401
        finally:
            os.chdir(old_cwd)
    import src.core
    return src.core


class FakeStatus:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


def _update():
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        effective_message=None,
    )


def _context():
    return SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})


def _patch_route_plumbing(monkeypatch, intent, logged):
    async def fake_blocks(user_id, context):
        return [], "", ""

    async def fake_classify(text, context_block="", known_items=""):
        return intent

    async def fake_log(context, user_id, channel, transcript, i):
        logged.append((channel, transcript, i.kind))
        return 42

    monkeypatch.setattr(voice, "_load_context_blocks", fake_blocks)
    monkeypatch.setattr(voice, "_classify", fake_classify)
    monkeypatch.setattr(voice, "_log_interaction", fake_log)


async def test_question_intent_calls_ask_directly_with_channel(core, monkeypatch):
    logged, asked, injected = [], [], []

    _patch_route_plumbing(
        monkeypatch, Intent(INTENT_QUESTION, "how much on beer?"), logged
    )

    async def fake_answer(update, context, question, channel="ask"):
        asked.append((question, channel))

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)
    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    status = FakeStatus()
    await voice._route_intent(
        _update(), _context(), "сколько я трачу на пиво", status, channel="voice"
    )

    # Classifier payload reaches the agent, not the verbatim transcript;
    # channel identifies the voice origin.
    assert asked == [("how much on beer?", "voice")]
    assert injected == []  # no "/ask ..." synthetic update any more
    assert logged == [("voice", "сколько я трачу на пиво", INTENT_QUESTION)]
    # Transcript echo kept as its own message (owner decision: two messages).
    assert status.edits == [
        (texts_en.VOICE_HEARD.format(transcript="сколько я трачу на пиво"), {})
    ]


async def test_free_text_question_keeps_text_channel(core, monkeypatch):
    """route_free_text shares _route_intent; its questions log channel='text'."""
    logged, asked = [], []
    _patch_route_plumbing(monkeypatch, Intent(INTENT_QUESTION, "total in june?"), logged)

    async def fake_answer(update, context, question, channel="ask"):
        asked.append((question, channel))

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)

    await voice._route_intent(
        _update(), _context(), "what was my june total", FakeStatus(), channel="text"
    )

    assert asked == [("total in june?", "text")]
    assert logged[0][0] == "text"


async def test_show_stat_intent_still_injects(core, monkeypatch):
    """Non-question intents keep the synthetic-update injection path."""
    logged, asked, injected = [], [], []
    _patch_route_plumbing(monkeypatch, Intent(INTENT_SHOW_STAT, "show_last"), logged)

    async def fake_answer(update, context, question, channel="ask"):
        asked.append((question, channel))

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)
    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    await voice._route_intent(
        _update(), _context(), "show my last records", FakeStatus(), channel="voice"
    )

    assert injected == ["/show_last"]
    assert asked == []


# ==========================================
# answer_ask_question threads channel into the interaction row
# ==========================================

class FakeInteractions:
    def __init__(self):
        self.rows = []

    async def add(self, user_id, channel, transcript, intent, payload, outcome=None):
        self.rows.append((user_id, channel, transcript, intent, payload, outcome))
        return 1


class FakeThinking:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)


# ==========================================
# Spoken confirm of a pending proposal (dv-2cf1)
# ==========================================

class FakeBot:
    def __init__(self):
        self.markup_edits = []

    async def edit_message_reply_markup(self, chat_id=None, message_id=None, reply_markup=None):
        self.markup_edits.append((chat_id, message_id, reply_markup))


def _proposed(intent="add_transaction", payload="пиво 10", row_id=42):
    return SimpleNamespace(
        intent=intent, payload=payload, outcome="proposed", id=row_id, transcript="x"
    )


def _patch_confirm_plumbing(monkeypatch, intent, recent, logged, outcomes):
    async def fake_blocks(user_id, context):
        return recent, "ctx-block", ""

    async def fake_classify(text, context_block="", known_items=""):
        return intent

    async def fake_log(context, user_id, channel, transcript, i):
        logged.append((channel, i.kind))
        return 99

    async def fake_outcome(context, interaction_id, user_id, outcome):
        outcomes.append((interaction_id, outcome))

    monkeypatch.setattr(voice, "_load_context_blocks", fake_blocks)
    monkeypatch.setattr(voice, "_classify", fake_classify)
    monkeypatch.setattr(voice, "_log_interaction", fake_log)
    monkeypatch.setattr(voice, "_set_outcome_safe", fake_outcome)


async def test_spoken_confirm_injects_pending_tx(core, monkeypatch):
    logged, outcomes, injected = [], [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_CONFIRM_PENDING), [_proposed()], logged, outcomes
    )

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    bot = FakeBot()
    context = SimpleNamespace(
        user_data={
            "cached_language": "en",
            "voice_tx_text": "пиво 10",
            "voice_tx_interaction_id": 42,
            "voice_confirm_msg": (7, 555),
        },
        bot_data={},
        bot=bot,
    )
    status = FakeStatus()
    await voice._route_intent(_update(), context, "да, добавляй", status, channel="voice")

    assert injected == ["пиво 10"]
    assert (42, "confirmed") in outcomes
    # stale Add/Cancel keyboard stripped, payload popped so a tap can't double-save
    assert bot.markup_edits == [(7, 555, None)]
    assert "voice_tx_text" not in context.user_data
    assert status.edits == [
        (
            texts_en.VOICE_TX_CONFIRMED_VOICE.format(
                transcript="да, добавляй", transaction="пиво 10"
            ),
            {},
        )
    ]


async def test_spoken_confirm_income_uses_save_income_text(core, monkeypatch):
    import src.handlers.records as records

    logged, outcomes, saved, injected = [], [], [], []
    _patch_confirm_plumbing(
        monkeypatch,
        Intent(INTENT_CONFIRM_PENDING),
        [_proposed(intent="add_income", payload="зп 500")],
        logged,
        outcomes,
    )

    async def fake_save(update, context, text):
        saved.append(text)
        return True

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(records, "save_income_text", fake_save)
    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    context = SimpleNamespace(
        user_data={
            "cached_language": "en",
            "voice_income_text": "зп 500",
            "voice_income_interaction_id": 42,
        },
        bot_data={},
        bot=FakeBot(),
    )
    await voice._route_intent(_update(), context, "да", FakeStatus(), channel="voice")

    # income never goes through plain text injection (T-035)
    assert saved == ["зп 500"]
    assert injected == []
    assert (42, "confirmed") in outcomes


async def test_spoken_confirm_falls_back_to_durable_payload(core, monkeypatch):
    """user_data lost (restart) — the stored row payload is used after
    re-validation."""
    logged, outcomes, injected = [], [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_CONFIRM_PENDING), [_proposed()], logged, outcomes
    )

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    context = SimpleNamespace(
        user_data={"cached_language": "en"}, bot_data={}, bot=FakeBot()
    )
    await voice._route_intent(_update(), context, "да", FakeStatus(), channel="voice")

    assert injected == ["пиво 10"]
    assert (42, "confirmed") in outcomes


async def test_spoken_confirm_nothing_pending_gets_canned_reply(core, monkeypatch):
    logged, outcomes, injected = [], [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_CONFIRM_PENDING), [], logged, outcomes
    )

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    context = SimpleNamespace(
        user_data={"cached_language": "en"}, bot_data={}, bot=FakeBot()
    )
    status = FakeStatus()
    await voice._route_intent(_update(), context, "да", status, channel="voice")

    assert injected == []
    # this turn's row downgraded — a stray "yes" must not read as routed
    assert (99, "unknown") in outcomes
    assert status.edits == [
        (texts_en.VOICE_NOTHING_PENDING.format(transcript="да"), {})
    ]


async def test_spoken_confirm_rejects_invalid_durable_payload(core, monkeypatch):
    """Corrupt/edited row payload fails re-validation — nothing injected."""
    logged, outcomes, injected = [], [], []
    _patch_confirm_plumbing(
        monkeypatch,
        Intent(INTENT_CONFIRM_PENDING),
        [_proposed(payload="/delete 5")],
        logged,
        outcomes,
    )

    async def fake_inject(update, context, text):
        injected.append(text)

    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    context = SimpleNamespace(
        user_data={"cached_language": "en"}, bot_data={}, bot=FakeBot()
    )
    status = FakeStatus()
    await voice._route_intent(_update(), context, "да", status, channel="voice")

    assert injected == []
    assert (42, "confirmed") not in outcomes


# ==========================================
# Chat fallthrough + partial-understanding echo (dv-2cf1 / dv-8233)
# ==========================================

async def test_chat_intent_routes_to_ask_with_context_block(core, monkeypatch):
    logged, outcomes, asked = [], [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_CHAT, "answer in English"), [], logged, outcomes
    )

    async def fake_answer(update, context, question, channel="ask", context_block=""):
        asked.append((question, channel, context_block))

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)

    context = SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})
    await voice._route_intent(
        _update(), context, "ответь по-английски", FakeStatus(), channel="voice"
    )

    # the conversation block reaches the agent so it can re-answer
    assert asked == [("answer in English", "voice", "ctx-block")]


async def test_unknown_with_partial_echoes_guess(core, monkeypatch):
    logged, outcomes = [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_UNKNOWN, partial="taxes 111"), [], logged, outcomes
    )

    context = SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})
    status = FakeStatus()
    await voice._route_intent(_update(), context, "налог наверное", status, channel="voice")

    assert status.edits == [
        (
            texts_en.VOICE_UNKNOWN_PARTIAL.format(
                transcript="налог наверное", partial="taxes 111"
            ),
            {},
        )
    ]


async def test_unknown_without_partial_keeps_generic_text(core, monkeypatch):
    logged, outcomes = [], []
    _patch_confirm_plumbing(
        monkeypatch, Intent(INTENT_UNKNOWN), [], logged, outcomes
    )

    context = SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})
    status = FakeStatus()
    await voice._route_intent(_update(), context, "мммм", status, channel="voice")

    assert status.edits == [(texts_en.VOICE_UNKNOWN.format(transcript="мммм"), {})]


@pytest.mark.parametrize("channel_kwargs, expected", [({}, "ask"), ({"channel": "voice"}, "voice")])
async def test_answer_ask_question_logs_caller_channel(
    core, monkeypatch, channel_kwargs, expected
):
    import domain.ask_summary as ask_summary
    import infrastructure.llm as llm
    import src.ai_access as ai_access
    import src.ask_agent_tools as ask_agent_tools

    interactions = FakeInteractions()
    thinking = FakeThinking()

    async def fake_access(user_id, context):
        return True

    async def fake_load_session(user_id, repos, **kwargs):
        return SimpleNamespace(
            transactions=[object()], language="en", currency="USD", user_id=100
        )

    class FakeClient:
        async def complete_with_tools(self, prompt, system, tools=None):
            return "you spent 42"

    monkeypatch.setattr(ai_access, "check_ai_access", fake_access)
    monkeypatch.setattr(core, "load_user_session", fake_load_session)
    monkeypatch.setattr(
        core, "get_repos", lambda context: SimpleNamespace(interactions=interactions)
    )
    monkeypatch.setattr(ask_summary, "build_finance_summary", lambda session: "summary")
    monkeypatch.setattr(
        ask_summary, "build_ask_system_prompt", lambda lang, tools_enabled=False: "sys"
    )
    monkeypatch.setattr(llm, "get_llm_client", lambda *a, **k: FakeClient())
    monkeypatch.setattr(ask_agent_tools, "build_ask_toolspecs", lambda session: [])

    async def fake_reply(text, **kwargs):
        return thinking

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        effective_message=SimpleNamespace(reply_text=fake_reply),
    )
    context = SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})

    await core.answer_ask_question(update, context, "how much?", **channel_kwargs)

    assert thinking.edits == ["you spent 42"]
    assert interactions.rows == [
        (100, expected, "how much?", "question", "you spent 42", "routed")
    ]


async def test_answer_ask_question_includes_context_block_in_prompt(core, monkeypatch):
    """dv-2cf1 chat fallthrough: the recent-conversation block reaches the
    agent prompt (between the data summary and the question), only when given."""
    import domain.ask_summary as ask_summary
    import infrastructure.llm as llm
    import src.ai_access as ai_access
    import src.ask_agent_tools as ask_agent_tools

    prompts = []

    async def fake_access(user_id, context):
        return True

    async def fake_load_session(user_id, repos, **kwargs):
        return SimpleNamespace(
            transactions=[object()], language="en", currency="USD", user_id=100
        )

    class FakeClient:
        async def complete_with_tools(self, prompt, system, tools=None):
            prompts.append(prompt)
            return "ok"

    monkeypatch.setattr(ai_access, "check_ai_access", fake_access)
    monkeypatch.setattr(core, "load_user_session", fake_load_session)
    monkeypatch.setattr(
        core, "get_repos", lambda context: SimpleNamespace(interactions=FakeInteractions())
    )
    monkeypatch.setattr(ask_summary, "build_finance_summary", lambda session: "summary")
    monkeypatch.setattr(
        ask_summary, "build_ask_system_prompt", lambda lang, tools_enabled=False: "sys"
    )
    monkeypatch.setattr(llm, "get_llm_client", lambda *a, **k: FakeClient())
    monkeypatch.setattr(ask_agent_tools, "build_ask_toolspecs", lambda session: [])

    async def fake_reply(text, **kwargs):
        return FakeThinking()

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        effective_message=SimpleNamespace(reply_text=fake_reply),
    )
    context = SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})

    await core.answer_ask_question(
        update, context, "in English please", channel="voice",
        context_block="1. [routed] user asked: «q» — bot answered: «a»",
    )
    await core.answer_ask_question(update, context, "plain question")

    assert "Recent conversation with the user:" in prompts[0]
    assert "bot answered: «a»" in prompts[0]
    assert prompts[0].index("summary") < prompts[0].index("Recent conversation")
    assert prompts[0].rindex("in English please") > prompts[0].index("Recent conversation")
    assert "Recent conversation" not in prompts[1]
