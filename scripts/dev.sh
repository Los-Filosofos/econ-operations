#!/usr/bin/env sh
# Local Dash + FastAPI server with reload. Usage: scripts/dev.sh [port]
# Needs SESSION_SECRET in apps/api/.env (or AUTH_REQUIRED=false for development only).
set -eu
project="$(cd "$(dirname "$0")/../apps/api" && pwd)"
port="${1:-8050}"
exec uv run --directory "$project" uvicorn app.main:app --host 127.0.0.1 --port "$port" --reload
