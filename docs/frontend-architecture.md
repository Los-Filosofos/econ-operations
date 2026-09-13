# Interfaces y arquitectura del hub

El sistema ofrece **dos modalidades de interfaz gráfica** conectadas al mismo backend FastAPI (`apps/api`):

1. **SPA Web Standalone (`frontend/`)**: Aplicación moderna en **Vite + Vanilla JS + Canvas 2D + Chart.js** (puerto `5173`), con tema oscuro (#0f1218), lienzo interactivo de grafo a 60 FPS, micro-animaciones y consumo directo de los 18 endpoints REST `/api/v1/*` vía CORS/Proxy.
2. **Consola Analítica Integrada (`apps/api`)**: Aplicación ejecutada en el mismo proceso Python mediante **Dash con componentes dash-mantine-components 2.8**, tablas AG Grid Community e iconos Tabler vendorizados (puerto `8050`).

SQLModel, Alembic y PostgreSQL/SQLite conservan la operación en el libro mayor (*OperationsLedger*). Las decisiones base se detallan en [ADR 0003](adr/0003-python-dash-hub.md), [ADR 0004](adr/0004-persistent-transfer-workflow.md) y [ADR 0005](adr/0005-session-auth-and-roles.md).

## Rutas y acceso

| Ruta | Contenido | Acceso |
| --- | --- | --- |
| `/login` | Formulario de inicio de sesión; `?next=` devuelve a la ruta pedida | Pública |
| `/`, `/resumen` y `/decisiones` | Lectura ejecutiva; gráficos de estados y agenda de uso; tabla de asuntos debajo | `read` |
| `/solicitudes` | Proyecto/solicitud, maquinaria, período, estado, traslado y recepción | `read` |
| `/solicitudes/{id}` | Asignación, evidencia, faltantes y preparación del movimiento; para una solicitud pendiente sin unidad, las unidades candidatas de `GET /api/v1/requests/{id}/suggestions` (elegible, por revisar o excluida, con motivo y faltantes «no verificable») | `read`; guardar plan exige `manage_transfers` |
| `/maquinaria` | Gráfico de estados administrativos de la lectura y después inventario con filtros y acceso por ID | `read` |
| `/maquinaria/{id}` | Comparación de evidencia por fuente, interpretación de estados y ubicación fechada | `read` |
| `/operaciones` y `/operaciones/{id}` | Planes guardados, envío, historial y declaración de recepción | `read`; cola y sincronización exigen `manage_transfers`, recepción `declare_reception` |
| `/integracion` | Visor por etapas con campos y reglas; tiempos y mapeo en pestañas, selección conservada durante la sesión | `read` |
| `/indicadores` | Hitos de una aprobación o barras de duraciones, registros visibles y SLA propuestos en tablas de referencia | `read` |
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
lateral, el cajón móvil y `render_page` se derivan de esa tabla; Integración y
Fuentes son utilidades secundarias. Resumen tiene una entrada; `/resumen` y
`/decisiones` conservan acceso como alias. Añadir una vista es añadir una fila.

Las páginas de trabajo conservan cabecera y navegación. La búsqueda se monta
bajo el título únicamente en las tres listas que la utilizan; los formularios
de búsqueda no incluyen selector de modo. Administración no consulta el hub.
El frontend del mapa se retiró a petición del usuario.

## Presentación y paleta

La navegación usa una barra lateral azul ECON y el área de trabajo una superficie
clara; los estados son texto legible, con icono solo para incidencias, sin
píldoras ni puntos decorativos. El rol de la sesión se consulta en el menú de cuenta.
Las variables de superficie se definen en `theme.py`. El enlace activo usa un
tono azul más oscuro con texto y borde blancos; se retiró el encabezado redundante.
Las tablas ocupan el ancho de trabajo; los análisis usan una superficie única,
sin laterales de explicación ni series de tarjetas.

La portada prioriza una agenda de uso con asignación a todo el ancho y la tabla
de acciones. Indicadores mantiene visibles los registros que sustentan el gráfico;
los SLA se consultan en tablas, sin gráficos de umbrales propuestos. Integración
abre en «Recorrido», con estados independientes por etapa y pendientes explícitos.
`coverage_analytics.py` presenta en Fuentes la cobertura de cada colección de
Prisma, sin convertir datos ausentes en ceros. Todos conservan acceso a evidencia.
El sondeo de estado lee solo metadatos del último corte y no carga su JSON de
proveedores. Mientras hay lecturas en curso, no dispara otra actualización
automática; el registro tampoco se vuelve a leer si ya tiene la misma versión.
La navegación se agrupa en Operación y Sistema; el menú «Datos de la lectura»
concentra modo, corte, cobertura y cambio de origen. La cobertura parcial permanece
visible en la franja de contexto. Las leyendas de gráficos conservan muestras
de color junto al texto para relacionar cada estado con sus barras.

`dashboard/theme.py` es la única fuente de color, compartida por Mantine, AG
Grid y el template Plotly `econ`:

| Uso | Valores | Regla |
| --- | --- | --- |
| Marca y acciones primarias | Azul ECON `#144f81` (`primaryColor: econ`, tono 7) | Solo identidad, enlaces y botón principal; **el azul no codifica estado** |
| Estados (cualitativa) | `pending #eb6834`, `active #199e70`, `busy #4a3aa7`, `issue #d03b3b`, `neutral #868e96` | `state_family` mapea `PENDIENTE/QUEUED/SENDING…`, `APROBADA/DISPONIBLE/SENT/COMPLETADA…`, `OCUPADA/ASIGNADA`, `FAILED/BLOCKED/RECHAZADA/UNKNOWN`; lo no reconocido es `neutral`. `issue` siempre va con icono y texto |
| Cantidades y duraciones | Grafito `#49515b` (`MEASURE`) | La longitud o posición expresa la magnitud; no el estado |
| Intensidad | Secuencial azul `#86b6ef → #0d366b` (`SEQUENTIAL`) | Reservada para datos donde la intensidad del color realmente codifique magnitud |
| Desviación frente a meta | Divergente `#0d366b … #f0efec … #b3261e` (`DIVERGING`) | Neutro `#f0efec` en el cero; azul por debajo, rojo por encima |

Tipografía Public Sans (OFL), servida localmente y compartida con Plotly y
AG Grid; radios pequeños, superficies claras y
`focusRing: auto`. Los gráficos Plotly usan `figure()` del tema (sin zoom,
ejes fijos, leyenda por texto) y siempre tienen una tabla alternativa; ver
[definiciones analíticas](analitica-decisiones.md). Las capturas existentes en
`docs/screenshots/` son referencias históricas; no validan esta reorganización.

Los iconos de navegación son Tabler locales
(`app/dashboard/assets/icons/*.svg`, licencia MIT), pintados con `mask-image`
para heredar el color del texto.

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
| `dashboard/views.py` | `PAGES`, navegación, línea de alcance, pestañas de filtro, resumen de decisiones, `decisions` (`/decisiones`), solicitudes, maquinaria, fuentes y `render_page` |
| `dashboard/analytics.py`, `dashboard/decision_analytics.py` | Relación solicitud/unidad, población filtrada, calendario y distribución por estado; `graph()` envuelve una figura Plotly del template `econ` |
| `dashboard/decision_priorities.py` | Un asunto con evidencia y siguiente paso por solicitud, sin puntajes de urgencia ni reloj |
| `dashboard/indicator_views.py` | Página `/indicadores`: una pregunta activa, resultados de `compute_indicators`, filas visibles y comparación gráfica cuando procede; metodología y SLA separados. No recalcula reglas ni alimenta un segundo resumen en la portada |
| `dashboard/evidence_views.py` | Comparación de hechos por origen, interpretación y cronología por solicitud |
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
| `dashboard/assets` | Estilos, Public Sans (OFL), iconos Tabler locales y logotipos ECON |

Se retiraron `icons.py`, `decision_views.py`, `equipment_views.py`, los SVG
locales, el menú clientside y el botón Actualizar: Mantine, los recursos locales
y el sondeo de `GET /api/v1/status` cubren esas funciones. La proyección
`GET /api/v1/graph` se consulta por HTTP y Swagger; los indicadores tienen la
página `/indicadores`, las sugerencias aparecen en el detalle de la solicitud
pendiente. El frontend usa los componentes Mantine y AG Grid de la plataforma.

Las relaciones usan IDs originales, fuente, entorno y evidencia compatibles.
Los movimientos que alimentan las decisiones deben corresponder también a la
asignación y período vigentes; el detalle conserva la evidencia histórica.
Una visita GPS o tarea completada no genera recepción. Esta requiere
responsable, instante con zona y referencia de constancia.

## Estado, errores y habilitaciones

La URL admite `mode`, `q` y `filter`. La navegación conserva el origen (`mode`)
y limpia búsqueda y filtro al cambiar de sección. **No hay búsqueda global:**
el buscador aparece bajo el título de `/solicitudes`, `/maquinaria` y
`/operaciones`, sin selector de modo dentro del formulario. Resumen y sus alias,
los detalles y las utilidades no filtran por `q`. Administración no depende de
los proveedores aunque un enlace conserve el parámetro de origen. Se rechazan
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

Los enlaces internos de las tablas AG Grid conservan el documento y los stores
al abrir solicitudes, maquinaria y movimientos. Los enlaces externos, descargas
y clics con modificadores mantienen su comportamiento nativo. Abrir/cerrar el
menú móvil, su atributo `aria-expanded` y la visibilidad del estado de lectura
son callbacks del navegador: no necesitan una consulta de sesión al servidor.

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
ahora»** (`#refresh`, relectura forzada). El ritmo de la sincronización con los proveedores no lo fija el
navegador: `SYNC_INTERVAL_SECONDS` (servidor; `0` apagado, mínimo 30) ejecuta
un ciclo live acotado por intervalo dentro del proceso, bajo el candado de ciclo
de PostgreSQL, y nunca en `fixture` ([despliegue](despliegue-backend.md)).

`WorkflowOverview.available` indica si se pudo leer el registro y `complete`
si todos los movimientos de ese modo/solicitud caben en la página leída (100
movimientos por defecto; HTTP admite `page` y `page_size` hasta 500). La tabla
de Operaciones pagina el registro en servidor, con tamaños 25, 50 o 100 y
50 por defecto; AG Grid no añade una segunda paginación. La búsqueda `q`
(referencia, IDs de solicitud, máquina y proyecto, nombre del proyecto) filtra
solo la página cargada. La ventana y su alcance se muestran junto a la tabla. Un resultado parcial
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
un rol o un flag del navegador no los encienden. El worker se inicia por CLI o
mediante el scheduler configurado en el servidor; navegar por el panel no lo inicia.
La centralización de todas las lecturas y los comandos por cambios posteriores
al envío son [propuestas de arquitectura](arquitectura-integracion-eventos.md),
no cambios introducidos por esta reorganización visual.

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
