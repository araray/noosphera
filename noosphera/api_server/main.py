# FILE: noosphera/api_server/main.py
from __future__ import annotations

from fastapi import FastAPI, Depends

from ..config.loader import load_settings
from ..config.schema import Settings
from ..observability.logging import setup_logging
from .routes import health_router, chat_router  # MOD

# DB engine & tenant manager initialization
from ..db.engine import init_engines, dispose_engines, get_admin_engine, get_app_engine, run_core_migrations
from ..services.tenant_manager import TenantManager
from ..security.auth import require_api_key  # NEW

def _enable_openapi_api_key(app: FastAPI, header_name: str) -> None:
    """
    Register an OpenAPI security scheme so Swagger shows the API key header.
    Docs-only; runtime enforcement is handled by require_api_key.
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Noosphera",
            version="0.1.0",
            routes=app.routes,
        )
        components = openapi_schema.get("components", {})
        components.setdefault("securitySchemes", {})
        components["securitySchemes"]["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": header_name,
        }
        openapi_schema["components"] = components
        openapi_schema["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

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
        # Step 1.2: Initialize database engines & run core migrations
        await init_engines(settings)
        await run_core_migrations(settings)
        app.state.tenant_manager = TenantManager(get_admin_engine(), get_app_engine())
        return None

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        # Step 1.2: Dispose DB engines
        await dispose_engines()
        return None

    # Determine protected dependencies (Step 1.3)
    protected_deps = [Depends(require_api_key)] if app.state.settings.features.auth_enabled else []

    # Public system endpoints (health is explicitly public in 1.1)
    app.include_router(health_router, prefix="/api/v1", tags=["system"])

    # When auth is enabled, expose API-key scheme in Swagger (ergonomics)
    if app.state.settings.features.auth_enabled:
        _enable_openapi_api_key(app, app.state.settings.security.api_key_header)

    # NEW (Step 1.4): Chat routes (protected)
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"], dependencies=protected_deps)

    # NOTE: Future routers (sessions/providers/etc.) must be included with:
    # app.include_router(chat_router, prefix="/api/v1", dependencies=protected_deps)
    # app.include_router(models_router, prefix="/api/v1", dependencies=protected_deps)

    return app
