# RATIONALE:
# - Provide OpenAPI security helper as required by the dossier.
# - Not strictly enforced at runtime; enables correct header hint in docs.
from __future__ import annotations

from fastapi.security import APIKeyHeader


def api_key_scheme(header_name: str) -> APIKeyHeader:
    """
    Construct an APIKeyHeader security scheme with the configured header name.
    auto_error=False so our dependency can surface precise 401/403 messages.
    """
    return APIKeyHeader(name=header_name, auto_error=False)
