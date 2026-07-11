"""
Alembic environment for BudgetBot.

The app connects with asyncpg using a plain ``postgresql://`` DATABASE_URL.
SQLAlchemy needs the driver spelled out, so we rewrite the scheme to
``postgresql+asyncpg://`` and run migrations over an async engine — no extra
sync driver (psycopg2) is needed in the image.
"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLAlchemy models/metadata — migrations are handwritten, autogenerate unsupported.
target_metadata = None

DEFAULT_DATABASE_URL = "postgresql://budgetbot:budgetbot_dev_pass@localhost:5432/budgetbot"


def _database_url() -> str:
    """DATABASE_URL with the scheme rewritten for SQLAlchemy's asyncpg dialect."""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if url.startswith("postgres://"):  # heroku-style shorthand
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of connecting (``alembic upgrade head --sql``)."""
    context.configure(
        url=_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    engine = create_async_engine(_database_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
