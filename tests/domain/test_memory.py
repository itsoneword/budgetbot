"""Tests for domain/memory.py — size-based interaction-log compaction (T-041)."""
from dataclasses import dataclass

from domain.memory import (
    KEEP_NEWEST,
    build_compaction_prompt,
    needs_compaction,
    split_for_compaction,
    total_interaction_chars,
)


@dataclass
class StubRow:
    """Attribute shape of InteractionRepository.AIInteraction rows."""
    id: int
    transcript: str = "кофе 4"
    payload: str = "кофе 4"
    intent: str = "add_transaction"
    outcome: str = "confirmed"
    channel: str = "voice"


def make_rows(n, chars_each=10):
    # oldest-first, like InteractionRepository.get_all_for_user
    return [StubRow(id=i, transcript="x" * chars_each, payload="") for i in range(1, n + 1)]


class TestTotalChars:
    def test_empty(self):
        assert total_interaction_chars([]) == 0
        assert total_interaction_chars(None) == 0

    def test_sums_transcript_and_payload(self):
        rows = [StubRow(id=1, transcript="abc", payload="de")]
        assert total_interaction_chars(rows) == 5


class TestNeedsCompaction:
    def test_under_threshold(self):
        assert needs_compaction(make_rows(30, chars_each=10), 1000) is False

    def test_over_threshold(self):
        assert needs_compaction(make_rows(30, chars_each=100), 1000) is True

    def test_never_when_within_keep_window(self):
        # Few huge rows: over the char budget but nothing older than the
        # always-kept window -> nothing to compact.
        rows = make_rows(KEEP_NEWEST, chars_each=10_000)
        assert needs_compaction(rows, 1000) is False


class TestSplitForCompaction:
    def test_short_history_untouched(self):
        rows = make_rows(KEEP_NEWEST)
        to_compact, kept = split_for_compaction(rows)
        assert to_compact == []
        assert kept == rows

    def test_splits_oldest_for_compaction(self):
        rows = make_rows(KEEP_NEWEST + 5)
        to_compact, kept = split_for_compaction(rows)
        assert [r.id for r in to_compact] == [1, 2, 3, 4, 5]
        assert len(kept) == KEEP_NEWEST
        assert kept[-1].id == KEEP_NEWEST + 5  # newest stays raw

    def test_custom_keep(self):
        rows = make_rows(10)
        to_compact, kept = split_for_compaction(rows, keep_newest=3)
        assert [r.id for r in to_compact] == list(range(1, 8))
        assert [r.id for r in kept] == [8, 9, 10]

    def test_empty(self):
        assert split_for_compaction([]) == ([], [])


class TestBuildCompactionPrompt:
    def test_lists_rows_with_channel_and_outcome(self):
        rows = [
            StubRow(id=1, transcript="холм дом пять", payload="холм дом 5",
                    outcome="superseded"),
            StubRow(id=2, transcript="не холм дом, а дом", payload="дом 5"),
        ]
        prompt = build_compaction_prompt(rows)
        assert "[voice/superseded] «холм дом пять» -> add_transaction: холм дом 5" in prompt
        assert "«не холм дом, а дом»" in prompt
        assert "Previous memory note" not in prompt

    def test_previous_summary_folded_in(self):
        prompt = build_compaction_prompt(
            [StubRow(id=1)], previous_summary="«холм дом» -> «дом»"
        )
        assert prompt.startswith("Previous memory note:\n«холм дом» -> «дом»")

    def test_long_rows_capped(self):
        prompt = build_compaction_prompt(
            [StubRow(id=1, transcript="x" * 5000, payload="y" * 5000)]
        )
        assert len(prompt) < 1000
