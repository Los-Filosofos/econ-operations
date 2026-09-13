param([switch]$Container)
# Ruff, format check, pytest and the two documentation checks for apps/api.
# With ECON_TEST_POSTGRES_URL / ECON_TEST_POSTGRES_MIGRATIONS_URL defined, the PostgreSQL
# tests run (and fail if the database does not answer); without them they are skipped.
$ErrorActionPreference = 'Stop'
$rootPath = Join-Path $PSScriptRoot '..'
$projectPath = Join-Path $rootPath 'apps\api'
uv sync --project $projectPath --locked
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --directory $projectPath ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --directory $projectPath ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$previousDatabase = $env:DATABASE_URL
$previousLive = $env:ALLOW_LIVE_READS
try {
    $env:DATABASE_URL = 'sqlite://'
    $env:ALLOW_LIVE_READS = 'false'
    uv run --directory $projectPath pytest
    $testExit = $LASTEXITCODE
} finally {
    $env:DATABASE_URL = $previousDatabase
    $env:ALLOW_LIVE_READS = $previousLive
}
if ($testExit -ne 0) { exit $testExit }
# RF-01: the generated dictionary must match the declared models.
uv run --project $projectPath python (Join-Path $rootPath 'scripts\docs\generar_diccionario.py') --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# RNF-02: CSV/XLSX exports must match the Markdown matrices (stdlib + pinned openpyxl).
uv run --no-project --with openpyxl==3.1.5 python (Join-Path $rootPath 'scripts\docs\exportar_matrices.py') --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# RNF-02: the ENTREGABLES spreadsheets must match each deliverable's Markdown table.
uv run --no-project --with openpyxl==3.1.5 python (Join-Path $rootPath 'scripts\docs\exportar_entregables.py') --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Container) {
    docker build -t econ-hub:check $projectPath
    exit $LASTEXITCODE
}
