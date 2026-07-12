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
    MAX_TRANSCRIPT_CHARS,
    Intent,
    build_intent_prompt,
    build_intent_system_prompt,
    parse_intent_response,
)
from infrastructure.llm import LLMError, get_llm_client
from infrastructure.stt import STTError, transcribe_ogg
from src.ai_access import check_ai_access
from src.language_util import check_language
from src.logger import log_user_interaction

MAX_VOICE_SECONDS = int(os.getenv("VOICE_MAX_SECONDS", "120"))


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

    await _route_intent(update, context, transcript, status)


async def route_free_text(update: Update, context: CallbackContext, text: str):
    """Intent-route a typed message that didn't match the transaction pattern."""
    texts = check_language(update, context)
    status = await update.effective_message.reply_text(texts.VOICE_ROUTING)
    await _route_intent(update, context, text[:MAX_TRANSCRIPT_CHARS], status)


async def _route_intent(
    update: Update, context: CallbackContext, transcript: str, status: Message
):
    texts = check_language(update, context)
    intent = await _classify(transcript)
    logging.info(
        f"Intent routed for user {update.effective_user.id}: "
        f"{intent.kind} payload={intent.payload!r}"
    )

    if intent.kind == INTENT_ADD_TRANSACTION:
        context.user_data["voice_tx_text"] = intent.payload
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
    if query.data == "vtx_yes" and tx_text:
        await query.edit_message_text(texts.VOICE_TX_ACCEPTED.format(transaction=tx_text))
        await _inject_text(update, context, tx_text)
    else:
        await query.edit_message_text(texts.VOICE_TX_CANCELLED)


async def handle_voice_income_confirmation(update: Update, context: CallbackContext):
    """vinc_yes/vinc_no taps on the voice-income confirm keyboard.

    Saves through save_income_text() directly — injecting the payload as
    plain text would save it as a spending (T-035)."""
    query = update.callback_query
    texts = check_language(update, context)
    await query.answer()

    income_text = context.user_data.pop("voice_income_text", None)
    if query.data == "vinc_yes" and income_text:
        from src.handlers.records import save_income_text

        await query.edit_message_text(texts.VOICE_INCOME_ACCEPTED.format(income=income_text))
        if not await save_income_text(update, context, income_text):
            await query.message.reply_text(texts.TRANSACTION_ERROR_TEXT)
    else:
        await query.edit_message_text(texts.VOICE_TX_CANCELLED)


async def _classify(text: str) -> Intent:
    """Classify via a small/fast model; failures degrade to unknown, never raise."""
    client = get_llm_client(os.getenv("LLM_INTENT_MODEL", "haiku"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %A")
    try:
        raw = await client.complete(build_intent_prompt(text, today), build_intent_system_prompt())
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
