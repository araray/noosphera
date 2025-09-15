# RATIONALE:
# - Implements API-key auth dependency per Step 1.3.
# - Delegates crypto/verification to TenantManager (prefix+bcrypt).
# - Binds tenant context on success; maps suspended tenants to 403.
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
    Reserved fields (roles/scopes) come in later phases.
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

    Note: We intentionally do NOT log plaintext tokens.
    """
    # 1) resolve header name from runtime settings attached by app factory
    try:
        header_name: str = request.app.state.settings.security.api_key_header  # type: ignore[attr-defined]
    except Exception:
        # Defensive default to keep service usable if settings not yet wired
        header_name = "X-Noosphera-API-Key"

    token = request.headers.get(header_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # 2) verify via TenantManager
    tm: TenantManager = request.app.state.tenant_manager  # type: ignore[attr-defined]
    try:
        tenant, key = await tm.verify_api_key(token)
    except PermissionError:
        # Best-effort mapping to 403 if tenant is suspended:
        # If we can parse prefix and find a non-active tenant bound to it, return 403.
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
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tenant suspended",
                    )
        except HTTPException:
            raise
        except Exception:
            # fall through to generic 401
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    except ValueError:
        # Malformed token format
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # 3) success: bind to request context and return an AuthContext
    request.state.tenant = tenant
    request.state.api_key = key
    return AuthContext(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        key_prefix=key.key_prefix,
        api_key_id=key.id,
    )
