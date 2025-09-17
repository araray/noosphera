# Noosphera

This repo provides the initial service scaffold:
- **FastAPI** app factory and ASGI entrypoint
- **Confy**-driven layered configuration (defaults → file → `.env` → env vars → overrides)
- Base Pydantic models (Role/Message/Usage)
- Public health endpoint: `GET /api/v1/health`

> Roadmap: DB & Tenants (Step 1.2), Auth (1.3), Sessions (1.4), Providers (1.5), **Observability (1.6)**.

## Quickstart

```bash
# (optional) create venv and install
pip install -e .

# run API (reload for dev)
uvicorn noosphera.api_server.asgi:app --reload
# open: http://localhost:8000/api/v1/health
# docs: http://localhost:8000/docs
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

---

## Phase 1.2 – Database & Tenants Quickstart

> Requires: PostgreSQL (13+) with `pgvector` extension available.
> The Step 1.2 migration will `CREATE EXTENSION IF NOT EXISTS "vector"` automatically.

1. **Configure DB URLs** (see `.env.example`):

```bash
cp .env.example .env
# edit credentials if needed
```

2. **Initialize database (core schema + tables)**

```bash
./scripts/db_init.sh
```

3. **Create a tenant & issue an API key**

```bash
# Create a tenant
noosphera-tenant create-tenant --name "Acme Corp"

# List tenants
noosphera-tenant list-tenants

# Create an API key (save it; it's shown once)
noosphera-tenant create-key --tenant <TENANT_UUID> --name "server-1"
```

4. **Run API**

```bash
uvicorn noosphera.api_server.asgi:app --reload
```

The app initializes DB engines and runs core migrations on startup. Auth (Step 1.3) will use API keys to protect routes.

---

## Phase 1.3 – API Key Authentication

From this step, Noosphera is **secure by default** (except `/api/v1/health` which remains public).

### Header

* Default header: `X-Noosphera-API-Key` (configurable via `security.api_key_header`).

### Usage

```bash
# Public endpoint (no key required)
curl -i http://localhost:8000/api/v1/health
```

For protected endpoints (added in later steps), include the API key:

```bash
curl -H "X-Noosphera-API-Key: ns_<prefix>_<secret>" http://localhost:8000/api/v1/...
```

### Dev Toggle

To temporarily disable enforcement in dev (not recommended in prod):

```bash
# via env
export NOOSPHERA_FEATURE_FLAGS__AUTH_ENABLED=false

# or in a config file
[features]
auth_enabled = false
```

The header name can be customized:

```toml
[security]
api_key_header = "X-Your-Header"
```

---

## Phase 1.4 – Chat Sessions & Messages (Mock LLM)

This step introduces per‑tenant chat storage and minimal context assembly. Endpoints are **protected** by the API key.

### Config

```toml
[chat]
history_max_messages = 20
mock_llm_enabled = true   # set false when Step 1.5 providers are wired
```

### Endpoints

**Create/continue + reply**

```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Noosphera-API-Key: ns_<prefix>_<secret>' \
  -d '{
        "session_id": null,
        "message": {"role":"user", "content":"Hello there"},
        "model": null,
        "provider": null
      }'
# => {"session_id":"<UUID>","reply":{"role":"assistant","content":"Echo: Hello there"}}
```

**List sessions**

```bash
curl -s -H 'X-Noosphera-API-Key: ns_<prefix>_<secret>' \
  http://localhost:8000/api/v1/chat/sessions
```

**List messages in a session**

```bash
curl -s -H 'X-Noosphera-API-Key: ns_<prefix>_<secret>' \
  "http://localhost:8000/api/v1/chat/sessions/<SESSION_UUID>"
```

> Per‑tenant tables (`chat_sessions`, `chat_messages`) are created lazily on first use.

---

## Phase 1.6 – Observability & Diagnostics

### Request Correlation (Request ID)

* Middleware sets/propagates a **request ID** from `logging.request_id_header` (default `X-Request-ID`).
* The value is returned in the same response header.
* Logs include `correlation_id` and (if authenticated) `tenant_id`.

```bash
curl -i http://localhost:8000/api/v1/health \
  -H 'X-Request-ID: 12345'
# response will include 'X-Request-ID: 12345'
```

### Prometheus Metrics

* Enable/disable with:

```toml
[metrics]
enabled = true
path = "/metrics"
include_tenant_label = false
```

* When enabled, scrape `GET /metrics`.
* **Cardinality caution:** set `include_tenant_label=true` only if tenant count is bounded.

### Tracing (Stub)

```toml
[tracing]
enabled = false
otlp_endpoint = ""
sample_ratio = 0.01
```

> If you install OpenTelemetry packages and set `enabled = true`, the service will initialize a sampler and (optionally) an OTLP exporter endpoint.

### Dev Diagnostics: Redacted Config

* Expose redacted effective config (protected) **only when** enabled:

```toml
[debug]
config_inspect_enabled = true
```

* Then call:

```bash
curl -H "X-Noosphera-API-Key: ns_<prefix>_<secret>" \
  http://localhost:8000/api/v1/config
```

Sensitive keys like `api_key`, `token`, `secret`, `password` are masked.
