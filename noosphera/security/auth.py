# RATIONALE:
# Step 1.3 auth dependency: parse header -> verify token (prefix+bcrypt via TenantManager)
# -> bind tenant context -> 401/403 mapping. Keep header name configurable via settings.
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from ..db.models.core import ApiKey, Tenant, TenantStatus
from ..db.session import get_session
from ..services.tenant_manager import TenantManager


class AuthContext(BaseModel):
    """
    Minimal request auth context for downstream dependencies/handlers.
    Reserved fields (roles/scopes) can be added later.
    """
    tenant_id: UUID
    tenant_name: str
    key_prefix: str
    api_key_id: Optional[UUID] = None


def _parse_token(token: str) -> tuple[str, str]:
    """
    Parse `ns_<prefix>_<secret>` and return (prefix, secret).
    Raises ValueError on invalid format.
    """
    if not token or not token.startswith("ns_"):
        raise ValueError("Invalid token format")
    parts = token.split("_", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise ValueError("Invalid token format")
    return parts[1], parts[2]


async def require_api_key(request: Request) -> AuthContext:
    """
    Enforce API-key auth:
      1) Read header from settings.security.api_key_header.
      2) Verify via TenantManager.verify_api_key(token).
      3) On success: attach tenant/key to request.state, return AuthContext.
      4) On failure: 401; if tenant is suspended for that key prefix: 403.

    Note: Do NOT log plaintext tokens.
    """
    # Header name from runtime settings; defensive default if missing
    try:
        header_name: str = request.app.state.settings.security.api_key_header  # type: ignore[attr-defined]
    except Exception:
        header_name = "X-Noosphera-API-Key"

    token = request.headers.get(header_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    tm: TenantManager = request.app.state.tenant_manager  # type: ignore[attr-defined]
    try:
        tenant, key = await tm.verify_api_key(token)
    except PermissionError:
        # Map suspended tenants (by prefix) to 403; otherwise 401.
        try:
            prefix, _ = _parse_token(token)
            async with get_session() as s:
                res = await s.execute(
                    select(Tenant.status)
                    .select_from(ApiKey)
                    .join(Tenant, Tenant.id == ApiKey.tenant_id)
                    .where(ApiKey.key_prefix == prefix)
                )
                row = res.first()
                if row and row[0] != TenantStatus.active:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant suspended")
        except HTTPException:
            raise
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Success: bind to request context
    request.state.tenant = tenant
    request.state.api_key = key
    return AuthContext(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        key_prefix=key.key_prefix,
        api_key_id=key.id,
    )
