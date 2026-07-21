"""
JobQueue jobs: daily recurring transactions (T-026), reminder sweep (T-034)
and AI interaction-log compaction (T-041).

run_recurring_rules is registered on PTB's JobQueue in src/core.py main():
once per day at RECURRING_HOUR_UTC, plus a run_once startup catch-up 60s
after boot. Idempotency lives in RecurringRepository.claim_run — the job can
run any number of times per day (or after long downtime) without
double-posting: each (rule, period) is claimed atomically exactly once.

run_reminders is a run_repeating sweep (every REMINDER_SWEEP_SECONDS): all
state is in the reminders table, so restarts need no re-registration and the
repeating sweep is its own catch-up. ReminderRepository.claim_send mirrors
claim_run — one send per (reminder, local date), no matter how many sweeps
race.

run_interaction_compaction runs daily (T-041, size-based retention — owner
decision 2026-07-13): each user whose raw ai_interactions rows exceed
AI_INTERACTION_COMPACT_CHARS gets all but the newest rows summarized by a
small model into one durable summary row (channel='system'), the raw rows
deleted and any previous summary folded in. LLM failure -> skip the user,
retry next day.
"""
import logging
import os
from datetime import datetime, timezone

from telegram.error import Forbidden
from telegram.ext import CallbackContext

from domain.memory import (
    build_compaction_prompt,
    build_compaction_system_prompt,
    needs_compaction,
    split_for_compaction,
)
from domain.recurring import is_due
from domain.reminders import is_due as reminder_is_due
from shared.di import get_repos
from src.config import AI_INTERACTION_COMPACT_CHARS
from src.language_util import get_texts_for_language

logger = logging.getLogger(__name__)


async def run_recurring_rules(context: CallbackContext) -> None:
    """Materialize every due recurring rule into a normal transaction."""
    repos = get_repos(context)
    today = datetime.now(timezone.utc).date()
    rules = await repos.recurring.get_active()
    posted = 0

    for rule in rules:
        try:
            due = is_due(rule, today)
            if due is None:
                continue
            # Claim the period first: False means another run (or a restart
            # replay) already posted it — skip without side effects.
            if not await repos.recurring.claim_run(rule.id, due):
                continue

            # Mirror _save_transaction_to_db (src/save_transaction.py):
            # save via the normal transactions path, backdated to the due
            # date, and keep the category dictionary in sync.
            timestamp = datetime(due.year, due.month, due.day, tzinfo=timezone.utc)
            save = (
                repos.transactions.save_income
                if rule.transaction_type == "income"
                else repos.transactions.save_spending
            )
            await save(
                user_id=rule.user_id,
                category=rule.category_name,
                subcategory=rule.subcategory_name,
                amount=float(rule.amount),
                currency=rule.currency,
                timestamp=timestamp,
            )
            config = await repos.users.get_config(rule.user_id)
            language = config.language if config else "en"
            if rule.category_name and rule.subcategory_name:
                await repos.categories.add_category(
                    rule.user_id, rule.category_name, rule.subcategory_name, language
                )
            posted += 1

            texts = get_texts_for_language(language)
            try:
                await context.bot.send_message(
                    chat_id=rule.user_id,
                    text=texts.RECURRING_POSTED.format(
                        name=rule.subcategory_name,
                        amount=rule.amount,
                        currency=rule.currency,
                        date=due.isoformat(),
                    ),
                )
            except Forbidden:
                # User blocked the bot — the transaction is saved; don't let
                # one blocked user kill the rest of the batch.
                logger.warning("Recurring notify: user %s blocked the bot", rule.user_id)
        except Exception:
            logger.exception("Recurring rule %s failed", rule.id)

    if posted:
        logger.info("Recurring run posted %d transaction(s)", posted)


async def run_reminders(context: CallbackContext) -> None:
    """Send every due daily add-transactions reminder (T-034 sweep).

    Always reminds (owner decision 2026-07-19, dv-ff5f) — no skip when the
    user already logged transactions that day. A user may have several
    active times; each row fires at most once per local day on its own
    last_sent_on cursor.
    """
    repos = get_repos(context)
    now_utc = datetime.now(timezone.utc)
    sent = 0

    for reminder, tz_offset_min in await repos.reminders.get_active_with_tz():
        try:
            due = reminder_is_due(reminder, tz_offset_min, now_utc)
            if due is None:
                continue
            # Claim the local date first: False means another sweep (or a
            # restart replay) already handled it — skip without side effects.
            if not await repos.reminders.claim_send(reminder.id, due):
                continue

            config = await repos.users.get_config(reminder.user_id)
            texts = get_texts_for_language(config.language if config else "en")
            try:
                await context.bot.send_message(
                    chat_id=reminder.user_id, text=texts.REMINDER_TEXT
                )
                sent += 1
            except Forbidden:
                # User blocked the bot — claim stays consumed, so we don't
                # retry them all day, and one blocked user can't kill the batch.
                logger.warning("Reminder: user %s blocked the bot", reminder.user_id)
        except Exception:
            logger.exception("Reminder %s failed", reminder.id)

    if sent:
        logger.info("Reminder sweep sent %d nudge(s)", sent)


async def run_interaction_compaction(context: CallbackContext) -> None:
    """Compact oversized AI interaction logs into summary rows (T-041).

    Size-based, not time-based (owner decision 2026-07-13): raw rows persist
    until a user crosses AI_INTERACTION_COMPACT_CHARS, then all but the
    newest domain.memory.KEEP_NEWEST rows are summarized (ASR-correction
    pairs, preferences, Q&A topics), one summary row is inserted
    (channel='system', intent='summary') and the raw rows plus any previous
    summary (folded into the new one) are deleted. LLM failure -> skip the
    user, retry tomorrow.
    """
    from infrastructure.llm import LLMError, get_llm_client
    from infrastructure.repositories.interaction_repository import (
        SUMMARY_CHANNEL,
        SUMMARY_INTENT,
    )

    repos = get_repos(context)
    try:
        user_ids = await repos.interactions.get_users_over_size(
            AI_INTERACTION_COMPACT_CHARS
        )
    except Exception:
        logger.exception("Interaction compaction: size scan failed")
        return

    compacted = 0
    for user_id in user_ids:
        try:
            rows = await repos.interactions.get_all_for_user(user_id)
            if not needs_compaction(rows, AI_INTERACTION_COMPACT_CHARS):
                continue  # raced with another change; re-check per user
            to_compact, _kept = split_for_compaction(rows)
            previous = await repos.interactions.get_latest_summary(user_id)
            prompt = build_compaction_prompt(
                to_compact, previous.transcript if previous else ""
            )

            client = get_llm_client(os.getenv("LLM_INTENT_MODEL", "haiku"))
            try:
                summary = await client.complete(prompt, build_compaction_system_prompt())
            except LLMError as e:
                logger.error(
                    "Interaction compaction: LLM failed for user %s, skipping: %s",
                    user_id,
                    e,
                )
                continue
            summary = summary.strip()
            if not summary:
                logger.error(
                    "Interaction compaction: empty summary for user %s, skipping",
                    user_id,
                )
                continue

            # Insert the new summary BEFORE deleting anything — a crash in
            # between leaves duplicate memory, never lost memory.
            await repos.interactions.add(
                user_id,
                SUMMARY_CHANNEL,
                summary,
                SUMMARY_INTENT,
                outcome="routed",
            )
            ids = [row.id for row in to_compact]
            if previous:
                ids.append(previous.id)  # folded into the new summary
            deleted = await repos.interactions.delete_by_ids(user_id, ids)
            compacted += 1
            logger.info(
                "Interaction compaction: user %s — %d row(s) summarized and deleted",
                user_id,
                deleted,
            )
        except Exception:
            logger.exception("Interaction compaction failed for user %s", user_id)

    if compacted:
        logger.info("Interaction compaction run compacted %d user(s)", compacted)
