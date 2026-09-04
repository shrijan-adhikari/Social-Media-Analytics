"""Alembic migration environment.

Reads DATABASE_URL from the environment (or .env file via app.core.config),
applies it to the Alembic config, and runs migrations against the SQLAlchemy
metadata collected from all models imported in app.db.base.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the backend package importable when running alembic from backend/.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Trigger model registration on Base.metadata.
from app.db.base import Base  # noqa: E402
from app.core.config import get_settings  # noqa: E402

# Alembic Config object — gives access to alembic.ini values.
config = context.config

# Wire the DATABASE_URL from our settings into the alembic config.
# This avoids hardcoding credentials in alembic.ini.
settings = get_settings()
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata that drives autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
