# Desarrollo del hub Python

Dash, Plotly, Dash AG Grid y FastAPI se ejecutan juntos en `apps/api`.
Se usa Python 3.13 y uv; `apps/api/uv.lock` fija las dependencias.

## Preparar y ejecutar

```powershell
uv sync --project apps/api --locked
if (-not (Test-Path -LiteralPath apps/api/.env)) {
    Copy-Item -LiteralPath apps/api/.env.example -Destination apps/api/.env
}
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
.\scripts\dev.ps1
```

La copia conserva los `.env` existentes. Compose conserva `econ-backend`, el
volumen `econ-backend_postgres18_data` y PostgreSQL en `127.0.0.1:54329`.
Las migraciones se ejecutan explícitamente, no al arrancar.

Usar `scripts/dev.ps1 -Port 8051` para otro puerto. En cualquier plataforma:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

| Dirección | Uso |
| --- | --- |
| `http://127.0.0.1:8050` | Panel Dash |
| `/docs` | API y contrato OpenAPI |
| `/api/v1/hub?mode=fixture` | Proyección operativa común |
| `/health/live` | Proceso disponible |
| `/health/ready` | Conexión con la base |

Para una demo temporal sin Docker, usar una terminal PowerShell separada:

```powershell
$env:DATABASE_URL = 'sqlite://'
$env:ALLOW_LIVE_READS = 'false'
.\scripts\dev.ps1
```

Esto no modifica el `.env` ni PostgreSQL. Los fixtures no requieren
almacenamiento; SQLite en memoria permite el control de salud. El historial
persistente de negocio continúa pendiente.

## Estructura

| Ruta en `app/` | Responsabilidad |
| --- | --- |
| `services/hub.py` | Consulta, normalización, relaciones, alertas y cobertura |
| `api/hub.py` | Adaptador HTTP de la consulta |
| `dashboard/application.py` | Shell Dash, callbacks y lectura compartida |
| `dashboard/views.py` | Vistas, tablas, ficha y evidencia |
| `dashboard/analytics.py` | Agregados del corte y gráficos Plotly |
| `dashboard/context.py` | Validación de modo, búsqueda, filtros y enlaces |
| `dashboard/assets` | CSS, logos y tipografía locales |
| `integrations`, `models` | Conectores, fixtures y contrato Pydantic |

## Recorrido de revisión

1. Abrir Vista general: tres equipos, tres solicitudes y cuatro alertas
   agrupadas en dos asuntos. Los tres indicadores muestran uno.
2. Abrir cada indicador y revisar su conjunto exacto de registros.
3. Ordenar y filtrar Maquinaria. La ficha CF-03 explica Ocupada/Completada;
   EX-02 conserva las causas de mantenimiento y traslado pendiente.
4. Buscar RE-03, aplicar, navegar y recargar: origen y búsqueda siguen en la
   URL; sus vínculos y ubicación permanecen desconocidos.
5. Revisar Solicitudes, Traslados, Atención y Fuentes. Expandir evidencia y
   datos tabulares de gráficos. Las tareas pertenecen a su solicitud exacta.
6. Cambiar a Sandbox en vivo y aplicar: si está deshabilitado, los conteos son
   desconocidos y no reaparecen fixtures. Actualizar permite reintentar.
7. Revisar móvil y teclado. Las tablas anchas tienen desplazamiento horizontal
   y paginación; no se ocultan columnas de negocio.

Navegar o filtrar la presentación reutiliza el corte de la sesión; Actualizar
o cambiar origen/búsqueda consulta otra vez. No hay polling automático ni
DataFrames globales modificables. El navegador no autoriza los conectores.

## Verificaciones

```powershell
.\scripts\check.ps1 -Container
```

Comandos equivalentes:

```sh
uv run --directory apps/api ruff check .
uv run --directory apps/api ruff format --check .
uv run --directory apps/api pytest
docker build -t econ-hub:check apps/api
```

Sin `.env`, exportar `DATABASE_URL=sqlite://` antes de pytest. Las pruebas
aíslan bases y proveedores y comprueban rutas, callbacks HTTP, assets y API.
La imagen contiene los assets; construirla no hace un despliegue remoto.

`ALLOW_LIVE_READS=false` sigue siendo el valor predeterminado. Credenciales
solo en el servidor, nunca en `dcc.Store`, URLs o assets. La API key de
Startrack sigue pendiente; [ver evidencia](revision-contexto.md).
