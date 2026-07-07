#!/usr/bin/env python3
"""
Test script to verify repository classes work with the migrated data.

Usage:
    python scripts/test_repositories.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.database.connection import get_database, close_database
from infrastructure.repositories import (
    TransactionRepository,
    UserRepository,
    CategoryRepository,
)


async def test_repositories():
    """Test all repository operations."""
    print("Testing Repository Classes")
    print("=" * 50)
    
    db = get_database()
    pool = await db.connect()
    
    # Initialize repositories
    tx_repo = TransactionRepository(pool)
    user_repo = UserRepository(pool)
    cat_repo = CategoryRepository(pool)
    
    try:
        # ==========================================
        # Test UserRepository
        # ==========================================
        print("\n[UserRepository]")
        
        user_count = await user_repo.count_users()
        print(f"  Total users: {user_count}")
        
        # Get first user for testing
        users = await user_repo.get_all_users()
        if users:
            test_user_id = users[0].user_id
            print(f"  Test user ID: {test_user_id}")
            
            # Get config
            config = await user_repo.get_config(test_user_id)
            if config:
                print(f"  Config: lang={config.language}, currency={config.currency}, limit={config.monthly_limit}")
            else:
                print("  Config: None")
        else:
            print("  No users found!")
            return
        
        print("  [OK] UserRepository tests passed")
        
        # ==========================================
        # Test CategoryRepository
        # ==========================================
        print("\n[CategoryRepository]")
        
        categories = await cat_repo.get_all_categories(test_user_id, config.language)
        print(f"  Categories for user {test_user_id}: {len(categories)}")
        if categories:
            print(f"  Sample categories: {categories[:5]}")
            
            # Get subcategories for first category
            subcats = await cat_repo.get_subcategories(test_user_id, categories[0], config.language)
            print(f"  Subcategories for '{categories[0]}': {subcats[:5]}")
        
        # Get full dictionary
        dictionary = await cat_repo.get_dictionary(test_user_id, config.language)
        total_subcats = sum(len(v) for v in dictionary.values())
        print(f"  Dictionary: {len(dictionary)} categories, {total_subcats} subcategories")
        
        print("  [OK] CategoryRepository tests passed")
        
        # ==========================================
        # Test TransactionRepository
        # ==========================================
        print("\n[TransactionRepository]")
        
        tx_count = await tx_repo.count_for_user(test_user_id)
        print(f"  Total transactions for user {test_user_id}: {tx_count}")
        
        # Get latest transactions
        latest = await tx_repo.get_latest(test_user_id, limit=3)
        print(f"  Latest {len(latest)} transactions:")
        for tx in latest:
            print(f"    - {tx.timestamp.date()}: {tx.category_name}/{tx.subcategory_name} = {tx.amount} {tx.currency}")
        
        # Get current month summary
        now = datetime.now(timezone.utc)
        summary = await tx_repo.get_monthly_summary(test_user_id, now.year, now.month)
        print(f"  Current month ({now.year}-{now.month}) summary:")
        for cat, total in list(summary.items())[:5]:
            print(f"    - {cat}: {total}")
        
        # Get monthly total
        total = await tx_repo.get_monthly_total(test_user_id, now.year, now.month)
        print(f"  Current month total: {total}")
        
        # Test limit calculation
        limit_info = await tx_repo.calculate_limit_usage(test_user_id, config.monthly_limit)
        print(f"  Limit usage: {limit_info['total_spent']}/{limit_info['limit']} ({limit_info['percentage_used']:.1f}%)")
        
        # Get frequent categories
        frequent = await tx_repo.get_frequent_categories(test_user_id, limit=5)
        print(f"  Most used categories: {frequent}")
        
        print("  [OK] TransactionRepository tests passed")
        
        # ==========================================
        # Summary
        # ==========================================
        print("\n" + "=" * 50)
        print("All repository tests passed!")
        print("Repositories are ready to replace file_ops.py and pandas_ops.py")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await close_database()
    
    return True


if __name__ == '__main__':
    success = asyncio.run(test_repositories())
    sys.exit(0 if success else 1)
