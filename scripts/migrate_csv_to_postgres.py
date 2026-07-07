#!/usr/bin/env python3
"""
CSV to PostgreSQL Migration Script for BudgetBot.

This script migrates all user data from CSV files to PostgreSQL.
Run with --dry-run first to validate without making changes.

Usage:
    python scripts/migrate_csv_to_postgres.py --dry-run
    python scripts/migrate_csv_to_postgres.py
    python scripts/migrate_csv_to_postgres.py --resume  # Resume interrupted migration
"""
import os
import sys
import json
import shutil
import argparse
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from configparser import ConfigParser
from typing import Optional, Dict, Any, List

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

from infrastructure.database.connection import get_database


# Configuration
USER_DATA_DIR = PROJECT_ROOT / "user_data"
BACKUP_DIR = USER_DATA_DIR / ".bak"
CONFIGS_DIR = PROJECT_ROOT / "configs"


class MigrationStats:
    """Track migration statistics."""
    def __init__(self):
        self.users_migrated = 0
        self.users_failed = 0
        self.transactions_migrated = 0
        self.categories_migrated = 0
        self.configs_migrated = 0
        self.errors: List[str] = []
    
    def summary(self) -> str:
        return f"""
Migration Summary:
==================
Users migrated:        {self.users_migrated}
Users failed:          {self.users_failed}
Transactions migrated: {self.transactions_migrated}
Categories migrated:   {self.categories_migrated}
Configs migrated:      {self.configs_migrated}
Errors:                {len(self.errors)}
"""


def get_user_dirs() -> List[Path]:
    """Get all user data directories."""
    if not USER_DATA_DIR.exists():
        return []
    
    user_dirs = []
    for item in USER_DATA_DIR.iterdir():
        if item.is_dir() and item.name.isdigit():
            user_dirs.append(item)
    
    return sorted(user_dirs, key=lambda p: int(p.name))


def parse_config_ini(config_path: Path) -> Dict[str, Any]:
    """Parse user config.ini file."""
    config = ConfigParser()
    config.read(config_path)
    
    result = {
        'language': 'en',
        'currency': 'EUR',
        'monthly_limit': 99999999.00,
        'name': None,
    }
    
    if config.has_section('settings'):
        result['language'] = config.get('settings', 'language', fallback='en')
        result['currency'] = config.get('settings', 'currency', fallback='EUR')
        limit_str = config.get('settings', 'limit', fallback='99999999')
        try:
            result['monthly_limit'] = float(limit_str)
        except ValueError:
            pass
        result['name'] = config.get('settings', 'name', fallback=None)
    
    return result


def parse_dictionary_json(dict_path: Path) -> List[Dict[str, str]]:
    """Parse user dictionary JSON file."""
    if not dict_path.exists():
        return []
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  WARNING: Could not parse dictionary: {e}")
        return []
    
    categories = []
    
    # Handle both formats: {"lang": {"cat": ["subcat"]}} or {"cat": ["subcat"]}
    for lang_or_cat, value in data.items():
        if isinstance(value, dict):
            # Format: {"en": {"Food": ["Groceries", "Restaurant"]}}
            language = lang_or_cat
            for category_name, subcategories in value.items():
                if isinstance(subcategories, list):
                    for subcategory in subcategories:
                        categories.append({
                            'language': language,
                            'category_name': category_name,
                            'subcategory_name': subcategory,
                        })
        elif isinstance(value, list):
            # Format: {"Food": ["Groceries", "Restaurant"]} - assume 'en'
            category_name = lang_or_cat
            for subcategory in value:
                categories.append({
                    'language': 'en',
                    'category_name': category_name,
                    'subcategory_name': subcategory,
                })
    
    return categories


def parse_spendings_csv(csv_path: Path) -> pd.DataFrame:
    """Parse user spendings CSV file."""
    if not csv_path.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  WARNING: Could not parse CSV: {e}")
        return pd.DataFrame()
    
    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()
    
    # Ensure required columns exist
    required = ['timestamp', 'category', 'subcategory', 'amount', 'currency']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"  WARNING: Missing columns: {missing}")
        return pd.DataFrame()
    
    return df


def safe_parse_timestamp(value) -> Optional[datetime]:
    """
    Safely parse various timestamp formats to timezone-aware datetime.
    Handles: pandas Timestamp, strings, datetime objects, etc.
    """
    if pd.isna(value) or value is None:
        return None
    
    try:
        # Convert to pandas Timestamp first (handles many formats)
        ts = pd.to_datetime(value)
        
        # Convert to Python datetime
        if hasattr(ts, 'to_pydatetime'):
            dt = ts.to_pydatetime()
        else:
            dt = ts
        
        # Make timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except Exception:
        # Last resort: try parsing common formats manually
        if isinstance(value, str):
            for fmt in [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%d.%m.%Y %H:%M:%S',
                '%d.%m.%Y %H:%M',
                '%d.%m.%Y',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y',
            ]:
                try:
                    dt = datetime.strptime(value.strip(), fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        
        return None


def detect_transaction_type(row: pd.Series) -> str:
    """Detect if a transaction is income or spending."""
    # Heuristics for detecting income:
    # 1. Category contains "income" (case-insensitive)
    # 2. Amount is negative (some systems use negative for income)
    category = str(row.get('category', '')).lower()
    
    if 'income' in category or 'salary' in category or 'доход' in category:
        return 'income'
    
    return 'spending'


def calculate_checksum(user_dir: Path) -> str:
    """Calculate checksum for user data files."""
    hasher = hashlib.md5()
    
    files_to_hash = [
        user_dir / 'config.ini',
        user_dir / f'dictionary_{user_dir.name}.json',
        user_dir / f'spendings_{user_dir.name}.csv',
    ]
    
    for file_path in files_to_hash:
        if file_path.exists():
            hasher.update(file_path.read_bytes())
    
    return hasher.hexdigest()


async def migrate_user(
    conn: asyncpg.Connection,
    user_id: int,
    user_dir: Path,
    stats: MigrationStats,
    dry_run: bool = False
) -> bool:
    """Migrate a single user's data to PostgreSQL."""
    print(f"\n  Migrating user {user_id}...")
    
    try:
        # 1. Insert user record
        if not dry_run:
            await conn.execute("""
                INSERT INTO users (user_id, created_at)
                VALUES ($1, NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, user_id)
        print(f"    [{'DRY' if dry_run else 'OK'}] User record")
        
        # 2. Migrate config
        config_path = user_dir / 'config.ini'
        if config_path.exists():
            config = parse_config_ini(config_path)
            if not dry_run:
                await conn.execute("""
                    INSERT INTO user_configs (user_id, language, currency, monthly_limit, name)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO UPDATE SET
                        language = EXCLUDED.language,
                        currency = EXCLUDED.currency,
                        monthly_limit = EXCLUDED.monthly_limit,
                        name = EXCLUDED.name
                """, user_id, config['language'], config['currency'], 
                    config['monthly_limit'], config['name'])
            stats.configs_migrated += 1
            print(f"    [{'DRY' if dry_run else 'OK'}] Config: {config['language']}/{config['currency']}")
        
        # 3. Migrate dictionary/categories
        dict_path = user_dir / f'dictionary_{user_id}.json'
        categories = parse_dictionary_json(dict_path)
        if categories and not dry_run:
            await conn.executemany("""
                INSERT INTO user_categories (user_id, language, category_name, subcategory_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, language, category_name, subcategory_name) DO NOTHING
            """, [(user_id, c['language'], c['category_name'], c['subcategory_name']) 
                  for c in categories])
        stats.categories_migrated += len(categories)
        print(f"    [{'DRY' if dry_run else 'OK'}] Categories: {len(categories)}")
        
        # 4. Migrate transactions
        csv_path = user_dir / f'spendings_{user_id}.csv'
        df = parse_spendings_csv(csv_path)
        if not df.empty:
            # Add transaction_type column
            df['transaction_type'] = df.apply(detect_transaction_type, axis=1)
            
            # Convert to records
            transactions = []
            skipped = 0
            for idx, row in df.iterrows():
                try:
                    # Parse timestamp with timezone handling
                    timestamp = safe_parse_timestamp(row['timestamp'])
                    if timestamp is None:
                        print(f"    WARNING: Invalid timestamp at row {idx}: {row['timestamp']}")
                        skipped += 1
                        continue
                    
                    # Validate amount
                    try:
                        amount = float(row['amount'])
                    except (ValueError, TypeError):
                        print(f"    WARNING: Invalid amount at row {idx}: {row['amount']}")
                        skipped += 1
                        continue
                    
                    transactions.append((
                        user_id,
                        timestamp,
                        row['transaction_type'],
                        str(row['category'] or 'Unknown'),
                        str(row['subcategory'] or 'Unknown'),
                        amount,
                        str(row['currency'] or 'EUR')[:3].upper(),
                    ))
                except Exception as e:
                    print(f"    WARNING: Skipping row {idx}: {e}")
                    skipped += 1
            
            if skipped > 0:
                print(f"    [WARN] Skipped {skipped} invalid rows")
            
            if transactions and not dry_run:
                await conn.executemany("""
                    INSERT INTO transactions 
                    (user_id, timestamp, transaction_type, category_name, subcategory_name, amount, currency)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, transactions)
            
            stats.transactions_migrated += len(transactions)
            income_count = sum(1 for t in transactions if t[2] == 'income')
            print(f"    [{'DRY' if dry_run else 'OK'}] Transactions: {len(transactions)} ({income_count} income)")
        
        # 5. Log migration success
        if not dry_run:
            await conn.execute("""
                INSERT INTO migration_log (user_id, migration_type, source_file, records_count, status, completed_at)
                VALUES ($1, 'full', $2, $3, 'success', NOW())
            """, user_id, str(user_dir), stats.transactions_migrated)
        
        stats.users_migrated += 1
        return True
        
    except Exception as e:
        stats.users_failed += 1
        stats.errors.append(f"User {user_id}: {str(e)}")
        print(f"    ERROR: {e}")
        
        if not dry_run:
            await conn.execute("""
                INSERT INTO migration_log (user_id, migration_type, source_file, status, error_message, completed_at)
                VALUES ($1, 'full', $2, 'failed', $3, NOW())
            """, user_id, str(user_dir), str(e))
        
        return False


async def backup_user_data(user_dir: Path, dry_run: bool = False) -> bool:
    """Move user data to backup directory after successful migration."""
    if dry_run:
        print(f"    [DRY] Would backup to: {BACKUP_DIR / user_dir.name}")
        return True
    
    try:
        backup_path = BACKUP_DIR / user_dir.name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy files (not move, for safety)
        for item in user_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, backup_path / item.name)
        
        print(f"    [OK] Backed up to: {backup_path}")
        return True
    except Exception as e:
        print(f"    WARNING: Backup failed: {e}")
        return False


async def migrate_exchange_rates(conn: asyncpg.Connection, dry_run: bool = False) -> int:
    """Migrate exchange rates from JSON file."""
    rates_file = CONFIGS_DIR / 'exchangerates.json'
    if not rates_file.exists():
        return 0
    
    try:
        with open(rates_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"WARNING: Could not load exchange rates: {e}")
        return 0
    
    # Handle format: {"base": "EUR", "rates": {"USD": 1.1, ...}}
    base = data.get('base', 'EUR')
    rates = data.get('rates', {})
    
    if not dry_run:
        for target, rate in rates.items():
            await conn.execute("""
                INSERT INTO exchange_rates (base_currency, target_currency, rate, last_updated)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (base_currency, target_currency) DO UPDATE SET
                    rate = EXCLUDED.rate,
                    last_updated = NOW()
            """, base, target, float(rate))
    
    return len(rates)


async def run_migration(dry_run: bool = False, resume: bool = False):
    """Run the full migration."""
    print(f"\n{'='*60}")
    print(f"BudgetBot CSV → PostgreSQL Migration")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE'}")
    print(f"User data dir: {USER_DATA_DIR}")
    print(f"Backup dir: {BACKUP_DIR}")
    
    # Get user directories
    user_dirs = get_user_dirs()
    print(f"\nFound {len(user_dirs)} user directories")
    
    if not user_dirs:
        print("No users to migrate.")
        return
    
    # Connect to database
    db = get_database()
    stats = MigrationStats()
    
    try:
        pool = await db.connect()
        
        async with pool.acquire() as conn:
            # Check for previously migrated users if resuming
            migrated_users = set()
            if resume:
                rows = await conn.fetch("""
                    SELECT DISTINCT user_id FROM migration_log 
                    WHERE status = 'success'
                """)
                migrated_users = {row['user_id'] for row in rows}
                print(f"Resuming: skipping {len(migrated_users)} already migrated users")
            
            # Migrate exchange rates first
            print("\nMigrating exchange rates...")
            rates_count = await migrate_exchange_rates(conn, dry_run)
            print(f"  [{'DRY' if dry_run else 'OK'}] Exchange rates: {rates_count}")
            
            # Migrate each user
            print("\nMigrating users...")
            for user_dir in user_dirs:
                user_id = int(user_dir.name)
                
                if user_id in migrated_users:
                    print(f"\n  Skipping user {user_id} (already migrated)")
                    continue
                
                # Each user in its own transaction
                async with conn.transaction():
                    success = await migrate_user(conn, user_id, user_dir, stats, dry_run)
                    
                    if success and not dry_run:
                        await backup_user_data(user_dir, dry_run)
        
        # Print summary
        print(stats.summary())
        
        if stats.errors:
            print("Errors:")
            for error in stats.errors[:10]:
                print(f"  - {error}")
            if len(stats.errors) > 10:
                print(f"  ... and {len(stats.errors) - 10} more")
        
        if dry_run:
            print("\nThis was a DRY RUN. No changes were made.")
            print("Run without --dry-run to perform the actual migration.")
        else:
            print("\nMigration complete!")
            print(f"Backups saved to: {BACKUP_DIR}")
            
    finally:
        await db.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Migrate BudgetBot CSV data to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Validate without making changes')
    parser.add_argument('--resume', action='store_true',
                        help='Resume interrupted migration (skip already migrated users)')
    
    args = parser.parse_args()
    
    asyncio.run(run_migration(dry_run=args.dry_run, resume=args.resume))


if __name__ == '__main__':
    main()
