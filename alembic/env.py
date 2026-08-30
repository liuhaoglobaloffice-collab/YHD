"""
Alembic migration environment for LiuHao AI OS.

Uses the project's Base metadata and Settings to connect to the database.
Supports both SQLite (development) and PostgreSQL (production).
"""

import logging
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the project's declarative Base and all models so they register
from src.database.base import Base  # noqa: E402
from src.database import models  # noqa: E402, F401

target_metadata = Base.metadata

# Read the database URL from the project's settings, falling back to the ini
# value.  This lets the project's .env / environment variables control the
# target database during migrations.
def _get_database_url() -> str:
    """Get database URL from project settings or environment."""
    from src.core.config import get_settings

    settings = get_settings()
    url = settings.database_url
    if url:
        # Convert async URLs to sync for Alembic
        url = url.replace("+aiosqlite", "")
        url = url.replace("+asyncpg", "")
        url = url.replace("+aiomysql", "")
        return url
    # Fallback: build from ini or environment
    return config.get_main_option("sqlalchemy.url", "sqlite:///./liuhao_ai_os.db")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to live database)."""
    url = _get_database_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()