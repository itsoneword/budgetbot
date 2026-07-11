import os
import importlib
import configparser


def get_user_language(user_id):
    """Get the language setting for a user from their config file (legacy fallback)"""
    config = configparser.ConfigParser()
    config_path = f"user_data/{user_id}/config.ini"

    if not os.path.exists(config_path):
        return "en"  # Default to English

    config.read(config_path)
    language = config.get("DEFAULT", "language", fallback="en")
    return language


def get_texts_for_language(language):
    """Return the texts module for a language code ('ru' -> texts_ru, else texts).

    Use when there is no Update to derive the language from (e.g. scheduler
    notifications, T-026); handlers should keep using check_language.
    """
    if language == "ru":
        return importlib.import_module("src.texts_ru")
    return importlib.import_module("src.texts")


def check_language(update, context):
    """Check the language setting for the current user and return the appropriate texts module.

    First checks context.user_data['cached_language'] (set by DB-aware handlers),
    then falls back to config.ini file (legacy).
    """
    if update and update.effective_user:
        user_id =update.effective_user.id

        # Check cache first (populated by converted handlers)
        language = None
        if context and hasattr(context, 'user_data') and context.user_data:
            language = context.user_data.get('cached_language')

        # Fallback to file-based lookup if not cached
        if not language:
            language = get_user_language(user_id)

        return get_texts_for_language(language)
    else:
        # Default to English if update or user is None
        return get_texts_for_language("en")


async def cache_user_language(context, repos, user_id: int) -> str:
    """
    Fetch user config from DB and cache language, currency, and limit in context.user_data.
    Call this at the start of converted handlers.
    Returns the language code.
    """
    config = await repos.users.get_config(user_id)
    language = config.language if config else 'en'
    currency = config.currency if config else 'EUR'
    monthly_limit = config.monthly_limit if config else None

    if context and hasattr(context, 'user_data'):
        context.user_data['cached_language'] = language
        context.user_data['cached_currency'] = currency
        context.user_data['cached_monthly_limit'] = monthly_limit

    return language


def get_cached_currency(context, default: str = 'EUR') -> str:
    """
    Get cached currency from context.user_data.
    Call cache_user_language() first in the handler chain.
    """
    if context and hasattr(context, 'user_data') and context.user_data:
        return context.user_data.get('cached_currency', default)
    return default


def get_cached_monthly_limit(context):
    """
    Get cached monthly limit from context.user_data.
    Returns None if not cached.
    """
    if context and hasattr(context, 'user_data') and context.user_data:
        return context.user_data.get('cached_monthly_limit')
    return None


async def ensure_user_config_cached(context, repos, user_id: int) -> dict:
    """
    Ensure user config is cached. If already cached, returns cached values.
    If not cached, fetches from DB and caches.
    
    Returns dict with 'language', 'currency', 'monthly_limit'.
    """
    if context and hasattr(context, 'user_data'):
        cached_lang = context.user_data.get('cached_language')
        if cached_lang:
            # Already cached
            return {
                'language': cached_lang,
                'currency': context.user_data.get('cached_currency', 'EUR'),
                'monthly_limit': context.user_data.get('cached_monthly_limit'),
            }
    
    # Not cached, fetch and cache
    await cache_user_language(context, repos, user_id)
    return {
        'language': context.user_data.get('cached_language', 'en'),
        'currency': context.user_data.get('cached_currency', 'EUR'),
        'monthly_limit': context.user_data.get('cached_monthly_limit'),
    }
