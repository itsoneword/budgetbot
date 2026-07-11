"""
AI access gate (T-022).

Single check consulted by every AI entry point: /ask (core.py), free-text
intent routing (core.py handle_text) and voice notes (src/handlers/voice.py).

Tiers, in order:
1. is_llm_allowed(): ADMIN_USER_ID always, plus the legacy LLM_ALLOWED_USERS
   env allowlist (migration fallback — removed in the T-023 release);
2. DB entitlement via EntitlementRepository.has_ai_access().

Fail-closed: a DB error denies access (except tier 1) and logs loudly —
if all non-admin users suddenly lose AI access, check DB health before
suspecting a mass revocation.
"""
import logging

from telegram.ext import CallbackContext

from shared.di import get_repos
from src.config import is_llm_allowed


async def check_ai_access(user_id: int, context: CallbackContext) -> bool:
    """True if this user may use LLM-backed features."""
    if is_llm_allowed(user_id):
        return True
    try:
        repos = get_repos(context)
        return await repos.entitlements.has_ai_access(user_id)
    except Exception:
        logging.exception(
            "AI access check failed for user %s — failing closed. "
            "This is a DB/container error, NOT a revocation.",
            user_id,
        )
        return False
