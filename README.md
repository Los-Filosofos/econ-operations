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
# Poner en apps/api/.env el secreto de sesión (obligatorio):
python -c "import secrets; print(secrets.token_urlsafe(32))"   # → SESSION_SECRET=
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m app.cli.create_user \
  --email admin@example.com --role admin --name "Administración"   # pide la contraseña
./scripts/dev.sh            # PowerShell: .\scripts\dev.ps1
```

Abrir **http://127.0.0.1:8050**, iniciar sesión en `/login` con ese usuario y
crear el resto en `/administracion`. El servicio también expone `/docs`,
`/api/v1/hub`, `/health/live` y `/health/ready`. Sin `SESSION_SECRET` la
aplicación no arranca; `AUTH_REQUIRED=false` desactiva el login **solo para
desarrollo**. Sin scripts:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

La [guía de desarrollo](docs/desarrollo.md) explica la demo sin Docker, los
controles y la configuración. Se conservan el proyecto Compose y su volumen
PostgreSQL.

## Recorrido

- **Mapa de operaciones (inicio):** grafo a pantalla completa de proyectos,
  maquinaria, asignaciones exactas y traslados confirmados. No muestra nodos
  físicos ni relaciones que las fuentes no permitan identificar. Las unidades
  sin asignación se agrupan visualmente —sin aristas— para consultar su estado;
  esa agrupación no se presenta como una base física.
- **Solicitudes:** proyecto, tipo requerido, período, unidad asignada, traslado,
  destino, llegada, recepción y evidencia pendiente.
- **Maquinaria:** inventario consultado, comparación de fuentes por unidad e
  interpretación de estados distintos.
- **Operaciones:** prepara y guarda el traslado, consulta su envío, conserva
  cambios de estado y registra una recepción con responsable y constancia.
- **Integración:** traza completa de una solicitud —lo leído de Prisma, la
  transformación de ECON con sus reglas, el payload preparado para Startrack, lo
  que Startrack devuelve y los tiempos del traslado—. Demuestra en una pantalla
  que la API acepta los datos de Prisma y produce el payload del proveedor.
- **Fuentes y cobertura:** diferencia muestras proporcionadas y lecturas live.
- **Administración** (solo `admin`): usuarios, roles, activación y contraseñas.

La interfaz usa componentes Mantine (dash-mantine-components) con iconos
Tabler, tablas AG Grid Community y gráficos Plotly. El azul ECON identifica la
marca y las acciones; los estados usan una paleta cualitativa propia y las
magnitudes y desviaciones escalas secuencial y divergente
([arquitectura](docs/frontend-architecture.md)). Los iconos Tabler son locales
(`app/dashboard/assets/icons`), sin peticiones a terceros. La cookie de sesión es
`Secure` por defecto: `SESSION_HTTPS_ONLY=false` solo para desarrollo local por HTTP.
La portada usa un lienzo HTML accesible con Roboto Mono y siluetas SVG locales,
aristas rectas, autoencuadre, desplazamiento y detalle contextual de nodos y
conexiones; no añade una dependencia de grafos.

El modo `fixture` contiene cinco máquinas y dos solicitudes extraídas del
OpenAPI proporcionado, con sus IDs y valores originales; no incluye
RE-03/PROY-006 ni tareas de Startrack. **Todo el caso usa datos sintéticos**:
`fixture` consulta ejemplos del archivo y `live` consulta el sandbox. Un fallo
de conexión no sustituye un origen por otro. La recepción requiere una
declaración explícita; el GPS no la crea.

FastAPI comparte con Dash el servicio que guarda planes, correspondencias,
historial y cortes en PostgreSQL. El SDK de Startrack crea tareas solo con
habilitación explícita; una cola persistente concilia resultados inciertos sin
repetir el envío. El envío al sandbox exige credenciales y flags del servidor
documentados en la [guía operativa](docs/solucion-integracion.md). Las
lecturas y escrituras remotas están deshabilitadas por defecto.

## Sesión y roles

El acceso exige iniciar sesión (cookie firmada `econ_session`, HttpOnly).
El primer administrador se crea con `app.cli.create_user`; los demás usuarios,
desde `/administracion` o `POST /api/v1/users`. Roles y permisos:

| Rol | Puede |
| --- | --- |
| `admin` | Todo: leer, gestionar traslados, declarar recepción y administrar usuarios |
| `logistica` | Leer, guardar planes, encolar y sincronizar, declarar recepción |
| `gerencia_proyecto` | Leer y declarar recepción |
| `mantenimiento`, `control_costos`, `lectura` | Leer |

Corresponden a la RACI de [equivalencias](docs/equivalencias-prisma-startrack.md).
Sin sesión la API responde 401 y las páginas redirigen a `/login`; sin permiso,
403. La autoridad de gestión viene del rol; `ALLOW_LOCAL_MANAGEMENT` solo cuenta
en desarrollo con `AUTH_REQUIRED=false`. Detalles en
[ADR 0005](docs/adr/0005-session-auth-and-roles.md).

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
[Sesión y roles](docs/adr/0005-session-auth-and-roles.md) ·
[Solución y operación](docs/solucion-integracion.md) ·
[Analítica](docs/analitica-decisiones.md) ·
[Mapeo y responsabilidades](docs/equivalencias-prisma-startrack.md) ·
[Gráficos y diagramas](docs/entregables-visuales.md) ·
[Backlog](https://github.com/Los-Filosofos/econ-operations/issues) ·
[OneDrive](docs/onedrive/README.md).

Los originales con accesos permanecen en `.context-work/`, excluida de Git.
Commits y PR en inglés; producto y documentación operativa en español.
