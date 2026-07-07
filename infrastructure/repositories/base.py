"""
Base repository class with common database operations.
"""
from typing import Optional, TypeVar, Generic, List, Any
from abc import ABC, abstractmethod
import asyncpg

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository with common operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query without returning results."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all matching rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch a single value."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_many(self, query: str, args_list: List[tuple]) -> None:
        """Execute a query multiple times with different arguments."""
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args_list)
