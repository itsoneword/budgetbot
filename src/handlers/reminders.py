"""
/reminder — daily add-transactions reminders + timezone picker (T-034,
multi-time dv-ff5f).

Write path = the internal action API (add_reminder_time / remove_reminder_time
/ disable_reminder / get_reminders): handler-independent, so the T-027-style
AI channel calls the same validated functions and the LLM never gets its own
write path (the voice intent routes through "/reminder <HH:MM|off>" injection
— HH:MM ADDS a time, "off" turns ALL times off).

A user may keep up to MAX_REMINDER_TIMES active times (e.g. midday +
evening); each fires once per local day on its own last_sent_on cursor.

Timezone is asked lazily: the first rem_set_/args add with no stored offset
stashes the pending time in user_data and shows the one-tap tzpick_ picker
(buttons = candidate current local times); picking saves the offset and
completes the pending reminder. Both ^rem_ and ^tzpick_ are standalone
CallbackQueryHandlers registered BEFORE spendings_handler in core.py, so its
pattern-less menu_callback fallback can't swallow them mid-conversation.
"""
import logging
from datetime import datetime, time, timezone
from typing import List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from domain.reminders import (
    MAX_REMINDER_TIMES,
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

async def add_reminder_time(
    repos, user_id: int, time_local: time, tz_offset_min: Optional[int]
) -> Reminder:
    """Add one daily reminder time (re-adding re-activates); input must be
    pre-validated (domain.reminders.parse_reminder_time). If the chosen time
    is already past in the user's local day, today's slot is consumed
    immediately so adding "17:00" at 18:00 first fires tomorrow instead of
    instantly."""
    reminder = await repos.reminders.add_time(user_id, time_local)
    due = is_due(reminder, tz_offset_min, datetime.now(timezone.utc))
    if due is not None:
        await repos.reminders.claim_send(reminder.id, due)
    return reminder


async def remove_reminder_time(repos, user_id: int, time_local: time) -> bool:
    """Delete one reminder time. True if it existed."""
    return await repos.reminders.remove_time(user_id, time_local)


async def disable_reminder(repos, user_id: int) -> bool:
    """Turn ALL times off (rows survive, so times come back on re-enable)."""
    return await repos.reminders.set_active(user_id, False)


async def get_reminders(repos, user_id: int) -> List[Reminder]:
    """All of the user's reminder rows, ordered by time."""
    return await repos.reminders.get_all_for_user(user_id)


# =========================================================================
# Rendering
# =========================================================================

def build_reminder_view(
    reminders: List[Reminder], texts, back_cb: Optional[str] = None
) -> Tuple[str, InlineKeyboardMarkup]:
    """(status text, keyboard) for the /reminder view.

    Status line lists all active times; presets ADD a time; each active time
    gets a removal button (tap = remove, view re-renders in place); the
    all-off button shows while anything is active. back_cb appends a Back row
    so the menu-opened view isn't a dead end (T-044); the /reminder command
    path passes nothing and is unchanged.
    """
    active = [r for r in reminders if r.active]
    if active:
        text = texts.REMINDER_STATUS_LIST.format(
            times=", ".join(format_reminder_time(r.time_local) for r in active)
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
    if active:
        keyboard.append([
            InlineKeyboardButton(
                f"{texts.REMINDER_REMOVE_BTN} {format_reminder_time(r.time_local)}",
                callback_data=f"rem_del_{format_reminder_time(r.time_local)}",
            )
            for r in active
        ])
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


async def _safe_edit(query, text, **kwargs) -> None:
    """edit_message_text that swallows Telegram's 'Message is not modified'.

    Re-rendering the same view (e.g. re-adding an already-active preset)
    re-issues an identical edit; without this guard the BadRequest would trip
    the global error handler. Everything else re-raises.
    """
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


def _existing_back_cb(message) -> Optional[str]:
    """Preserve a Back row across in-place re-renders (menu-opened views)."""
    markup = getattr(message, "reply_markup", None)
    if markup is None:
        return None
    for row in markup.inline_keyboard:
        for button in row:
            data = getattr(button, "callback_data", None)
            if data and data.startswith("back_"):
                return data
    return None


async def _rerender(query, repos, user_id: int, texts, prefix: str = "") -> None:
    """Edit the tapped message back into the (fresh) reminder list view."""
    reminders = await get_reminders(repos, user_id)
    text, markup = build_reminder_view(
        reminders, texts, back_cb=_existing_back_cb(query.message)
    )
    if prefix:
        text = prefix + "\n\n" + text
    await _safe_edit(query, text, reply_markup=markup)


# =========================================================================
# Handlers
# =========================================================================

async def reminder_command(update: Update, context: CallbackContext) -> None:
    """/reminder — status + presets; /reminder 17:00 — add; /reminder off."""
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    args = context.args or []

    if not args:
        reminders = await get_reminders(repos, user_id)
        text, markup = build_reminder_view(reminders, texts)
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

    active_times = [
        r.time_local for r in await get_reminders(repos, user_id) if r.active
    ]
    if len(active_times) >= MAX_REMINDER_TIMES and time_local not in active_times:
        await update.message.reply_text(
            texts.REMINDER_LIMIT_REACHED.format(limit=MAX_REMINDER_TIMES)
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

    await add_reminder_time(repos, user_id, time_local, tz_offset_min)
    await update.message.reply_text(
        texts.REMINDER_SET.format(time=format_reminder_time(time_local))
    )


async def handle_reminder_callback(update: Update, context: CallbackContext) -> None:
    """rem_set_HH:MM / rem_del_HH:MM / rem_off taps on the reminder keyboard.

    Every mutation re-renders the list view in place (dv-ff5f) so managing
    multiple times never requires reopening the menu.
    """
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    repos = get_repos(context)
    await ensure_user_config_cached(context, repos, user_id)
    texts = check_language(update, context)
    data = query.data

    if data == "rem_off":
        await disable_reminder(repos, user_id)
        await _rerender(query, repos, user_id, texts, prefix=texts.REMINDER_DISABLED)
        return

    if data.startswith("rem_del_"):
        time_local = parse_reminder_time(data[len("rem_del_"):])
        if time_local is None:
            logger.warning("Bad reminder callback data: %r", data)
            return
        removed = await remove_reminder_time(repos, user_id, time_local)
        prefix = (
            texts.REMINDER_TIME_REMOVED.format(time=format_reminder_time(time_local))
            if removed else ""
        )
        await _rerender(query, repos, user_id, texts, prefix=prefix)
        return

    if not data.startswith("rem_set_"):
        logger.warning("Unknown reminder callback action: %r", data)
        return

    time_local = parse_reminder_time(data[len("rem_set_"):])
    if time_local is None:
        logger.warning("Bad reminder callback data: %r", data)
        return

    active_times = [
        r.time_local for r in await get_reminders(repos, user_id) if r.active
    ]
    if len(active_times) >= MAX_REMINDER_TIMES and time_local not in active_times:
        await _rerender(
            query, repos, user_id, texts,
            prefix=texts.REMINDER_LIMIT_REACHED.format(limit=MAX_REMINDER_TIMES),
        )
        return

    config = await repos.users.get_config(user_id)
    tz_offset_min = config.tz_offset_min if config else None
    if tz_offset_min is None:
        context.user_data[_PENDING_TIME_KEY] = format_reminder_time(time_local)
        await query.edit_message_text(
            texts.TZ_PICK_PROMPT, reply_markup=build_tz_keyboard()
        )
        return

    await add_reminder_time(repos, user_id, time_local, tz_offset_min)
    await _rerender(query, repos, user_id, texts)


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
            await add_reminder_time(repos, user_id, time_local, offset_min)
            message = (
                texts.REMINDER_SET.format(time=format_reminder_time(time_local))
                + "\n\n" + message
            )

    await query.edit_message_text(message)
