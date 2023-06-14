import pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from file_ops import backup_charts


def make_table(user_id):
    # Load the data
    data = pd.read_csv(f"user_data/{user_id}/spendings_{user_id}.csv")

    # Convert the 'timestamp' column to datetime
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Extract the month from the 'timestamp' column
    data["month"] = data["timestamp"].dt.strftime("%B")
    # month_names = [calendar.month_name[int(month.split('-')[1])] if '-' in month else month for month in pivot_table.columns]

    # Create a pivot table
    pivot_table = pd.pivot_table(
        data,
        values="amount",
        index=["category"],
        columns=["month"],
        aggfunc=np.sum,
        fill_value=0,
    )

    # Sort the pivot table by month
    pivot_table = pivot_table.sort_index(axis=1).iloc[:, ::-1]

    # Add a 'Total' column
    pivot_table["Total"] = pivot_table.sum(axis=1)

    # Sort the pivot table by the 'Total' column
    pivot_table_sorted = pivot_table.sort_values(by="Total", ascending=False)

    # Add a 'Total' row
    pivot_table_sorted.loc["Total"] = pivot_table_sorted.sum()

    # Create a copy of the pivot table without the 'Total' column for the color mapping

    pivot_table_color = pivot_table_sorted.drop(columns=["Total"])

    # Apply a square root transformation to the data for the color mapping

    # pivot_table_color_log = np.log1p(pivot_table_color)
    # pivot_table_color_normalized = (
    #     pivot_table_color_log - pivot_table_color_log.values.min()
    # ) / (pivot_table_color_log.values.max() - pivot_table_color_log.values.min())
    # ax0_pivot_table_color_normalized = pivot_table_color_normalized.drop("Total")

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
        pivot_table_color_binned.drop("Total"),
        annot=pivot_table_color.drop("Total"),
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
        pivot_table_sorted[["Total"]].drop(["Total"]),
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
        pivot_table_sorted.loc[["Total"], :].drop(columns=["Total"]),
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


def make_chart(user_id):
    records_file = f"user_data/{user_id}/spendings_{user_id}.csv"

    df = pd.read_csv(records_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")
    df = df.resample("D").sum()  # Group by day and sum the amounts
    # print(df)
    # Step 2: Filter out outliers using the IQR method
    Q1 = df["amount"].quantile(0.25)
    Q3 = df["amount"].quantile(0.75)
    IQR = Q3 - Q1
    filter = df["amount"] <= Q3 + 1.5 * IQR
    df_filtered = df.loc[filter]

    # Step 3: Create the chart
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the daily amounts
    sns.lineplot(
        x=df_filtered.index,
        y="amount",
        data=df_filtered,
        ax=ax,
        marker="o",
        markersize=10,
    )

    sns.set_style("whitegrid")

    # Add vertical lines for Mondays
    mondays = df_filtered[df_filtered.index.weekday == 0].index
    for monday in mondays:
        ax.axvline(x=monday, color="r", linestyle="--", alpha=0.5)
        ax.text(
            monday, ax.get_ylim()[1], "Monday", rotation=90, verticalalignment="top"
        )
    # Set x-axis ticks to only show Mondays
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    # Rotate x-axis labels for better visibility
    plt.xticks(rotation=45)

    # plt.show()

    # Step 3: Save the chart as an image file
    plt.savefig(f"user_data/{user_id}/monthly_chart_{user_id}.jpg")
