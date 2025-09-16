# FILE: noosphera/providers/openai.py
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from ..config.schema import OpenAISettings
from .base import BaseProvider, ProviderChatResult, ModelInfo

log = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    Minimal HTTP client for OpenAI-compatible Chat Completions (no SDK).
    """

    def __init__(self, cfg: OpenAISettings) -> None:
        self._cfg = cfg
        self._base = cfg.base_url.rstrip("/")
        self._timeout = cfg.request_timeout_s

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
        }
        if self._cfg.api_key:
            h["Authorization"] = f"Bearer {self._cfg.api_key}"
        if self._cfg.organization:
            h["OpenAI-Organization"] = self._cfg.organization
        return h

    async def chat(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderChatResult:
        if not self._cfg.enabled:
            raise RuntimeError("OpenAI provider is disabled by configuration")
        if not self._cfg.api_key:
            raise RuntimeError("OpenAI API key is not configured")

        url = f"{self._base}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        # Never log prompts in Step 1.5 (conservative default)
        log.debug("openai.chat request model=%s", model)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract first choice
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI chat: no choices in response")
        msg = choices[0].get("message") or {}
        content = msg.get("content", "")

        usage = data.get("usage")
        model_name = data.get("model") or model

        return ProviderChatResult(
            text=content,
            model=model_name,
            provider="openai",
            usage=usage,
            raw=data,
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self._cfg.enabled:
            return []
        url = f"{self._base}/models"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
            items = []
            for it in data.get("data", []):
                name = it.get("id")
                if name:
                    items.append(ModelInfo(name=name, family=None, streaming=True))
            return items
        except Exception as exc:
            # Non-fatal; return default model if configured
            log.warning("openai.list_models failed: %s", exc)
            if self._cfg.default_model:
                return [ModelInfo(name=self._cfg.default_model, streaming=True)]
            return []
