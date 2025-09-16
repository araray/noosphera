# FILE: noosphera/providers/manager.py
from __future__ import annotations

import logging
from typing import Optional

from ..config.schema import ProvidersSettings, OpenAISettings, OllamaSettings, Settings
from .base import BaseProvider, ModelInfo
from .openai import OpenAIProvider
from .ollama import OllamaProvider

log = logging.getLogger(__name__)


class ProviderManager:
    """
    Lazily constructs and caches provider clients based on merged settings.
    """

    def __init__(self, settings: Settings, logger: Optional[logging.Logger] = None) -> None:
        self._cfg = settings.providers
        self._settings = settings
        self._logger = logger or log
        self._cache: dict[str, BaseProvider] = {}

    def _ensure(self, name: str) -> BaseProvider:
        key = name.lower()
        if key in self._cache:
            return self._cache[key]

        # Build from config
        if key == "openai":
            prov_cfg: OpenAISettings = self._cfg.openai
            client = OpenAIProvider(prov_cfg)
        elif key == "ollama":
            prov_cfg: OllamaSettings = self._cfg.ollama
            client = OllamaProvider(prov_cfg)
        else:
            raise ValueError(f"Unknown provider '{name}'")

        self._cache[key] = client
        return client

    def is_enabled(self, name: str) -> bool:
        name = name.lower()
        if name == "openai":
            return self._cfg.openai.enabled
        if name == "ollama":
            return self._cfg.ollama.enabled
        return False

    def get(self, name: Optional[str]) -> BaseProvider:
        """
        Resolve a provider by name; falls back to configured default provider.
        """
        if not self._cfg.enabled:
            raise RuntimeError("Providers are disabled (providers.enabled=false)")
        prov = (name or self._cfg.default_provider).lower()
        if not self.is_enabled(prov):
            raise RuntimeError(f"Provider '{prov}' is not enabled")
        return self._ensure(prov)

    def default_model(self, name: Optional[str]) -> Optional[str]:
        prov = (name or self._cfg.default_provider).lower()
        if prov == "openai":
            return self._cfg.openai.default_model or self._cfg.default_model or None
        if prov == "ollama":
            return self._cfg.ollama.default_model or self._cfg.default_model or None
        return self._cfg.default_model or None

    async def list_models(self, name: Optional[str] = None) -> dict[str, list[ModelInfo]]:
        """
        If name is provided, list models for that provider; else list for all enabled providers.
        """
        if not self._cfg.enabled:
            return {}

        out: dict[str, list[ModelInfo]] = {}
        if name:
            prov = name.lower()
            if self.is_enabled(prov):
                out[prov] = await self._ensure(prov).list_models()
            return out

        # all enabled
        for prov in ("openai", "ollama"):
            if self.is_enabled(prov):
                try:
                    out[prov] = await self._ensure(prov).list_models()
                except Exception as exc:
                    self._logger.warning("list_models(%s) failed: %s", prov, exc)
                    out[prov] = []
        return out
