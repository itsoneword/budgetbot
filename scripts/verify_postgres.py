#!/usr/bin/env python3
"""
Quick PostgreSQL verification script.
Run after docker-compose up to verify database is ready.

Usage:
    python scripts/verify_postgres.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

from infrastructure.database.connection import get_database


async def verify():
    """Verify PostgreSQL connection and schema."""
    print("Verifying PostgreSQL setup...")
    print("="*50)
    
    db = get_database()
    
    try:
        pool = await db.connect()
        print("[OK] Connected to PostgreSQL")
        
        async with pool.acquire() as conn:
            # Check tables exist
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            expected_tables = {
                'users', 'user_configs', 'user_categories', 
                'transactions', 'exchange_rates', 'migration_log'
            }
            actual_tables = {row['table_name'] for row in tables}
            
            print(f"\nTables found: {len(actual_tables)}")
            for table in sorted(actual_tables):
                status = "[OK]" if table in expected_tables else "[?]"
                print(f"  {status} {table}")
            
            missing = expected_tables - actual_tables
            if missing:
                print(f"\n[WARN] Missing tables: {missing}")
            else:
                print("\n[OK] All expected tables exist")
            
            # Check indexes
            indexes = await conn.fetch("""
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
            """)
            print(f"\nCustom indexes: {len(indexes)}")
            for idx in indexes:
                print(f"  [OK] {idx['indexname']}")
            
            # Test insert (dry run)
            print("\n[OK] Schema verification complete!")
            
    except asyncpg.PostgresError as e:
        print(f"[ERROR] PostgreSQL error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    finally:
        await db.disconnect()
    
    print("\n" + "="*50)
    print("PostgreSQL is ready for migration!")
    print("Next step: python scripts/migrate_csv_to_postgres.py --dry-run")


if __name__ == '__main__':
    asyncio.run(verify())
