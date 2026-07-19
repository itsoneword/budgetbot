"""
T-044 edit-in-place navigation units: _safe_edit double-tap swallow,
build_ai_offer Back-row flag, build_records_report None / limit-append.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest

import src.texts as texts_en
from src.handlers.menu import _back_kb, _safe_edit, _split_text
from src.handlers.payments import build_ai_offer

from tests.conftest import make_session, make_tx


# ==========================================
# _safe_edit
# ==========================================

class FakeQuery:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def edit_message_text(self, text, **kwargs):
        self.calls.append((text, kwargs))
        if self.error is not None:
            raise self.error


async def test_safe_edit_passes_text_and_kwargs_through():
    query = FakeQuery()
    await _safe_edit(query, "hello", parse_mode="HTML")
    assert query.calls == [("hello", {"parse_mode": "HTML"})]


async def test_safe_edit_swallows_not_modified():
    query = FakeQuery(error=BadRequest("Message is not modified: blah"))
    # Double-tap protection: must not raise.
    await _safe_edit(query, "same text")


async def test_safe_edit_reraises_other_bad_requests():
    query = FakeQuery(error=BadRequest("Chat not found"))
    with pytest.raises(BadRequest):
        await _safe_edit(query, "text")


# ==========================================
# _back_kb / _split_text
# ==========================================

def test_back_kb_single_back_button_default_target():
    kb = _back_kb(texts_en)
    assert len(kb.inline_keyboard) == 1
    button = kb.inline_keyboard[0][0]
    assert button.callback_data == "back_to_main_menu"
    assert button.text == texts_en.BACK_BUTTON


def test_back_kb_custom_target():
    kb = _back_kb(texts_en, cb="menu_settings")
    assert kb.inline_keyboard[0][0].callback_data == "menu_settings"


def test_split_text_respects_limit_and_preserves_content():
    text = "\n".join(f"line {i}" for i in range(1000))
    chunks = _split_text(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "\n".join(chunks) == text


# ==========================================
# build_ai_offer
# ==========================================

def test_build_ai_offer_default_has_only_buy_row():
    text, kb = build_ai_offer(texts_en)
    assert text
    assert len(kb.inline_keyboard) == 1
    assert kb.inline_keyboard[0][0].callback_data == "buy_ai"


def test_build_ai_offer_include_back_appends_back_row():
    plain_text, _ = build_ai_offer(texts_en)
    text, kb = build_ai_offer(texts_en, include_back=True)
    # The reply contract for /ask and voice denial: same text either way.
    assert text == plain_text
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].callback_data == "buy_ai"
    assert kb.inline_keyboard[1][0].callback_data == "back_to_main_menu"


# ==========================================
# build_records_report
# ==========================================

# A substring unique to the LIMIT_EXCEEDED block.
_LIMIT_MARKER = "avoid spending"


def _fake_update():
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        effective_message=None,
        callback_query=None,
    )


def _fake_context():
    return SimpleNamespace(user_data={"cached_language": "en"}, bot_data={})


def _patch_records(monkeypatch, session):
    import src.handlers.records as records

    async def fake_cache_user_language(context, repos, user_id):
        return "en"

    async def fake_load_user_session(user_id, repos, **kwargs):
        return session

    monkeypatch.setattr(records, "get_repos", lambda context: None)
    monkeypatch.setattr(records, "cache_user_language", fake_cache_user_language)
    monkeypatch.setattr(records, "load_user_session", fake_load_user_session)
    return records


async def test_build_records_report_none_when_no_records(monkeypatch):
    records = _patch_records(monkeypatch, make_session(transactions=[]))
    report = await records.build_records_report(
        _fake_update(), _fake_context(), tx_type="spending"
    )
    assert report is None


async def test_build_records_report_within_limit_no_warning(monkeypatch):
    now = datetime.now(timezone.utc)
    session = make_session(
        transactions=[
            make_tx(timestamp=now - timedelta(days=1), amount=Decimal("10")),
        ]
    )
    records = _patch_records(monkeypatch, session)
    report = await records.build_records_report(
        _fake_update(), _fake_context(), tx_type="spending"
    )
    assert report is not None
    assert "food" in report
    assert _LIMIT_MARKER not in report


# ==========================================
# Ask-AI typed-question mode (T-045)
# ==========================================

import src.texts_ru as texts_ru


@pytest.fixture(scope="module")
def core(tmp_path_factory):
    """Import src.core once, from a cwd with a stubbed configs/config.

    src/core.py reads configs/config (Telegram token) at import time; the
    repo checkout has no such file, so tests import it from a temp cwd
    holding a dummy one. Cached in sys.modules for every later user —
    including menu_call's in-function `from src.core import ...`.
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


def test_ask_ai_prompt_defined_in_both_languages():
    assert texts_en.ASK_AI_PROMPT
    assert texts_ru.ASK_AI_PROMPT
    assert texts_en.ASK_AI_PROMPT != texts_ru.ASK_AI_PROMPT


class FakeMenuQuery:
    """Callback query stand-in for menu_call: ack + edit recording."""

    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=100, first_name="Test")
        self.edits = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


def _menu_update(query):
    return SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
    )


async def test_menu_ask_ai_entitled_arms_flag_and_prompts(core, monkeypatch):
    import src.ai_access as ai_access

    async def fake_access(user_id, context):
        return True

    monkeypatch.setattr(ai_access, "check_ai_access", fake_access)
    from src.handlers.menu import menu_call

    query = FakeMenuQuery("menu_ask_ai")
    context = SimpleNamespace(user_data={"cached_language": "en"})
    await menu_call(_menu_update(query), context)

    assert context.user_data.get("awaiting_ask") is True
    text, kwargs = query.edits[-1]
    assert text == texts_en.ASK_AI_PROMPT
    kb = kwargs["reply_markup"].inline_keyboard
    assert kb[0][0].callback_data == "back_to_main_menu"


async def test_menu_ask_ai_non_entitled_offer_no_flag(core, monkeypatch):
    import src.ai_access as ai_access

    async def fake_access(user_id, context):
        return False

    monkeypatch.setattr(ai_access, "check_ai_access", fake_access)
    from src.handlers.menu import menu_call

    query = FakeMenuQuery("menu_ask_ai")
    context = SimpleNamespace(user_data={"cached_language": "en"})
    await menu_call(_menu_update(query), context)

    assert "awaiting_ask" not in context.user_data
    offer_text, _ = build_ai_offer(texts_en)
    assert query.edits[-1][0] == offer_text


async def test_menu_back_clears_stale_awaiting_ask(core):
    from src.handlers.menu import menu_call

    query = FakeMenuQuery("back_to_main_menu")
    context = SimpleNamespace(
        user_data={"cached_language": "en", "awaiting_ask": True}
    )
    await menu_call(_menu_update(query), context)

    assert "awaiting_ask" not in context.user_data
    assert query.edits[-1][0] == texts_en.MAIN_MENU_TEXT


async def test_any_menu_tap_clears_stale_awaiting_ask(core):
    from src.handlers.menu import menu_call

    query = FakeMenuQuery("menu_settings")
    context = SimpleNamespace(
        user_data={"cached_language": "en", "awaiting_ask": True}
    )
    await menu_call(_menu_update(query), context)
    assert "awaiting_ask" not in context.user_data


async def test_handle_text_awaiting_ask_routes_to_ask_flow(core, monkeypatch):
    questions = []

    async def fake_answer(update, context, question):
        questions.append(question)

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        message=SimpleNamespace(text="how much did I spend on beer this year?"),
    )
    context = SimpleNamespace(
        user_data={"cached_language": "en", "awaiting_ask": True}
    )
    state = await core.handle_text(update, context)

    assert questions == ["how much did I spend on beer this year?"]
    assert "awaiting_ask" not in context.user_data
    assert state == core.TRANSACTION


async def test_ask_command_joins_args_and_delegates(core, monkeypatch):
    questions = []

    async def fake_answer(update, context, question):
        questions.append(question)

    monkeypatch.setattr(core, "answer_ask_question", fake_answer)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
    )
    context = SimpleNamespace(args=["beer", "spend?"], user_data={"cached_language": "en"})
    await core.ask(update, context)
    assert questions == ["beer spend?"]


async def test_voice_entry_clears_awaiting_ask(monkeypatch):
    import src.handlers.voice as voice

    async def fake_access(user_id, context):
        return False  # earliest exit after the pop — offer instead of routing

    offers = []

    async def fake_offer(update, context):
        offers.append(True)

    monkeypatch.setattr(voice, "check_ai_access", fake_access)
    import src.handlers.payments as payments
    monkeypatch.setattr(payments, "send_ai_offer", fake_offer)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        effective_message=SimpleNamespace(voice=None),
    )
    context = SimpleNamespace(user_data={"cached_language": "en", "awaiting_ask": True})
    await voice.handle_voice(update, context)

    assert "awaiting_ask" not in context.user_data
    assert offers == [True]


async def test_build_records_report_appends_limit_block_when_exceeded(monkeypatch):
    from domain.models.user_session import UserConfig

    now = datetime.now(timezone.utc)
    session = make_session(
        transactions=[
            make_tx(timestamp=now - timedelta(days=1), amount=Decimal("5000")),
        ],
        config=UserConfig(user_id=100, monthly_limit=Decimal("10")),
    )
    records = _patch_records(monkeypatch, session)
    report = await records.build_records_report(
        _fake_update(), _fake_context(), tx_type="spending"
    )
    assert report is not None
    # Warning is appended to the SAME text (single edit/message), not sent
    # as a separate message.
    assert _LIMIT_MARKER in report
