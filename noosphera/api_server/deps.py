from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.schema import Settings
from ..db.session import get_session
from ..security.auth import AuthContext, require_api_key


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


async def get_current_tenant(ctx: AuthContext = Depends(require_api_key)) -> AuthContext:
    """
    Convenience dependency to obtain the authenticated tenant context.
    """
    return ctx
