"""
Tests for the AI-staged recurring UX in src/handlers/recurring.py (dv-82c8):
send_staged_recurring_actions keyboards + ai_rec_text, and the vrc_ confirm
tap re-injecting the exact '/recurring add' command.
"""
from types import SimpleNamespace

import src.texts as texts_en
from src.handlers.recurring import (
    handle_ai_recurring_confirmation,
    send_staged_recurring_actions,
)


class FakeMessage:
    def __init__(self):
        self.sent = []

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.edited = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edited.append(text)


def _update(query=None):
    return SimpleNamespace(
        effective_message=FakeMessage(),
        effective_user=SimpleNamespace(id=100),
        callback_query=query,
    )


def _context(**user_data):
    user_data.setdefault("cached_language", "en")
    return SimpleNamespace(user_data=user_data)


def _flat_callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


# ==========================================
# send_staged_recurring_actions
# ==========================================

async def test_staged_add_sends_confirm_message_and_arms_ai_rec_text():
    update, context = _update(), _context()
    staged = {"recurring_add": {
        "name": "gym membership", "amount": 49.99, "day": 15, "currency": "EUR",
    }}
    await send_staged_recurring_actions(update, context, staged, texts_en)

    assert context.user_data["ai_rec_text"] == "/recurring add gym membership 49.99 15"
    [(text, markup)] = update.effective_message.sent
    assert "gym membership" in text and "49.99" in text and "EUR" in text and "15" in text
    assert _flat_callbacks(markup) == ["vrc_yes", "vrc_no"]


async def test_staged_add_whole_amount_rendered_without_trailing_zero():
    update, context = _update(), _context()
    staged = {"recurring_add": {"name": "rent", "amount": 500.0, "day": 1, "currency": "EUR"}}
    await send_staged_recurring_actions(update, context, staged, texts_en)
    assert context.user_data["ai_rec_text"] == "/recurring add rent 500 1"


async def test_staged_cancel_sends_pause_delete_back_buttons():
    update, context = _update(), _context()
    staged = {"recurring_cancel": {"id": 42, "name": "netflix"}}
    await send_staged_recurring_actions(update, context, staged, texts_en)

    assert "ai_rec_text" not in context.user_data
    [(text, markup)] = update.effective_message.sent
    assert "netflix" in text
    assert _flat_callbacks(markup) == ["rr_pause_42", "rr_delc_42", "rr_back"]


async def test_staged_add_and_cancel_arrive_as_separate_messages():
    update, context = _update(), _context()
    staged = {
        "recurring_add": {"name": "rent", "amount": 500, "day": 1, "currency": "EUR"},
        "recurring_cancel": {"id": 7, "name": "gym"},
    }
    await send_staged_recurring_actions(update, context, staged, texts_en)
    assert len(update.effective_message.sent) == 2


async def test_empty_staged_sends_nothing():
    update, context = _update(), _context()
    await send_staged_recurring_actions(update, context, {}, texts_en)
    assert update.effective_message.sent == []


# ==========================================
# handle_ai_recurring_confirmation (^vrc_)
# ==========================================

async def test_vrc_yes_injects_command_and_pops_state(monkeypatch):
    injected = []

    async def fake_inject(update, context, text):
        injected.append(text)

    import src.handlers.voice as voice
    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    query = FakeQuery("vrc_yes")
    update = _update(query)
    context = _context(ai_rec_text="/recurring add rent 500 1")
    await handle_ai_recurring_confirmation(update, context)

    assert injected == ["/recurring add rent 500 1"]
    assert query.edited == [texts_en.AI_RECURRING_ADD_ACCEPTED]
    assert "ai_rec_text" not in context.user_data


async def test_vrc_no_cancels_without_injection(monkeypatch):
    injected = []

    async def fake_inject(update, context, text):
        injected.append(text)

    import src.handlers.voice as voice
    monkeypatch.setattr(voice, "_inject_text", fake_inject)

    query = FakeQuery("vrc_no")
    update = _update(query)
    context = _context(ai_rec_text="/recurring add rent 500 1")
    await handle_ai_recurring_confirmation(update, context)

    assert injected == []
    assert query.edited == [texts_en.AI_RECURRING_ADD_CANCELLED]
    assert "ai_rec_text" not in context.user_data


async def test_vrc_yes_with_no_staged_text_cancels():
    query = FakeQuery("vrc_yes")
    update = _update(query)
    context = _context()  # stale tap after restart: no ai_rec_text
    await handle_ai_recurring_confirmation(update, context)
    assert query.edited == [texts_en.AI_RECURRING_ADD_CANCELLED]
