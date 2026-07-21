# BudgetBot

BudgetBot is a Telegram bot for personal finance tracking. Log expenses and income by text or voice, organize them into categories, and get charts and AI-powered answers about your spending.

Release history: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Features

### Transaction tracking
Send a message with an amount and category and it is saved to PostgreSQL. Multi-transaction messages (comma-separated items) and dated entries (`dd.mm` prefix) are supported. Inline keyboards drive category selection, editing and deletion.

### Voice input
Send a voice message — it is transcribed locally with faster-whisper (no cloud STT, audio never leaves the host) and routed by intent: log a transaction, show stats, or answer a question. Multi-transaction and relative-date phrases work by voice too.

### AI Q&A (/ask)
Ask free-form questions about your spending ("how much did I spend on food last month?"). Your data is summarized into the prompt — the model never touches the database. Access is gated by an admin allowlist.

### Spending analysis and charts
Totals, per-category breakdowns, average daily spend, monthly pivots, yearly bar and pie charts, heatmaps, and month-end spending predictions.

### Categories and limits
Custom categories and subcategories, frequently-used shortcuts, monthly and daily spending limits with overspend warnings.

### Multi-currency
Track spending in different currencies; transactions are converted to your current currency at daily exchange rates.

### Localization
English and Russian interfaces.

### Data ownership
Data lives in your own PostgreSQL instance (Docker volume on your machine). Nothing is shared with third parties.

## Getting Started

The bot runs under my own production: https://t.me/mybudgetassistantbot — or host it yourself.

### Run with Docker Compose

```bash
git clone https://github.com/itsoneword/budgetbot.git
cd budgetbot
```

Add your Telegram bot token to `configs/config`:

```
[TELEGRAM]
TOKEN = place_your_token_here
```

Then start the stack (PostgreSQL + bot):

```bash
./deploy.sh --dev    # dev: base compose, Postgres on 127.0.0.1:5432 only
./deploy.sh          # prod: adds docker-compose.prod.yml overlay — no DB port
                     # published, secrets from ~/.claude/service-secrets/budgetbot.env
```

Dev reads secrets from the repo-local `.env` (`API_KEY`, `POSTGRES_PASSWORD`, `ADMIN_USER_ID`); prod reads the same keys from `/home/cleversol/.claude/service-secrets/budgetbot.env` (chmod 600) so they survive re-clones. Postgres data persists in `./pgdata`. The optional AI features (/ask, voice routing) authenticate via a dedicated `claude setup-token` env file — see `docker-compose.yml` comments (T-038); host OAuth credentials are deliberately not mounted.

Optional: set `SENTRY_DSN` in `.env` to enable Sentry error reporting (`SENTRY_ENVIRONMENT` defaults to `prod`). Leave it unset to run without Sentry — the SDK is never even imported.

### Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Point the bot at a running PostgreSQL via `DATABASE_URL` and put your token in `configs/config` as above.

3. Start the bot:

```bash
python3 run.py
```

## Project Structure

- `src/` — Telegram handlers and bot wiring
- `domain/` — pure business logic
- `infrastructure/` — repositories, database, external APIs
- `shared/` — DI container and utilities
- `docs/` — architecture, roadmap, changelog, task board

## Contributing

Contributions are welcome — contact me directly in Telegram: @dy0r2.

## License

BudgetBot is licensed under the [MIT License](LICENSE).

## Contact

Questions or feedback: tg @dy0r2.
