"""
Session loader - batch fetches user data from database.

This is the only place where DB queries happen for read operations.
After loading, all filtering/aggregation happens in Python.

Usage:
    from domain.session_loader import load_user_session
    from shared.di import get_repos

    repos = get_repos(context)
    session = await load_user_session(user_id, repos)

    # Now use pure Python filters
    from domain.filters import filter_by_period, calculate_summary
    filtered = filter_by_period(session.transactions, '3m')
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from domain.models.user_session import UserSession, UserConfig, Transaction

if TYPE_CHECKING:
    from shared.di.container import RepositoryContainer


async def load_user_session(
    user_id: int,
    repos: 'RepositoryContainer',
    load_transactions: bool = True,
    transactions_months: int = 12,
    transaction_type: Optional[str] = None,
) -> UserSession:
    """
    Load complete user session data from database.

    Args:
        user_id: Telegram user ID
        repos: Repository container from DI
        load_transactions: Whether to load transactions (can skip for settings-only ops)
        transactions_months: How many months of transactions to load (default: 12)
        transaction_type: Filter by type ('spending'/'income'), None = all

    Returns:
        UserSession with config, categories, and transactions
    """
    # 1. Load user config
    db_config = await repos.users.get_config(user_id)
    if db_config:
        config = UserConfig(
            user_id=db_config.user_id,
            language=db_config.language,
            currency=db_config.currency,
            monthly_limit=db_config.monthly_limit,
            name=db_config.name,
        )
    else:
        # Create default config if not exists
        config = UserConfig(user_id=user_id)

    # 2. Load categories dictionary
    categories = await repos.categories.get_dictionary(user_id, config.language)

    # 3. Load transactions (optional, can skip for settings-only operations)
    transactions = []
    transactions_since = None

    if load_transactions:
        # Calculate start date
        now = datetime.now(timezone.utc)
        if transactions_months:
            transactions_since = now - timedelta(days=transactions_months * 30)

        # Fetch from DB
        db_transactions = await _fetch_transactions(
            repos, user_id, transactions_since, transaction_type
        )

        # Convert to domain model
        transactions = [Transaction.from_repo(tx) for tx in db_transactions]

    return UserSession(
        user_id=user_id,
        config=config,
        categories=categories,
        transactions=transactions,
        transactions_since=transactions_since,
    )


async def _fetch_transactions(
    repos: 'RepositoryContainer',
    user_id: int,
    since: Optional[datetime],
    transaction_type: Optional[str],
):
    """
    Fetch transactions from database.
    This is the single query for all transaction data.
    """
    if since:
        # Use date range query
        from datetime import date
        return await repos.transactions.get_by_date_range(
            user_id=user_id,
            start_date=since.date() if isinstance(since, datetime) else since,
            end_date=date(2099, 12, 31),  # Far future
            transaction_type=transaction_type,
        )
    else:
        # Get all transactions (no limit on time)
        return await repos.transactions.get_latest(
            user_id=user_id,
            limit=10000,  # Reasonable max
            transaction_type=transaction_type,
        )


async def load_minimal_session(
    user_id: int,
    repos: 'RepositoryContainer',
) -> UserSession:
    """
    Load session without transactions (for settings/config operations).
    Much faster when you only need config and categories.
    """
    return await load_user_session(
        user_id, repos,
        load_transactions=False,
    )


async def refresh_transactions(
    session: UserSession,
    repos: 'RepositoryContainer',
    months: int = 12,
    transaction_type: Optional[str] = None,
) -> UserSession:
    """
    Refresh only transactions in an existing session.
    Useful after saving a new transaction.
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=months * 30)

    db_transactions = await _fetch_transactions(
        repos, session.user_id, since, transaction_type
    )

    transactions = [Transaction.from_repo(tx) for tx in db_transactions]

    # Return new session with updated transactions
    return UserSession(
        user_id=session.user_id,
        config=session.config,
        categories=session.categories,
        transactions=transactions,
        transactions_since=since,
    )
