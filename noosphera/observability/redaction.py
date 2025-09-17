# FILE: noosphera/observability/redaction.py
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence

_SENSITIVE_KEYS = ("api_key", "apikey", "token", "secret", "password", "authorization")


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _SENSITIVE_KEYS)


def redact(obj: Any, mask: str = "***REDACTED***") -> Any:
    """
    Recursively mask sensitive values by key name.
    Preserves types for non-sensitive fields; sequences are redacted element-wise.
    """
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str) and _is_sensitive(k):
                out[k] = mask if v is not None else v
            else:
                out[k] = redact(v, mask=mask)
        return out
    if isinstance(obj, (list, tuple)):
        t = type(obj)
        return t(redact(v, mask=mask) for v in obj)
    return obj
