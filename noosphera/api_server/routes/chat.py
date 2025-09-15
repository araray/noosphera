# FILE: noosphera/api_server/routes/chat.py
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    ChatMessageOut,
)
from ..deps import get_current_tenant, get_db, get_settings, get_chat_service
from ...config.schema import Settings
from ...security.auth import AuthContext
from ...services.chat_service import ChatService
from ...db.engine import get_admin_engine

chat_router = APIRouter()


@chat_router.post("/chat", response_model=ChatResponse, summary="Create/continue a session and get assistant reply")
async def post_chat(
    req: ChatRequest,
    request: Request,
    ctx: AuthContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    svc: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    # 1) ensure per-tenant tables
    await svc.ensure_bootstrap(get_admin_engine())

    # 2) ensure/resolve session
    session_id = await svc.ensure_session(req.session_id)

    # 3) run turn
    reply = await svc.run_turn(
        session_id,
        incoming_role=req.message.role,
        incoming_text=req.message.content,
        model=req.model,
        provider=req.provider,
    )

    return ChatResponse(session_id=session_id, reply=reply)  # type: ignore[arg-type]


@chat_router.get("/chat/sessions", response_model=list[ChatSessionSummary], summary="List chat sessions (newest first)")
async def list_chat_sessions(
    request: Request,
    ctx: AuthContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    svc: ChatService = Depends(get_chat_service),
    limit: int = Query(50, ge=1, le=200),
) -> list[ChatSessionSummary]:
    await svc.ensure_bootstrap(get_admin_engine())
    # Simple list; "before" cursor can be added later if needed
    items = await svc._repo.list_sessions(limit=limit)
    return [ChatSessionSummary(**it) for it in items]


@chat_router.get(
    "/chat/sessions/{session_id}",
    response_model=list[ChatMessageOut],
    summary="List messages in a session (ascending)",
)
async def get_session_messages(
    session_id: UUID,
    request: Request,
    ctx: AuthContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    svc: ChatService = Depends(get_chat_service),
    limit: int = Query(100, ge=1, le=500),
    before: Optional[UUID] = Query(None),
) -> list[ChatMessageOut]:
    await svc.ensure_bootstrap(get_admin_engine())
    exists = await svc._repo.get_session_exists(session_id)
    if not exists:
        return []
    rows = await svc._repo.fetch_session_messages(session_id, limit=limit, before=before)
    return [ChatMessageOut(**r) for r in rows]
