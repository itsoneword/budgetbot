"""
Bot integration helpers for accessing repositories from handlers.
Provides convenient functions to get repositories from context.
"""
from typing import TYPE_CHECKING
from telegram.ext import Application, ContextTypes

from .container import Container, init_container, close_container

if TYPE_CHECKING:
    from infrastructure.repositories import (
        TransactionRepository,
        UserRepository, 
        CategoryRepository,
    )


# Key used to store container in bot_data
CONTAINER_KEY = 'di_container'


async def setup_container(application: Application) -> None:
    """
    Initialize the DI container and store it in bot_data.
    Call this in Application.post_init callback.
    """
    container = await init_container()
    application.bot_data[CONTAINER_KEY] = container
    print("[OK] Database container initialized")


async def cleanup_container(application: Application) -> None:
    """
    Clean up the DI container.
    Call this in Application.post_shutdown callback.
    """
    container = application.bot_data.get(CONTAINER_KEY)
    if container:
        await container.close()
        print("[OK] Database container closed")
    await close_container()


def get_repos(context: ContextTypes.DEFAULT_TYPE) -> Container:
    """
    Get the DI container from context.
    
    Usage in handlers:
        repos = get_repos(context)
        transactions = await repos.transactions.get_latest(user_id, limit=10)
    """
    container = context.bot_data.get(CONTAINER_KEY)
    if not container or not container.is_initialized:
        raise RuntimeError("DI container not initialized. Ensure setup_container was called.")
    return container


def get_transaction_repo(context: ContextTypes.DEFAULT_TYPE) -> 'TransactionRepository':
    """Shortcut to get transaction repository."""
    return get_repos(context).transactions


def get_user_repo(context: ContextTypes.DEFAULT_TYPE) -> 'UserRepository':
    """Shortcut to get user repository."""
    return get_repos(context).users


def get_category_repo(context: ContextTypes.DEFAULT_TYPE) -> 'CategoryRepository':
    """Shortcut to get category repository."""
    return get_repos(context).categories
