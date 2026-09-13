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
`/api/v1/hub`, `/api/v1/graph`, `/api/v1/indicators`, `/health/live` y
`/health/ready`. Sin `SESSION_SECRET` la
aplicación no arranca; `AUTH_REQUIRED=false` desactiva el login **solo para
desarrollo**. Sin scripts:

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

## Entregables y demo para el jurado

Enlaces directos a lo que pide el [brief](docs/onedrive/02-brief-del-reto.md):

| Entregable | Dónde está |
| --- | --- |
| Matriz de mapeo y glosario (RF-01/RF-02) | [Markdown editable](docs/equivalencias-prisma-startrack.md) · [CSV y XLSX](output/matrices/MANIFEST.md) (`output/matrices/*.csv`, `matrices-econ.xlsx`, manifiesto con SHA-256) |
| Matriz RACI (RF-03) | [Propuesta en la matriz](docs/equivalencias-prisma-startrack.md#responsabilidades-propuestas-para-confirmar) · [`raci-propuesta.csv`](output/matrices/raci-propuesta.csv); roles de sesión en [ADR 0005](docs/adr/0005-session-auth-and-roles.md) |
| Diccionario del modelo (RF-01) | [docs/diccionario-modelo-econ.md](docs/diccionario-modelo-econ.md), generado y verificado en CI |
| Diagrama de arquitectura y «dónde vive cada estado» | [Gráficos y diagramas](docs/entregables-visuales.md) · [PNG](docs/assets/entregables/diagrama-estados.png) / [SVG](docs/assets/entregables/diagrama-estados.svg) |
| PDFs (dossier visual de 16 páginas y decisiones técnicas de 2) | [`output/pdf`](output/pdf) con fecha, páginas y SHA-256 en [MANIFEST.md](output/pdf/MANIFEST.md) |
| Decisiones técnicas | [docs/decisiones-tecnicas.md](docs/decisiones-tecnicas.md) · [ADR 0006](docs/adr/0006-postgresql-unica-infraestructura-de-estado.md) |
| Indicadores (RF-06 y calculables) | [Definición única de RF-06](docs/entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado) · [Indicadores calculables](docs/indicadores-calculables.md) (`GET /api/v1/indicators`) |
| Requisitos y brechas | [Matriz de requisitos](docs/matriz-requisitos-entregables.md) |

Guion de la prueba en vivo en diez pasos (modo `fixture`, sin proveedores; el
jurado elige el equipo y nada se inventa). Cada página conserva `mode` en la URL
y los enlaces de las listas llevan el ID original codificado
(`nexus:equipment:…`, `nexus:request:…`):

1. **Arrancar y elegir el equipo.** Iniciar sesión (o `AUTH_REQUIRED=false` en
   desarrollo) y abrir `/maquinaria?mode=fixture`: cinco unidades de la muestra
   (CF-01, CF-02, CF-03, EXC-01, EXC-02) con estado administrativo, proyecto y
   procedencia. El jurado elige cualquiera; el guion sigue con CF-03
   (`nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03`).
2. **Consulta unificada de la unidad** ([RF-04](docs/matriz-requisitos-entregables.md#trazabilidad-de-los-requisitos-funcionales))
   en `/maquinaria/{id}`: estado administrativo, mantenimiento, ventana de
   asignación, solicitudes por `maquinaria_id` exacto y la ubicación marcada
   como **no verificable**, porque el fixture no trae visitas ni posición.
3. **La solicitud** en `/solicitudes/{id}` (la APROBADA es
   `nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135`): aprobación con
   `approved_at`, unidad asignada, período de uso (no es ventana de entrega),
   señales de intervalos y lo que falta para preparar el movimiento.
4. **Preparar el traslado** desde ese detalle hacia `/operaciones`: guardar el
   plan con destino y usuarios de Startrack produce un movimiento `draft` o
   `blocked` con su preparación y sus reglas; `/operaciones/{id}` muestra
   estados, eventos y el actor de cada transición. En fixture no hay envío.
5. **Estados que difieren y cómo se resuelven**
   ([RF-05](docs/matriz-requisitos-entregables.md#trazabilidad-de-los-requisitos-funcionales)):
   CF-03 está OBSOLETA en Prisma y tiene solicitud APROBADA; ECON lo muestra
   como tensión y no lo «corrige». La regla de
   [estados separados](docs/equivalencias-prisma-startrack.md#fechas-unidades-y-estados-separados)
   y el [diagrama «dónde vive cada estado»](docs/entregables-visuales.md#diagrama-6-dónde-vive-cada-estado)
   explican por qué. El caso con un estado de Startrack distinto al de Prisma
   necesita evidencia live; con la muestra queda pendiente y se dice así.
6. **La traza** en `/integracion` (selector «Solicitud a seguir»): qué leyó de
   Prisma, cómo lo nombra ECON, el payload preparado para `POST /api/job` y lo
   que Startrack devolvería; los
   [tiempos del traslado](docs/solucion-integracion.md#tiempos-del-traslado-qué-se-sabe-y-qué-no)
   solo se calculan con instantes existentes. La misma respuesta está en
   `GET /api/v1/integration/{request_id}`.
7. **Grafo en Swagger** (`/docs`): `GET /api/v1/graph?mode=fixture` devuelve 5
   máquinas, 2 solicitudes y 1 proyecto `referenced_only`, 4 aristas con
   evidencia, 0 conflictos, la tensión `obsolete_with_approved_request` y
   `gaps` «no verificable» (ubicación de cada máquina, proyecto no leído,
   Startrack no consultado); `coverage.complete=false`.
   Detalle en [api-swagger](docs/api-swagger.md#grafo-indicadores-y-sugerencias-con-la-muestra).
8. **Indicadores**: `GET /api/v1/indicators?mode=fixture` publica ocho fichas
   por fila, sin promedios: `approval_time` evaluable para la APROBADA
   (42,2 s entre creación y aprobación) y «sin approved_at» para la
   PENDIENTE; el resto «no evaluable» con el motivo (sin corte de observación,
   sin tareas en la muestra). La ausencia no es cero
   ([fichas](docs/indicadores-calculables.md)).
9. **Sugerencia de unidad**:
   `GET /api/v1/requests/nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888/suggestions?mode=fixture`
   (la PENDIENTE, «Cargador frontal»): CF-01 y CF-02 elegibles, CF-03 excluida
   por OBSOLETA, EXC-01/EXC-02 por clase distinta; cada candidata lista
   ubicación, operadores y tarifa como «no verificable». Recomendar no es
   asignar: la asignación se registra en Prisma.
10. **Qué muestra Prisma, qué mostraría Startrack y por qué falta**: `/fuentes`
    separa muestras proporcionadas y sandbox. La tarea aparecería en
    `/operaciones/{id}` (`job_id`, `status`, `workflow_role`), el GPS como
    visita a la geocerca del movimiento (`arrival_event_time`; el vehículo
    rastreado puede ser el transportador) y la recepción solo como declaración
    con responsable, instante, referencia y usuario de sesión. El fixture **no
    los trae** porque el OpenAPI proporcionado no contiene tareas, visitas ni
    recepciones; esas filas quedan visibles como faltantes en lugar de
    rellenarse. Cierre: matrices en `output/matrices`, PDFs con
    [manifiesto](output/pdf/MANIFEST.md) y `scripts/check.sh` en verde.

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
API, filtros, reglas y errores sin fallback. Con `ECON_TEST_POSTGRES_URL` y
`ECON_TEST_POSTGRES_MIGRATIONS_URL` definidas (CI levanta `postgres:16`; en local
sirve el Compose con `econ_test` y `econ_test_migrations`) también se ejecutan
las pruebas de PostgreSQL (exclusividad en vuelo, `SKIP LOCKED`, append-only,
migración 0004); sin ellas se omiten y SQLite no acredita ese comportamiento.
`check.sh` termina con `generar_diccionario.py --check` (RF-01) y
`exportar_matrices.py --check` (RNF-02). El segundo comando construye la
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
[Indicadores calculables](docs/indicadores-calculables.md) ·
[Matrices CSV/XLSX](output/matrices/MANIFEST.md) ·
[Backlog](https://github.com/Los-Filosofos/econ-operations/issues) ·
[OneDrive](docs/onedrive/README.md).

Los originales con accesos permanecen en `.context-work/`, excluida de Git.
Commits y PR en inglés; producto y documentación operativa en español.
