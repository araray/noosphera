# FILE: noosphera/api_server/deps.py
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.schema import Settings
from ..db.session import get_session
from ..security.auth import AuthContext, require_api_key

# NEW: chat service factory bits
from ..repositories.chat_repository import ChatRepository
from ..services.chat_service import ChatService
from ..ports.llm import MockLLM


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


async def get_chat_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """
    Construct a ChatService scoped to the current tenant.
    LLM: MockLLM if settings.chat.mock_llm_enabled; otherwise placeholder.
    """
    # Tenant model is attached by require_api_key
    tenant = getattr(request.state, "tenant", None)
    if tenant is None or not getattr(tenant, "db_schema_name", None):
        raise RuntimeError("Tenant context missing or invalid")

    schema: str = tenant.db_schema_name
    repo = ChatRepository(session=db, schema=schema)

    # For Step 1.4, only MockLLM is wired.
    llm = MockLLM() if settings.chat.mock_llm_enabled else MockLLM()

    return ChatService(repo=repo, llm=llm, settings=settings, schema=schema)
