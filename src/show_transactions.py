    # utils.py

import configparser, json
from dateutil.parser import parse, ParserError
from datetime import datetime, timezone, timedelta
import pandas as pd
from file_ops import check_dictionary_format, add_category



def process_transaction_input(user_id, parts):
    subcategory = " ".join(parts[:-1])
    category = None
    subcat_to_cat_file = f"user_data/{user_id}/dictionary_{user_id}.json"
    subcat_to_cat = read_subcat_to_cat_from_file(subcat_to_cat_file, user_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    if len(parts) > 2:
        #print(parts[0][0] , type(parts[0][0]))
        #print (parts[0][0].isdigit() , parts[0][-1].isdigit())
        if parts[0][0].isdigit() and parts[0][-1].isdigit():
            try:
                timestamp = toDateUtc(parts[0])
            except Exception as e:
                print(e)
            if len(parts) > 3:
                category = parts[1]
                subcategory = parts[2]
            else:
                subcategory = parts[1]
                category = subcat_to_cat.get(subcategory, None)
        else:
            category = parts[0]
            subcategory = parts[1]
            add_category(user_id, category, subcategory)
    else:
        category = None
        subcategory = parts[0]

    category = category or subcat_to_cat.get(subcategory, None)
    if category is None:
        category = "other"
        # Set a flag to indicate that the category needs to be chosen by the user
        unknown_cat = True
    else:
        unknown_cat = False

    # subcategory = subcategory or "other"

    return timestamp, category, subcategory, unknown_cat


def process_income_input(user_id, parts):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    category = "salary"
    if len(parts) == 3:
        try:
            timestamp = parse(parts[0], dayfirst=True)
            category = parts[1]
        except (ValueError, ParserError):
            category = parts[0]
    elif len(parts) == 2:
        try:
            timestamp = parse(parts[0], dayfirst=True)
        except (ValueError, ParserError):
            category = parts[0]

    return timestamp, category


def toDateUtc(mdate):
    # Assuming your date string is in the format 'dd.mm'
    date_string = mdate
    current_year = datetime.now().year

    # Parse the date string and add the current year
    date_obj = datetime.strptime(f"{current_year}-{date_string}", "%Y-%d.%m")

    # Set the timezone to UTC and convert it to the desired format
    date_obj_utc = date_obj.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return date_obj_utc


def read_subcat_to_cat_from_file(file_path, user_id):

    check_dictionary_format(user_id)
    # Get user's language
    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    user_language = config.get("DEFAULT", "language")

    with open(file_path, "r") as file:
        try:
            all_dicts = json.load(file)
        except json.JSONDecodeError:
            return None

    cat_dict = all_dicts.get(user_language, {})

    # Transpose the dictionary to subcategory:category
    subcat_to_cat = {}
    for category, subcategories in cat_dict.items():
        for subcategory in subcategories:
            subcat_to_cat[subcategory] = category

    return subcat_to_cat


# def parse_input(parts, subcat_to_cat):

#     timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
#     if len(parts) > 2:
#         if parts[0][0].isdigit() and parts[0][-1].isdigit():
#             timestamp = toDateUtc(parts[0])
#             if len(parts) > 3:
#                 category = parts[1]
#                 subcategory = parts[2]
#             else:
#                 subcategory = parts[1]
#                 category = subcat_to_cat.get(subcategory, "other")
#         else:
#             category = parts[0]
#             subcategory = parts[1]
#     else:
#         category = None
#         subcategory = parts[0]

#     category = category or subcat_to_cat.get(subcategory, "other")
#     subcategory = subcategory or "other"

#     return timestamp, category, subcategory

def get_all_user_categories(user_id):
    """Get all unique categories from user's spending file"""
    try:
        # Read user's spending file into pandas DataFrame
        file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
        df = pd.read_csv(file_path)
        # Get unique categories and sort alphabetically
        categories = sorted(df['category'].unique().tolist())
        return categories
    except Exception as e:
        print(f"Error getting categories: {e}")
        return []

def filter_transactions_by_period(user_id, period):
    """Filter transactions based on selected time period"""
    try:
        # Read user's spending file
        file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
        df = pd.read_csv(file_path)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Determine the date range based on the period
        current_date = datetime.now()
        
        if period == "3m":
            # Last 3 months
            start_date = current_date - timedelta(days=90)
        elif period == "6m":
            # Last 6 months
            start_date = current_date - timedelta(days=180)
        elif period == "12m":
            # Last 12 months
            start_date = current_date - timedelta(days=365)
        elif period == "ytd":
            # Year to date (from January 1st of current year)
            start_date = datetime(current_date.year, 1, 1)
        else:
            # Default to last month if period is invalid
            start_date = current_date - timedelta(days=30)
        
        # Filter data based on date range
        filtered_df = df[df['timestamp'] >= start_date]
        
        return filtered_df
    except Exception as e:
        print(f"Error filtering transactions: {e}")
        return pd.DataFrame()

def get_transactions_by_categories(user_id, categories, period):
    """Get transactions for selected categories and time period"""
    try:
        # Get filtered transactions
        df = filter_transactions_by_period(user_id, period)
        
        # Filter by selected categories if any are specified
        if categories:
            df = df[df['category'].isin(categories)]
        
        # Sort DataFrame by timestamp in descending order (newest first)
        df = df.sort_values(by='timestamp', ascending=False)
        
        # Format transactions for display
        transactions = []
        for index, row in df.iterrows():
            # Check if ID column exists and use it if available
            tx_id = row.get('id', index)
            
            # Format: "id: timestamp, category, subcategory, amount, currency"
            timestamp = row['timestamp']
            if not isinstance(timestamp, str):
                timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
            transaction_str = f"{tx_id}: {timestamp}, {row['category']}, {row['subcategory']}, {row['amount']}, {row['currency']}"
            transactions.append(transaction_str)
        
        return transactions
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

def calculate_category_summary(user_id, categories, period):
    """Calculate summary statistics for selected categories and time period"""
    try:
        # Get filtered transactions
        df = filter_transactions_by_period(user_id, period)
        
        # Filter by selected categories if any are specified
        if categories:
            df = df[df['category'].isin(categories)]
        
        # Get user's currency
        config = configparser.ConfigParser()
        config.read(f"user_data/{user_id}/config.ini")
        user_currency = config.get("DEFAULT", "currency")
        
        # Calculate total spending
        total_spending = df['amount'].sum()
        
        # Calculate sum per category
        category_sums = df.groupby('category')['amount'].sum().to_dict()
        
        # Calculate top subcategories per category
        subcategory_data = {}
        for category in categories:
            category_df = df[df['category'] == category]
            top_subcats = category_df.groupby('subcategory')['amount'].sum().nlargest(6).to_dict()
            subcategory_data[category] = top_subcats
        
        return {
            'total': total_spending,
            'currency': user_currency,
            'category_sums': category_sums,
            'subcategory_data': subcategory_data,
            'period': period,
            'transaction_count': len(df)
        }
    except Exception as e:
        print(f"Error calculating summary: {e}")
        return {
            'total': 0,
            'currency': 'USD',
            'category_sums': {},
            'subcategory_data': {},
            'period': period,
            'transaction_count': 0
        }

def format_period_text(period):
    """Convert period code to human-readable text"""
    if period == "3m":
        return "3 months"
    elif period == "6m":
        return "6 months"
    elif period == "12m":
        return "12 months"
    elif period == "ytd":
        return "year to date"
    else:
        return "selected period"
