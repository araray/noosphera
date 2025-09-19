from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Import metadata from core models
from noosphera.db.models.core import metadata as target_metadata  # noqa: F401

# Alembic Config object
config = context.config


def _get_url() -> str:
    # Prefer DATABASE_URL env (helper scripts can set it), else alembic option.
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL (or sqlalchemy.url) must be set for migrations.")
    return url


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="core",
        compare_type=True,
    )
    with context.begin_transaction():
        # Ensure the version-table schema exists even in offline SQL output
        context.execute('CREATE SCHEMA IF NOT EXISTS core')
        context.run_migrations()


def _run_sync_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="core",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(_get_url(), poolclass=pool.NullPool)
    async with connectable.begin() as connection:
        # Ensure target schema exists before Alembic creates core.alembic_version
        await connection.execute(text('CREATE SCHEMA IF NOT EXISTS "core"'))
        await connection.run_sync(_run_sync_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
