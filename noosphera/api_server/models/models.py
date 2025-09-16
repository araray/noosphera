# FILE: noosphera/api_server/routes/models.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from ..models.models import ModelListResponse, ModelInfo
from ..deps import get_provider_manager
from ...providers.manager import ProviderManager

models_router = APIRouter()


@models_router.get("/models", response_model=ModelListResponse, summary="List available models")
async def list_models(
    provider: Optional[str] = None,
    pm: ProviderManager = Depends(get_provider_manager),
) -> ModelListResponse:
    data = await pm.list_models(provider)
    # Pydantic coercion
    return ModelListResponse(models={k: [ModelInfo(**mi.__dict__) for mi in v] for k, v in data.items()})
