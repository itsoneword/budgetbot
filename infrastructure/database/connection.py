"""
Database connection management for BudgetBot.
Uses asyncpg for async PostgreSQL access.
"""
import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

try:
    import asyncpg
except ImportError:
    asyncpg = None  # Will be installed as part of migration

# Default connection string for development
DEFAULT_DATABASE_URL = "postgresql://budgetbot:budgetbot_dev_pass@localhost:5432/budgetbot"


class DatabaseConnection:
    """Manages PostgreSQL connection pool."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> asyncpg.Pool:
        """Create connection pool if not exists."""
        if asyncpg is None:
            raise ImportError("asyncpg is not installed. Run: pip install asyncpg")
        
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
        return self._pool
    
    async def disconnect(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        pool = await self.connect()
        async with pool.acquire() as connection:
            yield connection
    
    @asynccontextmanager
    async def transaction(self):
        """Execute operations within a transaction."""
        async with self.acquire() as connection:
            async with connection.transaction():
                yield connection
    
    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        """Get the connection pool (may be None if not connected)."""
        return self._pool


# Singleton instance for the application
_db: Optional[DatabaseConnection] = None


def get_database() -> DatabaseConnection:
    """Get or create the database connection singleton."""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db


async def init_database() -> asyncpg.Pool:
    """Initialize database connection pool."""
    db = get_database()
    return await db.connect()


async def close_database():
    """Close database connection pool."""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
