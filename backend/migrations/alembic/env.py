"""Alembic environment, wired to the app's SQLAlchemy metadata + DATABASE_URL.

Design notes:
* ``target_metadata`` is the app's ``Base.metadata``. We import ``app.models``
  (and the balance/offline/device modules) so EVERY table is registered before
  autogenerate/compare runs.
* The database URL comes from ``DATABASE_URL`` (env) or the app settings — never
  hardcoded — so the same migrations run in every environment.
* This does NOT replace the app's ``Base.metadata.create_all`` boot path; it is
  additive tooling for versioned schema management.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# --------------------------------------------------------------------------- #
# Make the backend package importable (backend/ is two parents up:
# migrations/alembic/env.py -> migrations -> backend).
# --------------------------------------------------------------------------- #
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Alembic Config object.
config = context.config

# Configure Python logging from alembic.ini if present.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        # Logging config is optional; never fail migrations because of it.
        pass

# --------------------------------------------------------------------------- #
# Import the app metadata. Importing these modules registers all ORM tables
# (core + balance + offline + device) onto Base.metadata.
# --------------------------------------------------------------------------- #
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (core tables)
import app.models.balance  # noqa: E402,F401
import app.models.offline  # noqa: E402,F401
import app.models.device  # noqa: E402,F401

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL from env, then app settings, then ini."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    try:
        from app.config import settings

        if settings.database_url:
            return settings.database_url
    except Exception:
        pass
    return config.get_main_option("sqlalchemy.url") or ""


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with a live DB connection)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
