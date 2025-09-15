# FILE: noosphera/api_server/models/chat.py
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, constr


class ChatMessageIn(BaseModel):
    role: Literal["user", "system"]
    content: constr(strip_whitespace=True, min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: ChatMessageIn
    model: Optional[str] = None
    provider: Optional[str] = None


class ChatReply(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatResponse(BaseModel):
    session_id: UUID
    reply: ChatReply


class ChatSessionSummary(BaseModel):
    id: UUID
    created_at: datetime
    name: Optional[str] = None


class ChatMessageOut(BaseModel):
    id: UUID
    role: Literal["system", "user", "assistant"]
    content: str
    created_at: datetime
