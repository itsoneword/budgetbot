import pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, matplotlib.dates as mdates, calendar
from matplotlib.gridspec import GridSpec
from dateutil.relativedelta import relativedelta
from datetime import datetime
from file_ops import backup_charts
from pandas_ops import get_user_currency, get_exchange_rate, recalculate_currency

def monthly_pivot_chart(user_id):
    # Load the data
    data = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")
    # Convert the 'timestamp' column to datetime
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    #  Determine the current date
    # Calculate the start date (six months ago)
    start_date = (datetime.now() - relativedelta(months=6)).replace(day=1)
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
    #print("print4:", sorted_months)
    # period_to_month_name = {period: period.strftime('%B') for period in sorted_month_years}
    # data['month_name'] = data['month_year'].map(period_to_month_name)
    # Create a pivot table
    pivot_table = pd.pivot_table(
        data,
        values="amount_cr_currency",
        index=["category"],
        columns=["month_name"],
        aggfunc=np.sum,
        fill_value=0,
    )[sorted_months]

    #print("print5: ", pivot_table)
    # Add a 'Total' column
    total_name = f"Total {currency}"
    pivot_table[total_name] = pivot_table.sum(axis=1)

    # Sort the pivot table by the 'Total' column
    pivot_table_sorted = pivot_table.sort_values(by=total_name, ascending=False)

    # Add a 'Total' row
    pivot_table_sorted.loc[total_name] = pivot_table_sorted.sum()

    # Create a copy of the pivot table without the 'Total' column for the color mapping

    pivot_table_color = pivot_table_sorted.drop(columns=[total_name])

    # Apply a square root transformation to the data for the color mapping

    # pivot_table_color_log = np.log1p(pivot_table_color)
    # pivot_table_color_normalized = (
    #     pivot_table_color_log - pivot_table_color_log.values.min()
    # ) / (pivot_table_color_log.values.max() - pivot_table_color_log.values.min())
    # ax0_pivot_table_color_normalized = pivot_table_color_normalized.drop(total_name)

    bins = np.arange(
        0, pivot_table_color.max().max() + 20, 20
    )  # create bins of width 10
    pivot_table_color_binned = pivot_table_color.applymap(
        lambda x: np.digitize(x, bins)
    )  # apply binning

    # Create a figure and a set of subplots with specified layout
    fig = plt.figure(figsize=(8, 10))
    gs = GridSpec(3, 2, height_ratios=[9, 1, 1], width_ratios=[9, 1])
    # Define your colors in RGB

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
    # plt.show()
    fig.savefig(f"user_data/{user_id}/monthly_pivot_{user_id}.jpg")


def monthly_line_chart(user_id):
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


def make_yearly_pie_chart(user_id):
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
    years = data["year"].unique()

    # Loop through each year and create a pie chart
    for year in years:
        yearly_data = data[data["year"] == year]
        category_sum = yearly_data.groupby("category")["amount_cr_currency"].sum()

        # Calculate total sum
        total_sum = category_sum.sum()
        # Sort categories by amount
        category_sum.sort_values(ascending=False, inplace=True)
        # Create labels with category name and total amount
        labels = [
            f"{category}: {total:.2f}" for category, total in category_sum.items()
        ]
        plt.figure(figsize=(10, 6))
        pie_chart = category_sum.plot(
            kind="pie",
            labels=labels,
            autopct=lambda p: "{:.1f}%".format(p) if p > 0 else "",
            startangle=0,
        )

        # Rotate category names
        for text in pie_chart.texts:
            text.set_rotation(0)

        plt.title(
            f"Spending Distribution by Category in {year} (Total: {currency}{total_sum:.2f})"
        )
        plt.ylabel("")
        # plt.show()
        plt.savefig(f"user_data/{user_id}/yearly_pie_chart_{year}_{user_id}.jpg")
    return years
