# BudgetBot

BudgetBot is a powerful and user-friendly Telegram bot designed to help you manage your personal finances. With BudgetBot, you can easily track your daily expenses, incomes, and gain insights into your spending habits.

## New Release 0.0.3 (14.06.2023)

We're excited to introduce a number of new features in this release:

### Charts and Heatmap

Visualize your monthly spending with our interactive charts and heatmap. These tools provide an easy-to-understand overview of your spending habits, helping you identify areas where you might be overspending.

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

The bot is currently available under my own production: https://t.me/mybudgetassistantbot 
You can also get started with self deployment, follow these steps:

1. Clone the repository: `git clone https://github.com/itsoneword/budgetbot.git`
2. Navigate to the project directory: `cd budgetbot\configs`
3. Create "config" file with the token inside:  
```
[TELEGRAM]  
TOKEN = your_token_here
```
4. Install the necessary dependencies:  
* pandas
* matplotlib
* seaborn
* python-telegram-bot
5. Start the bot: "python3 core.py"

## Contributing

We welcome contributions from the community. If you'd like to contribute, please contact me directly in telegram @dy0r2.

## License

BudgetBot is licensed under the [MIT License](LICENSE).

## Contact

If you have any questions or feedback, please feel free to contact me directly tg: @dy0r2.

