# FILE: noosphera/api_server/routes/system.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...config.schema import Settings
from ...api_server.deps import get_settings
from ...observability.redaction import redact

system_router = APIRouter()


@system_router.get("/config", summary="Redacted effective config (dev diagnostics)")
async def get_config(settings: Settings = Depends(get_settings)) -> dict:
    if not settings.debug.config_inspect_enabled:
        # Defensive: even if router is mounted accidentally, enforce runtime guard.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Config inspection disabled")
    return {"config": redact(settings.model_dump())}
