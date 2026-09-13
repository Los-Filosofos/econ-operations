# ECON · Hub de operaciones

Aplicación **Python con Dash, Plotly y FastAPI** del Equipo 6 — Los Filósofos.
Sigue cada solicitud desde el proyecto y la unidad asignada hasta el traslado,
la llegada y la recepción, mostrando los vínculos y la evidencia que faltan.
Interfaz y API viven en **un mismo proceso y origen**; no hay compilación
frontend ni Node.js ([ADR 0003](docs/adr/0003-python-dash-hub.md)).

## Inicio

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/) y Docker para el
PostgreSQL local. Desde la raíz:

```sh
uv sync --project apps/api --locked
[ -f apps/api/.env ] || cp apps/api/.env.example apps/api/.env
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
./scripts/dev.sh            # PowerShell: .\scripts\dev.ps1
```

Abrir **http://127.0.0.1:8050**. El servicio también expone `/docs`,
`/api/v1/hub`, `/health/live` y `/health/ready`. Sin scripts:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

La [guía de desarrollo](docs/desarrollo.md) explica la demo sin Docker, los
controles y la configuración. Se conservan el proyecto Compose y su volumen
PostgreSQL.

## Recorrido

- **Resumen:** decisiones por solicitud, evidencia y siguiente paso; calendario
  de uso como apoyo y estados en un desplegable.
- **Solicitudes:** proyecto, tipo requerido, período, unidad asignada, traslado,
  destino, llegada, recepción y evidencia pendiente.
- **Maquinaria:** inventario consultado, comparación de fuentes por unidad e
  interpretación de estados distintos.
- **Operaciones:** prepara y guarda el traslado, consulta su envío, conserva
  cambios de estado y registra una recepción con responsable y constancia.
- **Fuentes y cobertura:** diferencia muestras proporcionadas y lecturas live.

<!-- TODO(ui): actualizar este recorrido y añadir capturas cuando termine el rediseño. -->

El modo `fixture` contiene cinco máquinas y dos solicitudes extraídas del
OpenAPI proporcionado, con sus IDs y valores originales; no incluye
RE-03/PROY-006 ni tareas de Startrack. **Todo el caso usa datos sintéticos**:
`fixture` consulta ejemplos del archivo y `live` consulta el sandbox. Un fallo
de conexión no sustituye un origen por otro. La recepción requiere una
declaración explícita; el GPS no la crea.

FastAPI comparte con Dash el servicio que guarda planes, correspondencias,
historial y cortes en PostgreSQL. El SDK de Startrack crea tareas solo con
habilitación explícita; una cola persistente concilia resultados inciertos sin
repetir el envío. Gestionar planes desde el equipo local requiere
`ALLOW_LOCAL_MANAGEMENT=true`; el envío al sandbox exige además credenciales y
flags documentados en la [guía operativa](docs/solucion-integracion.md). Las
lecturas y escrituras remotas están deshabilitadas por defecto.

<!-- TODO(auth): describir el inicio de sesión, los roles y el usuario administrador inicial. -->

## Verificar y desplegar

```sh
./scripts/check.sh              # PowerShell: .\scripts\check.ps1
./scripts/check.sh --container  # PowerShell: .\scripts\check.ps1 -Container
```

Las pruebas usan SQLite y HTTP controlado: callbacks reales de Dash, contrato
API, filtros, reglas y errores sin fallback. El segundo comando construye la
imagen Docker; no publica servicios. El [despliegue](docs/despliegue-backend.md)
sirve interfaz y API juntas.

## Documentación

[Índice](docs/README.md) · [Contexto vigente](docs/contexto-vigente.md) ·
[Arquitectura Dash](docs/frontend-architecture.md) ·
[Solución y operación](docs/solucion-integracion.md) ·
[Analítica](docs/analitica-decisiones.md) ·
[Mapeo y responsabilidades](docs/equivalencias-prisma-startrack.md) ·
[Gráficos y diagramas](docs/entregables-visuales.md) ·
[Backlog](output/auditoria-2026-09-12/README.md) ·
[OneDrive](docs/onedrive/README.md).

Los originales con accesos permanecen en `.context-work/`, excluida de Git.
Commits y PR en inglés; producto y documentación operativa en español.
