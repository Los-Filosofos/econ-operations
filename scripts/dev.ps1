param([int]$Port = 8050)
$ErrorActionPreference = 'Stop'
$projectPath = Join-Path $PSScriptRoot '..\apps\api'
uv run --directory $projectPath uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
exit $LASTEXITCODE
