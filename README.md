# ECON · Hub de operaciones

Aplicación **Python con Dash, Plotly y FastAPI** del Equipo 6 — Los Filósofos.
Relaciona maquinaria, solicitudes, mantenimiento y traslados para consultar
qué necesita atención, quién debe revisarlo y con qué evidencia.

La interfaz y la API funcionan en **un mismo proceso y origen**. No hay
compilación frontend ni instalación de Node.js. La
[decisión de migración](docs/adr/0003-python-dash-hub.md) registra el cambio.

## Inicio

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/) y Docker para usar
el PostgreSQL local existente. Desde la raíz:

```powershell
uv sync --project apps/api --locked
if (-not (Test-Path apps/api/.env)) {
    Copy-Item apps/api/.env.example apps/api/.env
}
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
.\scripts\dev.ps1
```

Abrir **http://127.0.0.1:8050**. El servicio también expone `/docs`,
`/api/v1/hub`, `/health/live` y `/health/ready`. Comando multiplataforma:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

La [guía de desarrollo](docs/desarrollo.md) explica la demo sin Docker,
los controles y la configuración. Se conservan el proyecto Compose y su
volumen PostgreSQL; cambiar la interfaz no migra ni elimina la base.

## Recorrido

- **Vista general:** solicitudes pendientes con inicio alcanzado, aprobadas sin
  unidad, fallas activas, estados administrativos, calendario de inicios y asuntos.
- **Maquinaria y ficha:** búsqueda, filtros, solicitudes, múltiples tareas,
  mantenimiento, ubicación fechada y procedencia.
- **Solicitudes, traslados y atención:** tablas ordenables, filtros por columna
  y evidencia de las condiciones que requieren revisión.
- **Fuentes:** conexión, corte y cobertura de cada origen.

Seleccionar origen y búsqueda; **Aplicar** actualiza la consulta. **Actualizar**
vuelve a leerla. La URL conserva origen, búsqueda y filtro.

Los ejemplos son sintéticos locales. `live` está deshabilitado por defecto y
nunca se sustituye por ejemplos ante un fallo. Nexus tiene un conector de
lectura acotada; Startrack sigue pendiente de clave API y validación del contrato.
No hay login propio, sincronización persistente ni historial del hub. La
interfaz conserva estos límites; una tarea completada no demuestra recepción.

## Verificar y desplegar

```powershell
.\scripts\check.ps1
.\scripts\check.ps1 -Container
```

Las pruebas usan SQLite y HTTP controlado. Incluyen callbacks reales de Dash,
contrato API, filtros, separación de sesiones, reglas y errores sin fallback.
El segundo comando construye Docker; no publica servicios. El
[despliegue Python](docs/despliegue-backend.md) sirve interfaz y API juntas.
La antigua salida estática de Cloudflare fue retirada.

## Contexto

[Índice](docs/README.md) · [Arquitectura Dash](docs/frontend-architecture.md) ·
[Analítica](docs/analitica-decisiones.md) · [Modelo y matrices](docs/modelo-operativo.md) ·
[OneDrive](docs/onedrive/README.md) · [Integraciones](docs/integraciones-reales.md).

Los originales con accesos y la copia local del frontend anterior permanecen
en `.context-work/`, excluida de Git. Commits y PR en inglés; producto y
documentación operativa en español.
