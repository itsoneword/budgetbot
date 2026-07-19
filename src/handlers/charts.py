"""
Chart handlers for generating and sending transaction visualizations.

Handles: monthly charts, extended charts, yearly pie charts.
"""

import asyncio
from datetime import timedelta

from telegram import Update, InputMediaPhoto
from telegram.ext import CallbackContext

from src.language_util import check_language
from shared.di import get_repos
from src.logger import log_debug, log_user_interaction
from src.charts import (
    load_chart_data,
    monthly_pivot_chart,
    monthly_line_chart,
    monthly_ext_pivot_chart,
    make_yearly_pie_chart,
)

# Charts get a stale-rates caption when the cached exchange rates are older than this
STALE_RATES_MAX_AGE_HOURS = 48


def _stale_rates_caption(update: Update, context: CallbackContext, repos) -> str | None:
    """Caption warning about stale exchange rates, or None when rates are fresh."""
    age = repos.currency.rates_age()
    if age is None or age <= timedelta(hours=STALE_RATES_MAX_AGE_HOURS):
        return None
    texts = check_language(update, context)
    return texts.RATES_STALE_NOTE.format(hours=int(age.total_seconds() // 3600))


async def send_chart(update: Update, context: CallbackContext) -> bool:
    """Send monthly spending charts (pivot + line).

    Returns True when a new message was sent (menu callers then restore the
    anchor to the main menu), False when there was nothing to send — in
    callback context the no-data text is NOT sent, the menu edits the tapped
    message instead (T-044).
    """
    user_id = update.effective_user.id
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )

    # Load data from PostgreSQL
    repos = get_repos(context)
    data, user_currency = await load_chart_data(user_id, repos, months=12)

    # Generate charts in worker threads so rendering doesn't block the event
    # loop. Must stay sequential (no gather): both mutate the shared DataFrame
    # in place.
    pivot_chart = await asyncio.to_thread(
        monthly_pivot_chart, user_id, data=data, user_currency=user_currency
    )
    line_chart = await asyncio.to_thread(
        monthly_line_chart, user_id, data=data, user_currency=user_currency
    )

    # Create media group from BytesIO objects (stale-rates note on the first photo)
    stale_note = _stale_rates_caption(update, context, repos)
    media = []
    for chart in (pivot_chart, line_chart):
        if chart:
            media.append(InputMediaPhoto(chart, caption=stale_note if not media else None))

    if media:
        await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
        return True
    if update.callback_query is None:
        # Command context only — the menu shows no-data in the anchor itself.
        texts = check_language(update, context)
        await update.effective_message.reply_text(texts.NO_DATA)
    return False


async def send_ext_chart(update: Update, context: CallbackContext) -> bool:
    """Send extended monthly chart with category breakdown.

    Same return contract as send_chart (T-044)."""
    user_id = update.effective_user.id
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )

    # Load data from PostgreSQL
    repos = get_repos(context)
    data, user_currency = await load_chart_data(user_id, repos, months=12)

    # Generate chart in a worker thread (returns BytesIO)
    ext_chart = await asyncio.to_thread(
        monthly_ext_pivot_chart, user_id, data=data, user_currency=user_currency
    )

    if ext_chart:
        stale_note = _stale_rates_caption(update, context, repos)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=ext_chart, caption=stale_note
        )
        return True
    if update.callback_query is None:
        texts = check_language(update, context)
        await update.effective_message.reply_text(texts.NO_DATA)
    return False


async def send_yearly_piechart(update: Update, context: CallbackContext) -> bool:
    """Send yearly pie charts showing spending distribution by category.

    Same return contract as send_chart (T-044)."""
    user_id = update.effective_user.id
    log_user_interaction(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    log_debug(f"Starting send_yearly_piechart for user {user_id}")

    # Load data from PostgreSQL (load more months for yearly charts)
    repos = get_repos(context)
    data, user_currency = await load_chart_data(user_id, repos, months=36)  # 3 years

    # Render in a worker thread; returns a list of BytesIO objects
    all_charts = await asyncio.to_thread(
        make_yearly_pie_chart, user_id, data=data, user_currency=user_currency
    )
    log_debug(f"Received {len(all_charts)} charts from make_yearly_pie_chart")

    if not all_charts:
        log_debug("No charts returned")
        if update.callback_query is None:
            texts = check_language(update, context)
            await update.effective_message.reply_text(texts.NO_YEARLY_DATA)
        return False

    # Build media group from BytesIO objects (stale-rates note on the first photo)
    stale_note = _stale_rates_caption(update, context, repos)
    media = []
    for i, chart_buf in enumerate(all_charts):
        try:
            media.append(InputMediaPhoto(chart_buf, caption=stale_note if not media else None))
            log_debug(f"Added chart {i+1}/{len(all_charts)} to media group")
        except Exception as e:
            log_debug(f"Error adding chart {i+1} to media group: {e}")

    log_debug(f"Created media group with {len(media)} photos")
    # Send the media group if it contains any photos
    if media:
        try:
            log_debug(f"Sending media group with {len(media)} photos")
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
            log_debug(f"Successfully sent media group to chat {update.effective_chat.id}")
        except Exception as e:
            log_debug(f"Error sending media group for user {user_id}: {e}")
            texts = check_language(update, context)
            await update.effective_message.reply_text(texts.ERROR_SENDING_CHARTS)
        # Something (charts or the error text) was delivered as a new message.
        return True
    log_debug("No media to send, sending ERROR_GENERATING_CHARTS message")
    texts = check_language(update, context)
    await update.effective_message.reply_text(texts.ERROR_GENERATING_CHARTS)
    return True
