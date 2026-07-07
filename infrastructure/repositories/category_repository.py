"""
Category repository for database operations on user categories (dictionary).
Replaces file_ops.py category-related functions.
"""
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass
import asyncpg

from .base import BaseRepository


@dataclass
class Category:
    """Category data model."""
    id: Optional[int]
    user_id: int
    language: str
    category_name: str
    subcategory_name: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_record(cls, record: asyncpg.Record) -> 'Category':
        return cls(
            id=record['id'],
            user_id=record['user_id'],
            language=record['language'],
            category_name=record['category_name'],
            subcategory_name=record['subcategory_name'],
            created_at=record.get('created_at'),
        )


class CategoryRepository(BaseRepository[Category]):
    """Repository for category/dictionary operations."""
    
    # ==========================================
    # CREATE
    # ==========================================
    
    async def add_category(
        self,
        user_id: int,
        category_name: str,
        subcategory_name: str,
        language: str = 'en',
    ) -> Category:
        """
        Add a new category/subcategory combination.
        Replaces: file_ops.add_category
        """
        query = """
            INSERT INTO user_categories (user_id, language, category_name, subcategory_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, language, category_name, subcategory_name) DO NOTHING
            RETURNING *
        """
        record = await self.fetch_one(query, user_id, language, category_name, subcategory_name)
        
        if record:
            return Category.from_record(record)
        
        # If conflict (already exists), fetch the existing one
        existing = await self.fetch_one("""
            SELECT * FROM user_categories 
            WHERE user_id = $1 AND language = $2 AND category_name = $3 AND subcategory_name = $4
        """, user_id, language, category_name, subcategory_name)
        return Category.from_record(existing)
    
    async def add_subcategory(
        self,
        user_id: int,
        category_name: str,
        subcategory_name: str,
        language: str = 'en',
    ) -> Category:
        """Alias for add_category (same operation)."""
        return await self.add_category(user_id, category_name, subcategory_name, language)
    
    async def bulk_add_categories(
        self,
        user_id: int,
        categories: List[Dict[str, str]],
        language: str = 'en',
    ) -> int:
        """
        Add multiple categories at once.
        categories: List of {'category': str, 'subcategory': str}
        """
        if not categories:
            return 0
        
        query = """
            INSERT INTO user_categories (user_id, language, category_name, subcategory_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, language, category_name, subcategory_name) DO NOTHING
        """
        
        args = [
            (user_id, language, c['category'], c['subcategory'])
            for c in categories
        ]
        
        await self.execute_many(query, args)
        return len(args)
    
    # ==========================================
    # READ
    # ==========================================
    
    async def get_all_categories(
        self,
        user_id: int,
        language: str = 'en',
    ) -> List[str]:
        """
        Get all unique category names for a user.
        Replaces: part of file_ops.read_dictionary
        """
        query = """
            SELECT DISTINCT category_name 
            FROM user_categories
            WHERE user_id = $1 AND language = $2
            ORDER BY category_name
        """
        records = await self.fetch_all(query, user_id, language)
        return [r['category_name'] for r in records]
    
    async def get_subcategories(
        self,
        user_id: int,
        category_name: str,
        language: str = 'en',
    ) -> List[str]:
        """
        Get all subcategories for a specific category.
        Replaces: part of file_ops.read_dictionary
        """
        query = """
            SELECT subcategory_name 
            FROM user_categories
            WHERE user_id = $1 AND language = $2 AND category_name = $3
            ORDER BY subcategory_name
        """
        records = await self.fetch_all(query, user_id, language, category_name)
        return [r['subcategory_name'] for r in records]
    
    async def get_dictionary(
        self,
        user_id: int,
        language: str = 'en',
    ) -> Dict[str, List[str]]:
        """
        Get full category dictionary (category -> [subcategories]).
        Replaces: file_ops.read_dictionary
        """
        query = """
            SELECT category_name, subcategory_name 
            FROM user_categories
            WHERE user_id = $1 AND language = $2
            ORDER BY category_name, subcategory_name
        """
        records = await self.fetch_all(query, user_id, language)
        
        result: Dict[str, List[str]] = {}
        for r in records:
            cat = r['category_name']
            if cat not in result:
                result[cat] = []
            result[cat].append(r['subcategory_name'])
        
        return result
    
    async def category_exists(
        self,
        user_id: int,
        category_name: str,
        language: str = 'en',
    ) -> bool:
        """Check if a category exists."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM user_categories 
                WHERE user_id = $1 AND language = $2 AND category_name = $3
            )
        """
        return await self.fetch_val(query, user_id, language, category_name)
    
    async def subcategory_exists(
        self,
        user_id: int,
        category_name: str,
        subcategory_name: str,
        language: str = 'en',
    ) -> bool:
        """Check if a specific subcategory exists."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM user_categories 
                WHERE user_id = $1 AND language = $2 
                  AND category_name = $3 AND subcategory_name = $4
            )
        """
        return await self.fetch_val(query, user_id, language, category_name, subcategory_name)
    
    async def find_category_by_subcategory(
        self,
        user_id: int,
        subcategory_name: str,
        language: str = 'en',
    ) -> List[str]:
        """
        Find which categories contain a given subcategory.
        Useful for auto-categorization.
        """
        query = """
            SELECT DISTINCT category_name 
            FROM user_categories
            WHERE user_id = $1 AND language = $2 AND subcategory_name = $3
        """
        records = await self.fetch_all(query, user_id, language, subcategory_name)
        return [r['category_name'] for r in records]
    
    async def search_subcategories(
        self,
        user_id: int,
        search_term: str,
        language: str = 'en',
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Search for subcategories matching a term (case-insensitive).
        Returns list of {category, subcategory} matches.
        """
        query = """
            SELECT category_name, subcategory_name 
            FROM user_categories
            WHERE user_id = $1 AND language = $2 
              AND subcategory_name ILIKE $3
            ORDER BY subcategory_name
            LIMIT $4
        """
        records = await self.fetch_all(query, user_id, language, f'%{search_term}%', limit)
        return [
            {'category': r['category_name'], 'subcategory': r['subcategory_name']}
            for r in records
        ]
    
    async def get_frequently_used_subcategories(
        self,
        user_id: int,
        category_name: str,
        language: str = 'en',
        limit: int = 5,
    ) -> List[str]:
        """
        Get most frequently used subcategories for a category.
        Replaces: file_ops.get_frequently_used_subcategories
        """
        query = """
            SELECT uc.subcategory_name, COUNT(t.id) as usage_count
            FROM user_categories uc
            LEFT JOIN transactions t ON 
                t.user_id = uc.user_id 
                AND t.category_name = uc.category_name 
                AND t.subcategory_name = uc.subcategory_name
            WHERE uc.user_id = $1 AND uc.language = $2 AND uc.category_name = $3
            GROUP BY uc.subcategory_name
            ORDER BY usage_count DESC, uc.subcategory_name
            LIMIT $4
        """
        records = await self.fetch_all(query, user_id, language, category_name, limit)
        return [r['subcategory_name'] for r in records]
    
    # ==========================================
    # UPDATE
    # ==========================================
    
    async def rename_category(
        self,
        user_id: int,
        old_name: str,
        new_name: str,
        language: str = 'en',
    ) -> int:
        """
        Rename a category (updates all subcategory entries).
        Replaces: file_ops.update_category
        Returns: number of updated rows
        """
        query = """
            UPDATE user_categories 
            SET category_name = $1
            WHERE user_id = $2 AND language = $3 AND category_name = $4
        """
        result = await self.execute(query, new_name, user_id, language, old_name)
        # Parse "UPDATE X" to get count
        return int(result.split()[-1]) if result else 0
    
    async def rename_subcategory(
        self,
        user_id: int,
        category_name: str,
        old_name: str,
        new_name: str,
        language: str = 'en',
    ) -> bool:
        """Rename a subcategory within a category."""
        query = """
            UPDATE user_categories 
            SET subcategory_name = $1
            WHERE user_id = $2 AND language = $3 
              AND category_name = $4 AND subcategory_name = $5
        """
        result = await self.execute(query, new_name, user_id, language, category_name, old_name)
        return result == "UPDATE 1"
    
    # ==========================================
    # DELETE
    # ==========================================
    
    async def delete_category(
        self,
        user_id: int,
        category_name: str,
        language: str = 'en',
    ) -> int:
        """
        Delete a category and all its subcategories.
        Replaces: file_ops.remove_category
        Returns: number of deleted rows
        """
        query = """
            DELETE FROM user_categories 
            WHERE user_id = $1 AND language = $2 AND category_name = $3
        """
        result = await self.execute(query, user_id, language, category_name)
        return int(result.split()[-1]) if result else 0
    
    async def delete_subcategory(
        self,
        user_id: int,
        category_name: str,
        subcategory_name: str,
        language: str = 'en',
    ) -> bool:
        """Delete a specific subcategory."""
        query = """
            DELETE FROM user_categories 
            WHERE user_id = $1 AND language = $2 
              AND category_name = $3 AND subcategory_name = $4
        """
        result = await self.execute(query, user_id, language, category_name, subcategory_name)
        return result == "DELETE 1"
    
    # ==========================================
    # UTILITY
    # ==========================================
    
    async def count_categories(self, user_id: int, language: str = 'en') -> int:
        """Count unique categories for a user."""
        query = """
            SELECT COUNT(DISTINCT category_name) 
            FROM user_categories 
            WHERE user_id = $1 AND language = $2
        """
        return await self.fetch_val(query, user_id, language)
    
    async def count_subcategories(self, user_id: int, language: str = 'en') -> int:
        """Count total subcategories for a user."""
        query = """
            SELECT COUNT(*) 
            FROM user_categories 
            WHERE user_id = $1 AND language = $2
        """
        return await self.fetch_val(query, user_id, language)
    
    async def copy_default_categories(
        self,
        user_id: int,
        language: str = 'en',
    ) -> int:
        """
        Copy default categories from a template (for new users).
        This could be populated from configs/dictionary.json
        Returns: number of categories added
        """
        # Default categories - can be expanded
        defaults = [
            ('Food', 'Groceries'),
            ('Food', 'Restaurant'),
            ('Food', 'Coffee'),
            ('Transport', 'Public'),
            ('Transport', 'Taxi'),
            ('Transport', 'Fuel'),
            ('Housing', 'Rent'),
            ('Housing', 'Utilities'),
            ('Entertainment', 'Movies'),
            ('Entertainment', 'Games'),
            ('Health', 'Medicine'),
            ('Health', 'Doctor'),
            ('Shopping', 'Clothes'),
            ('Shopping', 'Electronics'),
        ]
        
        query = """
            INSERT INTO user_categories (user_id, language, category_name, subcategory_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, language, category_name, subcategory_name) DO NOTHING
        """
        
        args = [(user_id, language, cat, subcat) for cat, subcat in defaults]
        await self.execute_many(query, args)
        return len(defaults)
