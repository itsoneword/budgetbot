"""
Size-based compaction of the AI interaction log (T-041, amended step 8).

Pure logic only — row selection and prompt building for the daily
run_interaction_compaction job in src/scheduler.py. Retention is size-based
(owner decision 2026-07-13): all conversations are kept until a user's raw
rows exceed the char threshold, then everything but the newest KEEP_NEWEST
rows is summarized into one durable summary row and the raw rows are
deleted. Summaries are never auto-deleted; repeated compactions fold the
previous summary into the new one (hierarchical).
"""

# Rows always kept raw — the intent classifier's N=3 window plus headroom so
# a compaction run never eats context the user could still correct against.
KEEP_NEWEST = 20

# Cap on prompt space per raw row when building the compaction prompt.
_PROMPT_LINE_CHARS = 300


def total_interaction_chars(interactions) -> int:
    """Total stored size of non-summary rows (transcript + payload)."""
    return sum(len(i.transcript) + len(i.payload) for i in interactions or [])


def needs_compaction(interactions, threshold_chars: int) -> bool:
    """True when the raw rows exceed the size budget AND there is anything
    older than the always-kept window to compact."""
    if len(interactions or []) <= KEEP_NEWEST:
        return False
    return total_interaction_chars(interactions) > threshold_chars


def split_for_compaction(interactions, keep_newest: int = KEEP_NEWEST):
    """Split oldest-first rows into (to_compact, kept).

    to_compact: everything except the newest keep_newest rows — the summary
    input, deleted after summarization. kept: the newest rows, left raw.
    """
    interactions = list(interactions or [])
    if len(interactions) <= keep_newest:
        return [], interactions
    return interactions[:-keep_newest], interactions[-keep_newest:]


def build_compaction_system_prompt() -> str:
    return (
        "You summarize a user's interaction history with a personal finance "
        "Telegram bot (voice transcripts, intents, outcomes; English or Russian). "
        "Write a compact plain-text memory note (max ~150 words) that preserves only "
        "durable facts:\n"
        "1. Confirmed speech-recognition correction pairs, as «misheard» -> «real item» "
        "(e.g. «холм дом» -> «дом»).\n"
        "2. Recurring phrasings and preferences (typical items, currencies, phrasing "
        "habits).\n"
        "3. Notable question topics the user asks about.\n"
        "If a previous memory note is provided, fold it in: keep its still-relevant "
        "facts, drop duplicates. Output ONLY the note text, no preamble, no markdown."
    )


def build_compaction_prompt(interactions, previous_summary: str = "") -> str:
    """Prompt body for the compaction LLM call. Pure.

    interactions: oldest-first rows to summarize (objects with
    .channel/.outcome/.transcript/.intent/.payload). previous_summary: text
    of the user's existing summary row, folded into the new note.
    """
    lines = []
    for entry in interactions or []:
        transcript = " ".join(entry.transcript.split())[:_PROMPT_LINE_CHARS]
        payload = " ".join(entry.payload.split())[:_PROMPT_LINE_CHARS]
        suffix = f" -> {entry.intent}: {payload}" if payload else f" -> {entry.intent}"
        lines.append(f"[{entry.channel}/{entry.outcome}] «{transcript}»{suffix}")
    parts = []
    if previous_summary:
        parts.append(f"Previous memory note:\n{previous_summary}")
    parts.append("Interactions to summarize (oldest first):\n" + "\n".join(lines))
    return "\n\n".join(parts)
