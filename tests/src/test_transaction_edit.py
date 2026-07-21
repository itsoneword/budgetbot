"""
dv-0b63 income in Edit-recent-entries units: format_entry_line marker/format,
income vs spending edit keyboards, tx_<id> parsing with a mixed list (the
marker-never-in-keyboard-input trap), and the T-035-style type-mismatch guard
in handle_edit_option.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

import src.texts as texts_en
import src.texts_ru as texts_ru
from src.keyboards import (
    create_numbered_transaction_keyboard,
    create_transaction_edit_keyboard,
)
from src.handlers.transactions import (
    INCOME_MARKER,
    format_entry_line,
    format_transaction_details,
    format_delete_confirmation,
    is_edit_type_mismatch,
    handle_edit_option,
    handle_edit_income_category,
)
from src.states import EDIT_INCOME_CATEGORY, TRANSACTION_EDIT, TRANSACTION_LIST

from tests.conftest import make_tx


def _income_tx(**overrides):
    defaults = dict(
        transaction_type="income",
        category="salary",
        subcategory="",
        amount=Decimal("1000"),
    )
    defaults.update(overrides)
    return make_tx(**defaults)


def _kb_callbacks(kb):
    return [btn.callback_data for row in kb.inline_keyboard for btn in row]


# ==========================================
# format_entry_line
# ==========================================

def test_format_entry_line_spending_keeps_historical_format():
    tx = make_tx()
    line = format_entry_line(1, tx)
    assert line == f"1. {tx.date_str} - food: coffee 10 EUR"
    assert INCOME_MARKER not in line


def test_format_entry_line_income_marked_no_subcategory():
    tx = _income_tx()
    line = format_entry_line(3, tx)
    assert line == f"3. {INCOME_MARKER} {tx.date_str} - salary: 1000 EUR"
    # No dangling ": " from the empty income subcategory
    assert ":  " not in line


# ==========================================
# create_transaction_edit_keyboard variants
# ==========================================

def test_income_edit_keyboard_reduced_no_subcategory():
    kb = create_transaction_edit_keyboard({"transaction_type": "income"}, texts_en)
    callbacks = _kb_callbacks(kb)
    assert callbacks == [
        "edit_date",
        "edit_amount",
        "edit_income_category",
        "delete_transaction",
        "back_to_transactions",
    ]
    assert "edit_subcategory" not in callbacks
    assert "edit_category" not in callbacks


def test_spending_edit_keyboard_unchanged():
    kb = create_transaction_edit_keyboard({"transaction_type": "spending"}, texts_en)
    callbacks = _kb_callbacks(kb)
    assert callbacks == [
        "edit_date",
        "edit_amount",
        "edit_category",
        "edit_subcategory",
        "delete_transaction",
        "back_to_transactions",
    ]


def test_edit_keyboard_missing_type_defaults_to_spending():
    # Cached/legacy dicts without transaction_type must keep the full keyboard.
    kb = create_transaction_edit_keyboard({}, texts_en)
    assert "edit_subcategory" in _kb_callbacks(kb)


# ==========================================
# tx_<id> parsing with a mixed list (marker trap)
# ==========================================

def test_numbered_keyboard_parses_tx_ids_from_mixed_display_strings():
    txs = [make_tx(), _income_tx(), make_tx(category="transport")]
    display = [tx.to_display_string() for tx in txs]
    kb = create_numbered_transaction_keyboard(display, 0, len(txs), texts_en)

    numbered = [
        btn for row in kb.inline_keyboard for btn in row
        if btn.callback_data.startswith("tx_")
        and btn.callback_data not in ("tx_prev_page", "tx_next_page")
    ]
    assert [int(b.callback_data.replace("tx_", "")) for b in numbered] == [
        tx.id for tx in txs
    ]


def test_income_marker_never_in_display_string():
    # The keyboard parses the id out of to_display_string(); the marker lives
    # only in format_entry_line message text. A marker prefix would make the
    # id un-parseable — pin both sides of that invariant.
    tx = _income_tx()
    assert INCOME_MARKER not in tx.to_display_string()
    marked = f"{INCOME_MARKER} {tx.to_display_string()}"
    with pytest.raises(ValueError):
        int(marked.split(", ")[0].split(": ")[0])


# ==========================================
# is_edit_type_mismatch / detail texts
# ==========================================

def test_is_edit_type_mismatch_matrix():
    assert is_edit_type_mismatch("edit_category", "income")
    assert is_edit_type_mismatch("edit_subcategory", "income")
    assert is_edit_type_mismatch("edit_income_category", "spending")
    assert not is_edit_type_mismatch("edit_income_category", "income")
    assert not is_edit_type_mismatch("edit_category", "spending")
    assert not is_edit_type_mismatch("edit_date", "income")
    assert not is_edit_type_mismatch("edit_amount", "income")
    assert not is_edit_type_mismatch("delete_transaction", "income")


_INCOME_DICT = {
    "id": 7,
    "timestamp": "2026-06-15T12:00:00",
    "transaction_type": "income",
    "category": "salary",
    "subcategory": "",
    "amount": 1000.0,
    "currency": "EUR",
}

_SPENDING_DICT = {
    "id": 8,
    "timestamp": "2026-06-15T12:00:00",
    "transaction_type": "spending",
    "category": "food",
    "subcategory": "coffee",
    "amount": 10.0,
    "currency": "EUR",
}


def test_income_details_marked_and_without_subcategory_line():
    text = format_transaction_details(_INCOME_DICT, texts_en)
    assert INCOME_MARKER in text
    assert "Subcategory" not in text
    spending_text = format_transaction_details(_SPENDING_DICT, texts_en)
    assert "Subcategory" in spending_text
    assert INCOME_MARKER not in spending_text


def test_income_delete_confirmation_marked_and_without_subcategory_line():
    text = format_delete_confirmation(_INCOME_DICT, texts_en)
    assert INCOME_MARKER in text
    assert "Subcategory" not in text
    spending_text = format_delete_confirmation(_SPENDING_DICT, texts_en)
    assert "Subcategory" in spending_text


def test_income_edit_texts_defined_in_both_languages():
    for name in (
        "TRANSACTION_DETAILS_INCOME",
        "CONFIRM_DELETE_INCOME",
        "ENTER_NEW_INCOME_CATEGORY",
        "EDIT_TYPE_MISMATCH",
    ):
        assert getattr(texts_en, name)
        assert getattr(texts_ru, name)
        assert getattr(texts_en, name) != getattr(texts_ru, name)


# ==========================================
# handle_edit_option guard (stale/forged callbacks)
# ==========================================

class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.edits = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


def _edit_update(query):
    return SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
    )


def _edit_context(transaction):
    return SimpleNamespace(
        user_data={
            "cached_language": "en",
            "current_transaction": dict(transaction),
            "current_tx_id": transaction["id"],
        }
    )


async def test_spending_callback_on_income_row_refused(monkeypatch):
    import src.handlers.transactions as tr

    monkeypatch.setattr(tr, "get_repos", lambda context: None)
    query = FakeQuery("edit_subcategory")
    state = await handle_edit_option(_edit_update(query), _edit_context(_INCOME_DICT))

    assert state == TRANSACTION_EDIT
    text, kwargs = query.edits[-1]
    assert texts_en.EDIT_TYPE_MISMATCH in text
    # Re-rendered with the income keyboard — the stale option is gone.
    callbacks = _kb_callbacks(kwargs["reply_markup"])
    assert "edit_subcategory" not in callbacks
    assert "edit_income_category" in callbacks


async def test_income_callback_on_spending_row_refused(monkeypatch):
    import src.handlers.transactions as tr

    monkeypatch.setattr(tr, "get_repos", lambda context: None)
    query = FakeQuery("edit_income_category")
    state = await handle_edit_option(_edit_update(query), _edit_context(_SPENDING_DICT))

    assert state == TRANSACTION_EDIT
    text, kwargs = query.edits[-1]
    assert texts_en.EDIT_TYPE_MISMATCH in text
    assert "edit_income_category" not in _kb_callbacks(kwargs["reply_markup"])


async def test_income_category_callback_on_income_row_prompts(monkeypatch):
    import src.handlers.transactions as tr

    monkeypatch.setattr(tr, "get_repos", lambda context: None)
    query = FakeQuery("edit_income_category")
    state = await handle_edit_option(_edit_update(query), _edit_context(_INCOME_DICT))

    assert state == EDIT_INCOME_CATEGORY
    assert query.edits[-1][0] == texts_en.ENTER_NEW_INCOME_CATEGORY


# ==========================================
# handle_edit_income_category
# ==========================================

class FakeTxRepo:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    async def update(self, tx_id, user_id, **fields):
        self.calls.append((tx_id, user_id, fields))
        return self.result


def _text_update(text, replies):
    async def reply_text(message, **kwargs):
        replies.append(message)

    return SimpleNamespace(
        effective_user=SimpleNamespace(id=100, first_name="Test", username="test"),
        message=SimpleNamespace(text=text, reply_text=reply_text),
    )


async def test_handle_edit_income_category_normalizes_and_updates(monkeypatch):
    import src.handlers.transactions as tr

    repo = FakeTxRepo()
    monkeypatch.setattr(tr, "get_repos", lambda context: SimpleNamespace(transactions=repo))

    async def fake_show_recent(update, context):
        return TRANSACTION_LIST

    monkeypatch.setattr(tr, "show_recent_entries", fake_show_recent)

    replies = []
    update = _text_update("  Freelance Work  ", replies)
    context = SimpleNamespace(
        user_data={"cached_language": "en", "current_tx_id": 7}
    )
    state = await handle_edit_income_category(update, context)

    # Lowercased + stripped, same normalization as save_income_text
    assert repo.calls == [(7, 100, {"category_name": "freelance work"})]
    assert texts_en.CATEGORY_UPDATED_SUCCESS in replies
    assert state == TRANSACTION_LIST


async def test_handle_edit_income_category_empty_input_reprompts(monkeypatch):
    import src.handlers.transactions as tr

    repo = FakeTxRepo()
    monkeypatch.setattr(tr, "get_repos", lambda context: SimpleNamespace(transactions=repo))

    replies = []
    update = _text_update("   ", replies)
    context = SimpleNamespace(
        user_data={"cached_language": "en", "current_tx_id": 7}
    )
    state = await handle_edit_income_category(update, context)

    assert repo.calls == []
    assert replies == [texts_en.ENTER_NEW_INCOME_CATEGORY]
    assert state == EDIT_INCOME_CATEGORY
