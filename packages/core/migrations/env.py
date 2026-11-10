"""Alembic environment. Runs as the migration (owner) role, never the application role."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, text

from core import config
from core.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    url = context.config.attributes.get("url") or config.settings().migration_database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        # Fail fast instead of queueing behind live queries (R-11).
        connection.execute(text("SET lock_timeout = '5s'"))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("offline migrations are not supported")
run_migrations_online()
