# FILE: noosphera/ports/llm_provider_adapter.py
from __future__ import annotations

from typing import Optional

from .llm import ChatLLMPort
from ..providers.manager import ProviderManager


class ProviderBackedLLM(ChatLLMPort):
    """
    Adapter that implements ChatLLMPort by delegating to concrete providers via ProviderManager.
    """

    def __init__(self, provider_manager: ProviderManager, default_model: Optional[str] = None) -> None:
        self._pm = provider_manager
        self._fallback_model = default_model

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
        prov = self._pm.get(provider)
        effective_model = model or self._pm.default_model(provider) or self._fallback_model
        if not effective_model:
            raise RuntimeError("No model specified and no default model configured")

        res = await prov.chat(
            messages=messages,
            model=effective_model,
            temperature=temperature,
            max_tokens=max_tokens,
            request_id=request_id,
        )
        return {
            "role": "assistant",
            "content": res.text,
            "model": res.model,
            "provider": res.provider,
            "usage": res.usage,
            "meta": {"provider": res.provider, "model": res.model, "usage": res.usage},
        }
