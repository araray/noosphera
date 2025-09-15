# FILE: noosphera/db/tenant_chat_bootstrap.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .tenancy import create_tenant_schema


async def ensure_tenant_chat_tables(admin_engine: AsyncEngine, schema: str) -> None:
    """
    Idempotently ensure the per-tenant chat tables exist.
    Uses admin engine (DDL privileges). Validates/creates schema if missing.
    """
    await create_tenant_schema(admin_engine, schema)
    async with admin_engine.begin() as conn:
        # chat_sessions
        await conn.execute(
            text(
                f'''
                CREATE TABLE IF NOT EXISTS "{schema}".chat_sessions (
                  id UUID PRIMARY KEY,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                  name TEXT NULL
                )
                '''
            )
        )

        # chat_messages
        await conn.execute(
            text(
                f'''
                CREATE TABLE IF NOT EXISTS "{schema}".chat_messages (
                  id UUID PRIMARY KEY,
                  session_id UUID NOT NULL REFERENCES "{schema}".chat_sessions(id) ON DELETE CASCADE,
                  role TEXT NOT NULL CHECK (role IN ('system','user','assistant')),
                  content TEXT NOT NULL,
                  meta JSONB NULL,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                '''
            )
        )
        # index for efficient listing
        await conn.execute(
            text(
                f'''
                CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created
                ON "{schema}".chat_messages (session_id, created_at DESC)
                '''
            )
        )
