"""
JobQueue jobs: daily recurring transactions (T-026) and reminder sweep (T-034).

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
"""
import logging
from datetime import datetime, timezone

from telegram.error import Forbidden
from telegram.ext import CallbackContext

from domain.recurring import is_due
from domain.reminders import is_due as reminder_is_due, local_day_start_utc
from shared.di import get_repos
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
    """Send every due daily add-transactions reminder (T-034 sweep)."""
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

            # Skip-if-logged (owner decision 2026-07-11): a user who already
            # logged something this local day doesn't need the nudge. The
            # claim stays consumed — one decision per day, no late re-fires.
            day_start = local_day_start_utc(due, tz_offset_min)
            if await repos.transactions.has_transaction_since(reminder.user_id, day_start):
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
