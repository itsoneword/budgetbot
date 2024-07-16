# BudgetBot

BudgetBot is a powerful and user-friendly Telegram bot designed to help you manage your personal finances. With BudgetBot, you can easily track your daily expenses, incomes, and gain insights into your spending habits.
## New Release 0.1.0 (16.07.2024)
### Fixed minor issues
### Added version control to /about
### Changed monthly stat charts and ShowExt command. now showing 8 months and 5 top cats acordingly. 
### added details subcat_cat chart showing monthly based statistic/monthly_ext_stat
### we are celebrating our first users! 3 people constantly using the app now!

## New Release 0.0.6 (24.02.2024)
### Fixed minor issues
### Added version control to /about

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

