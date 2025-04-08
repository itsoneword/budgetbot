# pandas_ops.py
import os, calendar, pandas as pd, configparser, json, numpy as np, yfinance as yf
from datetime import datetime, timedelta
#from utils import get_exchange_rate, recalculate_currency, get_user_currency

def get_user_path(user_id):

    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"
    return file_path


def get_top_categories(file_path, n=5):
    if not os.path.exists(file_path):
        return []
    df = pd.read_csv(file_path)
    top_categories = (
        df[df["category"] != "Other"]["category"].value_counts().head(n).index.tolist()
    )
    return top_categories


def get_current_month_data(user_id, file_path):
    data = pd.read_csv(file_path)

    # Convert 'timestamp' column to datetime objects
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Filter the DataFrame to include only records from the current month

    current_month_data = data[
        (data["timestamp"].dt.month == current_month)
        & (data["timestamp"].dt.year == current_year)
    ].copy()
    #current_month_data_copy = current_month_data.copy()
        #recalc total in current currency
    exchange_rates = get_exchange_rate()
    currency = get_user_currency(user_id)
    current_month_data = recalculate_currency(current_month_data, currency,exchange_rates)

    return current_month_data


def get_last_month_data(user_id, file_path):
    data = pd.read_csv(file_path)

    # Convert 'timestamp' column to datetime objects
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Get the last month and year
    current_date = datetime.now()
    last_month_date = current_date.replace(day=1) - timedelta(days=1)
    last_month = last_month_date.month
    last_month_year = last_month_date.year

    # Filter the DataFrame to include only records from last month
    last_month_data = data[
        (data["timestamp"].dt.month == last_month)
        & (data["timestamp"].dt.year == last_month_year)
    ].copy()

    # Recalculate totals in current currency
    exchange_rates = get_exchange_rate()
    currency = get_user_currency(user_id)
    last_month_data = recalculate_currency(last_month_data, currency, exchange_rates)

    return last_month_data


def show_sum_per_cat(user_id, file_path):
    file_path = get_user_path(user_id)
    current_month_data = get_current_month_data(user_id, file_path)
    sum_per_cat = (
        current_month_data.groupby("category")["amount_cr_currency"]
        .sum()
        .sort_values(ascending=False)
    )
    return sum_per_cat


def show_top_subcategories(user_id):
    file_path = get_user_path(user_id)

    current_month_data = get_current_month_data(user_id, file_path)

    # Calculate the total sum per subcategory within each category
    sum_per_subcat = (
        current_month_data.groupby(["category", "subcategory"])["amount_cr_currency"]
        .sum()
        .reset_index()
    )

    # Sort by amount within each category and take the top 3
    top_subcats = sum_per_subcat.sort_values(
        ["category", "amount_cr_currency"], ascending=[True, False]
    )
    top_subcats = top_subcats.groupby("category").head(5)

    return top_subcats


# def top_5_cat(user_id):

#     df = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")
#     # Assuming df is your DataFrame and 'category' is the column with categories
#     top5cat = df["category"].value_counts().nlargest(5).index.tolist()

#     return top5cat


def show_av_per_day(user_id, file_path):

    current_month_data = get_current_month_data(user_id, file_path)
    selected_categories = get_top_categories(file_path)
    # Filter the data to only include the selected categories
    filtered_data = current_month_data[
        current_month_data["category"].isin(selected_categories)
    ]
    total = show_total(user_id, file_path)
    # Calculate the total sum per selected category
    total_per_cat = filtered_data.groupby("category")["amount_cr_currency"].sum()
    day_number = datetime.now().day

    # Calculate the average per day
    av_per_day = round(total_per_cat / day_number, 1)
    
    rent_sum = current_month_data.loc[current_month_data['category'] == 'rent', 'amount_cr_currency'].sum()
    investing_sum = current_month_data.loc[current_month_data['category'] == 'investing', 'amount_cr_currency'].sum()
    excluding_amount = rent_sum + investing_sum
 
    total_av_per_day = round((current_month_data["amount_cr_currency"].sum() - excluding_amount) / day_number, 1)

    # Calculate the prediction for the end of the month
    current_month_days = calendar.monthrange(datetime.now().year, datetime.now().month)[
        1
    ]
    prediction = total + round(av_per_day.sum()) * (current_month_days - day_number)
    # Store the total average spending for today

    # Calculate the total average spending until yesterday
    yesterday_data = filtered_data[filtered_data["timestamp"].dt.day < day_number]
    av_per_day_yesterday = (
        round(yesterday_data["amount_cr_currency"].sum() / (day_number - 1), 1)
        if day_number > 1
        else 0
    )
    # Calculate the comparison with yesterday's total average spending
    comparison = (
        round((av_per_day.sum() - av_per_day_yesterday) / av_per_day_yesterday * 100, 2)
        if av_per_day_yesterday != 0
        else 0
    )

    return av_per_day, total_av_per_day, prediction, comparison


def show_total(user_id, file_path):
    current_month_data = get_current_month_data(user_id, file_path)
    total_spendings = current_month_data["amount_cr_currency"].sum()
    return total_spendings


def show_last_month_sum_per_cat(user_id, file_path):
    file_path = get_user_path(user_id)
    last_month_data = get_last_month_data(user_id, file_path)
    sum_per_cat = (
        last_month_data.groupby("category")["amount_cr_currency"]
        .sum()
        .sort_values(ascending=False)
    )
    return sum_per_cat


def show_last_month_total(user_id, file_path):
    last_month_data = get_last_month_data(user_id, file_path)
    total_spendings = last_month_data["amount_cr_currency"].sum()
    return total_spendings


def show_last_month_av_per_day(user_id, file_path):
    last_month_data = get_last_month_data(user_id, file_path)
    selected_categories = get_top_categories(file_path)
    # Filter the data to only include the selected categories
    filtered_data = last_month_data[
        last_month_data["category"].isin(selected_categories)
    ]
    total = show_last_month_total(user_id, file_path)
    # Calculate the total sum per selected category
    total_per_cat = filtered_data.groupby("category")["amount_cr_currency"].sum()
    
    # Get the number of days in last month
    current_date = datetime.now()
    last_month_date = current_date.replace(day=1) - timedelta(days=1)
    days_in_last_month = calendar.monthrange(last_month_date.year, last_month_date.month)[1]
    
    # Calculate the average per day
    av_per_day = round(total_per_cat / days_in_last_month, 1)
    
    rent_sum = last_month_data.loc[last_month_data['category'] == 'rent', 'amount_cr_currency'].sum()
    investing_sum = last_month_data.loc[last_month_data['category'] == 'investing', 'amount_cr_currency'].sum()
    excluding_amount = rent_sum + investing_sum
 
    total_av_per_day = round((last_month_data["amount_cr_currency"].sum() - excluding_amount) / days_in_last_month, 1)

    # No need for prediction or comparison since the month is already over
    prediction = total
    comparison = 0

    return av_per_day, total_av_per_day, prediction, comparison


def calculate_limit(user_id):

    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"

    monthly_limit = float(config.get("DEFAULT", "MONTHLY_LIMIT"))
    total_spendings = show_total(user_id, file_path)
   
    # EXcluding Investing and Rent because it is not daily spendings.
    exclude_df = get_current_month_data(user_id, file_path)
    rent_sum = exclude_df.loc[exclude_df['category'] == 'rent', 'amount_cr_currency'].sum()
    investing_sum = exclude_df.loc[exclude_df['category'] == 'investing', 'amount_cr_currency'].sum()
    excluding_amount = rent_sum + investing_sum
 
    #print ("this is the print statement 23222222!!!",excluding_amount)
    # Calculate daily and weekly limits
    current_date = datetime.now()
    days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
    daily_limit = (monthly_limit - excluding_amount) / days_in_month
    #weekly_limit = daily_limit * 7

    # Calculate current daily average
    current_day = current_date.day
    #not_spendings = 
    current_daily_average = (total_spendings - excluding_amount) / current_day

    # Calculate percentage difference
    percent_difference = ((current_daily_average - daily_limit) / daily_limit) * 100

    # Calculate how many days spendings should be 0
    days_zero_spending = (current_daily_average - daily_limit) / (
        daily_limit / (current_day + 1)
    )
    if days_zero_spending < 0:
        days_zero_spending = 0

    # Calculate new daily limit
    remaining_days = days_in_month - current_day
    new_daily_limit = (monthly_limit - total_spendings) / remaining_days
    if new_daily_limit < 0:
        new_daily_limit = 0
    # Using round function
    current_daily_average = round(current_daily_average, 2)
    percent_difference = round(percent_difference, 2)
    daily_limit = round(daily_limit, 2)
    days_zero_spending = round(days_zero_spending, 2)
    new_daily_limit = round(new_daily_limit, 2)

    return [
        current_daily_average,
        percent_difference,
        daily_limit,
        days_zero_spending,
        new_daily_limit,
    ]
import pandas as pd

def calculate_new_value(data, user_currency, exchange_rates):
    current_currency = user_currency.upper()
    
    if isinstance(data, pd.DataFrame):
        # If data is a DataFrame, apply the function to each row
        return data.apply(lambda row: calculate_new_value_single(row, current_currency, exchange_rates), axis=1)
    else:
        # If data is a single row (Series or dict), process it directly
        return calculate_new_value_single(data, current_currency, exchange_rates)

def calculate_new_value_single(row, current_currency, exchange_rates):
    tx_currency = row["currency"]
    amount = row["amount"]
    
    try:
        if tx_currency == current_currency:
            return amount
        elif tx_currency != "USD" and current_currency == "USD":
            rate = exchange_rates[f"USD{tx_currency}"]
            return (amount / rate)
        elif tx_currency == "USD" and current_currency != "USD":
            rate = exchange_rates[f"USD{current_currency}"]
            return (amount * rate)
        elif tx_currency != "USD" and current_currency != "USD":
            rate1 = exchange_rates[f"USD{tx_currency}"]
            rate2 = exchange_rates[f"USD{current_currency}"]
            return ((amount / rate1) * rate2)
        else:
            print(f"Unsupported original currency: {tx_currency}")
            return amount
    except Exception as e:
        print(f"Error processing row: {row}")
        print(f"Exception: {str(e)}")
        return amount

def recalculate_currency(data, user_currency, exchange_rates):
    data = data.copy()
    data.loc[:,'amount_cr_currency'] = calculate_new_value(data, user_currency, exchange_rates)

    return data

def get_user_currency(user_id):
    user_dir = f"user_data/{user_id}"
    try:
        # Attempt to read the configuration file
        config = configparser.ConfigParser()
        config.read(f"{user_dir}/config.ini")
        
        # Attempt to get the currency from the configuration
        currency = config.get("DEFAULT", "CURRENCY")
    except (configparser.Error, FileNotFoundError, KeyError):
        # Handle errors by setting a default value (USD)
        currency = "USD"
   #print("getUserCurrency exceuted")
    return currency

def get_exchange_rate():
    """
    Fetches current exchange rates for USD to other currencies (USDEUR, USDRUB, USDAMD, USDUSD, USDTHB).
    Returns rates in format where USDAMD = ~400 (number of AMD per 1 USD).
    Caches results for 12 hours to avoid excessive API calls.
    """
    # Define currency pairs
    currency_pairs = ['USDEUR', 'USDRUB', 'USDAMD', 'USDUSD', 'USDTHB']
    # Initialize exchange rates dictionary
    exchange_rates = {}
    # Get current time
    current_time = datetime.now()

    # Ensure configs directory exists
    os.makedirs('configs', exist_ok=True)

    # Load existing exchange rates and last update time from the file
    try:
        with open('configs/exchangerates.json', 'r') as file:
            data = json.load(file)
            existing_time = datetime.fromisoformat(data['last_update'])
            exchange_rates = data['exchange_rates']
            
            # Verify all required rates exist
            all_rates_exist = all(pair in exchange_rates for pair in currency_pairs)
            if not all_rates_exist:
                # Force update if any rate is missing
                existing_time = current_time - timedelta(days=1)
    except (FileNotFoundError, json.JSONDecodeError):
        # Handle file not found or invalid JSON data
        existing_time = current_time - timedelta(days=1)  # Set a default time to force an update
        # Initialize with empty exchange rates
        exchange_rates = {}
    
    # Check if more than 12 hours have passed since the last update
    time_difference = current_time - existing_time
    if time_difference > timedelta(hours=12) or not exchange_rates:
        print("Fetching fresh exchange rates")
        try:
            # Use Exchange Rates API (free and reliable)
            api_url = "https://open.er-api.com/v6/latest/USD"
            import requests
            response = requests.get(api_url)
            response.raise_for_status()
            
            api_data = response.json()
            if api_data["result"] == "success":
                # Extract rates directly (these are already in USD-to-currency format)
                rates = api_data["rates"]
                
                # Set the values for our currency pairs
                exchange_rates['USDEUR'] = rates.get('EUR', 0.92)  # Default fallback if API fails
                exchange_rates['USDRUB'] = rates.get('RUB', 90.0)
                exchange_rates['USDAMD'] = rates.get('AMD', 400.0)
                exchange_rates['USDUSD'] = 1.0  # Always 1.0
                exchange_rates['USDTHB'] = rates.get('THB', 35.0)
                
                print("Successfully fetched exchange rates:", exchange_rates)
                
                # Update the last update time
                last_update_time = current_time.isoformat()
                
                # Save exchange rates and last update time to the file
                with open('configs/exchangerates.json', 'w') as file:
                    json.dump({'exchange_rates': exchange_rates, 'last_update': last_update_time}, file)
            else:
                print("API error, falling back to default rates")
                # If API fails and no cached rates, set defaults
                if not exchange_rates:
                    exchange_rates = {
                        'USDEUR': 0.92, 
                        'USDRUB': 90.0, 
                        'USDAMD': 400.0, 
                        'USDUSD': 1.0,
                        'USDTHB': 35.0
                    }
        except Exception as e:
            print(f"Error fetching exchange rates: {str(e)}")
            # If API fails and no cached rates, set defaults
            if not exchange_rates:
                exchange_rates = {
                    'USDEUR': 0.92, 
                    'USDRUB': 90.0, 
                    'USDAMD': 400.0, 
                    'USDUSD': 1.0,
                    'USDTHB': 35.0
                }
    
    return exchange_rates
