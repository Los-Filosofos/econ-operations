# ECON · Hub de operaciones

Aplicación **Python con Dash, Plotly y FastAPI** del Equipo 6 — Los Filósofos.
Sigue cada solicitud desde el proyecto y la unidad asignada hasta el traslado,
la llegada y la recepción, mostrando los vínculos y la evidencia que faltan.

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

- **Resumen:** decisiones por solicitud, evidencia y siguiente paso, sin cards
  de conteos. Calendario de uso como apoyo y estados en un desplegable.
  Navegación lateral adaptable a móvil.
- **Solicitudes:** proyecto, tipo requerido, período, unidad asignada, traslado,
  destino, llegada, recepción y evidencia pendiente.
- **Detalle de solicitud:** cadena por IDs, condición de la maquinaria y
  procedencia de cada dato. No infiere recepción desde el GPS o cierre de tarea.
- **Operaciones:** prepara y guarda el traslado, consulta su envío, conserva
  cambios de estado y registra una recepción con responsable y constancia.
- **Fuentes y cobertura:** diferencia muestras proporcionadas y lecturas live.

Las tablas concentran seis columnas. Procedencia completa, referencias técnicas,
historial y preparación del traslado se consultan al desplegar su sección.

Seleccionar origen y búsqueda; **Aplicar** actualiza la consulta. **Actualizar**
vuelve a leerla. La URL conserva origen, búsqueda y filtro.

El modo `fixture` contiene cinco máquinas y dos solicitudes extraídas del OpenAPI
proporcionado, con sus IDs y valores originales. Se retiraron los casos inventados.
La muestra no incluye RE-03/PROY-006 ni tareas de Startrack; no tiene un corte
conjunto y no es una lectura actual. **Todo el caso usa datos sintéticos**:
`fixture` consulta ejemplos del archivo y `live` consulta su estado actual en el
sandbox. Un fallo de conexión no sustituye un origen por otro.

FastAPI comparte con Dash el servicio que guarda planes, correspondencias,
historial y cortes en PostgreSQL. El SDK de Startrack permite crear tareas con
habilitación explícita; una cola persistente conserva resultados inciertos para
conciliarlos sin repetir el envío. La sincronización usa consultas periódicas.
La recepción requiere una declaración explícita; el GPS no la crea.

Para gestionar planes desde el equipo local, configurar
`ALLOW_LOCAL_MANAGEMENT=true` en `apps/api/.env` y reiniciar. El envío al sandbox
requiere además las credenciales y flags documentados en la
[solución y guía operativa](docs/solucion-integracion.md). Los defaults siguen
permitiendo una demo de consulta sin login. La validación autenticada del envío
a Startrack permanece pendiente; las pruebas de integración usan HTTP controlado.

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

[Contexto vigente](docs/contexto-vigente.md) · [Índice](docs/README.md) · [Arquitectura Dash](docs/frontend-architecture.md) ·
[Solución y operación](docs/solucion-integracion.md) ·
[Analítica](docs/analitica-decisiones.md) · [Mapeo y responsabilidades](docs/equivalencias-prisma-startrack.md) ·
[Gráficos y diagramas](docs/entregables-visuales.md) ·
[Auditoría y backlog](output/auditoria-2026-09-12/README.md) ·
[OneDrive](docs/onedrive/README.md) · [Integraciones](docs/integraciones-reales.md).

Los originales con accesos y la copia local del frontend anterior permanecen
en `.context-work/`, excluida de Git. Commits y PR en inglés; producto y
documentación operativa en español.
