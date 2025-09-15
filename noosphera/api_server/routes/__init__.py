# FILE: noosphera/api_server/routes/__init__.py
from .health import health_router
from .chat import chat_router  # NEW

__all__ = ["health_router", "chat_router"]
