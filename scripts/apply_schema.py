#!/usr/bin/env python3
"""
Apply database schema manually.
Use this when the docker-entrypoint-initdb.d didn't run (existing volume).

Usage:
    python scripts/apply_schema.py
"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

from infrastructure.database.connection import get_database

SCHEMA_FILE = PROJECT_ROOT / "infrastructure/database/migrations/001_initial_schema.sql"


async def apply_schema():
    """Apply the schema SQL file to the database."""
    print("Applying database schema...")
    print(f"Schema file: {SCHEMA_FILE}")
    
    if not SCHEMA_FILE.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)
    
    schema_sql = SCHEMA_FILE.read_text()
    
    db = get_database()
    
    try:
        pool = await db.connect()
        
        async with pool.acquire() as conn:
            # Execute the schema SQL
            await conn.execute(schema_sql)
            print("[OK] Schema applied successfully")
            
            # Verify tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            print(f"\nTables now available ({len(tables)}):")
            for row in tables:
                print(f"  - {row['table_name']}")
                
    except asyncpg.PostgresError as e:
        print(f"[ERROR] PostgreSQL error: {e}")
        sys.exit(1)
    finally:
        await db.disconnect()
    
    print("\n[OK] Schema ready for migration!")


if __name__ == '__main__':
    asyncio.run(apply_schema())
