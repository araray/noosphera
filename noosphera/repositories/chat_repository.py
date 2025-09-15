# FILE: noosphera/repositories/chat_repository.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AsyncSession as _AsyncSession  # type hint clarity
from ..db.tenancy import set_search_path
from ..db.models.tenant_chat import get_chat_models


class ChatRepository:
    """
    Data access for chat sessions/messages within a tenant schema.
    All operations set `search_path` to target the tenant schema.
    """

    def __init__(self, session: AsyncSession, schema: str) -> None:
        self._s = session
        self._schema = schema
        self._Base, self._ChatSession, self._ChatMessage = get_chat_models(schema)

    async def _scope(self) -> None:
        await set_search_path(self._s, self._schema)

    async def create_session(self, *, name: Optional[str] = None) -> UUID:
        await self._scope()
        sid = uuid4()
        obj = self._ChatSession(id=sid, name=name)
        self._s.add(obj)
        await self._s.commit()
        return sid

    async def get_session_exists(self, session_id: UUID) -> bool:
        await self._scope()
        res = await self._s.execute(
            select(self._ChatSession.id).where(self._ChatSession.id == session_id)
        )
        return res.scalar_one_or_none() is not None

    async def append_message(
        self, session_id: UUID, role: str, content: str, meta: Optional[dict] = None
    ) -> UUID:
        await self._scope()
        mid = uuid4()
        msg = self._ChatMessage(id=mid, session_id=session_id, role=role, content=content, meta=meta)
        self._s.add(msg)
        await self._s.commit()
        return mid

    async def fetch_recent_messages(self, session_id: UUID, limit: int) -> list[dict]:
        await self._scope()
        res = await self._s.execute(
            select(self._ChatMessage)
            .where(self._ChatMessage.session_id == session_id)
            .order_by(self._ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = list(res.scalars())
        rows.reverse()  # oldest→newest for context
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "created_at": r.created_at,
            }
            for r in rows
        ]

    async def list_sessions(self, limit: int = 50, before: Optional[datetime] = None) -> list[dict]:
        await self._scope()
        q = select(self._ChatSession).order_by(self._ChatSession.created_at.desc()).limit(limit)
        if before is not None:
            q = q.where(self._ChatSession.created_at < before)
        res = await self._s.execute(q)
        rows = list(res.scalars())
        return [{"id": r.id, "created_at": r.created_at, "name": r.name} for r in rows]

    async def fetch_session_messages(
        self, session_id: UUID, limit: int = 100, before: Optional[UUID] = None
    ) -> list[dict]:
        await self._scope()
        q = select(self._ChatMessage).where(self._ChatMessage.session_id == session_id)

        if before is not None:
            # Find the timestamp of the 'before' message for pagination
            res0 = await self._s.execute(
                select(self._ChatMessage.created_at).where(self._ChatMessage.id == before)
            )
            ts = res0.scalar_one_or_none()
            if ts is not None:
                q = q.where(self._ChatMessage.created_at < ts)

        q = q.order_by(self._ChatMessage.created_at.desc()).limit(limit)
        res = await self._s.execute(q)
        rows = list(res.scalars())
        rows.reverse()
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "created_at": r.created_at,
            }
            for r in rows
        ]
