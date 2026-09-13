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
`/api/v1/hub`, `/api/v1/graph`, `/api/v1/indicators`,
`/api/v1/requests/{id}/suggestions`, `/api/v1/status`, `/health/live` y
`/health/ready`. Sin `SESSION_SECRET` la aplicación no arranca;
`AUTH_REQUIRED=false` desactiva el login **solo para desarrollo**. Sin scripts:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

La [guía de desarrollo](docs/desarrollo.md) explica la demo sin Docker, los
controles y la configuración. Se conservan el proyecto Compose y su volumen
PostgreSQL.

## Recorrido

- **Mapa de operaciones (inicio):** grafo a pantalla completa que inicia sólo
  con lugares confirmados. Al seleccionar un proyecto despliega únicamente la
  maquinaria relacionada por identificadores exactos; una unidad en traslado
  permanece visible. No crea bases, talleres, agrupaciones ni relaciones que
  las fuentes no permitan identificar. La maquinaria sin vínculo verificable
  no se atribuye a una base ni se clasifica como disponible por inferencia.
- **Solicitudes:** proyecto, tipo requerido, período, unidad asignada, traslado,
  destino, llegada, recepción y evidencia pendiente. El detalle de una solicitud
  pendiente sin unidad lista las **unidades candidatas** por reglas explícitas
  (clase, estado administrativo, paro, período), sin GPS ni puntajes;
  recomendar no es asignar.
- **Maquinaria:** inventario consultado, comparación de fuentes por unidad e
  interpretación de estados distintos.
- **Operaciones:** prepara y guarda el traslado, consulta su envío, conserva
  cambios de estado y registra una recepción con responsable y constancia. La
  tabla pagina en el navegador (15, 30 o 50 filas) la lectura del registro y
  declara cuando esa lectura es parcial.
- **Integración:** traza completa de una solicitud —lo leído de Prisma, la
  transformación de ECON con sus reglas, el payload preparado para Startrack, lo
  que Startrack devuelve y los tiempos del traslado—. Demuestra en una pantalla
  que la API acepta los datos de Prisma y produce el payload del proveedor.
- **Indicadores y SLA:** las ocho fichas de `GET /api/v1/indicators` agrupadas
  por el área que decide, cada una con una lectura en lenguaje llano, sus filas
  (evaluables, parciales o no evaluables con motivo) y el SLA propuesto al lado
  con umbral «a validar con ECON»; sin promedios ni porcentajes, y la ausencia
  nunca es cero.
- **Decisiones:** un asunto por solicitud con su evidencia y siguiente paso,
  las tres lecturas más accionables de los indicadores, el calendario de
  períodos de uso solicitado y la distribución por estado, cada gráfico con
  tabla alternativa.
- **Fuentes y cobertura:** diferencia muestras proporcionadas y lecturas live.
- **Administración** (solo `admin`): usuarios, roles, activación y contraseñas.

Cada página conserva `mode` en la URL; los enlaces llevan el ID original
codificado (`nexus:equipment:…`, `nexus:request:…`). No hay botón de
actualizar: la interfaz sondea `GET /api/v1/status` cada 15 segundos y vuelve a
leer el hub y el registro solo cuando `registry_version` cambia. En el servidor,
`SYNC_INTERVAL_SECONDS` (0 = apagado; mínimo 30) ejecuta un ciclo live acotado
por intervalo dentro del mismo proceso, bajo el candado de ciclo de PostgreSQL;
exige `ALLOW_LIVE_READS=true`, nunca corre en `fixture` y ningún refresco
sustituye una lectura fallida por la anterior.

La interfaz usa componentes Mantine (dash-mantine-components) con iconos
Tabler, tablas AG Grid Community y gráficos Plotly. El azul ECON identifica la
marca y las acciones; los estados usan una paleta cualitativa propia y las
magnitudes y desviaciones escalas secuencial y divergente
([arquitectura](docs/frontend-architecture.md)). Los iconos Tabler son locales
(`app/dashboard/assets/icons`), sin peticiones a terceros. La cookie de sesión es
`Secure` por defecto: `SESSION_HTTPS_ONLY=false` solo para desarrollo local por HTTP.
La portada usa un lienzo HTML accesible con Roboto Mono y siluetas SVG locales,
lugares de 80 px, maquinaria de 48 px, aristas rectas, autoencuadre,
desplazamiento y detalle contextual de nodos y conexiones. Al seleccionar una
entidad, el lienzo ocupa 68% y el detalle 32% en escritorio; no añade una
dependencia de grafos.

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

## Guion de demo para el jurado

Diez pasos en modo `fixture`, sin proveedores; el jurado elige la unidad o la
solicitud y nada se inventa. Cada paso dice qué URL abrir y qué mostrar; lo que
la muestra no trae se enseña como faltante, no se rellena. Los IDs largos son
los de la muestra: CF-03 es `nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03`,
la solicitud APROBADA es `nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135`
y la PENDIENTE es `nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888`.

1. **Arrancar, iniciar sesión y dejar que el jurado elija.** `/login` y luego
   `/maquinaria?mode=fixture`: cinco unidades (CF-01, CF-02, CF-03, EXC-01,
   EXC-02) con estado administrativo, proyecto y procedencia; el buscador filtra
   por código, activo, nombre o proyecto. El jurado elige cualquiera; el guion
   sigue con CF-03. Con `live` habilitado en el servidor la misma tabla lista lo
   leído de Prisma, con la cobertura de páginas declarada.
2. **Grafo de portada de la unidad elegida.** `/?mode=fixture`: el lienzo
   inicia con los lugares confirmados (PROY-014); seleccionar el proyecto revela
   CF-03 unida por `project_id` y `maquinaria_id` exactos, y el panel de detalle
   (68/32 en escritorio) muestra hechos, procedencia y faltantes. Las otras
   cuatro unidades no se atribuyen a ninguna base. Enter abre el detalle,
   Escape lo cierra; `+`, `-` y `0` controlan el zoom.
3. **Consulta unificada de la unidad** ([RF-04](docs/matriz-requisitos-entregables.md#matriz-de-trazabilidad)).
   `/maquinaria/{id}?mode=fixture`: estado administrativo de Prisma
   (`OBSOLETA`), mantenimiento (sin falla activa), ventana de asignación 11–14/09,
   solicitudes por `maquinaria_id` exacto y, del registro local, tarea y visita
   de Startrack y recepción; con la muestra esas filas dicen **no verificable**
   porque el archivo no trae tareas ni posición, y así se dice.
4. **Estados que difieren y cómo se resuelven** ([RF-05](docs/matriz-requisitos-entregables.md#matriz-de-trazabilidad)).
   Misma pantalla y `/solicitudes/{id APROBADA}?mode=fixture`: la solicitud
   está APROBADA con `approved_at` sobre una unidad `OBSOLETA`; ECON lo muestra
   como tensión y no lo «corrige». La regla de
   [estados separados](docs/equivalencias-prisma-startrack.md#fechas-unidades-y-estados-separados)
   y el [diagrama «dónde vive cada estado»](docs/entregables-visuales.md#diagrama-6-dónde-vive-cada-estado)
   explican el caso Ocupada/Completada; el caso con un estado de Startrack
   distinto necesita evidencia live y con la muestra queda pendiente.
5. **Sugerencia de unidad para la solicitud sin unidad.**
   `/solicitudes/{id PENDIENTE}?mode=fixture` («Cargador frontal», 16–18/09):
   el bloque de candidatas lista CF-01 y CF-02 elegibles, CF-03 excluida por
   `OBSOLETA` y EXC-01/EXC-02 por clase distinta; ubicación, operadores y
   tarifa figuran como «no verificable». Recomendar no es asignar: la
   asignación se registra en Prisma. La misma respuesta está en
   `GET /api/v1/requests/{id}/suggestions?mode=fixture`.
6. **Preparar el traslado y leer el registro.** Desde la APROBADA hacia
   `/operaciones?mode=fixture`: guardar el plan con destino, usuarios de
   Startrack, referencia y programación produce un movimiento `draft` o
   `blocked` con su preparación y sus reglas; `/operaciones/{id}` muestra
   estados, eventos y el usuario de sesión que actuó; la tabla pagina la
   lectura del registro y avisa si es parcial. Con un usuario `lectura` no
   aparecen acciones. En fixture no hay envío: encolar responde 409.
7. **La traza de integración.** `/integracion?mode=fixture` (selector
   «Solicitud a seguir»): qué leyó de Prisma, cómo lo nombra ECON y con qué
   reglas, el payload preparado para `POST /api/job` y lo que Startrack
   devolvería. El bloque «Mapeo campo a campo» marca los campos **sin
   equivalente** (Origen, «Completar antes de», ventana horaria, artículos) que
   el jurado puede pedir, y los
   [tiempos del traslado](docs/solucion-integracion.md#tiempos-del-traslado-qué-se-sabe-y-qué-no)
   solo se calculan con instantes existentes. Misma respuesta en
   `GET /api/v1/integration/{request_id}`.
8. **Indicadores y decisiones.** `/indicadores?mode=fixture` («Indicadores y
   SLA»): ocho fichas agrupadas por área; `approval_time` es evaluable para la
   APROBADA (42,2 s entre creación y aprobación) y «sin approved_at» para la
   PENDIENTE; el resto «no evaluable» con el motivo (sin corte de observación,
   sin tareas en la muestra), y cada ficha lleva al lado su SLA propuesto con
   umbral «a validar con ECON». La ausencia no es cero y no hay promedios
   ([fichas](docs/indicadores-calculables.md)). `/decisiones?mode=fixture`: un
   asunto por solicitud con evidencia y siguiente paso, «Lo que dicen los
   indicadores», calendario de períodos de uso (11–14 y 16–18/09) y
   distribución por estado con tabla alternativa.
9. **Las proyecciones en Swagger.** `/docs` (iniciar sesión con
   `POST /api/v1/auth/login` en la misma pestaña): `GET /api/v1/graph?mode=fixture`
   devuelve 5 máquinas, 2 solicitudes y 1 proyecto `referenced_only`, 4 aristas
   con evidencia, 0 conflictos, la tensión `obsolete_with_approved_request` y
   `gaps` «no verificable» con `coverage.complete=false`; `GET /api/v1/indicators`
   y `GET /api/v1/requests/{id}/suggestions` devuelven lo mismo que las páginas;
   `GET /api/v1/status?mode=fixture` devuelve `registry_version`, la última
   lectura guardada del registro y `sync.enabled=false` (la sincronización
   automática nunca corre en fixture). Detalle en
   [api-swagger](docs/api-swagger.md#grafo-indicadores-y-sugerencias-con-la-muestra).
10. **Qué muestra Prisma, qué mostraría Startrack y por qué falta.**
    `/fuentes?mode=fixture` separa muestras proporcionadas y sandbox. La tarea
    aparecería en `/operaciones/{id}` (`job_id`, `status`, `workflow_role`), el
    GPS como visita a la geocerca del movimiento (`arrival_event_time`; el
    vehículo rastreado puede ser el transportador) y la recepción solo como
    declaración con responsable, instante, referencia y usuario de sesión. El
    fixture **no los trae** porque el OpenAPI proporcionado no contiene tareas,
    visitas ni recepciones; esas filas quedan visibles como faltantes. Cierre:
    matrices en `output/matrices`, PDFs con [manifiesto](output/pdf/MANIFEST.md)
    y `scripts/check.sh` en verde.

## Cómo revisar las matrices

Las matrices que pide el [brief](docs/onedrive/02-brief-del-reto.md) (RF-02,
RF-03 y RNF-02) se editan en Markdown y se copian sin cambios a CSV y XLSX;
el manifiesto registra el SHA-256 de cada origen y de cada archivo, y CI falla
si las copias quedan desactualizadas.

| Qué revisar | Origen editable | Copia reutilizable |
| --- | --- | --- |
| Matriz de mapeo de campos (RF-02): formulario de tarea en cinco secciones, campos API sin control, inventario Prisma, identidad y cardinalidad; los casos sin equivalente aparecen en la columna «Clasificación y alcance» | [docs/equivalencias-prisma-startrack.md](docs/equivalencias-prisma-startrack.md) | `output/matrices/formulario-tarea-completo.csv`, `otros-campos-api-tarea.csv`, `inventario-prisma.csv`, `identidad-cardinalidad.csv` |
| Glosario de sinónimos (RF-01/RF-02): nombre exacto de cada concepto en Prisma, Startrack y ECON | [glosario](docs/equivalencias-prisma-startrack.md#glosario-de-sinónimos-entre-plataformas) | `output/matrices/glosario-sinonimos.csv` |
| Matriz RACI (RF-03): nueve decisiones con R/A/C/I para Gerencia de Proyecto, Logística y Equipo, Mantenimiento, Operador, Control de Costos, Soporte de integración y Responsable receptor | [responsabilidades propuestas](docs/equivalencias-prisma-startrack.md#responsabilidades-propuestas-para-confirmar) | `output/matrices/raci-propuesta.csv`; páginas 2 a 4 del dossier PDF; roles de sesión en [ADR 0005](docs/adr/0005-session-auth-and-roles.md) |
| Estados por objeto y regla de interpretación (RF-05); evidencia de retorno implementada (RF-04) | [fechas, unidades y estados separados](docs/equivalencias-prisma-startrack.md#fechas-unidades-y-estados-separados) | `output/matrices/estados-separados.csv`, `evidencia-retorno.csv` |
| Trazabilidad de requisitos: RF-01 a RF-06, RNF-01 a RNF-04 y entregables de §6/§9 con evidencia, dónde lo ve el jurado, estado y brecha | [docs/matriz-requisitos-entregables.md](docs/matriz-requisitos-entregables.md) | `output/matrices/trazabilidad-requisitos.csv` |
| Diccionario del modelo ECON (RF-01): campo, tipo, ejemplo, significado y procedencia | [docs/diccionario-modelo-econ.md](docs/diccionario-modelo-econ.md), generado desde los modelos | Verificado en CI con `generar_diccionario.py --check` |

Cómo abrirlas y verificarlas:

- `output/matrices/*.csv` son UTF-8 con fila de cabecera (Excel: «Datos ▸
  Desde texto/CSV» con codificación UTF-8; LibreOffice y Google Sheets los abren
  directamente). `output/matrices/matrices-econ.xlsx` reúne las 17 tablas, una
  hoja por tabla con la cabecera fija y sin formato decorativo.
- [`output/matrices/MANIFEST.md`](output/matrices/MANIFEST.md) lista tabla,
  documento y sección de origen, requisito que responde, filas, columnas y
  SHA-256; `sha256sum output/matrices/*.csv` debe coincidir.
- Regenerar y comprobar desde la raíz:
  `uv run --project apps/api python scripts/docs/exportar_matrices.py`
  y `… --check` (también `uv run --no-project --with openpyxl==3.1.5 python …`,
  que es lo que ejecutan `scripts/check.sh` y CI).
- Reglas: no se inventan filas ni IDs; la RACI es una propuesta pendiente de
  validación empresarial; una correspondencia documentada no acredita identidad
  de registros entre plataformas.

El resto de entregables y dónde está cada uno:

| Entregable | Dónde está |
| --- | --- |
| Diagrama de arquitectura y «dónde vive cada estado» | [Gráficos y diagramas](docs/entregables-visuales.md) · [PNG](docs/assets/entregables/diagrama-estados.png) / [SVG](docs/assets/entregables/diagrama-estados.svg) |
| PDFs (dossier visual de 16 páginas y decisiones técnicas de 2) | [`output/pdf`](output/pdf) con fecha, páginas y SHA-256 en [MANIFEST.md](output/pdf/MANIFEST.md) |
| Decisiones técnicas | [docs/decisiones-tecnicas.md](docs/decisiones-tecnicas.md) · [ADR 0006](docs/adr/0006-postgresql-unica-infraestructura-de-estado.md) |
| Indicadores (RF-06 y calculables) | [Definición única de RF-06](docs/entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado) · [Indicadores calculables](docs/indicadores-calculables.md) (`/indicadores`, `GET /api/v1/indicators`) |
| Requisitos, estado y brechas | [Matriz de trazabilidad](docs/matriz-requisitos-entregables.md#matriz-de-trazabilidad): 13 cumple, 5 parcial, 1 pendiente (la presentación de diez diapositivas) |

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
en desarrollo con `AUTH_REQUIRED=false`. El usuario que guarda un plan, encola,
resuelve o declara una recepción queda registrado como actor del evento
(`actor_*`, `declared_by_*`; migración `0004_guards`). Detalles en
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
sirve interfaz y API juntas y documenta `SYNC_INTERVAL_SECONDS` y
`/api/v1/status`.

## Documentación

[Índice](docs/README.md) · [Contexto vigente](docs/contexto-vigente.md) ·
[Arquitectura Dash](docs/frontend-architecture.md) ·
[Sesión y roles](docs/adr/0005-session-auth-and-roles.md) ·
[Solución y operación](docs/solucion-integracion.md) ·
[Analítica](docs/analitica-decisiones.md) ·
[Mapeo y responsabilidades](docs/equivalencias-prisma-startrack.md) ·
[Gráficos y diagramas](docs/entregables-visuales.md) ·
[Indicadores calculables](docs/indicadores-calculables.md) ·
[Matriz de trazabilidad](docs/matriz-requisitos-entregables.md) ·
[Matrices CSV/XLSX](output/matrices/MANIFEST.md) ·
[Backlog](https://github.com/Los-Filosofos/econ-operations/issues) ·
[OneDrive](docs/onedrive/README.md).

Los originales con accesos permanecen en `.context-work/`, excluida de Git.
Commits y PR en inglés; producto y documentación operativa en español.
