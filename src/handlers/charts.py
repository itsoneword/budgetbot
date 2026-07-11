"""
Chart handlers for generating and sending transaction visualizations.

Handles: monthly charts, extended charts, yearly pie charts.
"""

import asyncio

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


async def send_chart(update: Update, context: CallbackContext) -> None:
    """Send monthly spending charts (pivot + line)."""
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

    # Create media group from BytesIO objects
    media = []
    if pivot_chart:
        media.append(InputMediaPhoto(pivot_chart))
    if line_chart:
        media.append(InputMediaPhoto(line_chart))

    if media:
        await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
    else:
        texts = check_language(update, context)
        await update.message.reply_text(texts.NO_DATA)


async def send_ext_chart(update: Update, context: CallbackContext) -> None:
    """Send extended monthly chart with category breakdown."""
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
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=ext_chart)
    else:
        texts = check_language(update, context)
        await update.message.reply_text(texts.NO_DATA)


async def send_yearly_piechart(update: Update, context: CallbackContext) -> None:
    """Send yearly pie charts showing spending distribution by category."""
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
        texts = check_language(update, context)
        log_debug("No charts returned, sending NO_YEARLY_DATA message")
        await update.message.reply_text(texts.NO_YEARLY_DATA)
        return

    # Build media group from BytesIO objects
    media = []
    for i, chart_buf in enumerate(all_charts):
        try:
            media.append(InputMediaPhoto(chart_buf))
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
            await update.message.reply_text(texts.ERROR_SENDING_CHARTS)
    else:
        log_debug("No media to send, sending ERROR_GENERATING_CHARTS message")
        texts = check_language(update, context)
        await update.message.reply_text(texts.ERROR_GENERATING_CHARTS)
