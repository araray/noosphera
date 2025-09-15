# FILE: noosphera/db/models/tenant_chat.py
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class _Base(DeclarativeBase):
    pass


@lru_cache(maxsize=256)
def get_chat_models(schema: str) -> Tuple[type[_Base], type, type]:
    """
    Return ORM Base and model classes bound to a specific tenant schema.
    Cached per schema to avoid recreating classes.
    """

    class Base(_Base):
        __abstract__ = True

    class ChatSession(Base):
        __tablename__ = "chat_sessions"
        __table_args__ = ({"schema": schema},)

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )
        name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

        messages: Mapped[list["ChatMessage"]] = relationship(
            back_populates="session", cascade="all, delete-orphan"
        )

    class ChatMessage(Base):
        __tablename__ = "chat_messages"
        __table_args__ = (
            UniqueConstraint("id", name="uq_chat_messages_id"),
            {"schema": schema},
        )

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
        session_id: Mapped[UUID] = mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey(f'{schema}.chat_sessions.id', ondelete="CASCADE"),
            nullable=False,
        )
        role: Mapped[str] = mapped_column(String(length=16), nullable=False)  # system|user|assistant
        content: Mapped[str] = mapped_column(Text, nullable=False)
        meta: Mapped[Optional[dict]] = mapped_column(PG_JSONB, nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )

        session: Mapped[ChatSession] = relationship(back_populates="messages")

    return Base, ChatSession, ChatMessage
