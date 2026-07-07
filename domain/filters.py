"""
Pure Python filter and aggregation functions for transactions.

These functions operate on in-memory data (List[Transaction]) instead of SQL.
Benefits: testable, no DB round-trips, simple logic.

Usage:
    from domain.filters import filter_by_period, calculate_summary

    filtered = filter_by_period(session.transactions, '3m')
    summary = calculate_summary(filtered, session.currency)
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import calendar

from domain.models.user_session import Transaction


# ==========================================
# FILTERING
# ==========================================

def filter_by_period(
    transactions: List[Transaction],
    period: str,
    reference_date: Optional[datetime] = None,
) -> List[Transaction]:
    """
    Filter transactions by time period.

    Args:
        transactions: List of Transaction objects
        period: '3m', '6m', '12m', 'ytd', 'current_month', 'last_month'
        reference_date: Reference point for calculation (default: now)

    Returns:
        Filtered list of transactions
    """
    now = reference_date or datetime.now(timezone.utc)

    if period == "3m":
        start_date = now - timedelta(days=90)
    elif period == "6m":
        start_date = now - timedelta(days=180)
    elif period == "12m":
        start_date = now - timedelta(days=365)
    elif period == "ytd":
        start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    elif period == "current_month":
        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    elif period == "last_month":
        if now.month == 1:
            start_date = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
            end_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        else:
            start_date = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
            end_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        return [tx for tx in transactions if start_date <= tx.timestamp < end_date]
    else:
        # Default to last 30 days
        start_date = now - timedelta(days=30)

    return [tx for tx in transactions if tx.timestamp >= start_date]


def filter_by_categories(
    transactions: List[Transaction],
    categories: List[str],
) -> List[Transaction]:
    """Filter transactions to only include specified categories."""
    if not categories:
        return transactions
    category_set = set(categories)
    return [tx for tx in transactions if tx.category in category_set]


def filter_by_type(
    transactions: List[Transaction],
    transaction_type: str = 'spending',
) -> List[Transaction]:
    """Filter by transaction type ('spending' or 'income')."""
    return [tx for tx in transactions if tx.transaction_type == transaction_type]


def filter_current_month(
    transactions: List[Transaction],
    reference_date: Optional[datetime] = None,
) -> List[Transaction]:
    """Get transactions for current month only."""
    now = reference_date or datetime.now(timezone.utc)
    return [
        tx for tx in transactions
        if tx.timestamp.year == now.year and tx.timestamp.month == now.month
    ]


def sort_by_date(
    transactions: List[Transaction],
    descending: bool = True,
) -> List[Transaction]:
    """Sort transactions by timestamp."""
    return sorted(transactions, key=lambda tx: tx.timestamp, reverse=descending)


# ==========================================
# AGGREGATIONS
# ==========================================

def get_unique_categories(transactions: List[Transaction]) -> List[str]:
    """Get sorted list of unique categories from transactions."""
    return sorted(set(tx.category for tx in transactions))


def get_total(transactions: List[Transaction]) -> Decimal:
    """Calculate total amount of all transactions."""
    return sum((tx.amount for tx in transactions), Decimal('0'))


def get_sum_per_category(transactions: List[Transaction]) -> Dict[str, Decimal]:
    """
    Calculate sum per category, sorted by total descending.
    Returns: {category: total_amount}
    """
    totals: Dict[str, Decimal] = {}
    for tx in transactions:
        totals[tx.category] = totals.get(tx.category, Decimal('0')) + tx.amount

    # Sort by total descending
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def get_sum_per_subcategory(
    transactions: List[Transaction],
    category: Optional[str] = None,
    limit: int = 6,
) -> Dict[str, Decimal]:
    """
    Calculate sum per subcategory, optionally filtered by category.
    Returns top N subcategories by total.
    """
    if category:
        transactions = [tx for tx in transactions if tx.category == category]

    totals: Dict[str, Decimal] = {}
    for tx in transactions:
        totals[tx.subcategory] = totals.get(tx.subcategory, Decimal('0')) + tx.amount

    # Sort by total descending and limit
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_items[:limit])


def calculate_summary(
    transactions: List[Transaction],
    categories: Optional[List[str]] = None,
    currency: str = 'EUR',
) -> Dict[str, Any]:
    """
    Calculate full summary for detailed transactions view.

    Returns:
        {
            'total': Decimal,
            'currency': str,
            'category_sums': {category: total},
            'subcategory_data': {category: {subcategory: total}},
            'transaction_count': int,
        }
    """
    # Filter by categories if specified
    if categories:
        transactions = filter_by_categories(transactions, categories)

    total = get_total(transactions)
    category_sums = get_sum_per_category(transactions)

    # Get subcategory breakdown for each category
    cats_to_process = categories if categories else list(category_sums.keys())
    subcategory_data = {}
    for cat in cats_to_process:
        subcategory_data[cat] = get_sum_per_subcategory(transactions, category=cat, limit=6)

    return {
        'total': total,
        'currency': currency,
        'category_sums': category_sums,
        'subcategory_data': subcategory_data,
        'transaction_count': len(transactions),
    }


def calculate_daily_average(
    transactions: List[Transaction],
    reference_date: Optional[datetime] = None,
) -> Decimal:
    """
    Calculate daily average for current month.
    Divides total by current day of month.
    """
    now = reference_date or datetime.now(timezone.utc)
    current_day = now.day

    if current_day == 0:
        return Decimal('0')

    # Filter to current month
    month_tx = filter_current_month(transactions, now)
    total = get_total(month_tx)

    return round(total / current_day, 2)


def calculate_daily_average_per_category(
    transactions: List[Transaction],
    categories: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None,
) -> Dict[str, Decimal]:
    """
    Calculate daily average per category for current month.
    """
    now = reference_date or datetime.now(timezone.utc)
    current_day = now.day

    if current_day == 0:
        return {}

    # Filter to current month
    month_tx = filter_current_month(transactions, now)

    # Filter by categories if specified
    if categories:
        month_tx = filter_by_categories(month_tx, categories)

    # Get sum per category and divide by days
    category_sums = get_sum_per_category(month_tx)

    return {
        cat: round(total / current_day, 1)
        for cat, total in category_sums.items()
    }


def calculate_limit_usage(
    transactions: List[Transaction],
    monthly_limit: Decimal,
    reference_date: Optional[datetime] = None,
    exclude_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate detailed limit usage for the current month.

    Args:
        transactions: All user transactions (will filter to current month)
        monthly_limit: User's monthly spending limit
        exclude_categories: Categories to exclude (e.g., ['rent', 'investing'])

    Returns:
        {
            'current_daily_average': Decimal,
            'percent_difference': Decimal,
            'daily_limit': Decimal,
            'days_zero_spending': Decimal,
            'new_daily_limit': Decimal,
            'exceeded': bool,
            'total_spent': Decimal,
            'remaining': Decimal,
        }
    """
    now = reference_date or datetime.now(timezone.utc)
    current_day = now.day
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    # Filter to current month spending
    month_tx = filter_current_month(transactions, now)
    month_tx = filter_by_type(month_tx, 'spending')

    # Calculate totals
    category_sums = get_sum_per_category(month_tx)
    total = sum(category_sums.values(), Decimal('0'))

    # Calculate excluded amount
    exclude_cats = exclude_categories or ['rent', 'investing']
    excluded_amount = sum(
        category_sums.get(cat, Decimal('0'))
        for cat in exclude_cats
    )

    # Daily limit (excluding rent/investing from budget)
    daily_limit = (monthly_limit - excluded_amount) / days_in_month if days_in_month > 0 else Decimal('0')

    # Current daily average (excluding rent/investing)
    spending_for_avg = total - excluded_amount
    current_daily_average = spending_for_avg / current_day if current_day > 0 else Decimal('0')

    # Percent difference from daily limit
    percent_difference = (
        ((current_daily_average - daily_limit) / daily_limit * 100)
        if daily_limit > 0 else Decimal('0')
    )

    # Days of zero spending needed to recover
    days_zero_spending = Decimal('0')
    if daily_limit > 0 and current_daily_average > daily_limit:
        days_zero_spending = (current_daily_average - daily_limit) / (
            daily_limit / (current_day + 1)
        ) if current_day > 0 else Decimal('0')

    # New daily limit for remaining days
    remaining_days = days_in_month - current_day
    new_daily_limit = (
        (monthly_limit - total) / remaining_days
        if remaining_days > 0 else Decimal('0')
    )
    if new_daily_limit < 0:
        new_daily_limit = Decimal('0')

    return {
        'current_daily_average': round(current_daily_average, 2),
        'percent_difference': round(percent_difference, 2),
        'daily_limit': round(daily_limit, 2),
        'days_zero_spending': round(days_zero_spending, 2),
        'new_daily_limit': round(new_daily_limit, 2),
        'exceeded': current_daily_average > daily_limit,
        'total_spent': total,
        'remaining': monthly_limit - total,
    }


def calculate_prediction(
    transactions: List[Transaction],
    reference_date: Optional[datetime] = None,
) -> Decimal:
    """
    Predict end-of-month total based on current spending rate.
    """
    now = reference_date or datetime.now(timezone.utc)
    current_day = now.day
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    month_tx = filter_current_month(transactions, now)
    total = get_total(month_tx)

    if current_day == 0:
        return total

    daily_avg = total / current_day
    remaining_days = days_in_month - current_day

    return round(total + (daily_avg * remaining_days), 2)



def get_period_summary(
    transactions: List[Transaction],
    period: str = 'current_month',
    transaction_type: str = 'spending',
    reference_date: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Unified summary for any period.
    
    Args:
        transactions: List of Transaction objects
        period: 'current_month' or 'last_month'
        transaction_type: 'spending' or 'income'
        reference_date: Reference point for calculation (default: now)
    
    Returns None if no transactions found.
    Returns:
        {
            'sum_per_cat': {category: total},
            'av_per_day': {category: daily_avg},
            'total': Decimal,
            'total_av_per_day': Decimal,
            'prediction': Decimal,
            'comparison': Decimal,
        }
    """
    now = reference_date or datetime.now(timezone.utc)
    
    # Calculate period boundaries
    if period == 'current_month':
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        period_end = now
        days_elapsed = now.day
        days_in_period = calendar.monthrange(now.year, now.month)[1]
        is_complete = False
        
        # For comparison: need yesterday's data
        if now.month == 1:
            prev_period_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
        else:
            prev_period_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        prev_period_end = period_start
        
    elif period == 'last_month':
        if now.month == 1:
            period_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
            period_end = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            prev_period_start = datetime(now.year - 1, 11, 1, tzinfo=timezone.utc)
        else:
            period_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
            period_end = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            if now.month == 2:
                prev_period_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
            else:
                prev_period_start = datetime(now.year, now.month - 2, 1, tzinfo=timezone.utc)
        
        days_in_period = calendar.monthrange(period_start.year, period_start.month)[1]
        days_elapsed = days_in_period  # Full month
        is_complete = True
        prev_period_end = period_start
    else:
        raise ValueError(f"Unsupported period: {period}")
    
    # Filter transactions
    typed_tx = filter_by_type(transactions, transaction_type)
    
    if period == 'current_month':
        period_tx = filter_current_month(typed_tx, now)
    else:
        period_tx = [
            tx for tx in typed_tx 
            if period_start <= tx.timestamp < period_end
        ]
    
    if not period_tx:
        return None
    
    # Sum per category
    sum_per_cat = get_sum_per_category(period_tx)
    total = sum(sum_per_cat.values(), Decimal('0'))
    
    # Top 5 categories for daily average
    top_categories = list(sum_per_cat.keys())[:5]
    
    # Daily average per category
    av_per_day = {}
    if days_elapsed > 0:
        for cat in top_categories:
            cat_total = sum_per_cat.get(cat, Decimal('0'))
            av_per_day[cat] = round(cat_total / days_elapsed, 1)
    
    # Total daily average (excluding rent/investing)
    exclude_cats = ['rent', 'investing']
    excluded_amount = sum(
        sum_per_cat.get(cat, Decimal('0')) for cat in exclude_cats
    )
    total_av_per_day = round(
        (total - excluded_amount) / days_elapsed, 1
    ) if days_elapsed > 0 else Decimal('0')
    
    # Prediction
    if is_complete:
        # For completed periods, prediction = actual total
        prediction = total
    else:
        # For incomplete periods, project to end of month
        av_sum = sum(av_per_day.values()) if av_per_day else Decimal('0')
        remaining_days = days_in_period - days_elapsed
        prediction = round(total + av_sum * remaining_days, 2)
    
    # Comparison
    comparison = Decimal('0')
    if is_complete:
        # Compare to previous month total
        prev_month_tx = [
            tx for tx in typed_tx 
            if prev_period_start <= tx.timestamp < prev_period_end
        ]
        if prev_month_tx:
            prev_total = sum((tx.amount for tx in prev_month_tx), Decimal('0'))
            if prev_total > 0:
                comparison = round((total - prev_total) / prev_total * 100, 2)
    else:
        # Compare to yesterday's daily average (for current month)
        if days_elapsed > 1 and top_categories:
            av_sum = sum(av_per_day.values()) if av_per_day else Decimal('0')
            yesterday_tx = [
                tx for tx in period_tx
                if tx.timestamp.day < days_elapsed
            ]
            if yesterday_tx:
                yesterday_total = sum(
                    (tx.amount for tx in yesterday_tx if tx.category in top_categories),
                    Decimal('0')
                )
                av_yesterday = yesterday_total / (days_elapsed - 1)
                if av_yesterday > 0:
                    comparison = round((av_sum - av_yesterday) / av_yesterday * 100, 2)
    
    return {
        'sum_per_cat': sum_per_cat,
        'av_per_day': av_per_day,
        'total': total,
        'total_av_per_day': total_av_per_day,
        'prediction': prediction,
        'comparison': comparison,
    }

def get_records_summary(
    transactions: List[Transaction],
    transaction_type: str = 'spending',
    reference_date: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get current month summary for show_records display.
    Wrapper around get_period_summary() for backward compatibility.
    
    Returns None if no transactions found.
    Returns:
        {
            'sum_per_cat': {category: total},
            'av_per_day': {category: daily_avg},
            'total': Decimal,
            'total_av_per_day': Decimal,
            'prediction': Decimal,
            'comparison': Decimal,
        }
    """
    return get_period_summary(
        transactions,
        period='current_month',
        transaction_type=transaction_type,
        reference_date=reference_date,
    )


def get_last_month_summary(
    transactions: List[Transaction],
    transaction_type: str = 'spending',
    reference_date: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get last month summary for show_last_month display.
    Wrapper around get_period_summary() for backward compatibility.
    
    Returns None if no transactions found.
    Returns:
        {
            'sum_per_cat': {category: total},
            'av_per_day': {category: daily_avg},
            'total': Decimal,
            'total_av_per_day': Decimal,
            'prediction': Decimal (actual total for completed month),
            'comparison': Decimal (% change from previous month),
        }
    """
    return get_period_summary(
        transactions,
        period='last_month',
        transaction_type=transaction_type,
        reference_date=reference_date,
    )


# ==========================================
# DISPLAY HELPERS
# ==========================================

def format_period_text(period: str) -> str:
    """Convert period code to human-readable text."""
    period_map = {
        "3m": "3 months",
        "6m": "6 months",
        "12m": "12 months",
        "ytd": "year to date",
        "current_month": "this month",
        "last_month": "last month",
    }
    return period_map.get(period, "selected period")


def format_transactions_for_display(
    transactions: List[Transaction],
    start_index: int = 0,
) -> List[str]:
    """
    Format transactions for display in bot messages.
    Returns list of formatted strings with display numbers.
    """
    result = []
    for i, tx in enumerate(transactions, start=start_index + 1):
        line = f"{i}. {tx.date_str} - {tx.category}: {tx.subcategory} {tx.amount} {tx.currency}"
        result.append(line)
    return result


def create_tx_display_mapping(
    transactions: List[Transaction],
    page: int = 0,
    page_size: int = 15,
) -> Dict[int, int]:
    """
    Create mapping from display number (1-15) to transaction ID.
    Used for transaction selection in UI.
    """
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(transactions))

    mapping = {}
    for i, tx in enumerate(transactions[start_idx:end_idx], start=1):
        mapping[i] = tx.id

    return mapping
