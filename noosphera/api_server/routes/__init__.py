# FILE: noosphera/api_server/routes/__init__.py
from .health import health_router
from .chat import chat_router  # NEW
from .models import models_router  # NEW
from .system import system_router  # NEW (1.6)

__all__ = ["health_router", "chat_router", "models_router", "system_router"]
