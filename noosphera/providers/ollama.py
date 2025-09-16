# FILE: noosphera/providers/ollama.py
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from ..config.schema import OllamaSettings
from .base import BaseProvider, ProviderChatResult, ModelInfo

log = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """
    Minimal HTTP client for Ollama local server.
    Prefers /api/chat, falls back to /api/generate (non-streaming).
    """

    def __init__(self, cfg: OllamaSettings) -> None:
        self._cfg = cfg
        self._host = cfg.host.rstrip("/")
        self._timeout = cfg.request_timeout_s

    async def _try_chat_endpoint(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> Optional[ProviderChatResult]:
        url = f"{self._host}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = float(temperature)
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return None  # fallback to /api/generate
            data = resp.json()

        msg = (data or {}).get("message") or {}
        content = msg.get("content", "")
        model_name = data.get("model") or model
        return ProviderChatResult(
            text=content,
            model=model_name,
            provider="ollama",
            usage=None,
            raw=data,
        )

    async def _fallback_generate(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> ProviderChatResult:
        # Naive prompt concat (Phase 1)
        parts = []
        for m in messages:
            parts.append(f"{m.get('role', 'user')}: {m.get('content', '')}")
        prompt = "\n".join(parts)

        url = f"{self._host}/api/generate"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["num_predict"] = int(max_tokens)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = (data or {}).get("response", "")
        model_name = data.get("model") or model
        return ProviderChatResult(
            text=content,
            model=model_name,
            provider="ollama",
            usage=None,
            raw=data,
        )

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
            raise RuntimeError("Ollama provider is disabled by configuration")

        log.debug("ollama.chat request model=%s", model)

        res = await self._try_chat_endpoint(
            messages=messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        if res is not None:
            return res
        return await self._fallback_generate(
            messages=messages, model=model, temperature=temperature, max_tokens=max_tokens
        )

    async def list_models(self) -> list[ModelInfo]:
        if not self._cfg.enabled:
            return []
        url = f"{self._host}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            result: list[ModelInfo] = []
            for it in data.get("models", []):
                name = it.get("name")
                family = None
                details = it.get("details") or {}
                if isinstance(details, dict):
                    family = details.get("family")
                if name:
                    result.append(ModelInfo(name=name, family=family, streaming=True))
            return result
        except Exception as exc:
            log.warning("ollama.list_models failed: %s", exc)
            if self._cfg.default_model:
                return [ModelInfo(name=self._cfg.default_model, streaming=True)]
            return []
