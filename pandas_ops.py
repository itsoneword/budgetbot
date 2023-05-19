# pandas_ops.py

import pandas as pd
from datetime import datetime


def get_current_month_data(user_id):
    user_dir = f"user_data/{user_id}"
    data = pd.read_csv(f"{user_dir}/spendings_{user_id}.csv")

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


def show_sum_per_cat(user_id):
    current_month_data = get_current_month_data(user_id)
    sum_per_cat = (
        current_month_data.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )
    return sum_per_cat


def show_top_subcategories(user_id):
    current_month_data = get_current_month_data(user_id)

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


def show_av_per_day(user_id):
    current_month_data = get_current_month_data(user_id)
    selected_categories = [
        "food",
        "transport",
        "groceries",
        "alcohol",
        "транспорт",
        "продукты",
        "алкоголь",
        "еда",
    ]

    # Filter the data to only include the selected categories
    filtered_data = current_month_data[
        current_month_data["category"].isin(selected_categories)
    ]

    # Calculate the total sum per category
    total_per_cat = filtered_data.groupby("category")["amount"].sum()

    # Get today's day number
    day_number = datetime.now().day

    # Calculate the average per day
    av_per_day = round(total_per_cat / day_number, 1)

    return av_per_day


def show_total(user_id):
    current_month_data = get_current_month_data(user_id)
    total_spendings = current_month_data["amount"].sum()
    return total_spendings
