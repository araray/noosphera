from __future__ import annotations

from fastapi import FastAPI

from ..config.loader import load_settings
from ..config.schema import Settings
from ..observability.logging import setup_logging
from .routes import health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    App factory: loads Confy-backed settings, configures logging,
    attaches settings to app.state, and includes routers.
    """
    settings = settings or load_settings()
    setup_logging(settings.logging.level, settings.logging.json)

    app = FastAPI(title="Noosphera", version="0.1.0")

    # Single source of truth for runtime config
    app.state.settings = settings

    @app.on_event("startup")
    async def _startup() -> None:
        # Future steps (DB/auth/providers) will initialize here.
        # Step 1.1 intentionally minimal.
        return None

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        # Future teardown hooks.
        return None

    # Public system endpoints (health is explicitly public in 1.1)
    app.include_router(health_router, prefix="/api/v1", tags=["system"])

    return app
