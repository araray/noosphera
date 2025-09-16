# FILE: noosphera/api_server/main.py
from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader

from ..config.loader import load_settings
from ..config.schema import Settings
from ..db.engine import dispose_engines, get_admin_engine, get_app_engine, init_engines, run_core_migrations
from ..observability.logging import setup_logging
from ..services.tenant_manager import TenantManager
from ..security.security_schemes import api_key_scheme
from .routes import health_router, chat_router, models_router  # NEW


def _enable_openapi_api_key(app: FastAPI, header_name: str) -> None:
    key_header = api_key_scheme(header_name)

    def custom_openapi() -> dict[str, Any]:  # pragma: no cover (docs shape only)
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Noosphera API",
            version="1.0.0",
            description="Noosphera API",
            routes=app.routes,
        )
        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
        openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": header_name,
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[assignment]


def create_app() -> FastAPI:
    settings: Settings = load_settings()

    # Logging bootstrap
    setup_logging(level=settings.logging.level, json=settings.logging.json)

    app = FastAPI(title="Noosphera", version="0.1.4")

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
    from ..security.auth import require_api_key  # local import to avoid cycles
    protected_deps = [Depends(require_api_key)] if app.state.settings.features.auth_enabled else []

    # Public system endpoints (health is explicitly public in 1.1)
    app.include_router(health_router, prefix="/api/v1", tags=["system"])

    # When auth is enabled, expose API-key scheme in Swagger (ergonomics)
    if app.state.settings.features.auth_enabled:
        _enable_openapi_api_key(app, app.state.settings.security.api_key_header)

    # Chat routes (protected)
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"], dependencies=protected_deps)

    # NEW: Models listing (protected)
    app.include_router(models_router, prefix="/api/v1", tags=["models"], dependencies=protected_deps)

    return app
