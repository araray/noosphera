#!/usr/bin/env bash
set -euo pipefail

# Load .env into environment (non-destructive to existing env vars)
if [ -f ".env" ]; then
  # shellcheck disable=SC2046
  set -a
  . ".env"
  set +a
fi

HOST="${NOOSPHERA_SERVER_HOST:-0.0.0.0}"
PORT="${NOOSPHERA_SERVER_PORT:-8000}"

exec uvicorn noosphera.api_server.asgi:app --host "${HOST}" --port "${PORT}" --reload
