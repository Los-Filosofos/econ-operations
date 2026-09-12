param([switch]$Container)
$ErrorActionPreference = 'Stop'
$projectPath = Join-Path $PSScriptRoot '..\apps\api'
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
if ($Container) {
    docker build -t econ-hub:check $projectPath
    exit $LASTEXITCODE
}
