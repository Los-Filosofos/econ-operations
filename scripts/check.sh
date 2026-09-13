#!/usr/bin/env sh
# Ruff, format check, pytest and the two documentation checks for apps/api.
# Pass --container to also build the image.
# With ECON_TEST_POSTGRES_URL / ECON_TEST_POSTGRES_MIGRATIONS_URL defined, the PostgreSQL
# tests run (and fail if the database does not answer); without them they are skipped.
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
project="$root/apps/api"
uv sync --project "$project" --locked
uv run --directory "$project" ruff check .
uv run --directory "$project" ruff format --check .
DATABASE_URL='sqlite://' ALLOW_LIVE_READS='false' uv run --directory "$project" pytest
# RF-01: the generated dictionary must match the declared models.
uv run --project "$project" python "$root/scripts/docs/generar_diccionario.py" --check
# RNF-02: CSV/XLSX exports must match the Markdown matrices (stdlib + pinned openpyxl).
uv run --no-project --with openpyxl==3.1.5 python "$root/scripts/docs/exportar_matrices.py" --check
# RNF-02: the ENTREGABLES spreadsheets must match each deliverable's Markdown table.
uv run --no-project --with openpyxl==3.1.5 python "$root/scripts/docs/exportar_entregables.py" --check
if [ "${1:-}" = "--container" ]; then
    docker build -t econ-hub:check "$project"
fi
