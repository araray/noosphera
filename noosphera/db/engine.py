from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import make_url

from ..config.schema import Settings, DatabaseSettings
from ..core.errors import StartupError
from ..observability.logging import setup_logging

# Alembic (programmatic runner)
from alembic import command
from alembic.config import Config as AlembicConfig

_admin_engine: Optional[AsyncEngine] = None
_app_engine: Optional[AsyncEngine] = None


def _build_async_engine(url: str, db: DatabaseSettings) -> AsyncEngine:
    # SQLAlchemy 2.x with psycopg3 async: "postgresql+psycopg://..."
    # create_async_engine will select the async dialect for psycopg. See docs.
    return create_async_engine(
        url,
        pool_size=db.pool_size,
        max_overflow=db.max_overflow,
        connect_args={"connect_timeout": db.connect_timeout_s},
        pool_pre_ping=True,
    )


async def init_engines(settings: Settings) -> None:
    """
    Initialize and cache the admin & app async engines.

    Admin engine uses elevated privileges (DDL/migrations).
    App engine uses least-privilege credentials for runtime.
    """
    global _admin_engine, _app_engine
    if _admin_engine or _app_engine:
        return

    db = settings.database
    try:
        # Fail early on invalid URLs
        make_url(db.admin_url)
        make_url(db.url)
    except Exception as exc:  # pragma: no cover
        raise StartupError(f"Invalid database URL(s): {exc}") from exc

    _admin_engine = _build_async_engine(db.admin_url, db)
    _app_engine = _build_async_engine(db.url, db)


def get_admin_engine() -> AsyncEngine:
    if _admin_engine is None:
        raise StartupError("Admin engine not initialized. Call init_engines() first.")
    return _admin_engine


def get_app_engine() -> AsyncEngine:
    if _app_engine is None:
        raise StartupError("App engine not initialized. Call init_engines() first.")
    return _app_engine


async def dispose_engines() -> None:
    global _admin_engine, _app_engine
    if _admin_engine is not None:
        await _admin_engine.dispose()
        _admin_engine = None
    if _app_engine is not None:
        await _app_engine.dispose()
        _app_engine = None


def _alembic_config(db_url: str) -> AlembicConfig:
    """
    Build an in-memory Alembic config that points at our package migrations and DB URL.
    No alembic.ini is required.
    """
    cfg = AlembicConfig()
    # script_location => the "noosphera/db/migrations" package folder
    script_path = Path(__file__).with_name("migrations")
    cfg.set_main_option("script_location", str(script_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Alembic version table stored under 'core' schema as our control plane
    cfg.set_main_option("version_table_schema", "core")
    return cfg


async def run_core_migrations(settings: Settings) -> None:
    """
    Run Alembic migrations programmatically using the admin URL.
    This function is async-friendly by offloading the blocking call.
    """
    cfg = _alembic_config(settings.database.admin_url)

    def _upgrade() -> None:
        command.upgrade(cfg, "head")

    await asyncio.to_thread(_upgrade)
