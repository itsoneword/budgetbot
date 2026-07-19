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
