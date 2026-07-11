"""
Simple dependency injection container for BudgetBot.
Holds database connections and repository instances.
"""
from typing import Optional
import asyncpg

from infrastructure.database.connection import DatabaseConnection, get_database
from infrastructure.repositories import (
    TransactionRepository,
    UserRepository,
    CategoryRepository,
    EntitlementRepository,
    RecurringRepository,
)
from infrastructure.external.currency_service import CurrencyService


class Container:
    """
    Dependency injection container.
    Provides access to repositories and other shared resources.
    """
    
    def __init__(self):
        self._db: Optional[DatabaseConnection] = None
        self._pool: Optional[asyncpg.Pool] = None
        self._transaction_repo: Optional[TransactionRepository] = None
        self._user_repo: Optional[UserRepository] = None
        self._category_repo: Optional[CategoryRepository] = None
        self._entitlement_repo: Optional[EntitlementRepository] = None
        self._recurring_repo: Optional[RecurringRepository] = None
        self._currency_service: Optional[CurrencyService] = None
        self._initialized = False
    
    async def init(self) -> 'Container':
        """Initialize all resources."""
        if self._initialized:
            return self
        
        # Initialize database connection
        self._db = get_database()
        self._pool = await self._db.connect()
        
        # Initialize repositories
        self._transaction_repo = TransactionRepository(self._pool)
        self._user_repo = UserRepository(self._pool)
        self._category_repo = CategoryRepository(self._pool)
        self._entitlement_repo = EntitlementRepository(self._pool)
        self._recurring_repo = RecurringRepository(self._pool)

        # Initialize services
        self._currency_service = CurrencyService(self._pool)

        self._initialized = True
        return self
    
    async def close(self):
        """Clean up all resources."""
        if self._db:
            await self._db.disconnect()
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def pool(self) -> asyncpg.Pool:
        """Get database connection pool."""
        if not self._pool:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._pool
    
    @property
    def transactions(self) -> TransactionRepository:
        """Get transaction repository."""
        if not self._transaction_repo:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._transaction_repo
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        if not self._user_repo:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._user_repo
    
    @property
    def categories(self) -> CategoryRepository:
        """Get category repository."""
        if not self._category_repo:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._category_repo

    @property
    def entitlements(self) -> EntitlementRepository:
        """Get AI entitlement repository."""
        if not self._entitlement_repo:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._entitlement_repo
    def recurring(self) -> RecurringRepository:
        """Get recurring rules repository."""
        if not self._recurring_repo:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._recurring_repo

    @property
    def currency(self) -> CurrencyService:
        """Get currency service."""
        if not self._currency_service:
            raise RuntimeError("Container not initialized. Call init() first.")
        return self._currency_service


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


async def init_container() -> Container:
    """Initialize and return the global container."""
    container = get_container()
    await container.init()
    return container


async def close_container():
    """Close the global container and clean up resources."""
    global _container
    if _container:
        await _container.close()
        _container = None
