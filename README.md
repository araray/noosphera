# Noosphera — Phase 1.1 Scaffold

This repo provides the initial service scaffold:
- **FastAPI** app factory and ASGI entrypoint
- **Confy**-driven layered configuration (defaults → file → `.env` → env vars → overrides)
- Base Pydantic models (Role/Message/Usage)
- Public health endpoint: `GET /api/v1/health`

> Roadmap: DB & Tenants (Step 1.2), Auth (1.3), Sessions (1.4), Providers (1.5), Observability (1.6).

## Quickstart

```bash
# (optional) create venv and install
pip install -e .

# run API (reload for dev)
uvicorn noosphera.api_server.asgi:app --reload
# open: http://127.0.0.1:8000/api/v1/health
# docs: http://127.0.0.1:8000/docs
````

## Configuration (Confy)

**Precedence**: `defaults (repo) < config file < .env < env < overrides`
Defaults live at `noosphera/config/default.toml`. You can supply a config file via
`$NOOSPHERA_CONFIG=/path/to/config.toml` or `-c` in CLI. The `.env` file (if present) is
loaded **non-destructively** (won’t override already-set env vars).
**Env prefix** is `NOOSPHERA` to avoid collisions.

**Env var mapping (Confy rules)**:

* `_` → `.` (nesting)
* `__` → `_` (literal underscore)
  Examples:
* `NOOSPHERA_SERVER_PORT=8081` → `server.port`
* `NOOSPHERA_LOGGING_LEVEL="DEBUG"` → `logging.level`
* `NOOSPHERA_FEATURE_FLAGS__AUTH_ENABLED=true` → `features.auth_enabled`

> See the Confy guide for details.

## Config CLI (skeleton)

```bash
# show merged configuration as JSON
noosphera-conf show

# get a single key (JSON output)
noosphera-conf get server.port

# (in-memory) set a key (Step 1.1); to persist use the confy CLI
noosphera-conf set logging.level "\"DEBUG\""
```

## Healthcheck

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","service":"noosphera"}
```
