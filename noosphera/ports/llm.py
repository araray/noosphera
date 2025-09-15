# FILE: noosphera/ports/llm.py
from __future__ import annotations

from typing import Protocol, List, Dict, Any


class ChatLLMPort(Protocol):
    async def chat(self, *, messages: list[dict], model: str | None = None, provider: str | None = None) -> dict:
        """
        Given a list of messages [{"role": "...", "content": "..."}], produce assistant reply:
        Returns: {"role": "assistant", "content": "...", "meta": {...}?}
        """
        ...


class MockLLM:
    """
    Deterministic mock: replies with an echo of the last user message (or last message if none).
    """

    async def chat(self, *, messages: list[dict], model: str | None = None, provider: str | None = None) -> dict:
        last_user = None
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m
                break
        target = (last_user or (messages[-1] if messages else {"content": ""})).get("content", "")
        return {"role": "assistant", "content": f"Echo: {target}"}
