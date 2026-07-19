"""
/reminder — daily add-transactions reminder + timezone picker (T-034).

Write path = the internal action API (set_reminder / disable_reminder /
get_reminder): handler-independent, so the T-027-style AI channel calls the
same validated functions and the LLM never gets its own write path (the
voice intent routes through "/reminder <HH:MM|off>" injection).

Timezone is asked lazily: the first rem_set_/args set with no stored offset
stashes the pending time in user_data and shows the one-tap tzpick_ picker
(buttons = candidate current local times); picking saves the offset and
completes the pending reminder. Both ^rem_ and ^tzpick_ are standalone
CallbackQueryHandlers registered BEFORE spendings_handler in core.py, so its
pattern-less menu_callback fallback can't swallow them mid-conversation.
"""
import logging
from datetime import datetime, time, timezone
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from domain.reminders import (
    REAL_UTC_OFFSETS_MIN,
    build_offset_candidates,
    format_reminder_time,
    format_utc_offset,
    is_due,
    parse_reminder_time,
)
from infrastructure.repositories import Reminder
from shared.di import get_repos
from src.language_util import check_language, ensure_user_config_cached

logger = logging.getLogger(__name__)

# Preset fire times shown as one-tap buttons (default 17:00 in the middle).
PRESET_TIMES = ("09:00", "12:00", "17:00", "20:00", "21:00")

_PENDING_TIME_KEY = "pending_reminder_time"


# =========================================================================
# Internal action API (also the T-027-style AI-channel surface)
# =========================================================================

async def set_reminder(repos, user_id: int, time_local: time, tz_offset_min: Optional[int]) -> Reminder:
    """Create/update the daily reminder; input must be pre-validated
    (domain.reminders.parse_reminder_time). If the chosen time is already past
    in the user's local day, today's slot is consumed immediately so setting
    "17:00" at 18:00 first fires tomorrow instead of instantly."""
    reminder = await repos.reminders.upsert(user_id, time_local)
    due = is_due(reminder, tz_offset_min, datetime.now(timezone.utc))
    if due is not None:
        await repos.reminders.claim_send(reminder.id, due)
    return reminder


async def disable_reminder(repos, user_id: int) -> bool:
    return await repos.reminders.set_active(user_id, False)


async def get_reminder(repos, user_id: int) -> Optional[Reminder]:
    return await repos.reminders.get_for_user(user_id)


# =========================================================================
# Rendering
# =========================================================================

def build_reminder_view(
    reminder: Optional[Reminder], texts, back_cb: Optional[str] = None
) -> Tuple[str, InlineKeyboardMarkup]:
    """(status text, preset keyboard) for the /reminder view.

    back_cb appends a Back row so the menu-opened view isn't a dead end
    (T-044); the /reminder command path passes nothing and is unchanged.
    """
    if reminder and reminder.active:
        text = texts.REMINDER_STATUS_ACTIVE.format(
            time=format_reminder_time(reminder.time_local)
        )
    else:
        text = texts.REMINDER_STATUS_OFF
    keyboard = [
        [
            InlineKeyboardButton(f"⏰ {preset}", callback_data=f"rem_set_{preset}")
            for preset in PRESET_TIMES[:3]
        ],
        [
            InlineKeyboardButton(f"⏰ {preset}", callback_data=f"rem_set_{preset}")
            for preset in PRESET_TIMES[3:]
        ],
    ]
    if reminder and reminder.active:
        keyboard.append([InlineKeyboardButton(texts.REMINDER_OFF_BTN, callback_data="rem_off")])
    if back_cb:
        keyboard.append(
            [InlineKeyboardButton(texts.BACK_BUTTON, callback_data=back_cb)]
        )
    return text, InlineKeyboardMarkup(keyboard)


def build_tz_keyboard(
    back_cb: Optional[str] = None, texts=None
) -> InlineKeyboardMarkup:
    """One-tap offset picker: each button is a candidate current local time.

    back_cb (+ texts for the label) appends a Back row — used by the
    settings-menu path (T-044); reminder-flow callers are unchanged.
    """
    candidates = build_offset_candidates(datetime.now(timezone.utc))
    keyboard = []
    for i in range(0, len(candidates), 4):
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"tzpick_{offset}")
            for offset, label in candidates[i : i + 4]
        ])
    if back_cb and texts is not None:
        keyboard.append(
            [InlineKeyboardButton(texts.BACK_BUTTON, callback_data=back_cb)]
        )
    return InlineKeyboardMarkup(keyboard)


# =========================================================================
# Handlers
# =========================================================================

async def reminder_command(update: Update, context: CallbackContext) -> None:
    """/reminder — status + presets; /reminder 17:00 — set; /reminder off."""
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    args = context.args or []

    if not args:
        reminder = await get_reminder(repos, user_id)
        text, markup = build_reminder_view(reminder, texts)
        await update.message.reply_text(text, reply_markup=markup)
        return

    if args[0].lower() == "off":
        await disable_reminder(repos, user_id)
        await update.message.reply_text(texts.REMINDER_DISABLED)
        return

    time_local = parse_reminder_time(args[0])
    if time_local is None:
        await update.message.reply_text(
            texts.REMINDER_INVALID_TIME + "\n\n" + texts.REMINDER_USAGE
        )
        return

    config = await repos.users.get_config(user_id)
    tz_offset_min = config.tz_offset_min if config else None
    if tz_offset_min is None:
        # Timezone unknown — stash the requested time, ask for the offset
        # first (one-tap picker); tzpick_ completes the reminder.
        context.user_data[_PENDING_TIME_KEY] = format_reminder_time(time_local)
        await update.message.reply_text(
            texts.TZ_PICK_PROMPT, reply_markup=build_tz_keyboard()
        )
        return

    await set_reminder(repos, user_id, time_local, tz_offset_min)
    await update.message.reply_text(
        texts.REMINDER_SET.format(time=format_reminder_time(time_local))
    )


async def handle_reminder_callback(update: Update, context: CallbackContext) -> None:
    """rem_set_HH:MM / rem_off taps on the reminder preset keyboard."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    data = query.data

    if data == "rem_off":
        await disable_reminder(repos, user_id)
        await query.edit_message_text(texts.REMINDER_DISABLED)
        return

    if not data.startswith("rem_set_"):
        logger.warning("Unknown reminder callback action: %r", data)
        return

    time_local = parse_reminder_time(data[len("rem_set_"):])
    if time_local is None:
        logger.warning("Bad reminder callback data: %r", data)
        return

    config = await repos.users.get_config(user_id)
    tz_offset_min = config.tz_offset_min if config else None
    if tz_offset_min is None:
        context.user_data[_PENDING_TIME_KEY] = format_reminder_time(time_local)
        await query.edit_message_text(
            texts.TZ_PICK_PROMPT, reply_markup=build_tz_keyboard()
        )
        return

    await set_reminder(repos, user_id, time_local, tz_offset_min)
    await query.edit_message_text(
        texts.REMINDER_SET.format(time=format_reminder_time(time_local))
    )


async def handle_tzpick_callback(update: Update, context: CallbackContext) -> None:
    """tzpick_<offset_min> tap: save the offset, complete any pending reminder."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)

    try:
        offset_min = int(query.data[len("tzpick_"):])
    except ValueError:
        logger.warning("Bad tzpick callback data: %r", query.data)
        return
    if offset_min not in REAL_UTC_OFFSETS_MIN:
        logger.warning("Rejected non-candidate tz offset: %r", query.data)
        return

    await repos.users.update_tz_offset(user_id, offset_min)
    message = texts.TZ_SAVED.format(offset=format_utc_offset(offset_min))

    pending = context.user_data.pop(_PENDING_TIME_KEY, None)
    if pending is not None:
        time_local = parse_reminder_time(pending)
        if time_local is not None:
            await set_reminder(repos, user_id, time_local, offset_min)
            message = (
                texts.REMINDER_SET.format(time=format_reminder_time(time_local))
                + "\n\n" + message
            )

    await query.edit_message_text(message)
