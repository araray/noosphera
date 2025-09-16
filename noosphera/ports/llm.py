# FILE: noosphera/ports/llm.py
from __future__ import annotations

from typing import Protocol


class ChatLLMPort(Protocol):
    async def chat(
        self,
        *,
        messages: list[dict],
        model: str | None = None,
        provider: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        request_id: str | None = None,
    ) -> dict:
        """
        Given a list of messages [{"role": "...", "content": "..."}], produce assistant reply.
        Returns:
          {
            "role": "assistant",
            "content": "...",
            "model": "<model-used>",
            "provider": "<provider-used>",
            "usage": {...} | None,
            "meta": {...} | None
          }
        """
        raise NotImplementedError("ChatLLMPort.chat must be implemented by adapters")


class MockLLM:
    """
    Deterministic mock: replies with an echo of the last user message (or last message if none).
    """

    async def chat(
        self,
        *,
        messages: list[dict],
        model: str | None = None,
        provider: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        request_id: str | None = None,
    ) -> dict:
        last_user = None
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m
                break
        target = (last_user or (messages[-1] if messages else {"content": ""})).get("content", "")
        return {
            "role": "assistant",
            "content": f"Echo: {target}",
            "model": model or "mock-model",
            "provider": provider or "mock",
            "usage": None,
            "meta": {"provider": provider or "mock", "model": model or "mock-model"},
        }
