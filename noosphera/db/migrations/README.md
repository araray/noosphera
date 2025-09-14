# Migrations (Core)

This package contains Alembic migrations for the **control-plane** schema `core`:

- Creates `core` schema and `vector` extension (pgvector).
- Creates `core.tenants` and `core.api_keys` (with enums & indexes).

## Running

You can run migrations **programmatically** (no `alembic.ini` needed):

```bash
python -c 'import asyncio; from noosphera.config.loader import load_settings; from noosphera.db.engine import run_core_migrations; asyncio.run(run_core_migrations(load_settings()))'
```

Or use the helper:

```bash
./scripts/db_init.sh
```

The runner uses **`database.admin_url`** for DDL. Ensure your config/env is set accordingly.
