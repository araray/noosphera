# FILE: noosphera/services/chat_service.py
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from ..config.schema import Settings
from ..repositories.chat_repository import ChatRepository
from ..db.tenant_chat_bootstrap import ensure_tenant_chat_tables
from ..ports.llm import ChatLLMPort

log = logging.getLogger(__name__)


class ChatService:
    """
    Orchestrates chat flow per tenant/session:
      - bootstrap per-tenant tables
      - ensure/resolve session
      - handle turn: save user -> call LLM -> save assistant -> return
    """

    def __init__(self, repo: ChatRepository, llm: ChatLLMPort, settings: Settings, *, schema: str) -> None:
        self._repo = repo
        self._llm = llm
        self._settings = settings
        self._schema = schema

    async def ensure_bootstrap(self, admin_engine: AsyncEngine) -> None:
        await ensure_tenant_chat_tables(admin_engine, self._schema)

    async def ensure_session(self, session_id: UUID | None, *, name: str | None = None) -> UUID:
        if session_id is None:
            return await self._repo.create_session(name=name)
        exists = await self._repo.get_session_exists(session_id)
        if not exists:
            raise LookupError(f"Session not found: {session_id}")
        return session_id

    async def run_turn(
        self,
        session_id: UUID,
        *,
        incoming_role: str,
        incoming_text: str,
        model: str | None,
        provider: str | None,
    ) -> dict:
        # 1) Load history
        n = int(self._settings.chat.history_max_messages)
        history = await self._repo.fetch_recent_messages(session_id, limit=n)

        # 2) Append incoming
        await self._repo.append_message(session_id, incoming_role, incoming_text)

        # 3) Build context
        msgs = [{"role": m["role"], "content": m["content"]} for m in history]
        msgs.append({"role": incoming_role, "content": incoming_text})

        # 4) LLM call
        reply = await self._llm.chat(messages=msgs, model=model, provider=provider)
        content = reply.get("content", "")

        # 5) Persist assistant
        await self._repo.append_message(session_id, "assistant", content, meta=reply.get("meta"))

        # 6) Observability (Phase-1 minimal)
        log.info(
            "chat_turn",
            extra={
                "tenant_schema": self._schema,
                "session_id": str(session_id),
                "len_history": len(history),
                "model": model,
                "provider": provider,
            },
        )

        return {"role": "assistant", "content": content}
