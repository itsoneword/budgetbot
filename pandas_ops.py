# pandas_ops.py
import os, calendar, pandas as pd, configparser
from datetime import datetime, timedelta


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


def get_current_month_data(file_path):
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
    ]

    return current_month_data


def show_sum_per_cat(user_id, file_path):
    file_path = get_user_path(user_id)
    current_month_data = get_current_month_data(file_path)
    sum_per_cat = (
        current_month_data.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )
    return sum_per_cat


def show_top_subcategories(user_id):
    file_path = get_user_path(user_id)

    current_month_data = get_current_month_data(file_path)

    # Calculate the total sum per subcategory within each category
    sum_per_subcat = (
        current_month_data.groupby(["category", "subcategory"])["amount"]
        .sum()
        .reset_index()
    )

    # Sort by amount within each category and take the top 3
    top_subcats = sum_per_subcat.sort_values(
        ["category", "amount"], ascending=[True, False]
    )
    top_subcats = top_subcats.groupby("category").head(3)

    return top_subcats


# def top_5_cat(user_id):

#     df = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")
#     # Assuming df is your DataFrame and 'category' is the column with categories
#     top5cat = df["category"].value_counts().nlargest(5).index.tolist()

#     return top5cat


def show_av_per_day(user_id, file_path):

    current_month_data = get_current_month_data(file_path)
    selected_categories = get_top_categories(file_path)
    # Filter the data to only include the selected categories
    filtered_data = current_month_data[
        current_month_data["category"].isin(selected_categories)
    ]
    total = show_total(user_id, file_path)
    # Calculate the total sum per selected category
    total_per_cat = filtered_data.groupby("category")["amount"].sum()
    day_number = datetime.now().day

    # Calculate the average per day
    av_per_day = round(total_per_cat / day_number, 1)
    total_av_per_day = round(current_month_data["amount"].sum() / day_number, 1)

    # Calculate the prediction for the end of the month
    current_month_days = calendar.monthrange(datetime.now().year, datetime.now().month)[
        1
    ]
    prediction = total + round(av_per_day.sum()) * (current_month_days - day_number)
    # Store the total average spending for today

    # Calculate the total average spending until yesterday
    yesterday_data = filtered_data[filtered_data["timestamp"].dt.day < day_number]
    av_per_day_yesterday = (
        round(yesterday_data["amount"].sum() / (day_number - 1), 1)
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
    current_month_data = get_current_month_data(file_path)
    total_spendings = current_month_data["amount"].sum()
    return total_spendings


def calculate_limit(user_id):

    config = configparser.ConfigParser()
    config.read(f"user_data/{user_id}/config.ini")
    file_path = f"user_data/{user_id}/spendings_{user_id}.csv"

    monthly_limit = float(config.get("DEFAULT", "MONTHLY_LIMIT"))
    total_spendings = show_total(user_id, file_path)
    # Calculate daily and weekly limits
    current_date = datetime.now()
    days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
    daily_limit = monthly_limit / days_in_month
    weekly_limit = daily_limit * 7

    # Calculate current daily average
    current_day = current_date.day
    current_daily_average = total_spendings / current_day

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
