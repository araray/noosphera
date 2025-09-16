# FILE: noosphera/api_server/deps.py
import logging
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.schema import Settings
from ..db.session import get_session
from ..security.auth import AuthContext, require_api_key

# chat service factory bits
from ..repositories.chat_repository import ChatRepository
from ..services.chat_service import ChatService
from ..ports.llm import MockLLM
from ..ports.llm_provider_adapter import ProviderBackedLLM
from ..providers.manager import ProviderManager


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


def get_logger() -> logging.Logger:
    """
    Provide a module-level logger to DI without coupling to specific impls.
    """
    return logging.getLogger("noosphera")


def get_provider_manager(
    cfg: Settings = Depends(get_settings),
    logger: logging.Logger = Depends(get_logger),
) -> ProviderManager:
    """
    Construct a ProviderManager for routing chat calls to concrete providers.
    """
    return ProviderManager(cfg, logger)


async def get_chat_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    pm: ProviderManager = Depends(get_provider_manager),
) -> ChatService:
    """
    Construct a ChatService scoped to the current tenant.
    Chooses LLM adapter based on config toggles.
    """
    # Tenant model is attached by require_api_key
    tenant = getattr(request.state, "tenant", None)
    if tenant is None or not getattr(tenant, "db_schema_name", None):
        raise RuntimeError("Tenant context missing or invalid")

    schema: str = tenant.db_schema_name
    repo = ChatRepository(session=db, schema=schema)

    if settings.chat.mock_llm_enabled:
        llm = MockLLM()
    elif settings.providers.enabled:
        llm = ProviderBackedLLM(pm, settings.providers.default_model or None)
    else:
        llm = MockLLM()  # conservative fallback

    return ChatService(repo=repo, llm=llm, settings=settings, schema=schema)
