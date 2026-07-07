"""
Currency exchange rate service using PostgreSQL storage.
Replaces pandas_ops.get_exchange_rate() and recalculate_currency().
"""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional
import pandas as pd

from src.logger import log_debug

# Path to fallback config (relative to project root)
CURRENCY_DEFAULTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'configs', 'currency_defaults.json'
)


class CurrencyService:
    """Service for currency conversion using PostgreSQL-backed exchange rates."""

    # Supported currency pairs (base is always USD)
    SUPPORTED_CURRENCIES = ['EUR', 'RUB', 'AMD', 'USD', 'THB']
    CACHE_TTL_HOURS = 12

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._cache: Dict[str, Decimal] = {}
        self._cache_time: Optional[datetime] = None

    async def get_rates(self) -> Dict[str, Decimal]:
        """
        Get exchange rates, fetching from API if cache is stale.
        Returns dict like {'USDEUR': 0.92, 'USDRUB': 90.0, ...}
        """
        # Check memory cache first
        if self._is_cache_valid():
            return self._cache

        # Try to load from DB
        rates = await self._load_from_db()

        # Check if DB rates are fresh enough
        if rates and self._is_db_cache_valid(rates.get('_last_updated')):
            self._update_memory_cache(rates)
            return self._cache

        # Fetch fresh rates from API
        fresh_rates = await self._fetch_from_api()
        if fresh_rates:
            await self._save_to_db(fresh_rates)
            self._update_memory_cache(fresh_rates)
            return self._cache

        # Fallback to whatever we have
        if rates:
            self._update_memory_cache(rates)
            return self._cache

        # Ultimate fallback - hardcoded defaults
        return self._get_default_rates()

    def _is_cache_valid(self) -> bool:
        """Check if memory cache is still valid."""
        if not self._cache or not self._cache_time:
            return False
        age = datetime.now(timezone.utc) - self._cache_time
        return age < timedelta(hours=self.CACHE_TTL_HOURS)

    def _is_db_cache_valid(self, last_updated: Optional[datetime]) -> bool:
        """Check if DB cache is fresh enough."""
        if not last_updated:
            return False
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_updated
        return age < timedelta(hours=self.CACHE_TTL_HOURS)

    async def _load_from_db(self) -> Optional[Dict[str, Decimal]]:
        """Load exchange rates from PostgreSQL."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT base_currency, target_currency, rate, last_updated
                    FROM exchange_rates
                    WHERE base_currency = 'USD'
                """)

                if not rows:
                    return None

                rates = {}
                min_updated = None
                for row in rows:
                    key = f"USD{row['target_currency']}"
                    rates[key] = Decimal(str(row['rate']))
                    if min_updated is None or row['last_updated'] < min_updated:
                        min_updated = row['last_updated']

                rates['_last_updated'] = min_updated
                log_debug(f"Loaded {len(rows)} exchange rates from DB")
                return rates
        except Exception as e:
            log_debug(f"Error loading exchange rates from DB: {e}")
            return None

    async def _save_to_db(self, rates: Dict[str, Decimal]) -> None:
        """Save exchange rates to PostgreSQL."""
        try:
            async with self.db_pool.acquire() as conn:
                now = datetime.now(timezone.utc)
                for key, rate in rates.items():
                    if key.startswith('USD') and key != '_last_updated':
                        target = key[3:]  # e.g., 'EUR' from 'USDEUR'
                        await conn.execute("""
                            INSERT INTO exchange_rates (base_currency, target_currency, rate, last_updated)
                            VALUES ('USD', $1, $2, $3)
                            ON CONFLICT (base_currency, target_currency)
                            DO UPDATE SET rate = $2, last_updated = $3
                        """, target, float(rate), now)
                log_debug(f"Saved exchange rates to DB")
        except Exception as e:
            log_debug(f"Error saving exchange rates to DB: {e}")

    def _get_supported_currencies(self) -> list:
        """Get list of supported currencies from config."""
        try:
            with open(CURRENCY_DEFAULTS_PATH, 'r') as f:
                config = json.load(f)
                return config.get('supported_currencies', ['EUR', 'RUB', 'AMD', 'USD', 'THB'])
        except (FileNotFoundError, json.JSONDecodeError):
            return ['EUR', 'RUB', 'AMD', 'USD', 'THB']

    def _build_rates_from_api(self, api_rates: dict) -> Dict[str, Decimal]:
        """Build rates dict from API response, using config defaults as fallback."""
        defaults = self._get_default_rates()
        currencies = self._get_supported_currencies()

        rates = {}
        for currency in currencies:
            key = f'USD{currency}'
            if currency == 'USD':
                rates[key] = Decimal('1.0')
            elif currency in api_rates:
                rates[key] = Decimal(str(api_rates[currency]))
            else:
                # Use config default if API doesn't have this currency
                rates[key] = defaults.get(key, Decimal('1.0'))
        return rates

    async def _fetch_from_api(self) -> Optional[Dict[str, Decimal]]:
        """Fetch fresh exchange rates from API."""
        try:
            import aiohttp
            api_url = "https://open.er-api.com/v6/latest/USD"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as response:
                    if response.status != 200:
                        log_debug(f"API returned status {response.status}")
                        return None

                    data = await response.json()
                    if data.get("result") != "success":
                        log_debug(f"API returned error: {data}")
                        return None

                    api_rates = data.get("rates", {})
                    rates = self._build_rates_from_api(api_rates)
                    log_debug(f"Fetched fresh exchange rates from API: {rates}")
                    return rates
        except ImportError:
            # aiohttp not installed, try sync requests
            return await asyncio.to_thread(self._fetch_from_api_sync)
        except Exception as e:
            log_debug(f"Error fetching exchange rates from API: {e}")
            return None

    def _fetch_from_api_sync(self) -> Optional[Dict[str, Decimal]]:
        """Synchronous fallback for API fetch."""
        try:
            import requests
            api_url = "https://open.er-api.com/v6/latest/USD"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("result") != "success":
                return None

            api_rates = data.get("rates", {})
            return self._build_rates_from_api(api_rates)
        except Exception as e:
            log_debug(f"Error in sync API fetch: {e}")
            return None

    def _update_memory_cache(self, rates: Dict[str, Decimal]) -> None:
        """Update the in-memory cache."""
        self._cache = {k: v for k, v in rates.items() if not k.startswith('_')}
        self._cache_time = datetime.now(timezone.utc)

    def _get_default_rates(self) -> Dict[str, Decimal]:
        """Load fallback rates from config file (configs/currency_defaults.json)."""
        try:
            with open(CURRENCY_DEFAULTS_PATH, 'r') as f:
                config = json.load(f)
                rates = config.get('rates', {})
                return {k: Decimal(str(v)) for k, v in rates.items()}
        except FileNotFoundError:
            log_debug(f"WARNING: Currency config not found at {CURRENCY_DEFAULTS_PATH}")
            raise RuntimeError(
                f"Currency config file missing: {CURRENCY_DEFAULTS_PATH}. "
                "Please ensure configs/currency_defaults.json exists."
            )
        except json.JSONDecodeError as e:
            log_debug(f"ERROR: Invalid JSON in currency config: {e}")
            raise RuntimeError(f"Invalid JSON in {CURRENCY_DEFAULTS_PATH}: {e}")

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        rates: Dict[str, Decimal]
    ) -> Decimal:
        """
        Convert amount from one currency to another.

        Args:
            amount: The amount to convert
            from_currency: Source currency code (e.g., 'EUR')
            to_currency: Target currency code (e.g., 'USD')
            rates: Exchange rates dict from get_rates()

        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount

        # Convert via USD as intermediate
        if from_currency == 'USD':
            # Direct conversion USD -> target
            rate = rates.get(f'USD{to_currency}', Decimal('1.0'))
            return amount * rate
        elif to_currency == 'USD':
            # Inverse conversion source -> USD
            rate = rates.get(f'USD{from_currency}', Decimal('1.0'))
            return amount / rate if rate else amount
        else:
            # Cross conversion: source -> USD -> target
            rate_from = rates.get(f'USD{from_currency}', Decimal('1.0'))
            rate_to = rates.get(f'USD{to_currency}', Decimal('1.0'))
            if rate_from:
                usd_amount = amount / rate_from
                return usd_amount * rate_to
            return amount

    def convert_dataframe(
        self,
        df: pd.DataFrame,
        to_currency: str,
        rates: Dict[str, Decimal],
        amount_col: str = 'amount',
        currency_col: str = 'currency',
        result_col: str = 'amount_cr_currency'
    ) -> pd.DataFrame:
        """
        Convert amounts in a DataFrame to target currency.

        Args:
            df: DataFrame with amount and currency columns
            to_currency: Target currency code
            rates: Exchange rates dict from get_rates()
            amount_col: Name of amount column
            currency_col: Name of currency column
            result_col: Name of result column to create

        Returns:
            DataFrame with new column containing converted amounts
        """
        if df.empty:
            df[result_col] = pd.Series(dtype=float)
            return df

        def convert_row(row):
            amount = Decimal(str(row[amount_col]))
            from_curr = row[currency_col]
            return float(self.convert(amount, from_curr, to_currency, rates))

        df = df.copy()
        df[result_col] = df.apply(convert_row, axis=1)
        return df


# Singleton instance for backward compatibility
_currency_service: Optional[CurrencyService] = None


def get_currency_service(db_pool=None) -> CurrencyService:
    """Get or create the currency service singleton."""
    global _currency_service
    if _currency_service is None and db_pool is not None:
        _currency_service = CurrencyService(db_pool)
    return _currency_service


def init_currency_service(db_pool) -> CurrencyService:
    """Initialize the currency service with a database pool."""
    global _currency_service
    _currency_service = CurrencyService(db_pool)
    return _currency_service
