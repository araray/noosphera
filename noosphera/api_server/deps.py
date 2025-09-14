from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.schema import Settings
from ..db.session import get_session


def get_settings(request: Request) -> Settings:
    """
    FastAPI dependency to access the merged, typed settings
    stored on the app state.
    """
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_db() -> AsyncSession:
    """
    FastAPI dependency to access a request-scoped database session.
    """
    async with get_session() as s:
        yield s
