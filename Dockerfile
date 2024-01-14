FROM python:3.9

COPY . /app

WORKDIR /app

RUN pip install pandas matplotlib seaborn python-telegram-bot yfinance

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
