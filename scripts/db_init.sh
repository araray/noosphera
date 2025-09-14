#!/usr/bin/env bash
set -euo pipefail

# Programmatic migration runner (no alembic.ini required).
# Uses NOOSPHERA_DATABASE_ADMIN_URL if present, else NOOSPHERA_DATABASE_URL.

python - <<'PYCODE'
import asyncio
from noosphera.config.loader import load_settings
from noosphera.db.engine import run_core_migrations

async def main():
    settings = load_settings()
    await run_core_migrations(settings)

asyncio.run(main())
PYCODE
