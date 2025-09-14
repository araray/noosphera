from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .engine import get_app_engine

_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def _ensure_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return _session_maker


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Async dependency/utility that yields a request-scoped AsyncSession bound to the app engine.
    """
    engine = get_app_engine()
    maker = _ensure_sessionmaker(engine)
    async with maker() as s:
        yield s
