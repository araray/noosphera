# FILE: noosphera/api_server/models/models.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    context_window: Optional[int] = None
    family: Optional[str] = None
    streaming: Optional[bool] = None


class ModelListResponse(BaseModel):
    """
    provider -> models[] mapping
    """
    models: dict[str, list[ModelInfo]]
