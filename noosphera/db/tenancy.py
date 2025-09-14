from __future__ import annotations

import re
from typing import Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

_VALID_SCHEMA = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_schema_name(schema: str) -> None:
    if not _VALID_SCHEMA.match(schema):
        raise ValueError(f"Invalid schema name: {schema}")


async def create_tenant_schema(admin_engine: AsyncEngine, schema: str) -> None:
    _validate_schema_name(schema)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


async def set_search_path(session: AsyncSession, schema: str) -> None:
    """
    Set a request-local search_path to the tenant schema + public.
    Keep 'core' accessed via explicit qualification.
    """
    _validate_schema_name(schema)
    await session.execute(text(f'SET LOCAL search_path TO "{schema}", public'))


async def assert_schema_exists(conn_or_session: Union[AsyncEngine, AsyncSession], schema: str) -> None:
    _validate_schema_name(schema)
    if isinstance(conn_or_session, AsyncEngine):
        async with conn_or_session.connect() as conn:
            res = await conn.execute(text("SELECT 1 FROM information_schema.schemata WHERE schema_name=:s"), {"s": schema})
            if res.scalar_one_or_none() is None:
                raise RuntimeError(f"Schema '{schema}' does not exist.")
    else:
        res = await conn_or_session.execute(
            text("SELECT 1 FROM information_schema.schemata WHERE schema_name=:s"), {"s": schema}
        )
        if res.scalar_one_or_none() is None:
            raise RuntimeError(f"Schema '{schema}' does not exist.")
