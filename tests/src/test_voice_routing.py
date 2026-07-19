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
from domain.intent import INTENT_QUESTION, INTENT_SHOW_STAT, Intent


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
