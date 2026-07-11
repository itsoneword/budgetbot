"""
Daily recurring-transactions job (T-026).

run_recurring_rules is registered on PTB's JobQueue in src/core.py main():
once per day at RECURRING_HOUR_UTC, plus a run_once startup catch-up 60s
after boot. Idempotency lives in RecurringRepository.claim_run — the job can
run any number of times per day (or after long downtime) without
double-posting: each (rule, period) is claimed atomically exactly once.
"""
import logging
from datetime import datetime, timezone

from telegram.error import Forbidden
from telegram.ext import CallbackContext

from domain.recurring import is_due
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
