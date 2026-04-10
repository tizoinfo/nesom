import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic can detect them
from src.database.base import Base  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL env var if available
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # alembic needs sync driver for config, but we convert to async later
    if database_url.startswith("mysql+aiomysql"):
        sync_url = database_url.replace("mysql+aiomysql", "mysql+pymysql", 1)
    else:
        sync_url = database_url
    config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    # Use async driver for migrations
    db_url = configuration.get("sqlalchemy.url", "")
    if db_url.startswith("mysql+pymysql"):
        db_url = db_url.replace("mysql+pymysql", "mysql+aiomysql", 1)
    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
