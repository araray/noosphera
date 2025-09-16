# FILE: noosphera/providers/base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Sequence


@dataclass(slots=True)
class ModelInfo:
    """
    Lightweight model descriptor unified across providers.
    """
    name: str
    context_window: Optional[int] = None
    family: Optional[str] = None
    streaming: Optional[bool] = None


@dataclass(slots=True)
class ProviderChatResult:
    """
    Normalized non-streaming chat result.
    """
    text: str
    model: str
    provider: str
    usage: Optional[dict] = None
    raw: Optional[dict] = None


class BaseProvider(Protocol):
    """
    Provider contract for Step 1.5 (no streaming).
    """

    async def chat(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ProviderChatResult:
        """
        Execute a chat completion and return a unified result.
        """
        raise NotImplementedError("Provider.chat() must be implemented")

    async def list_models(self) -> list[ModelInfo]:
        """
        Return available models for this provider.
        """
        raise NotImplementedError("Provider.list_models() must be implemented")

    def count_tokens(self, messages: Sequence[dict], model: str) -> Optional[int]:  # optional
        """
        (Optional) Estimate tokens for the given messages/model.
        Step 1.5: may return None.
        """
        return None
