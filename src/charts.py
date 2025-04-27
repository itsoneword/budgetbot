import pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, matplotlib.dates as mdates, calendar
from matplotlib.gridspec import GridSpec
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
import warnings
from src.logger import log_debug, timed_function, log_function_call
from pandas_ops import get_user_currency, get_exchange_rate, recalculate_currency
import re
import os

# Suppress Matplotlib font-related warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
plt.style.use('ggplot')


@timed_function
def monthly_pivot_chart(user_id):
    log_function_call()
    # Load the data
    data = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")
    # Convert the 'timestamp' column to datetime
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    #  Determine the current date
    # Calculate the start date (six months ago)
    #start_date = (datetime.now() - relativedelta(months=7)).replace(day=1)
    start_date = (datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=7))
    log_debug(f"Filtering data from {start_date}")
    # Filter data to include only the last six months
    data = data[data["timestamp"] >= start_date]
    #call getting exchange rates:
    exchange_rates = get_exchange_rate()
    currency = get_user_currency(user_id)
    data = recalculate_currency(data, currency,exchange_rates)

    # Extract the month and year from the 'timestamp' column
    data["month_year"] = data["timestamp"].dt.to_period('M')
    data["month_name"] = data["timestamp"].dt.strftime('%B')
    # Get unique month-year combinations present in the dataset
    unique_month_years = data["month_year"].unique()
    # Sort the unique month-year combinations in chronological order
    sorted_month_years = sorted(unique_month_years)
    # Extract the month names from the sorted month-year combinations

    sorted_months = [month_year.strftime('%B') for month_year in sorted_month_years]    
    log_debug(f"Creating pivot table for months: {sorted_months}")
    # Create a pivot table
    pivot_table = pd.pivot_table(
        data,
        values="amount_cr_currency",
        index=["category"],  # Include subcategory in the index
        columns=["month_name"],
        aggfunc=np.sum,
        fill_value=0,
    )[sorted_months]

    # Add a 'Total' column
    total_name = f"Total {currency}"
    pivot_table[total_name] = pivot_table.sum(axis=1)

    # Sort the pivot table by the 'Total' column
    pivot_table_sorted = pivot_table.sort_values(by=total_name, ascending=False)

    # Add a 'Total' row
    pivot_table_sorted.loc[total_name] = pivot_table_sorted.sum()

    # Create a copy of the pivot table without the 'Total' column for the color mapping
    pivot_table_color = pivot_table_sorted.drop(columns=[total_name])

    bins = np.arange(
        0, pivot_table_color.max().max() + 20, 20
    )  # create bins of width 10
    pivot_table_color_binned = pivot_table_color.applymap(
        lambda x: np.digitize(x, bins)
    )  # apply binning

    log_debug("Creating heatmap visualization")
    # Create a figure and a set of subplots with specified layout
    fig = plt.figure(figsize=(8, 10))
    gs = GridSpec(3, 2, height_ratios=[8, 1, 1], width_ratios=[9, 1])

    # Create a heatmap with the transformed data for the color mapping and the actual data for the annotations
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
        cmap=sns.cubehelix_palette(
            gamma=0.2,
            as_cmap=True,
        ),
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

    # Rotate the x-axis labels and adjust the y-axis labels
    plt.setp(ax0.get_xticklabels(), rotation=0)
    plt.setp(ax0.get_yticklabels(), rotation=0)
    plt.setp(ax1.get_xticklabels(), rotation=0)
    plt.setp(ax1.get_yticklabels(), rotation=0)
    plt.setp(ax2.get_xticklabels(), rotation=0)
    plt.setp(ax2.get_yticklabels(), rotation=0)

    # Show the plot
    plt.tight_layout()
    log_debug("Saving monthly pivot chart")
    fig.savefig(f"user_data/{user_id}/monthly_pivot_{user_id}.jpg")
    plt.close()

    
@timed_function
def monthly_ext_pivot_chart(user_id):
    log_function_call()
    # Load and preprocess data
    df = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.to_period('M')
    df['year'] = df['timestamp'].dt.year
    
    # Filter current year
    current_year = datetime.now().year
    df = df[df['year'] == current_year]
    
    log_debug("Calculating category totals")
    # Calculate category totals first
    category_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
    
    # Create hierarchical grouping
    grouped = df.groupby(['category', 'subcategory', 'month'])['amount'].sum().reset_index()
    log_debug("Creating pivot table")
    # Create pivot table
    pivot_table = grouped.pivot_table(
        index=['category', 'subcategory'],
        columns='month',
        values='amount',
        fill_value=0
    )
    
    # Calculate totals and sort
    pivot_table['Total'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table[pivot_table['Total'] >= 50]
    # Reorder categories based on total amounts
    pivot_table = pivot_table.reindex(category_totals.index, level=0)
    
    log_debug("Creating heatmap visualization")
    # Plotting with improved formatting
    plt.figure(figsize=(15, len(pivot_table.index) * 0.4))  # Adjust height based on number of rows
    
    # Add logarithmic normalization
    log_norm = plt.Normalize(vmin=np.log1p(pivot_table[pivot_table > 0].min().min()), 
                           vmax=np.log1p(pivot_table.max().max()))
    
    # Modify the heatmap to use log scaling
    sns.heatmap(
        np.log1p(pivot_table),  # Apply log transformation to values for coloring
        annot=pivot_table,      # Show original values in cells
        fmt='.0f',
        cmap='Reds',
        cbar=False,  
        norm=log_norm,
        square=False,
        annot_kws={'size': 8}  # Smaller font for numbers
    )

    # Improve readability
    plt.title('Monthly Expenses Heatmap', pad=12, size=12)
    plt.ylabel('Category:Subcategory', size=10)
    plt.xlabel('Month', size=10)
    plt.xticks(rotation=45, ha='right',fontsize=10)
    plt.yticks(rotation=0, ha='right',fontsize=10)
    plt.tight_layout()
    
    log_debug("Saving monthly extended pivot chart")
    # Save with high resolution
    plt.savefig(f"user_data/{user_id}/monthly_pivot_{user_id}.jpg", 
                bbox_inches='tight', 
                dpi=200,
                facecolor='white')
    plt.close()

@timed_function
def monthly_line_chart(user_id):
    log_function_call()
    data = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")

    # Convert timestamp column to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Filter data for the last 6 months
    twelve_months_ago = (pd.Timestamp.today() - pd.DateOffset(months=12)).replace(day=1)
    log_debug(f"Filtering data from {twelve_months_ago}")
  
    # Extract month and year from timestamp
    filtered_data = data[data['timestamp'] >= twelve_months_ago].copy()
    filtered_data['month'] = filtered_data['timestamp'].dt.to_period('M')
    
    log_debug("Calculating monthly sums by category")
    # Group by category and month, then sum the amount
    monthly_sum = filtered_data.groupby(['category', 'month']).agg({'amount': 'sum'}).reset_index()

    # Ensure 'amount' column is numeric
    monthly_sum['amount'] = pd.to_numeric(monthly_sum['amount'])

    # Remove duplicate entries if present
    monthly_sum = monthly_sum.drop_duplicates()

    # Compute total sum of amounts for each category
    category_totals = monthly_sum.groupby('category')['amount'].sum()
    # Select top 5 categories
    top_categories = category_totals.sort_values(ascending=False).head(8).index

    log_debug(f"Top categories for visualization: {list(top_categories)}")
    # Combine remaining categories into "Other"
    monthly_sum['category'] = monthly_sum['category'].apply(lambda x: x if x in top_categories else 'Other')
 
    # Compute total sum of amounts for each category
    monthly_sum = monthly_sum.groupby(['category', 'month']).agg({'amount': 'sum'}).reset_index()
    
    log_debug("Creating pivot table for stacked area chart")
    # Pivot the data for stacked area chart
    pivot_table = monthly_sum.pivot(index='month', columns='category', values='amount').fillna(0)

    log_debug("Creating stacked area chart visualization")
    # Set up the plot
    plt.figure(figsize=(14, 8))
    # Plot stacked area chart
    pivot_table.plot(kind='area', ax=plt.gca(), stacked=True)

    # Add vertical lines for each month
    for month in pivot_table.index:
        plt.axvline(x=month, color='gray', linestyle='-', linewidth=1)

    # Add labels and legend
    plt.xlabel('Month')
    plt.ylabel('Total Amount')
    plt.title('Monthly Total Amount by Top 7 Categories (Stacked)')
    plt.legend(title='Category')
    
    # Add horizontal lines based on the total amount values
    max_total_amount = pivot_table.sum(axis=1).max()  # Maximum total amount across all months
    line_values = np.arange(500, max_total_amount + 500, 500)  # Values for the horizontal lines
    for val in line_values:
        plt.axhline(y=val, color='red', linestyle='--', linewidth=1)

    log_debug("Saving monthly line chart")
    # Show plot
    plt.savefig(f"user_data/{user_id}/monthly_chart_{user_id}.jpg")
    plt.close()

def monthly_line_chart_old(user_id):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"
    
    df = pd.read_csv(records_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")
    exchange_rates = get_exchange_rate()
    currency = get_user_currency(user_id)
    df = recalculate_currency(df, currency,exchange_rates)
    df = df.resample("D").sum()  # Group by day and sum the amounts
    # print(df)
    # # Step 2: Filter out outliers using the IQR method
    # Q1 = df["amount"].quantile(0.25)
    # Q3 = df["amount"].quantile(0.75)
    # IQR = Q3 - Q1
    # filter = df["amount"] <= Q3 + 1.5 * IQR
    # df_filtered = df.loc[filter]

    # Calculate a rolling average with a window size (adjust as needed)
    rolling_avg = df["amount_cr_currency"].rolling(window=3).mean()

    # Create the chart
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the rolling average with dots
    sns.lineplot(
        x=rolling_avg.index,
        y=rolling_avg,
        data=df,
        ax=ax,
        marker="o",
        markersize=5,
    )

    sns.set_style("whitegrid")

    # Add vertical lines for Mondays
    mondays = df[df.index.weekday == 0].index
    for monday in mondays:
        ax.axvline(x=monday, color="r", linestyle="--", alpha=0.5)
        ax.text(
            monday, ax.get_ylim()[1], "Monday", rotation=90, verticalalignment="top"
        )

    # Set x-axis limits to show only 15 weeks (adjust as needed)
    max_date = df.index[-1]
    min_date = max_date - pd.DateOffset(weeks=16)
    ax.set_xlim(min_date, max_date)

    # Set x-axis ticks to only show Mondays
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    # Rotate x-axis labels for better visibility
    plt.xticks(rotation=45)

    # plt.show()

    # Step 3: Save the chart as an image file
    plt.savefig(f"user_data/{user_id}/monthly_chart_{user_id}.jpg")


@timed_function
def make_yearly_pie_chart(user_id):
    log_function_call()
    # Load the data, assuming the first row is a header
    data = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")

    # Convert the 'timestamp' column to datetime
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Extract year
    data["year"] = data["timestamp"].dt.year
    exchange_rates = get_exchange_rate()
    currency = get_user_currency(user_id)
    data = recalculate_currency(data, currency,exchange_rates)
    # Get unique years
    years = sorted(data["year"].unique()) # Sort years for consistent order
    log_debug(f"Generating pie charts for years: {list(years)}")

    all_chart_paths = [] # Initialize list to store all chart paths

    # Loop through each year and create a pie chart
    for year in years:
        log_debug(f"Creating pie chart for year {year}")
        yearly_data = data[data["year"] == year]
        # Skip year if no data
        if yearly_data.empty:
            log_debug(f"Skipping year {year} due to no data.")
            continue
            
        category_sum = yearly_data.groupby("category")["amount_cr_currency"].sum()

        # Skip year if no spending sum
        if category_sum.sum() == 0:
             log_debug(f"Skipping year {year} due to zero spending.")
             continue

        # Calculate total sum
        total_sum = category_sum.sum()
        # Sort categories by amount
        category_sum.sort_values(ascending=False, inplace=True)
        # Create labels with category name and total amount
        labels = [
            f"{category}:{total:.2f}" for category, total in category_sum.items()
        ]
        plt.figure(figsize=(10, 6))
        pie_chart = category_sum.plot(
            kind="pie",
            labels=labels, # Show labels with category name and amount
            autopct=lambda p: "{:.1f}%".format(p) if p > 1 else "", # Show percentage > 1%
            startangle=30, # Rotate  degrees right from the default 90
            pctdistance=0.85, # Move percentages inside
        )
        
        plt.title(
            f"Spending Distribution by Category in {year} (Total: {currency}{total_sum:.2f})",
         )
        plt.ylabel("")
        pie_chart_path = f"user_data/{user_id}/yearly_pie_chart_{year}_{user_id}.jpg"
        log_debug(f"Saving pie chart for year {year} to {pie_chart_path}")
        plt.tight_layout(rect=[0, 0, 0.75, 1]) # Adjust layout for legend
        plt.savefig(pie_chart_path)
        plt.close()
        all_chart_paths.append(pie_chart_path) # Add pie chart path

    # Generate comparison charts if there's more than one year with data
    if len(all_chart_paths) > 0: # Check if any pie charts were generated
       valid_years = [int(re.search(r'_(\d{4})_', path).group(1)) for path in all_chart_paths]
       log_debug(f"Valid years extracted from pie chart paths: {valid_years}")
       if len(valid_years) > 1:
           log_debug(f"Calling make_yearly_comparison_chart for years: {valid_years}")
           filtered_data = data[data['year'].isin(valid_years)]
           log_debug(f"Filtered data shape for comparison charts: {filtered_data.shape}")
           comparison_chart_paths = make_yearly_comparison_chart(user_id, filtered_data)
           log_debug(f"Received comparison chart paths: {comparison_chart_paths}")
           
           # Verify that the percentage chart path exists
           if len(comparison_chart_paths) == 2:
               pct_chart_path = comparison_chart_paths[1]
               if pct_chart_path and os.path.exists(pct_chart_path):
                   log_debug(f"Percentage chart file exists at {pct_chart_path}")
               else:
                   log_debug(f"Percentage chart file does not exist: {pct_chart_path}")
           else:
               log_debug(f"Expected 2 comparison chart paths but received {len(comparison_chart_paths)}")
           
           all_chart_paths.extend(comparison_chart_paths) # Add comparison chart paths
           log_debug(f"Total chart paths after adding comparison charts: {len(all_chart_paths)}")
       else:
           log_debug("Skipping comparison charts as there is data for only one year.")
    else:
        log_debug("Skipping comparison charts as no pie charts were generated (no valid yearly data).")

    log_debug(f"Final list of chart paths to return: {all_chart_paths}")
    return all_chart_paths # Return all generated chart paths

@timed_function
def make_yearly_comparison_chart(user_id, data):
    """Generates yearly comparison bar charts (absolute and percentage)."""
    log_function_call()
    log_debug(f"Generating yearly comparison charts for user {user_id}")
    currency = get_user_currency(user_id)
    # Pivot data for comparison
    yearly_category_sum = data.groupby(["year", "category"])["amount_cr_currency"].sum().unstack(fill_value=0)

    # Ensure categories are sorted by total amount across all years for better visualization
    total_category_sum = yearly_category_sum.sum(axis=0).sort_values(ascending=False)
    yearly_category_sum_sorted = yearly_category_sum[total_category_sum.index]

    # Transpose the data for plotting: Categories on X-axis, Years as bars
    comparison_data = yearly_category_sum_sorted.T 
    
    # --- Absolute Values Bar Chart (Categories on X-axis) ---
    log_debug("Creating absolute values yearly comparison chart (Categories on X)")
    fig_abs, ax_abs = plt.subplots(figsize=(max(12, len(comparison_data.index) * 0.8), 8)) # Dynamic width
    comparison_data.plot(kind='bar', ax=ax_abs, width=0.8)
    ax_abs.set_title('Yearly Spending Comparison by Category')
    ax_abs.set_ylabel(f'Total Amount ({currency})')
    ax_abs.set_xlabel('Category')
    ax_abs.tick_params(axis='x', rotation=45) # Rotate labels
    ax_abs.legend(title='Year', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout for legend
    abs_chart_path = f"user_data/{user_id}/yearly_comparison_absolute_{user_id}.jpg"
    log_debug(f"Saving absolute comparison chart to {abs_chart_path}")
    plt.savefig(abs_chart_path)
    plt.close(fig_abs)

    # --- Percentage Values Bar Chart (Categories on X-axis, Grouped by Year) ---
    log_debug("Creating percentage values yearly comparison chart (Categories on X, Grouped)")
    # Calculate total spending per year first
    yearly_totals = yearly_category_sum_sorted.sum(axis=1)
    log_debug(f"Yearly totals: {yearly_totals}")
    
    # Calculate percentage of each category relative to its year's total spending
    # Avoid division by zero for years with no spending
    yearly_percentage_of_total = yearly_category_sum_sorted.divide(yearly_totals, axis=0).fillna(0) * 100
    log_debug(f"Created yearly percentage table with shape {yearly_percentage_of_total.shape}")

    # Transpose for plotting (Categories on X-axis)
    comparison_data_pct = yearly_percentage_of_total.T
    log_debug(f"Transposed percentage data with shape {comparison_data_pct.shape}")
    
    try:
        fig_pct, ax_pct = plt.subplots(figsize=(max(12, len(comparison_data_pct.index) * 0.8), 8)) # Dynamic width
        # Plot grouped bars, not stacked
        comparison_data_pct.plot(kind='bar', stacked=False, ax=ax_pct, width=0.8) 
        ax_pct.set_title('Category Spending as Percentage of Yearly Total')
        ax_pct.set_ylabel('Percentage of Yearly Total (%)')
        ax_pct.set_xlabel('Category')
        ax_pct.tick_params(axis='x', rotation=45) # Rotate labels
        ax_pct.legend(title='Year', bbox_to_anchor=(1.05, 1), loc='upper left')
        ax_pct.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%')) # Format y-axis as percentage
        plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout for legend
        pct_chart_path = f"user_data/{user_id}/yearly_comparison_percentage_{user_id}.jpg"
        log_debug(f"Saving percentage comparison chart to {pct_chart_path}")
        plt.savefig(pct_chart_path)
        plt.close(fig_pct)
        log_debug(f"Successfully saved percentage chart to {pct_chart_path}")
    except Exception as e:
        log_debug(f"Error creating percentage chart: {e}")
        pct_chart_path = None

    return [abs_chart_path, pct_chart_path]
