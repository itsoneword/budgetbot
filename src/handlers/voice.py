"""
Voice input + free-text intent routing (T-019).

Flow: Telegram voice note -> local whisper transcription (infrastructure/stt)
-> LLM intent classification (validated in domain/intent.py) -> dispatch.

Dispatch works by synthetic-update injection: the routed intent is turned into
the exact text the user could have typed ("/ask <q>", "/show_last",
"coffee 4.5") and fed through application.process_update(), so it follows the
same handlers, gating and conversation states as typed input.

Guardrails:
- check_ai_access() gate (admin / env fallback / DB entitlement, T-022);
  voice duration and transcript length caps;
- the LLM output is reduced to an intent enum + validated payload — commands
  come from a hardcoded whitelist, transaction text must match the normal
  typed pattern (single line, no leading "/");
- transactions are never saved without an explicit inline-keyboard confirm.
"""
import logging
import os
from datetime import datetime, timezone

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageEntity,
    Update,
)
from telegram.ext import CallbackContext

from domain.intent import (
    INTENT_ADD_INCOME,
    INTENT_ADD_TRANSACTION,
    INTENT_QUESTION,
    INTENT_SET_REMINDER,
    INTENT_SHOW_STAT,
    INTENT_UNKNOWN,
    MAX_TRANSCRIPT_CHARS,
    Intent,
    build_intent_prompt,
    build_intent_system_prompt,
    find_correction_target,
    format_known_items,
    format_recent_context,
    parse_intent_response,
)
from infrastructure.llm import LLMError, get_llm_client
from infrastructure.stt import STTError, transcribe_ogg
from shared.di import get_repos
from src.ai_access import check_ai_access
from src.language_util import check_language
from src.logger import log_user_interaction

MAX_VOICE_SECONDS = int(os.getenv("VOICE_MAX_SECONDS", "120"))

# Recent interactions injected into the intent prompt (T-041, owner default).
RECENT_WINDOW = 3


async def handle_voice(update: Update, context: CallbackContext):
    """Transcribe a voice note and route it by intent."""
    user_id = update.effective_user.id
    texts = check_language(update, context)
    log_user_interaction(
        user_id, update.effective_user.first_name, update.effective_user.username
    )

    if not await check_ai_access(user_id, context):
        await update.effective_message.reply_text(texts.ASK_NOT_ALLOWED)
        return

    voice = update.effective_message.voice
    if voice.duration and voice.duration > MAX_VOICE_SECONDS:
        await update.effective_message.reply_text(
            texts.VOICE_TOO_LONG.format(seconds=MAX_VOICE_SECONDS)
        )
        return

    status = await update.effective_message.reply_text(texts.VOICE_TRANSCRIBING)
    try:
        tg_file = await voice.get_file()
        data = bytes(await tg_file.download_as_bytearray())
        transcript = await transcribe_ogg(data)
    except STTError as e:
        logging.error(f"Voice transcription failed for user {user_id}: {e}")
        await status.edit_text(texts.VOICE_ERROR)
        return

    if not transcript:
        await status.edit_text(texts.VOICE_NO_SPEECH)
        return
    transcript = transcript[:MAX_TRANSCRIPT_CHARS]

    await _route_intent(update, context, transcript, status, channel="voice")


async def route_free_text(update: Update, context: CallbackContext, text: str):
    """Intent-route a typed message that didn't match the transaction pattern."""
    texts = check_language(update, context)
    status = await update.effective_message.reply_text(texts.VOICE_ROUTING)
    await _route_intent(
        update, context, text[:MAX_TRANSCRIPT_CHARS], status, channel="text"
    )


async def _load_context_blocks(user_id: int, context: CallbackContext):
    """Recent interactions + prompt blocks for _classify (T-041).

    Failures degrade to empty blocks — context is an enhancement and must
    never block classification.
    """
    repos = get_repos(context)
    recent = []
    summary_text = ""
    try:
        recent = await repos.interactions.get_recent(user_id, RECENT_WINDOW)
        summary_row = await repos.interactions.get_latest_summary(user_id)
        summary_text = summary_row.transcript if summary_row else ""
    except Exception as e:
        logging.error(f"Interaction context load failed for user {user_id}: {e}")

    known_items = ""
    try:
        language = context.user_data.get("cached_language", "en")
        dictionary = await repos.categories.get_dictionary(user_id, language)
        subcategories = [sub for subs in dictionary.values() for sub in subs]
        known_items = format_known_items(subcategories)
    except Exception as e:
        logging.error(f"Known-items load failed for user {user_id}: {e}")

    return recent, format_recent_context(recent, summary_text), known_items


async def _log_interaction(
    context: CallbackContext, user_id: int, channel: str, transcript: str, intent: Intent
):
    """Persist one interaction row; every message counts, including unknown
    (a failed turn must still be visible as context to the next one).
    Returns the row id, or None on failure — logging never blocks routing."""
    if intent.kind in (INTENT_ADD_TRANSACTION, INTENT_ADD_INCOME):
        outcome = "proposed"
    elif intent.kind == INTENT_UNKNOWN:
        outcome = "unknown"
    else:
        outcome = "routed"  # reminder/stat/question dispatch immediately
    try:
        repos = get_repos(context)
        return await repos.interactions.add(
            user_id, channel, transcript, intent.kind, intent.payload, outcome=outcome
        )
    except Exception as e:
        logging.error(f"Interaction log insert failed for user {user_id}: {e}")
        return None


async def _set_outcome_safe(
    context: CallbackContext, interaction_id, user_id: int, outcome: str
):
    """Best-effort outcome update — a lost status must never break the flow."""
    if interaction_id is None:
        return
    try:
        repos = get_repos(context)
        await repos.interactions.set_outcome(interaction_id, user_id, outcome)
    except Exception as e:
        logging.error(f"Interaction outcome update failed for user {user_id}: {e}")


async def _try_correction(
    update: Update,
    context: CallbackContext,
    transcript: str,
    status: Message,
    intent: Intent,
    recent,
    interaction_id,
) -> bool:
    """Handle intent.corrects_previous (T-041). Returns True when the message
    was fully handled here (Replace old->new keyboard shown); False -> caller
    falls through to the normal confirm flow (never guess).

    Previous proposal pending -> supersede it, then the normal confirm
    overwrites the stale user_data payload. Previous already confirmed ->
    find the saved row (exactly one amount+item match among the newest 5) and
    offer delete + re-inject via the vfix_ keyboard.
    """
    user_id = update.effective_user.id
    texts = check_language(update, context)
    prev = next(
        (
            r
            for r in recent or []
            if r.intent in (INTENT_ADD_TRANSACTION, INTENT_ADD_INCOME)
        ),
        None,
    )
    if prev is None:
        return False

    if prev.outcome == "proposed":
        # Pending confirm superseded; the fresh keyboard below acts on the
        # new payload (user_data key is overwritten by the caller).
        await _set_outcome_safe(context, prev.id, user_id, "superseded")
        return False

    if prev.outcome != "confirmed":
        return False  # cancelled/unknown history — treat as a new transaction

    try:
        repos = get_repos(context)
        tx_type = "income" if prev.intent == INTENT_ADD_INCOME else "spending"
        latest = await repos.transactions.get_latest(
            user_id, limit=5, transaction_type=tx_type
        )
        candidates = [(tx.id, tx.subcategory_name, tx.amount) for tx in latest]
        tx_id = find_correction_target(prev.payload, candidates)
    except Exception as e:
        logging.error(f"Correction target lookup failed for user {user_id}: {e}")
        tx_id = None
    if tx_id is None:
        return False  # zero or many matches — never delete ambiguously

    context.user_data["voice_fix_tx_id"] = tx_id
    context.user_data["voice_fix_text"] = intent.payload
    context.user_data["voice_fix_is_income"] = prev.intent == INTENT_ADD_INCOME
    context.user_data["voice_fix_interaction_id"] = interaction_id
    context.user_data["voice_fix_prev_interaction_id"] = prev.id
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(texts.VOICE_TX_CONFIRM_BTN, callback_data="vfix_yes"),
                InlineKeyboardButton(texts.VOICE_TX_CANCEL_BTN, callback_data="vfix_no"),
            ]
        ]
    )
    await status.edit_text(
        texts.VOICE_CONFIRM_FIX.format(
            transcript=transcript, old=prev.payload, new=intent.payload
        ),
        reply_markup=keyboard,
    )
    return True


async def _route_intent(
    update: Update,
    context: CallbackContext,
    transcript: str,
    status: Message,
    channel: str = "voice",
):
    texts = check_language(update, context)
    user_id = update.effective_user.id
    recent, context_block, known_items = await _load_context_blocks(user_id, context)
    intent = await _classify(transcript, context_block, known_items)
    logging.info(
        f"Intent routed for user {user_id}: "
        f"{intent.kind} payload={intent.payload!r} corrects={intent.corrects_previous}"
    )
    interaction_id = await _log_interaction(context, user_id, channel, transcript, intent)

    # Correction path (T-041): only when the classifier flagged it AND a
    # previous add_* interaction exists; anything ambiguous falls through to
    # the normal confirm below — worst case one extra tap, never a silent edit.
    if intent.corrects_previous and intent.kind in (
        INTENT_ADD_TRANSACTION,
        INTENT_ADD_INCOME,
    ):
        if await _try_correction(
            update, context, transcript, status, intent, recent, interaction_id
        ):
            return

    if intent.kind == INTENT_ADD_TRANSACTION:
        context.user_data["voice_tx_text"] = intent.payload
        context.user_data["voice_tx_interaction_id"] = interaction_id
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(texts.VOICE_TX_CONFIRM_BTN, callback_data="vtx_yes"),
                    InlineKeyboardButton(texts.VOICE_TX_CANCEL_BTN, callback_data="vtx_no"),
                ]
            ]
        )
        await status.edit_text(
            texts.VOICE_CONFIRM_TX.format(transcript=transcript, transaction=intent.payload),
            reply_markup=keyboard,
        )
    elif intent.kind == INTENT_ADD_INCOME:
        # Distinct user_data key + vinc_ callbacks: a pending spending confirm
        # (voice_tx_text/vtx_) must not cross-talk with an income one (T-035).
        context.user_data["voice_income_text"] = intent.payload
        context.user_data["voice_income_interaction_id"] = interaction_id
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(texts.VOICE_TX_CONFIRM_BTN, callback_data="vinc_yes"),
                    InlineKeyboardButton(texts.VOICE_TX_CANCEL_BTN, callback_data="vinc_no"),
                ]
            ]
        )
        await status.edit_text(
            texts.VOICE_CONFIRM_INCOME.format(transcript=transcript, income=intent.payload),
            reply_markup=keyboard,
        )
    elif intent.kind == INTENT_SET_REMINDER:
        # Payload is strictly "HH:MM" | "off" (domain/intent.py) — routed
        # through the normal /reminder command, no LLM-specific write path
        # and no extra gating beyond check_ai_access (T-034).
        await status.edit_text(texts.VOICE_HEARD.format(transcript=transcript))
        await _inject_text(update, context, "/reminder " + intent.payload)
    elif intent.kind == INTENT_SHOW_STAT:
        await status.edit_text(texts.VOICE_HEARD.format(transcript=transcript))
        await _inject_text(update, context, "/" + intent.payload)
    elif intent.kind == INTENT_QUESTION:
        await status.edit_text(texts.VOICE_HEARD.format(transcript=transcript))
        await _inject_text(update, context, "/ask " + intent.payload)
    else:
        await status.edit_text(texts.VOICE_UNKNOWN.format(transcript=transcript))


async def handle_voice_tx_confirmation(update: Update, context: CallbackContext):
    """vtx_yes/vtx_no taps on the voice-transaction confirm keyboard."""
    query = update.callback_query
    texts = check_language(update, context)
    await query.answer()

    tx_text = context.user_data.pop("voice_tx_text", None)
    interaction_id = context.user_data.pop("voice_tx_interaction_id", None)
    if query.data == "vtx_yes" and tx_text:
        await _set_outcome_safe(
            context, interaction_id, update.effective_user.id, "confirmed"
        )
        await query.edit_message_text(texts.VOICE_TX_ACCEPTED.format(transaction=tx_text))
        await _inject_text(update, context, tx_text)
    else:
        await _set_outcome_safe(
            context, interaction_id, update.effective_user.id, "cancelled"
        )
        await query.edit_message_text(texts.VOICE_TX_CANCELLED)


async def handle_voice_income_confirmation(update: Update, context: CallbackContext):
    """vinc_yes/vinc_no taps on the voice-income confirm keyboard.

    Saves through save_income_text() directly — injecting the payload as
    plain text would save it as a spending (T-035)."""
    query = update.callback_query
    texts = check_language(update, context)
    await query.answer()

    income_text = context.user_data.pop("voice_income_text", None)
    interaction_id = context.user_data.pop("voice_income_interaction_id", None)
    if query.data == "vinc_yes" and income_text:
        from src.handlers.records import save_income_text

        await _set_outcome_safe(
            context, interaction_id, update.effective_user.id, "confirmed"
        )
        await query.edit_message_text(texts.VOICE_INCOME_ACCEPTED.format(income=income_text))
        if not await save_income_text(update, context, income_text):
            await query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
    else:
        await _set_outcome_safe(
            context, interaction_id, update.effective_user.id, "cancelled"
        )
        await query.edit_message_text(texts.VOICE_TX_CANCELLED)


async def handle_voice_fix_confirmation(update: Update, context: CallbackContext):
    """vfix_yes/vfix_no taps on the "Replace old -> new?" keyboard (T-041).

    Yes: delete the saved row, then re-inject the corrected text through the
    normal save pipeline (category resolution for free) — income goes through
    save_income_text, plain injection would save it as a spending (T-035)."""
    query = update.callback_query
    texts = check_language(update, context)
    user_id = update.effective_user.id
    await query.answer()

    tx_id = context.user_data.pop("voice_fix_tx_id", None)
    fix_text = context.user_data.pop("voice_fix_text", None)
    is_income = context.user_data.pop("voice_fix_is_income", False)
    interaction_id = context.user_data.pop("voice_fix_interaction_id", None)
    prev_interaction_id = context.user_data.pop("voice_fix_prev_interaction_id", None)

    if query.data != "vfix_yes" or not tx_id or not fix_text:
        await _set_outcome_safe(context, interaction_id, user_id, "cancelled")
        await query.edit_message_text(texts.VOICE_FIX_CANCELLED)
        return

    repos = get_repos(context)
    if not await repos.transactions.delete(tx_id, user_id):
        # Row vanished between the offer and the tap (e.g. /delete raced us).
        await _set_outcome_safe(context, interaction_id, user_id, "cancelled")
        await query.edit_message_text(texts.VOICE_FIX_NOT_FOUND)
        return

    await _set_outcome_safe(context, prev_interaction_id, user_id, "superseded")
    await _set_outcome_safe(context, interaction_id, user_id, "confirmed")
    await query.edit_message_text(texts.VOICE_FIX_DONE.format(transaction=fix_text))
    if is_income:
        from src.handlers.records import save_income_text

        if not await save_income_text(update, context, fix_text):
            await query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
    else:
        await _inject_text(update, context, fix_text)


async def _classify(text: str, context_block: str = "", known_items: str = "") -> Intent:
    """Classify via a small/fast model; failures degrade to unknown, never raise."""
    client = get_llm_client(os.getenv("LLM_INTENT_MODEL", "haiku"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %A")
    try:
        raw = await client.complete(
            build_intent_prompt(text, today, context_block, known_items),
            build_intent_system_prompt(),
        )
    except LLMError as e:
        logging.error(f"Intent classification failed: {e}")
        return Intent("unknown")
    return parse_intent_response(raw)


async def _inject_text(update: Update, context: CallbackContext, text: str):
    """Re-dispatch `text` as if the user had typed it.

    Builds a synthetic Message and runs it through process_update, so routed
    intents hit the exact same CommandHandlers / ConversationHandler states as
    typed input (PTB Message objects are immutable — mutating .text raises).
    """
    entities = ()
    if text.startswith("/"):
        entities = (
            MessageEntity(
                type=MessageEntity.BOT_COMMAND, offset=0, length=len(text.split()[0])
            ),
        )
    message = Message(
        message_id=update.effective_message.message_id,
        date=datetime.now(timezone.utc),
        chat=update.effective_chat,
        from_user=update.effective_user,
        text=text,
        entities=entities,
    )
    message.set_bot(context.bot)
    await context.application.process_update(
        Update(update_id=update.update_id, message=message)
    )
