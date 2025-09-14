from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ..db.models.core import ApiKey, KeyStatus, Tenant, TenantStatus
from ..db.session import get_session
from ..db.tenancy import create_tenant_schema
from ..security.crypto import hash_secret, verify_secret


def _gen_prefix(n: int = 8) -> str:
    # 8 hex chars: 32 bits of entropy, easy to read/copy, index-friendly
    return secrets.token_hex(n // 2)


def _gen_secret(nbytes: int = 24) -> str:
    # ~32 chars URL-safe; adjust as needed
    return secrets.token_urlsafe(nbytes)


@dataclass(slots=True)
class _ParsedToken:
    prefix: str
    secret: str


def _parse_token(token: str) -> _ParsedToken:
    # Format: ns_<prefix>_<secret>
    if not token.startswith("ns_"):
        raise ValueError("Invalid token format")
    try:
        _, prefix, secret = token.split("_", 2)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc
    if not prefix or not secret:
        raise ValueError("Invalid token format")
    return _ParsedToken(prefix=prefix, secret=secret)


class TenantManager:
    """
    Service for tenant lifecycle and API key issuance/verification.
    """

    def __init__(self, admin_engine: AsyncEngine, app_engine: AsyncEngine) -> None:
        self._admin_engine = admin_engine
        self._app_engine = app_engine

    async def create_tenant(self, name: str) -> Tenant:
        """
        Create a tenant entry and provision its isolated schema (t_<uuid>).
        """
        tenant_id = uuid4()
        schema = f"t_{tenant_id.hex}"

        # 1) DDL: ensure tenant schema exists (admin engine)
        await create_tenant_schema(self._admin_engine, schema)

        # 2) Control-plane row in core.tenants (app engine)
        async with get_session() as s:
            tenant = Tenant(id=tenant_id, name=name, db_schema_name=schema, status=TenantStatus.active)
            s.add(tenant)
            await s.commit()
            await s.refresh(tenant)
            return tenant

    async def list_tenants(self) -> list[Tenant]:
        async with get_session() as s:
            res = await s.execute(select(Tenant).order_by(Tenant.created_at.asc()))
            return list(res.scalars())

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        async with get_session() as s:
            res = await s.execute(select(Tenant).where(Tenant.id == tenant_id))
            t = res.scalar_one_or_none()
            if not t:
                raise LookupError(f"Tenant not found: {tenant_id}")
            return t

    async def create_api_key(
        self, tenant_id: UUID, *, name: Optional[str] = None, expires_at: Optional[datetime] = None
    ) -> str:
        """
        Create a new API key for the tenant. Returns the *plaintext* token once.

        Storage: only (key_prefix, bcrypt(key_secret)) are persisted.
        """
        prefix = _gen_prefix()
        secret = _gen_secret()
        token = f"ns_{prefix}_{secret}"

        hashed = await hash_secret(secret)

        async with get_session() as s:
            # Ensure tenant exists and active
            res = await s.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.status == TenantStatus.active))
            tenant = res.scalar_one_or_none()
            if not tenant:
                raise LookupError(f"Active tenant not found: {tenant_id}")

            key = ApiKey(
                tenant_id=tenant_id,
                key_prefix=prefix,
                key_hash=hashed,
                name=name,
                status=KeyStatus.active,
                expires_at=expires_at,
            )
            s.add(key)
            await s.commit()
        return token

    async def revoke_api_key(self, key_prefix: str) -> None:
        async with get_session() as s:
            await s.execute(
                update(ApiKey)
                .where(ApiKey.key_prefix == key_prefix, ApiKey.status == KeyStatus.active)
                .values(status=KeyStatus.revoked)
            )
            await s.commit()

    async def verify_api_key(self, token: str) -> tuple[Tenant, ApiKey]:
        """
        Verify an API token. Returns (Tenant, ApiKey) if valid & active; raises otherwise.
        """
        parsed = _parse_token(token)

        async with get_session() as s:
            res = await s.execute(
                select(ApiKey, Tenant)
                .join(Tenant, Tenant.id == ApiKey.tenant_id)
                .where(
                    ApiKey.key_prefix == parsed.prefix,
                    ApiKey.status == KeyStatus.active,
                    Tenant.status == TenantStatus.active,
                )
            )
            row = res.first()
            if not row:
                raise PermissionError("Invalid or revoked API key")

            key: ApiKey = row[0]
            tenant: Tenant = row[1]

            # Check expiry if set
            if key.expires_at and key.expires_at < datetime.utcnow().astimezone(key.expires_at.tzinfo):
                raise PermissionError("API key expired")

            ok = await verify_secret(parsed.secret, key.key_hash)
            if not ok:
                raise PermissionError("Invalid API key")

            # best-effort touch
            key.last_used_at = datetime.utcnow()
            s.add(key)
            await s.commit()

            return tenant, key
