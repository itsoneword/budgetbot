"""
Chart generation for spending visualizations.
Uses PostgreSQL for data loading.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import calendar
from matplotlib.gridspec import GridSpec
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, timezone
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
import time
import warnings
import re
import os
import asyncio
from io import BytesIO

from src.logger import log_debug, timed_function, log_function_call, LogConfig

# pandas_ops imports removed - data comes pre-converted from load_chart_data()

if TYPE_CHECKING:
    from shared.di.container import Container

# Suppress Matplotlib font-related warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
plt.style.use('ggplot')


async def load_chart_data(
    user_id: int,
    repos: 'Container',
    months: int = 12,
) -> tuple[pd.DataFrame, str]:
    """
    Load transaction data from PostgreSQL for chart generation.
    Also performs currency conversion using DB-backed exchange rates.

    Returns:
        tuple of (DataFrame with transactions already converted, user currency)
    """
    from domain.session_loader import load_user_session

    session = await load_user_session(
        user_id, repos,
        load_transactions=True,
        transactions_months=months,
        transaction_type='spending'  # Charts typically show spending
    )

    # Convert Transaction objects to DataFrame
    if not session.transactions:
        return pd.DataFrame(), session.config.currency

    data = []
    for tx in session.transactions:
        data.append({
            'timestamp': tx.timestamp,
            'category': tx.category,
            'subcategory': tx.subcategory,
            'amount': float(tx.amount),
            'currency': tx.currency,
        })

    df = pd.DataFrame(data)
    user_currency = session.config.currency

    # Perform currency conversion using DB-backed service
    if not df.empty:
        rates = await repos.currency.get_rates()
        # Convert Decimal rates to float for pandas compatibility
        float_rates = {k: float(v) for k, v in rates.items()}
        df = repos.currency.convert_dataframe(
            df, user_currency, rates,
            amount_col='amount',
            currency_col='currency',
            result_col='amount_cr_currency'
        )

    return df, user_currency



@timed_function
def monthly_pivot_chart(user_id, data: pd.DataFrame, user_currency: str):
    """Generate monthly pivot heatmap chart.
    
    Args:
        user_id: User ID
        data: DataFrame with transactions (from load_chart_data)
        user_currency: User's currency code
    """
    log_function_call()

    if data.empty:
        log_debug("No data available for monthly pivot chart")
        return

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
        data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Filter for last 7 months
    # Use timezone-aware datetime for comparison with PostgreSQL data
    start_date = pd.Timestamp.now(tz='UTC').replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=7)
    log_debug(f"Filtering data from {start_date}")
    # Ensure timestamp column is timezone-aware for comparison
    if data['timestamp'].dt.tz is None:
        data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')
    data = data[data["timestamp"] >= start_date]

    if data.empty:
        log_debug("No data in date range for monthly pivot chart")
        return

    # Extract the month and year from the 'timestamp' column
    data["month_year"] = data["timestamp"].dt.to_period('M')
    data["month_name"] = data["timestamp"].dt.strftime('%B')

    # Get unique month-year combinations present in the dataset
    unique_month_years = data["month_year"].unique()
    sorted_month_years = sorted(unique_month_years)
    sorted_months = [month_year.strftime('%B') for month_year in sorted_month_years]
    log_debug(f"Creating pivot table for months: {sorted_months}")

    # Create a pivot table
    pivot_table = pd.pivot_table(
        data,
        values="amount_cr_currency",
        index=["category"],
        columns=["month_name"],
        aggfunc=np.sum,
        fill_value=0,
    )[sorted_months]

    # Add a 'Total' column
    total_name = f"Total {user_currency}"
    pivot_table[total_name] = pivot_table.sum(axis=1)

    # Sort the pivot table by the 'Total' column
    pivot_table_sorted = pivot_table.sort_values(by=total_name, ascending=False)

    # Add a 'Total' row
    pivot_table_sorted.loc[total_name] = pivot_table_sorted.sum()

    # Create a copy of the pivot table without the 'Total' column for the color mapping
    pivot_table_color = pivot_table_sorted.drop(columns=[total_name])

    bins = np.arange(0, pivot_table_color.max().max() + 20, 20)
    pivot_table_color_binned = pivot_table_color.applymap(lambda x: np.digitize(x, bins))

    log_debug("Creating heatmap visualization")
    fig = plt.figure(figsize=(8, 10))
    gs = GridSpec(3, 2, height_ratios=[8, 1, 1], width_ratios=[9, 1])

    # Create a heatmap with the transformed data for the color mapping
    ax0 = plt.subplot(gs[0, 0])
    sns.heatmap(
        pivot_table_color_binned.drop(total_name),
        annot=pivot_table_color.drop(total_name),
        fmt=".2f",
        cmap=sns.light_palette((22, 200, 40), input="husl", as_cmap=True),
        cbar=False,
        ax=ax0,
    )
    ax0.set_xlabel("")
    ax0.set_ylabel("")

    # Create a separate heatmap for the 'Total' column
    ax1 = plt.subplot(gs[0, 1])
    sns.heatmap(
        pivot_table_sorted[[total_name]].drop([total_name]),
        annot=True,
        cbar=False,
        fmt=".2f",
        cmap=sns.cubehelix_palette(gamma=0.2, as_cmap=True),
        ax=ax1,
        yticklabels=False,
    )
    ax1.set_xlabel("")
    ax1.set_ylabel("")

    # Create a separate heatmap for the 'Total' row
    ax2 = plt.subplot(gs[1, 0])
    sns.heatmap(
        pivot_table_sorted.loc[[total_name], :].drop(columns=[total_name]),
        annot=True,
        cbar=False,
        fmt=".2f",
        cmap=sns.light_palette((0, 10, 50), input="husl"),
        ax=ax2,
        xticklabels=False,
    )
    ax2.set_xlabel("")
    ax2.set_ylabel("")

    # Rotate the x-axis labels
    plt.setp(ax0.get_xticklabels(), rotation=0)
    plt.setp(ax0.get_yticklabels(), rotation=0)
    plt.setp(ax1.get_xticklabels(), rotation=0)
    plt.setp(ax1.get_yticklabels(), rotation=0)
    plt.setp(ax2.get_xticklabels(), rotation=0)
    plt.setp(ax2.get_yticklabels(), rotation=0)

    plt.tight_layout()
    log_debug("Saving monthly pivot chart to BytesIO")
    
    # Return BytesIO instead of saving to file
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf


@timed_function
def monthly_ext_pivot_chart(user_id, data: pd.DataFrame, user_currency: str):
    """Generate extended monthly pivot chart with subcategories.
    
    Args:
        user_id: User ID
        data: DataFrame with transactions (from load_chart_data)
        user_currency: User's currency code
    """
    log_function_call()

    if data.empty:
        log_debug("No data available for extended pivot chart")
        return

    # Ensure proper types
    if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
        data['timestamp'] = pd.to_datetime(data['timestamp'])

    data['month'] = data['timestamp'].dt.to_period('M')
    data['year'] = data['timestamp'].dt.year

    # Filter current year
    current_year = datetime.now().year
    data = data[data['year'] == current_year]

    if data.empty:
        log_debug("No data for current year in extended pivot chart")
        return

    log_debug("Calculating category totals")
    category_totals = data.groupby('category')['amount'].sum().sort_values(ascending=False)

    # Create hierarchical grouping
    grouped = data.groupby(['category', 'subcategory', 'month'])['amount'].sum().reset_index()
    log_debug("Creating pivot table")

    pivot_table = grouped.pivot_table(
        index=['category', 'subcategory'],
        columns='month',
        values='amount',
        fill_value=0
    )

    # Calculate totals and sort
    pivot_table['Total'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table[pivot_table['Total'] >= 50]
    pivot_table = pivot_table.reindex(category_totals.index, level=0)

    log_debug("Creating heatmap visualization")
    plt.figure(figsize=(15, len(pivot_table.index) * 0.4))

    # Add logarithmic normalization
    log_norm = plt.Normalize(
        vmin=np.log1p(pivot_table[pivot_table > 0].min().min()),
        vmax=np.log1p(pivot_table.max().max())
    )

    sns.heatmap(
        np.log1p(pivot_table),
        annot=pivot_table,
        fmt='.0f',
        cmap='Reds',
        cbar=False,
        norm=log_norm,
        square=False,
        annot_kws={'size': 8}
    )

    plt.title('Monthly Expenses Heatmap', pad=12, size=12)
    plt.ylabel('Category:Subcategory', size=10)
    plt.xlabel('Month', size=10)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(rotation=0, ha='right', fontsize=10)
    plt.tight_layout()

    log_debug("Saving monthly extended pivot chart to BytesIO")
    
    # Return BytesIO instead of saving to file
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()
    return buf


@timed_function
def monthly_line_chart(user_id, data: pd.DataFrame, user_currency: str):
    """Generate monthly stacked area chart.
    
    Args:
        user_id: User ID
        data: DataFrame with transactions (from load_chart_data)
        user_currency: User's currency code
    """
    log_function_call()

    if data.empty:
        log_debug("No data available for line chart")
        return

    # Convert timestamp column to datetime
    if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
        data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Filter data for the last 12 months
    # Use timezone-aware timestamp for comparison with PostgreSQL data
    twelve_months_ago = (pd.Timestamp.now(tz='UTC') - pd.DateOffset(months=12)).replace(day=1)
    log_debug(f"Filtering data from {twelve_months_ago}")

    # Ensure timestamp column is timezone-aware for comparison
    if not data.empty and data['timestamp'].dt.tz is None:
        data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')
    filtered_data = data[data['timestamp'] >= twelve_months_ago].copy()

    if filtered_data.empty:
        log_debug("No data in date range for line chart")
        return

    filtered_data['month'] = filtered_data['timestamp'].dt.to_period('M')

    log_debug("Calculating monthly sums by category")
    monthly_sum = filtered_data.groupby(['category', 'month']).agg({'amount': 'sum'}).reset_index()
    monthly_sum['amount'] = pd.to_numeric(monthly_sum['amount'])
    monthly_sum = monthly_sum.drop_duplicates()

    # Compute total sum for each category
    category_totals = monthly_sum.groupby('category')['amount'].sum()
    top_categories = category_totals.sort_values(ascending=False).head(8).index

    log_debug(f"Top categories for visualization: {list(top_categories)}")
    monthly_sum['category'] = monthly_sum['category'].apply(lambda x: x if x in top_categories else 'Other')
    monthly_sum = monthly_sum.groupby(['category', 'month']).agg({'amount': 'sum'}).reset_index()

    log_debug("Creating pivot table for stacked area chart")
    pivot_table = monthly_sum.pivot(index='month', columns='category', values='amount').fillna(0)

    log_debug("Creating stacked area chart visualization")
    plt.figure(figsize=(14, 8))
    pivot_table.plot(kind='area', ax=plt.gca(), stacked=True)

    # Add vertical lines for each month
    for month in pivot_table.index:
        plt.axvline(x=month, color='gray', linestyle='-', linewidth=1)

    plt.xlabel('Month')
    plt.ylabel('Total Amount')
    plt.title('Monthly Total Amount by Top 7 Categories (Stacked)')
    plt.legend(title='Category')

    # Add horizontal reference lines
    max_total_amount = pivot_table.sum(axis=1).max()
    line_values = np.arange(500, max_total_amount + 500, 500)
    for val in line_values:
        plt.axhline(y=val, color='red', linestyle='--', linewidth=1)

    log_debug("Saving monthly line chart to BytesIO")
    
    # Return BytesIO instead of saving to file
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf


def generate_usage_summary_chart(
    days: int = 30,
    top_commands: int = 20,
    output_path: Optional[str] = None,
    label: Optional[str] = None,
) -> str:
    """Generate admin usage summary chart from log files."""
    log_path = os.path.join(LogConfig.LOG_DIR, LogConfig.USER_LOG_FILE)
    if label is None:
        label = "1y" if days >= 365 else f"{days}d"
    if output_path is None:
        output_path = os.path.join(LogConfig.LOG_DIR, f"admin_usage_summary_{label}.jpg")

    if not os.path.exists(log_path):
        raise FileNotFoundError("Log file not found.")

    records = []
    with open(log_path, "r") as log_file:
        for line in log_file:
            line = line.strip()
            if not line:
                continue
            try:
                timestamp_str, remainder = line.split(" - ", 1)
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            except ValueError:
                continue

            if "UserID:" not in remainder:
                continue
            details = remainder.split("UserID:", 1)[1].strip()
            parts = [part.strip() for part in details.split(",")]
            if len(parts) < 4:
                continue

            user_id, name, username, handler = parts[:4]
            records.append({
                "timestamp": timestamp,
                "user_id": user_id,
                "name": name,
                "username": username,
                "handler": handler,
            })

    if not records:
        raise ValueError("No log entries found.")

    df = pd.DataFrame(records)
    cutoff = datetime.now() - timedelta(days=days)
    df_recent = df[df["timestamp"] >= cutoff].copy()
    if df_recent.empty:
        raise ValueError("No log entries found for the selected period.")

    df_recent["date"] = df_recent["timestamp"].dt.date

    # Prepare user activity heatmap data
    user_counts = df_recent.groupby(["user_id", "name", "username", "date"]).size().reset_index(name="count")
    user_totals = (
        user_counts.groupby(["user_id", "name", "username"])["count"].sum().sort_values(ascending=False).head(10)
    )

    top_user_keys = list(user_totals.index)
    if top_user_keys:
        user_counts["user_key"] = list(zip(user_counts["user_id"], user_counts["name"], user_counts["username"]))
        user_counts = user_counts[user_counts["user_key"].isin(top_user_keys)]

        def format_user_label(key):
            _, name, username = key
            display_username = username if username else "(no username)"
            display_name = name if name else "Unknown"
            return f"{display_username} - {display_name}"

        label_order = [format_user_label(key) for key in top_user_keys]
        user_counts["label"] = user_counts["user_key"].apply(format_user_label)
        activity_matrix = (
            user_counts
            .pivot(index="label", columns="date", values="count")
            .reindex(label_order)
            .fillna(0)
        )
    else:
        activity_matrix = pd.DataFrame()

    # Prepare command distribution data
    command_counts_full = df_recent.groupby("handler").size().sort_values(ascending=False)
    command_limit = min(top_commands, 20)
    command_counts = command_counts_full.head(command_limit)

    num_users = len(activity_matrix)
    num_commands = len(command_counts)

    heatmap_height = max(3.5, 2.5 + num_users * 0.4)
    commands_height = max(3.0, 2.0 + num_commands * 0.3)
    fig_height = heatmap_height + commands_height

    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(16, fig_height),
        gridspec_kw={"height_ratios": [heatmap_height, commands_height]},
    )

    if not activity_matrix.empty:
        heatmap_data = np.log1p(activity_matrix)
        sns.heatmap(
            heatmap_data,
            ax=ax1,
            cmap="Blues",
            linewidths=0.3,
            linecolor="white",
            cbar_kws={"label": "log(1 + daily interactions)"},
        )
        ax1.set_xlabel("")
        ax1.set_ylabel("User")
        ax1.set_title(f"User activity (last {days} days)")
        ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha="right")
        ax1.set_yticklabels(ax1.get_yticklabels(), rotation=0)
    else:
        ax1.text(0.5, 0.5, "No user activity", ha="center", va="center")
        ax1.axis("off")

    if not command_counts.empty:
        ax2.barh(command_counts.index[::-1], command_counts.values[::-1], color="teal")
        ax2.set_xscale("log")
        ax2.set_xlabel("Command calls (log scale)")
        ax2.set_ylabel("Command")
        ax2.set_title("Top commands")
        ax2.grid(axis="x", linestyle="--", alpha=0.4)
        for idx, (lbl, value) in enumerate(zip(command_counts.index[::-1], command_counts.values[::-1])):
            ax2.text(value * 1.05, idx, str(value), va="center")
    else:
        ax2.text(0.5, 0.5, "No command usage", ha="center", va="center")
        ax2.axis("off")

    fig.suptitle(f"Bot usage summary ({label})", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return output_path



@timed_function
def make_yearly_pie_chart(user_id, data: pd.DataFrame, user_currency: str):
    """Generate yearly pie charts for spending distribution.
    
    Args:
        user_id: User ID
        data: DataFrame with transactions (from load_chart_data)
        user_currency: User's currency code
    
    Returns:
        List of BytesIO objects containing chart images (no files saved to disk)
    """
    log_function_call()

    if data.empty:
        log_debug("No data available for yearly pie chart")
        return []

    # Ensure proper types
    if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
        data["timestamp"] = pd.to_datetime(data["timestamp"])

    data["year"] = data["timestamp"].dt.year
    years = sorted(data["year"].unique())
    log_debug(f"Generating pie charts for years: {list(years)}")

    all_charts = []  # List of BytesIO objects
    valid_years = []

    for year in years:
        log_debug(f"Creating pie chart for year {year}")
        yearly_data = data[data["year"] == year]

        if yearly_data.empty:
            log_debug(f"Skipping year {year} due to no data.")
            continue

        category_sum = yearly_data.groupby("category")["amount_cr_currency"].sum()

        if category_sum.sum() == 0:
            log_debug(f"Skipping year {year} due to zero spending.")
            continue

        total_sum = category_sum.sum()
        category_sum.sort_values(ascending=False, inplace=True)
        labels = [f"{category}:{total:.2f}" for category, total in category_sum.items()]

        plt.figure(figsize=(10, 6))
        pie_chart = category_sum.plot(
            kind="pie",
            labels=labels,
            autopct=lambda p: "{:.1f}%".format(p) if p > 1 else "",
            startangle=30,
            pctdistance=0.85,
        )

        plt.title(f"Spending Distribution by Category in {year} (Total: {user_currency}{total_sum:.2f})")
        plt.ylabel("")
        plt.tight_layout(rect=[0, 0, 0.75, 1])
        
        # Save to BytesIO instead of file
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        all_charts.append(buf)
        valid_years.append(year)
        log_debug(f"Created pie chart for year {year} (BytesIO)")

    # Generate comparison charts if there's more than one year with data
    if len(valid_years) > 1:
        log_debug(f"Calling make_yearly_comparison_chart for years: {valid_years}")
        filtered_data = data[data['year'].isin(valid_years)]
        log_debug(f"Filtered data shape for comparison charts: {filtered_data.shape}")
        comparison_charts = make_yearly_comparison_chart(user_id, filtered_data, user_currency)
        log_debug(f"Received {len(comparison_charts)} comparison charts")
        all_charts.extend(comparison_charts)
    else:
        log_debug("Skipping comparison charts as there is data for only one year.")

    log_debug(f"Total charts to return: {len(all_charts)}")
    return all_charts


@timed_function
def make_yearly_comparison_chart(user_id, data: pd.DataFrame, user_currency: str):
    """Generate yearly comparison bar charts (absolute and percentage).
    
    Args:
        user_id: User ID
        data: DataFrame with transactions (from load_chart_data)
        user_currency: User's currency code
    
    Returns:
        List of BytesIO objects containing chart images
    """
    log_function_call()
    log_debug(f"Generating yearly comparison charts for user {user_id}")

    charts = []

    # Pivot data for comparison
    yearly_category_sum = data.groupby(["year", "category"])["amount_cr_currency"].sum().unstack(fill_value=0)

    # Sort by total amount across all years
    total_category_sum = yearly_category_sum.sum(axis=0).sort_values(ascending=False)
    yearly_category_sum_sorted = yearly_category_sum[total_category_sum.index]

    # Transpose for plotting
    comparison_data = yearly_category_sum_sorted.T

    # --- Absolute Values Bar Chart ---
    log_debug("Creating absolute values yearly comparison chart")
    fig_abs, ax_abs = plt.subplots(figsize=(max(12, len(comparison_data.index) * 0.8), 8))
    comparison_data.plot(kind='bar', ax=ax_abs, width=0.8)
    ax_abs.set_title('Yearly Spending Comparison by Category')
    ax_abs.set_ylabel(f'Total Amount ({user_currency})')
    ax_abs.set_xlabel('Category')
    ax_abs.tick_params(axis='x', rotation=45)
    ax_abs.legend(title='Year', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    
    # Save to BytesIO
    buf_abs = BytesIO()
    plt.savefig(buf_abs, format='png', dpi=100, bbox_inches='tight')
    buf_abs.seek(0)
    plt.close(fig_abs)
    charts.append(buf_abs)
    log_debug("Created absolute comparison chart (BytesIO)")

    # --- Percentage Values Bar Chart ---
    log_debug("Creating percentage values yearly comparison chart")
    yearly_totals = yearly_category_sum_sorted.sum(axis=1)
    log_debug(f"Yearly totals: {yearly_totals}")

    yearly_percentage_of_total = yearly_category_sum_sorted.divide(yearly_totals, axis=0).fillna(0) * 100
    log_debug(f"Created yearly percentage table with shape {yearly_percentage_of_total.shape}")

    comparison_data_pct = yearly_percentage_of_total.T
    log_debug(f"Transposed percentage data with shape {comparison_data_pct.shape}")

    try:
        fig_pct, ax_pct = plt.subplots(figsize=(max(12, len(comparison_data_pct.index) * 0.8), 8))
        comparison_data_pct.plot(kind='bar', stacked=False, ax=ax_pct, width=0.8)
        ax_pct.set_title('Category Spending as Percentage of Yearly Total')
        ax_pct.set_ylabel('Percentage of Yearly Total (%)')
        ax_pct.set_xlabel('Category')
        ax_pct.tick_params(axis='x', rotation=45)
        ax_pct.legend(title='Year', bbox_to_anchor=(1.05, 1), loc='upper left')
        ax_pct.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        # Save to BytesIO
        buf_pct = BytesIO()
        plt.savefig(buf_pct, format='png', dpi=100, bbox_inches='tight')
        buf_pct.seek(0)
        plt.close(fig_pct)
        charts.append(buf_pct)
        log_debug("Created percentage comparison chart (BytesIO)")
    except Exception as e:
        log_debug(f"Error creating percentage chart: {e}")

    return charts
