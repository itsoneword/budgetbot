"""
User repository for database operations on users and their configs.
Replaces file_ops.py user-related functions.
"""
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
import asyncpg

from .base import BaseRepository


@dataclass
class User:
    """User data model."""
    user_id: int
    username: Optional[str] = None
    telegram_username: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'User':
        return cls(
            user_id=record['user_id'],
            username=record.get('username'),
            telegram_username=record.get('telegram_username'),
            created_at=record.get('created_at'),
            updated_at=record.get('updated_at'),
        )


@dataclass
class UserConfig:
    """User configuration data model."""
    user_id: int
    language: str = 'en'
    currency: str = 'EUR'
    monthly_limit: Decimal = Decimal('99999999.00')
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'UserConfig':
        return cls(
            user_id=record['user_id'],
            language=record.get('language', 'en'),
            currency=record.get('currency', 'EUR'),
            monthly_limit=record.get('monthly_limit', Decimal('99999999.00')),
            name=record.get('name'),
            created_at=record.get('created_at'),
            updated_at=record.get('updated_at'),
        )


class UserRepository(BaseRepository[User]):
    """Repository for user and config operations."""
    
    # ==========================================
    # USER CRUD
    # ==========================================
    
    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        telegram_username: Optional[str] = None,
    ) -> User:
        """
        Create a new user record.
        Replaces: file_ops.update_user_list (partially)
        """
        query = """
            INSERT INTO users (user_id, username, telegram_username)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET
                username = COALESCE(EXCLUDED.username, users.username),
                telegram_username = COALESCE(EXCLUDED.telegram_username, users.telegram_username),
                updated_at = NOW()
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, username, telegram_username)
        return User.from_record(record)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE user_id = $1"
        record = await self.fetch_one(query, user_id)
        return User.from_record(record) if record else None
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists."""
        query = "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)"
        return await self.fetch_val(query, user_id)
    
    async def update_user_info(
        self,
        user_id: int,
        username: Optional[str] = None,
        telegram_username: Optional[str] = None,
    ) -> bool:
        """Update user's username/telegram_username (for future use)."""
        updates = []
        params = []
        
        if username is not None:
            params.append(username)
            updates.append(f"username = ${len(params)}")
        
        if telegram_username is not None:
            params.append(telegram_username)
            updates.append(f"telegram_username = ${len(params)}")
        
        if not updates:
            return False
        
        params.append(user_id)
        query = f"""
            UPDATE users SET {', '.join(updates)}, updated_at = NOW()
            WHERE user_id = ${len(params)}
        """
        result = await self.execute(query, *params)
        return result == "UPDATE 1"
    
    async def get_all_users(self) -> List[User]:
        """Get all users (for admin purposes)."""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        records = await self.fetch_all(query)
        return [User.from_record(r) for r in records]
    
    async def count_users(self) -> int:
        """Count total users."""
        return await self.fetch_val("SELECT COUNT(*) FROM users")
    
    # ==========================================
    # USER CONFIG CRUD
    # ==========================================
    
    async def create_config(
        self,
        user_id: int,
        language: str = 'en',
        currency: str = 'EUR',
        monthly_limit: Optional[Decimal] = None,
        name: Optional[str] = None,
    ) -> UserConfig:
        """
        Create user config (usually after user creation).
        Replaces: file_ops.create_config_file
        """
        limit = monthly_limit or Decimal('99999999.00')
        query = """
            INSERT INTO user_configs (user_id, language, currency, monthly_limit, name)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                language = EXCLUDED.language,
                currency = EXCLUDED.currency,
                monthly_limit = EXCLUDED.monthly_limit,
                name = COALESCE(EXCLUDED.name, user_configs.name),
                updated_at = NOW()
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, language, currency, limit, name)
        return UserConfig.from_record(record)
    
    async def get_config(self, user_id: int) -> Optional[UserConfig]:
        """
        Get user's configuration.
        Replaces: file_ops.read_config
        """
        query = "SELECT * FROM user_configs WHERE user_id = $1"
        record = await self.fetch_one(query, user_id)
        return UserConfig.from_record(record) if record else None
    
    async def get_or_create_config(
        self,
        user_id: int,
        default_language: str = 'en',
        default_currency: str = 'EUR',
    ) -> UserConfig:
        """Get config or create with defaults if not exists."""
        config = await self.get_config(user_id)
        if config:
            return config
        
        # Ensure user exists first
        await self.create_user(user_id)
        return await self.create_config(
            user_id,
            language=default_language,
            currency=default_currency,
        )
    
    async def update_language(self, user_id: int, language: str) -> bool:
        """
        Update user's language preference.
        Replaces: file_ops.save_user_setting (for language)
        """
        query = """
            UPDATE user_configs 
            SET language = $1, updated_at = NOW()
            WHERE user_id = $2
        """
        result = await self.execute(query, language, user_id)
        return result == "UPDATE 1"
    
    async def update_currency(self, user_id: int, currency: str) -> bool:
        """
        Update user's currency preference.
        Replaces: file_ops.save_user_setting (for currency)
        """
        query = """
            UPDATE user_configs 
            SET currency = $1, updated_at = NOW()
            WHERE user_id = $2
        """
        result = await self.execute(query, currency.upper()[:3], user_id)
        return result == "UPDATE 1"
    
    async def update_limit(self, user_id: int, monthly_limit: Decimal) -> bool:
        """
        Update user's monthly spending limit.
        Replaces: file_ops.save_user_setting (for limit)
        """
        query = """
            UPDATE user_configs 
            SET monthly_limit = $1, updated_at = NOW()
            WHERE user_id = $2
        """
        result = await self.execute(query, monthly_limit, user_id)
        return result == "UPDATE 1"
    
    async def update_name(self, user_id: int, name: str) -> bool:
        """Update user's display name."""
        query = """
            UPDATE user_configs 
            SET name = $1, updated_at = NOW()
            WHERE user_id = $2
        """
        result = await self.execute(query, name, user_id)
        return result == "UPDATE 1"
    
    # ==========================================
    # COMBINED OPERATIONS
    # ==========================================
    
    async def setup_new_user(
        self,
        user_id: int,
        language: str = 'en',
        currency: str = 'EUR',
        username: Optional[str] = None,
        telegram_username: Optional[str] = None,
    ) -> tuple[User, UserConfig]:
        """
        Complete setup for a new user (user record + config).
        Replaces: file_ops.create_user_dir_and_copy_dict + create_config_file
        """
        user = await self.create_user(user_id, username, telegram_username)
        config = await self.create_config(user_id, language, currency)
        return user, config
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user and all related data (CASCADE).
        Replaces: file_ops.archive_user_data
        """
        # Due to CASCADE, this will delete config, categories, and transactions
        query = "DELETE FROM users WHERE user_id = $1"
        result = await self.execute(query, user_id)
        return result == "DELETE 1"
    
    async def config_exists(self, user_id: int) -> bool:
        """
        Check if user has a config.
        Replaces: file_ops.check_config_exists
        """
        query = "SELECT EXISTS(SELECT 1 FROM user_configs WHERE user_id = $1)"
        return await self.fetch_val(query, user_id)
