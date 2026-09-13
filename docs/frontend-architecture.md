# Interfaces y arquitectura del hub

El sistema ofrece **dos modalidades de interfaz gráfica** conectadas al mismo backend FastAPI (`apps/api`):

1. **SPA Web Standalone (`frontend/`)**: Aplicación moderna en **Vite + Vanilla JS + Canvas 2D + Chart.js** (puerto `5173`), con tema oscuro (#0f1218), lienzo interactivo de grafo a 60 FPS, micro-animaciones y consumo directo de los 18 endpoints REST `/api/v1/*` vía CORS/Proxy.
2. **Consola Analítica Integrada (`apps/api`)**: Aplicación ejecutada en el mismo proceso Python mediante **Dash con componentes dash-mantine-components 2.8**, tablas AG Grid Community e iconos Tabler vendorizados (puerto `8050`).

SQLModel, Alembic y PostgreSQL/SQLite conservan la operación en el libro mayor (*OperationsLedger*). Las decisiones base se detallan en [ADR 0003](adr/0003-python-dash-hub.md), [ADR 0004](adr/0004-persistent-transfer-workflow.md) y [ADR 0005](adr/0005-session-auth-and-roles.md).

## Rutas y acceso

| Ruta | Contenido | Acceso |
| --- | --- | --- |
| `/login` | Formulario de inicio de sesión; `?next=` devuelve a la ruta pedida | Pública |
| `/` y `/resumen` | Grafo operativo a pantalla completa de identidades y relaciones verificadas | `read` |
| `/solicitudes` | Proyecto/solicitud, maquinaria, período, estado, traslado y recepción | `read` |
| `/solicitudes/{id}` | Asignación, evidencia, faltantes y preparación del movimiento; para una solicitud pendiente sin unidad, las unidades candidatas de `GET /api/v1/requests/{id}/suggestions` (elegible, por revisar o excluida, con motivo y faltantes «no verificable») | `read`; guardar plan exige `manage_transfers` |
| `/maquinaria` | Inventario consultado, incluidos equipos sin solicitud, con filtros y acceso por ID | `read` |
| `/maquinaria/{id}` | Comparación de evidencia por fuente, interpretación de estados y ubicación fechada | `read` |
| `/operaciones` y `/operaciones/{id}` | Planes guardados, envío, historial y declaración de recepción | `read`; cola y sincronización exigen `manage_transfers`, recepción `declare_reception` |
| `/integracion` | Traza de una solicitud: datos leídos de Prisma, transformación de ECON, payload preparado para Startrack, respuesta del proveedor y tiempos del traslado | `read` |
| `/indicadores` («Indicadores y SLA») | Las ocho fichas de `GET /api/v1/indicators` agrupadas por el área que decide (Mantenimiento, Logística, Proyectos, Información): una lectura en lenguaje llano por ficha, conteo de filas evaluables, parciales y no evaluables con su motivo, fechas de origen y cobertura, una barra por fila evaluable cuando hay horas (sin promedios), tabla AG Grid de filas y, al lado, el SLA propuesto con umbral «a validar con ECON»; enlace al JSON del contrato | `read` |
| `/decisiones` | Qué requiere atención: un asunto por solicitud con evidencia y siguiente paso, «Lo que dicen los indicadores» (las tres lecturas más accionables, con enlace a `/indicadores`), período de uso solicitado y distribución por estado, cada gráfico con tabla alternativa ([analítica](analitica-decisiones.md#página-de-decisiones)) | `read` |
| `/fuentes` | Procedencia, alcance y estado de las consultas | `read` |
| `/administracion` | Alta, rol, activación y contraseña de usuarios | `manage_users` (solo `admin`) |

Sin sesión, las páginas redirigen a `/login`; `/api/v1/*` y los callbacks de
Dash responden 401. Con sesión sin permiso, la acción responde 403 y la
interfaz no muestra el control. Los roles y permisos están en
[ADR 0005](adr/0005-session-auth-and-roles.md); el usuario y el cierre de
sesión aparecen en la cabecera (`header-user`). Con `AUTH_REQUIRED=false`
(solo desarrollo) no hay login y la gestión vuelve a depender de
`ALLOW_LOCAL_MANAGEMENT` desde loopback.

Las páginas se registran en la tabla `PAGES` de `dashboard/views.py` (ruta,
etiqueta, icono Tabler, función de lista y función de detalle). La navegación
lateral, el cajón móvil y `render_page` se derivan de esa tabla; `Fuentes` es
utilidad secundaria. Añadir una vista es añadir una fila.

La ruta principal conserva el mismo shell y stores, pero `operations-graph.js`
activa el modo visual de página completa: oculta cabecera, navegación, consulta y
alcance mientras el grafo está montado. Las demás rutas recuperan el shell normal.

## Presentación y paleta

La portada es un lienzo carbón cálido (`#111513`) sin cards, tablas, leyenda
extensa, brillos ni paneles permanentes. Inicia sólo con lugares confirmados.
Todos los lugares tienen diámetro de 80 px y la maquinaria de 48 px; las
posiciones se derivan de IDs ordenados y permanecen estables al actualizar. Al
seleccionar una entidad, el lienzo ocupa 68% y el panel contextual 32% en
escritorio; en móvil el panel se superpone para conservar una lectura útil.
Seleccionar un lugar revela
únicamente las unidades relacionadas por IDs exactos; una unidad en traslado
activo permanece visible. Una unidad sin relación verificable no se muestra bajo
una base ni se clasifica como disponible por inferencia. Los nodos usan botones
HTML enfocados por teclado y siluetas SVG locales. Las
aristas son segmentos CSS rectos y su etiqueta abre la evidencia de conexión:
la asignación fina dice «Asignación registrada»; el traslado confirmado es
dirigido; una tarea explícitamente activa
usa azul y movimiento discreto. Ámbar identifica mantenimiento y rojo una
falla/condición confirmada, siempre con texto o símbolo. `prefers-reduced-motion`
detiene la animación.

Hover o foco muestra identidad, estado, fuente y antigüedad. Seleccionar abre un
detalle temporal con asignación, destino, estado, responsable disponible,
historial, evidencia, incidentes, recepción y faltantes. Una conexión seleccionada
muestra entidades legibles, solicitudes, períodos y evidencia. La selección resalta el flujo
relacionado y atenúa el resto. El autoencuadre abre el flujo principal en móvil;
zoom, centrado, rueda y pan sólo cambian la presentación y nunca escriben datos.

El detalle contextual prioriza códigos operativos legibles, iconos, una matriz
compacta de hechos y una línea de eventos. UUID, claves normalizadas y referencias
técnicas se conservan en el modelo y en las relaciones internas, pero no se
imprimen en la ficha ordinaria. Si una fuente no ofrece código o nombre legible,
la interfaz indica «identificado» sin exponer fragmentos de la clave como etiqueta.

`dashboard/theme.py` es la única fuente de color, compartida por Mantine, AG
Grid y el template Plotly `econ`:

| Uso | Valores | Regla |
| --- | --- | --- |
| Marca y acciones primarias | Azul ECON `#144f81` (`primaryColor: econ`, tono 7) | Solo identidad, enlaces y botón principal; **el azul no codifica estado** |
| Estados (cualitativa) | `pending #eb6834`, `active #199e70`, `busy #4a3aa7`, `issue #d03b3b`, `neutral #868e96` | `state_family` mapea `PENDIENTE/QUEUED/SENDING…`, `APROBADA/DISPONIBLE/SENT/COMPLETADA…`, `OCUPADA/ASIGNADA`, `FAILED/BLOCKED/RECHAZADA/UNKNOWN`; lo no reconocido es `neutral`. `issue` siempre va con icono y texto |
| Magnitudes | Secuencial azul `#86b6ef → #0d366b` (`SEQUENTIAL`) | Un solo tono; más oscuro es más |
| Desviación frente a meta | Divergente `#0d366b … #f0efec … #b3261e` (`DIVERGING`) | Neutro `#f0efec` en el cero; azul por debajo, rojo por encima |

Tipografía Inter (OFL) para el shell y Roboto Mono Variable en peso 300 para el
grafo, ambas servidas localmente; radios pequeños, superficies claras y
`focusRing: auto`. Los gráficos Plotly usan `figure()` del tema (sin zoom,
ejes fijos, leyenda por texto) y siempre tienen una tabla alternativa; ver
[definiciones analíticas](analitica-decisiones.md). Capturas de referencia
verificadas a 1280 y 390 px en `docs/screenshots/`
(`2026-09-13-<página>-<ancho>.png`).

Los iconos de navegación son Tabler locales
(`app/dashboard/assets/icons/*.svg`, licencia MIT), pintados con `mask-image`
para heredar el color del texto. Las siluetas del grafo son SVG originales del
proyecto (`graph-*.svg`) y se eligen únicamente a partir de `equipment_class`;
cuando ese campo no permite distinguir el tipo se usa maquinaria genérica.
Ningún icono es el único portador de significado.

## Servicios y módulos

FastAPI y Dash llaman al mismo servicio de lectura; no hay HTTP interno.
`create_app` administra conectores, motor SQL, middleware de sesión y
autorización. Las lecturas y acciones bloqueantes se ejecutan en threadpool.
La función que presenta una página consume las proyecciones ya consultadas.

| Módulo bajo `apps/api/app` | Responsabilidad |
| --- | --- |
| `dashboard/application.py` | `MantineProvider`, `AppShell` (cabecera, navbar, `Drawer` móvil), callbacks, consultas, acciones y stores por navegador |
| `dashboard/theme.py` | Paleta, tema Mantine, tema AG Grid y template Plotly `econ`; `state_family`/`state_color` |
| `dashboard/components.py` | Bloques reutilizables: `icon`, `heading`, `section`, `notice`, `state_text`, `facts`, `rows_table`, `accordion`, `provenance`, `grid` (AG Grid con locale en español) |
| `dashboard/context.py` | Parámetros URL validados y enlaces con IDs codificados |
| `dashboard/views.py` | `PAGES`, navegación, línea de alcance, pestañas de filtro, resumen (grafo), `decisions` (`/decisiones`), solicitudes, maquinaria, fuentes y `render_page` |
| `dashboard/analytics.py`, `dashboard/decision_analytics.py` | Relación solicitud/unidad, población filtrada, calendario y distribución por estado; `graph()` envuelve una figura Plotly del template `econ` |
| `dashboard/decision_priorities.py` | Un asunto con evidencia y siguiente paso por solicitud, sin puntajes de urgencia ni reloj |
| `dashboard/indicator_views.py` | Página `/indicadores`: lectura en lenguaje llano por ficha derivada de las filas de `compute_indicators` (nunca recalcula reglas), tarjetas de SLA propuestos copiadas de `docs/indicadores-calculables.md`, gráfico de horas por fila, tabla AG Grid y bloque de cobertura; `indicator_insights` alimenta «Lo que dicen los indicadores» en `/decisiones` |
| `dashboard/evidence_views.py` | Comparación de hechos por origen, interpretación y cronología por solicitud |
| `dashboard/operations_graph.py` | Proyección visual de proyectos, maquinaria, aristas respaldadas y detalle contextual; no consulta proveedores ni duplica reglas |
| `dashboard/workflow_forms.py`, `dashboard/workflow_views.py`, `dashboard/workflow_actions.py` | Preparación, registro de movimientos, recepción y ejecución de acciones con permiso |
| `dashboard/auth_views.py`, `dashboard/admin_views.py` | Página `/login`, identidad en la cabecera, ayudas de permiso y página `/administracion`; las reglas viven en `api/users.py` |
| `core/auth.py`, `api/auth.py`, `api/users.py` | Roles, permisos, sesión, login/logout/me y administración de usuarios |
| `services/hub.py` | Proyección de lectura `HubResponse`, compartida con HTTP |
| `services/evidence.py` | Proyección de evidencia persistida mediante identidades y períodos compatibles |
| `services/workflow.py`, `services/ledger.py` | Reglas operativas, permiso por acción, persistencia, cortes, eventos y cola transaccional; `resolve` cierra un `unknown` como `failed` con actor; `registry_state` calcula la versión determinista del registro de un modo y `SyncScheduler` ejecuta un ciclo live acotado por intervalo dentro del proceso (`SYNC_INTERVAL_SECONDS`) |
| `api/status.py` | `GET /api/v1/status`: `registry_version`, última lectura guardada del registro, `hub_data_as_of` y estado de la sincronización automática (`enabled`, `interval_seconds`, `last_cycle_at`, `last_cycle_result`, `in_progress`); dos consultas SQL, sin proveedores; lo sondea la interfaz |
| `services/intervals.py` | Intervalos por día (período de uso, asignación vigente, programación, observación) y comparación inclusiva; fecha ausente, parcial o sin zona → «no verificable», nunca «sin conflicto». Lo usan hub, transfers y suggestions |
| `services/graph.py`, `api/graph.py` | `GraphProjection` de `GET /api/v1/graph`: nodos tipados, aristas con evidencia y alcance, conflictos, tensiones y faltantes «no verificable»; la presencia cuelga del movimiento, no de la máquina; sin geometría ni ETA |
| `services/indicators.py`, `api/indicators.py` | `IndicatorsReport` de `GET /api/v1/indicators`: ocho fichas por fila, sin promedios; la ausencia no es cero; fixture sin corte |
| `services/suggestions.py`, `api/suggestions.py` | `AssignmentSuggestion` de `GET /api/v1/requests/{id}/suggestions`: candidatas por reglas R0–R8, sin GPS ni puntajes; recomendar no es asignar |
| `api/integration.py` | Traza de una solicitud para `/integracion` y `GET /api/v1/integration/{request_id}` |
| `core/database.py`, `cli/sync_operations.py`, `cli/prune_snapshots.py` | Motor SQL y `cycle_lock` (`pg_try_advisory_lock`, un ciclo por proceso y por base); worker explícito y poda explícita de cortes (ADR 0006) |
| `dashboard/assets` | Estilos, Inter, Roboto Mono (OFL), siluetas SVG del grafo, iconos Tabler locales y logotipos ECON |

Se retiraron `icons.py`, `decision_views.py`, `equipment_views.py`, los SVG
locales, el menú clientside y el botón Actualizar: Mantine, los recursos locales
y el sondeo de `GET /api/v1/status` cubren esas funciones. La proyección
`GET /api/v1/graph` se consulta por HTTP y Swagger; los indicadores tienen la
página `/indicadores`, las sugerencias aparecen en el detalle de la solicitud
pendiente y el grafo de la portada (`operations_graph.py`) dibuja en el
navegador la lectura del hub ya cargada.

`assets/operations-graph.js` implementa únicamente interacción visual local
(zoom, pan, selección, cierre y reencuadre responsive). No inicia consultas: la
relectura la disparan los callbacks acotados del shell (cambio de origen o
búsqueda, resultado de una acción del flujo o cambio de `registry_version` en
`GET /api/v1/status`). Se eligió HTML/CSS más
SVG locales en lugar de otra dependencia porque preserva nodos como botones
accesibles y reutiliza el estado Dash sin un segundo modelo de grafo.

Las relaciones usan IDs originales, fuente, entorno y evidencia compatibles.
Los movimientos que alimentan las decisiones deben corresponder también a la
asignación y período vigentes; el detalle conserva la evidencia histórica.
Una visita GPS o tarea completada no genera recepción. Esta requiere
responsable, instante con zona y referencia de constancia.

## Estado, errores y habilitaciones

La URL conserva `mode`, `q` y `filter`. El **origen de datos (`mode`) se
conserva en la URL en todas las páginas**, incluidos los detalles, `/fuentes`,
`/integracion`, `/indicadores`, `/decisiones` y `/administracion`. El
**buscador (`q`) solo se muestra en las páginas con una población filtrable**
(Resumen, Solicitudes, Maquinaria, Operaciones y Decisiones); las páginas de
detalle, `/integracion`, `/indicadores`, `/fuentes` y `/administracion` no lo
presentan, porque ahí no filtraría nada. Se rechazan
modos desconocidos, parámetros duplicados, filtros inválidos y búsquedas
mayores de 100 caracteres.
Aplicar (o Enter en Buscar) y las pestañas de filtro actualizan la URL;
Atrás/Adelante sincroniza los controles. Abrir un detalle desde una lista
conserva el modo pero no limita el registro por la búsqueda.

Cada navegador guarda `HubResponse` en `dcc.Store(storage_type="memory")` con
clave `[modo, búsqueda]`. Cambiar página o filtro reutiliza esa lectura;
cambiar origen o búsqueda, o terminar una acción del flujo, vuelve a
consultarla. Un store separado conserva `WorkflowOverview` por modo. Planes,
cortes, eventos y recepciones persisten en PostgreSQL: el store del navegador
es una proyección, no el registro durable.

**Refresco sin botón.** No existe un botón Actualizar: el `dcc.Interval`
`status-poll` sondea `GET /api/v1/status?mode=…` cada 15 segundos
(`STATUS_POLL_SECONDS`; dos consultas SQL, sin proveedores; se pausa con la
pestaña oculta y vuelve a sondear al mostrarla) y solo cuando
`registry_version` difiere de la versión que llevan los stores —planes,
eventos, recepciones o un corte nuevo, lo haya guardado una acción del
navegador, el worker CLI o el ciclo automático del servidor— se recargan
`HubResponse` y `WorkflowOverview`; lo que está en pantalla permanece hasta que
llega la nueva lectura. Una relectura sin cambios conserva la versión y no
recarga nada. La cabecera muestra cuándo se leyó lo que se ve («hace X min»,
`role="status"`) y un menú «Estado de la lectura de datos» con las líneas de
registro, sincronización y sondeo más el respaldo accesible **«Volver a leer
ahora»** (`#refresh`, relectura forzada; el control propio del grafo lo
reutiliza). El ritmo de la sincronización con los proveedores no lo fija el
navegador: `SYNC_INTERVAL_SECONDS` (servidor; `0` apagado, mínimo 30) ejecuta
un ciclo live acotado por intervalo dentro del proceso, bajo el candado de ciclo
de PostgreSQL, y nunca en `fixture` ([despliegue](despliegue-backend.md)).

`WorkflowOverview.available` indica si se pudo leer el registro y `complete`
si todos los movimientos de ese modo/solicitud caben en la página leída (100
movimientos por defecto; HTTP admite `page` y `page_size` hasta 500). La tabla
de Operaciones (AG Grid, `components.grid`) pagina en el navegador esa lectura
en páginas de 15, 30 o 50 filas, filtra por la búsqueda `q` (referencia, IDs de
solicitud, máquina y proyecto, nombre del proyecto) y, cuando la lectura es
parcial, muestra `coverage.note` antes de la tabla. Un resultado parcial
conserva lo observado, pero no acredita la ausencia de otros movimientos. Esto
es independiente de `HubResponse.scope`.

Pydantic valida las proyecciones antes de presentarlas. Una respuesta de otro
modo o búsqueda se oculta; un fallo de lectura no sirve el resultado anterior
como si fuera actual. Errores, fuentes no disponibles y cobertura parcial
quedan visibles. Las respuestas de API y callbacks usan `Cache-Control:
no-store`; los mensajes omiten credenciales y cuerpos privados del proveedor.

`fixture` usa los cinco equipos y dos solicitudes del archivo suministrado;
`live` consulta datos actuales del sandbox. Ambos son sintéticos y no hay
fallback entre modos. Las lecturas remotas, escrituras remotas y encolado
automático siguen deshabilitados por defecto y solo los habilita el servidor;
un rol o un flag del navegador no los encienden. El worker se inicia por CLI;
navegar por el panel no lo inicia.

El grafo recibe exclusivamente `HubResponse` y `WorkflowOverview`. Proyectos se
deduplican por `project_id`; maquinaria por su ID normalizado; solicitudes se
unen por `maquinaria_id` exacto. Los traslados sólo promueven una arista cuando
la proyección de evidencia ya validó asignación, entorno y período. Un equipo sin
asignación no se agrega a un lugar inventado. Las bases y talleres requieren una
identidad y clasificación física verificables que el modelo normalizado actual
todavía no aporta. Una geocerca sin tipo físico confirmado no se presenta como
base o taller. La ubicación, mantenimiento, tarea, presencia GPS y recepción
permanecen hechos separados.

El detalle de maquinaria cuenta proyectos distintos usando únicamente IDs que
aparecen en asignaciones, solicitudes, traslados o movimientos persistidos
visibles. Los presenta por su código o nombre legible, no por el UUID. Es
trazabilidad documental de la lectura, no prueba de presencia física ni una
historia completa cuando la cobertura es parcial.

## Accesibilidad

- Enlace «Saltar al contenido» hacia `main#content` (`tabIndex=-1`), foco
  visible con `:focus-visible` y anillo de Mantine.
- `AppShell` con `nav[aria-label]`; el `Drawer` móvil se abre con el botón
  `burger` (`aria-controls`, `aria-expanded`), atrapa el foco, cierra con
  Escape, fondo o navegación y devuelve el foco al control.
- Todos los controles tienen etiqueta visible; pestañas de filtro con
  `aria-label`; mensajes de acción y el indicador de lectura de la cabecera en
  regiones `aria-live="polite"`; el menú «Estado de la lectura de datos» ofrece
  «Volver a leer ahora» por teclado como respaldo del refresco automático.
- AG Grid con teclado, locale en español y desplazamiento horizontal; las
  tablas no ocultan columnas de negocio en móvil (390 px).
- Los nodos del grafo son botones con nombre accesible y tooltip asociado; Enter
  o Espacio abre detalle, Escape lo cierra y devuelve el foco. El lienzo acepta
  `+`, `-` y `0` para zoom/centrado, además de controles visibles.
- `prefers-reduced-motion` desactiva animaciones.

## Desarrollo y verificación

Los comandos vigentes están en [desarrollo](desarrollo.md),
[servicio Python](../apps/api/README.md) y
[guía operativa](solucion-integracion.md). Ejecutar `scripts/check.sh` (o
`check.ps1`) para cambios de aplicación y `--container`/`-Container` para
validar la imagen. Los cambios de interfaz requieren revisar escritorio
(1280 px), móvil (390 px), teclado, estados vacío/error, preservación de
filtros y la vista con y sin permisos de gestión.

El CSS se registra con versión por contenido para servir estilos en rutas
internas desde el primer arranque. Dash distribuye los componentes del
navegador; el equipo mantiene los módulos Python y sus assets locales.
