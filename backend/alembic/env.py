from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import the declarative Base (via app.models so every model is registered
# on Base.metadata for autogenerate).
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def _database_url() -> str:
    """Prefer DATABASE_URL from the environment, fall back to alembic.ini."""
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, so no DBAPI
    needs to be available. The rendered SQL is written to stdout.
    """
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, using a live connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

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
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# To generate the migration for the new User/Task schema (run from ./backend):
#
#   cd backend
#   DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/todo_db" \
#       alembic revision --autogenerate -m "add users and task status/due_date/owner"
#
# Then apply it:
#
#   DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/todo_db" \
#       alembic upgrade head
