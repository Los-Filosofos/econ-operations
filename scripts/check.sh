#!/usr/bin/env sh
# Ruff, format check and pytest for apps/api. Pass --container to also build the image.
set -eu
project="$(cd "$(dirname "$0")/../apps/api" && pwd)"
uv sync --project "$project" --locked
uv run --directory "$project" ruff check .
uv run --directory "$project" ruff format --check .
DATABASE_URL='sqlite://' ALLOW_LIVE_READS='false' uv run --directory "$project" pytest
if [ "${1:-}" = "--container" ]; then
    docker build -t econ-hub:check "$project"
fi
