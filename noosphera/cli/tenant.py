from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from uuid import UUID

from ..config.loader import load_settings
from ..db.engine import get_admin_engine, get_app_engine, init_engines, run_core_migrations
from ..services.tenant_manager import TenantManager


def _print_tenant(t) -> None:
    print(
        f"{t.id}  name={t.name}  status={t.status.value}  schema={t.db_schema_name}  created_at={t.created_at.isoformat()}"
    )


async def _ensure_ready() -> TenantManager:
    settings = load_settings()
    await init_engines(settings)
    await run_core_migrations(settings)  # idempotent
    return TenantManager(get_admin_engine(), get_app_engine())


async def _cmd_create_tenant(name: str) -> int:
    tm = await _ensure_ready()
    t = await tm.create_tenant(name)
    print("TENANT CREATED")
    _print_tenant(t)
    return 0


async def _cmd_list_tenants() -> int:
    tm = await _ensure_ready()
    ts = await tm.list_tenants()
    print("TENANTS")
    for t in ts:
        _print_tenant(t)
    return 0


async def _cmd_create_key(tenant: UUID, name: str | None, expires: str | None) -> int:
    tm = await _ensure_ready()
    expires_at = datetime.fromisoformat(expires) if expires else None
    token = await tm.create_api_key(tenant, name=name, expires_at=expires_at)
    print("API KEY (store this securely; it will not be shown again):")
    print(token)
    return 0


async def _cmd_revoke_key(prefix: str) -> int:
    tm = await _ensure_ready()
    await tm.revoke_api_key(prefix)
    print(f"API KEY REVOKED: {prefix}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="noosphera-tenant", description="Tenant admin CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ct = sub.add_parser("create-tenant", help="Create a tenant")
    p_ct.add_argument("--name", required=True)

    sub.add_parser("list-tenants", help="List tenants")

    p_ck = sub.add_parser("create-key", help="Create an API key for a tenant")
    p_ck.add_argument("--tenant", required=True, type=UUID)
    p_ck.add_argument("--name", required=False, default=None)
    p_ck.add_argument("--expires", required=False, default=None, help="ISO date/time (e.g., 2025-12-31T23:59:00+00:00)")

    p_rk = sub.add_parser("revoke-key", help="Revoke an API key by prefix")
    p_rk.add_argument("--prefix", required=True)

    args = p.parse_args(argv)

    if args.cmd == "create-tenant":
        return asyncio.run(_cmd_create_tenant(args.name))
    if args.cmd == "list-tenants":
        return asyncio.run(_cmd_list_tenants())
    if args.cmd == "create-key":
        return asyncio.run(_cmd_create_key(args.tenant, args.name, args.expires))
    if args.cmd == "revoke-key":
        return asyncio.run(_cmd_revoke_key(args.prefix))

    print("Unknown command")
    return 2
