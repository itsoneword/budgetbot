# BudgetBot

BudgetBot is a powerful and user-friendly Telegram bot designed to help you manage your personal finances. With BudgetBot, you can easily track your daily expenses, incomes, and gain insights into your spending habits.

## fix patch 0.2.2 from 23.4.25
Minor changes in Ru version (saving message was changed)
Behevior for Single car transaction was changed (no more Permanent Menu return)

## major release of 0.2.0 from 1.4.25
Communication cahnged mostly to inline keyboard
Adding transactoin now offers a list of existing cat|subcat
namings of cats|subcats does not allow symbols anymore
category edit process is now easier with inline keyboard
deletion of transactions is more interactive with inline keyboard.

## fix patch from 12.3.25
Fix minor issues with charts

## fix patch from 16.2.25
Changed About command logic, how it handles settings changes.

## fix patch from 01.12.24
Updated monthly pivot charts to cover 1st month of the range fully (was covering only since 1st month day, current time)
Updated monthly_ext_stat function to use log scale and show sorted per category(was subcat)
Minor logging changes and bug fixes.
version 0.1.2

## Minor fix from 19.09.24
Updated logging and error handling for currency exchange functions.
Fixed "A value is trying to be set on a copy of a slice from a DataFrame." issue.

## New Release 0.1.0 (16.07.2024)
Fixed minor issues,  \n
Added version control to /about.
Changed monthly stat charts and ShowExt command. now showing 8 months and 5 top cats acordingly.
added detailed subcat_cat chart showing monthly based statistic/monthly_ext_stat.

### we are celebrating our first users! 3 people constantly using the app now!

## New Release 0.0.6 (24.02.2024)
Fixed minor issues,
Added version control to /about

## New Release 0.0.5 (13.11.2023)

### Fixed sorting months over the year
Now January is being shown after December as expected.
### Added /about command
Showing information about current currency, limits, and language.
### Added converting different currencies
Previous transaction in different currencies now are being re-calculated to the current based on today's exchange rate

## New Release 0.0.4 (13.11.2023)

### Yearly piecharts

Visualizing yearly spending with piechart. These tools provide an easy-to-understand overview of per category spendings on yearly basis

### Fixed bugs
Some bags related to stuck in Income mode are finally fixed

## New Release 0.0.3 (14.06.2023)

We're excited to introduce a number of new features in this release:

### Charts and Heatmap

Visualize your monthly spending with our charts and heatmap. These tools provide an easy-to-understand overview of your spending habits, helping you identify areas where you might be overspending.

### Income Tracking

Keep track of your income alongside your spending. By monitoring both, you can get a clearer picture of your overall financial health.

### Monthly and Daily Limit Tracking

Set monthly and daily spending limits and BudgetBot will notify you if you're exceeding these limits. This feature helps you stay within your budget and avoid overspending.

### /show_last Command

The re-considered /show_last command allows you to see the total sum and filter by category name (e.g. /show_last transport). This feature provides a quick and easy way to review your recent spending in specific categories.

## Basic Features

### Transaction Tracking

Record your daily transactions with ease. Simply send a message to the bot with the amount and category of your spending, and it will be logged for future reference.

### Category Management

Organize your transactions into categories. You can add new categories, change existing ones, and even get a list of your most frequently used categories.

### Spending Analysis

Get a detailed breakdown of your spending. The bot can show you the total amount you've spent, the sum per category, and even the average spending per day for each category.

### Spending Predictions

Based on your current spending, BudgetBot can predict your total spending for the month. It also compares your average daily spending with the previous day and shows you the percentage difference.

### Data Privacy

Your data is stored locally and is only accessible to you. BudgetBot respects your privacy and does not share your data with third parties.

BudgetBot is a great tool for anyone looking to gain more control over their personal finances. Whether you're a budgeting pro or just getting started, BudgetBot can help you keep track of your spending and make more informed financial decisions.


## Getting Started

This bot is currently available under my own production: https://t.me/mybudgetassistantbot
But you can also host it yourself

### Run using Docker

Build an image by running:

```Bash
git clone https://github.com/itsoneword/budgetbot.git
cd budgetbot
docker build -t budgetbot .
```

And start the container providing your API key:

```Bash
docker run --name budgetbot \
--restart unless-stopped \
-v /mydata/path:/app/user_data/ \
-e API_KEY=yourkey \
-d budgetbot
```
Change `/mydata/path` to your local folder where you want to keep your transaction history, and change `API_KEY` to your own.

Alternartivelly, you can use the following docker compose:

```Docker
version: '3.3'
services:
    bot:
        container_name: budgetbot
        restart: unless-stopped
        volumes:
            - /mydata/path:/app/user_data/
        environment:
            - API_KEY='yourkey'
        image: budgetbot
```


### Run locally

1. Install the necessary dependencies:  
* pandas
* matplotlib
* seaborn
* python-telegram-bot

2. Clone the repository 
```
git clone https://github.com/itsoneword/budgetbot.git
```
2. Add your key to the config file inside: `configs\config` file 
```
[TELEGRAM]  
TOKEN = place_your_token_here
```
3. Start the bot: 

```bash
python3 core.py
```

## Contributing

We welcome contributions from the community. If you'd like to contribute, please contact me directly in telegram @dy0r2.

## License

BudgetBot is licensed under the [MIT License](LICENSE).

## Contact

If you have any questions or feedback, please feel free to contact me directly tg: @dy0r2.

## Project Structure

The project now follows a more organized structure:

- `/src`: Contains all the core Python files for the application
- Root directory: Contains configuration files, deployment-related files, and the main entry point

## Running the Project

To run the project, use:

```bash
python3 run.py
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the required directories exist:
```bash
mkdir -p user_data
```

3. Configure the application by setting up the config file in the configs directory.

