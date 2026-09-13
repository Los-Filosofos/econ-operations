# Interfaz Dash y arquitectura del hub

La interfaz y la API se ejecutan en **un servicio Python** en `apps/api`: Dash
con componentes **dash-mantine-components 2.8** (Mantine v8), iconos Tabler locales
(SVG vendorizados en `assets/icons`), tablas **AG Grid Community** (dash-ag-grid) y gráficos Plotly
sobre FastAPI. SQLModel, Alembic y PostgreSQL conservan la operación. Las
decisiones aceptadas están en [ADR 0003](adr/0003-python-dash-hub.md),
[ADR 0004](adr/0004-persistent-transfer-workflow.md) y
[ADR 0005](adr/0005-session-auth-and-roles.md). No hay aplicación React,
`apps/web` ni compilación o despliegue web separado.

## Rutas y acceso

| Ruta | Contenido | Acceso |
| --- | --- | --- |
| `/login` | Inicio de sesión a dos columnas (identidad y formulario), sin tarjeta flotante; etiquetas visibles y el error como texto junto a los campos; `?next=` devuelve a la ruta pedida | Pública |
| `/`, `/resumen` y `/decisiones` | «Operación · Qué requiere atención»: bloque «Qué pasa» con la agenda de uso y su leyenda, y bloque «Qué hago» con un asunto por solicitud, su hecho observado y el siguiente paso. Los conteos por estado y los períodos excluidos quedan plegados en «Datos de la agenda» | `read` |
| `/solicitudes` | Proyecto/solicitud, maquinaria, período, estado, traslado y recepción | `read` |
| `/solicitudes/{id}` | Asignación, evidencia, faltantes y preparación del movimiento; para una solicitud pendiente sin unidad, las unidades candidatas de `GET /api/v1/requests/{id}/suggestions` (elegible, por revisar o excluida, con motivo y faltantes «no verificable») | `read`; guardar plan exige `manage_transfers` |
| `/maquinaria` | Gráfico de estados administrativos de la lectura y después inventario con filtros y acceso por ID | `read` |
| `/maquinaria/{id}` | Comparación de evidencia por fuente, interpretación de estados y ubicación fechada | `read` |
| `/operaciones` y `/operaciones/{id}` | Planes guardados, envío, recepción y el historial como cronología del movimiento; cada acción declara su efecto antes de ejecutarse | `read`; cola y sincronización exigen `manage_transfers`, recepción `declare_reception` |
| `/integracion` | Diagrama de secuencia: tres carriles de actores y cuatro filas de interacción seleccionables; tiempos, mapa de campos y respuesta JSON en pestañas, selección conservada durante la sesión | `read` |
| `/indicadores` | Tablero de trece cifras agrupadas por el área que decide y, debajo, una pregunta por pestaña con sus registros visibles y los SLA propuestos en tablas de referencia | `read` |
| `/fuentes` | Tres bloques: procedencia, alcance (cobertura por colección) y estado de cada fuente y del registro | `read` |
| `/administracion` | Alta, rol, activación y contraseña de usuarios en una tabla a ancho completo, con rol y estado en palabras; la tabla de permisos se deriva de `permissions_of()` | `manage_users` (solo `admin`) |

Sin sesión, las páginas redirigen a `/login`; `/api/v1/*` y los callbacks de
Dash responden 401. Con sesión sin permiso, la acción responde 403 y la
interfaz no muestra el control. Los roles y permisos están en
[ADR 0005](adr/0005-session-auth-and-roles.md); la cabecera (`header-user`)
muestra nombre y rol como texto junto a un botón «Cerrar sesión» con borde:
ya no hay menú de cuenta ni un control con ID `user-menu`. Con `AUTH_REQUIRED=false`
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

**Criterio de diseño.** La pasada de rediseño fija un criterio que debe sobrevivir
a cualquier pantalla nueva: el color solo aparece cuando codifica información;
la estructura se dibuja con reglas de 1 px y espacio, no con cajas; los radios
están topados en 4 px; no hay degradados ni sombras difusas —no existe ninguna
regla `gradient` en las hojas y los cuatro `box-shadow` que quedan son reglas
interiores sólidas, sin desenfoque, que marcan el enlace activo, la
interacción seleccionada o la fila sin mapeo directo—; las cifras se componen
con `tabular-nums` para poder compararlas en columna; las micro-etiquetas en
mayúsculas (`.eyebrow`) preceden a un título, una cifra o una columna y nunca
son la única señal.

La navegación usa una barra lateral azul ECON y el área de trabajo una superficie
clara; los estados son texto legible, con icono solo para incidencias, sin
píldoras ni puntos decorativos. Nombre y rol de la sesión se leen en la cabecera.
Las variables de superficie se definen en `theme.py`. El enlace activo usa un
tono azul más oscuro con texto y borde blancos; se retiró el encabezado redundante.
Las tablas ocupan el ancho de trabajo; los análisis usan una superficie única,
sin laterales de explicación ni series de tarjetas.

La escala tipográfica es contenida: títulos 28/24/20/17/15/13 px (el título de
página se compone en el paso `h2`), cuerpo 15 px y 13 px como paso menor de
Mantine; la micro-etiqueta `.eyebrow` de la hoja base baja a 11 px. El
`spacing` de Mantine avanza en múltiplos de 4 px, la misma rejilla vertical que
declara `--econ-step` en la hoja base. Los radios llegan a 4 px como máximo
—`lg` y `xl` valen lo mismo que `md`— y el radio por defecto es `xs`, 2 px;
la única excepción es la muestra circular de 8 px del estado de lectura en la
cabecera.

Cada página abre con `page_header` (micro-etiqueta de sección, título y una línea
que dice qué se decide ahí) y agrupa su contenido en `panel`. La portada prioriza
la agenda de uso a todo el ancho y las acciones por solicitud. Indicadores abre
con el tablero de cifras y mantiene visibles los registros que sustentan cada
pregunta; los SLA se consultan en tablas, sin gráficos de umbrales propuestos.
Integración abre en «Recorrido», con el diagrama de secuencia, estados
independientes por etapa y pendientes explícitos. Cuando una búsqueda o un filtro
no devuelven filas, la lista ofrece la salida hacia la lectura sin acotar.
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

La paleta no cambió en esta pasada: `BRAND`, `FAMILY_COLORS`, `FAMILIES`,
`SEQUENTIAL` y `DIVERGING` conservan sus valores. Lo que se añadió son neutros
de estructura: `LINE_STRONG` (regla fuerte de cabeceras y separaciones),
`CANVAS_ALT` (segundo tono de papel para bloques embebidos) y `GRID_LINE`
(rejilla de gráfico, un paso por debajo de `LINE`). `SHELL_VARIABLES` los
publica al navegador como `--econ-line-strong` y `--econ-canvas-alt`, y la hoja
base los repite en `:root` para las vistas que se dibujan fuera del shell
(login).

Tipografía Public Sans (OFL), servida localmente y compartida con Plotly y
AG Grid; superficies claras y `focusRing: auto`. El tema de AG Grid es Quartz
sin su apariencia de panel: cabecera blanca con regla fuerte (`LINE_STRONG`),
reglas de fila de 1 px, sin separadores de columna. Los gráficos Plotly usan
`figure()` del template `econ` (sin zoom, ejes fijos, leyenda por texto, rejilla
discreta y sin líneas ni marcas de eje) y siempre tienen una tabla alternativa;
ver [definiciones analíticas](analitica-decisiones.md). Las capturas existentes
en `docs/screenshots/` son referencias históricas; no validan esta
reorganización.

Los iconos de navegación son Tabler locales
(`app/dashboard/assets/icons/*.svg`, licencia MIT), pintados con `mask-image`
para heredar el color del texto.

### Hojas de estilo y su registro explícito

`assets/style.css` es la hoja base, ordenada en doce secciones numeradas
(tipografías, tokens, reset y accesibilidad, utilidades tipográficas, shell,
estructura de página, tablas y AG Grid, gráficos, vistas de integración, estado,
responsive, movimiento e impresión). Ahí viven las utilidades compartidas que
cualquier vista puede usar: `.eyebrow` (micro-etiqueta en mayúsculas), `.measure`
(medida de lectura de 72 ch), `.lede`, `.hairline` (una regla de 1 px en lugar de
una caja), `.numeric` (cifras tabulares alineadas a la derecha), `.stack-tight`,
`.data-strip` (franja de cifras separadas por reglas verticales) y
`.definition-list`. El bloque `@media print` oculta cabecera, barra lateral y
barra de consulta, pone el fondo en papel y evita partir secciones, filas de la
traza y tablas.

Encima de la base hay una hoja por área, todas con prefijo `z-` porque **se
cargan después de `style.css` y en orden alfabético**: `z-auth.css` (login,
bloque de sesión y administración), `z-flow.css` (integración, operaciones y
evidencia), `z-kpi.css` (tablero de `/indicadores`), `z-pages.css` (portada,
listas y fuentes) y `z-shell.css` (cabecera, barra lateral, área de trabajo y
cajón móvil). Ninguna introduce un color propio: usan los tokens de la base
(`z-flow.css` repite el valor del token como respaldo del `var()`).
Para no pisarse, cada hoja restringe sus selectores a un elemento de su área
(`.kpi-board .data-strip`, `.econ-header .read-status`, `.login-panel`) y
`z-flow.css`, que sí redeclara una clase compartida, lo hace con `:where()` para
que la base siga ganando el desempate. Hoy ninguna hoja repite un selector de
otra; si dos coincidieran, mandaría la última en orden alfabético.

`components.py` ofrece el equivalente Python de estas utilidades. `data_strip`
lo consume el tablero de KPIs y `.numeric` viaja como `cellClass` de AG Grid;
`measure`, `definition_list`, `.stack-tight` y `.hairline` están disponibles y
todavía sin uso en una vista.

**Trampa al añadir una hoja.** Dash descubre los assets al servir la primera
petición, pero las rutas catch-all de FastAPI pueden responder antes; un enlace
profundo en frío a `/login`, `/integracion` o `/indicadores` llegaría sin
estilos. Por eso `application.py` las enlaza explícitamente: `STYLESHEET_PATTERN`
(`(?:style|z-[\w-]+)\.css`) las excluye del escaneo con `assets_ignore`,
`stylesheets()` descubre cualquier `z-*.css` del directorio y `stylesheet_links()`
las pasa a `external_stylesheets` con una versión por contenido (hash del
archivo), de modo que un despliegue solo invalida la hoja que cambió. La
consecuencia práctica: una hoja nueva llamada `z-<área>.css` queda registrada sin
tocar código; **cualquier otro nombre no coincide con el patrón**, no se enlaza y
vuelve a depender del escaneo de Dash, con el fallo de enlace profundo en frío
que motivó este registro.

## Servicios y módulos

FastAPI y Dash llaman al mismo servicio de lectura; no hay HTTP interno.
`create_app` administra conectores, motor SQL, middleware de sesión y
autorización. Las lecturas y acciones bloqueantes se ejecutan en threadpool.
La función que presenta una página consume las proyecciones ya consultadas.

| Módulo bajo `apps/api/app` | Responsabilidad |
| --- | --- |
| `dashboard/application.py` | `MantineProvider`, `AppShell` (cabecera con identidad y estado de lectura como texto, navbar con la franja de origen, `Drawer` móvil), registro explícito de las hojas de estilo (`STYLESHEET_PATTERN`, `stylesheets()`, `stylesheet_links()`), callbacks, consultas, acciones y stores por navegador |
| `dashboard/theme.py` | Paleta, neutros de estructura (`LINE_STRONG`, `CANVAS_ALT`, `GRID_LINE`), `SHELL_VARIABLES`, escala tipográfica y de espacio, tema Mantine, tema AG Grid y template Plotly `econ`; `state_family`/`state_color` |
| `dashboard/components.py` | Bloques reutilizables: `icon`, `heading`, `section`, `notice`, `state_text`, `facts` (pares con `.fact-label`/`.fact-value`, ya no `dmc.Text`), `eyebrow`, `measure`, `data_strip`, `definition_list`, `rows_table`, `accordion`, `provenance`, `grid` (AG Grid con locale en español) |
| `dashboard/context.py` | Parámetros URL validados y enlaces con IDs codificados |
| `dashboard/views.py` | `PAGES`, navegación, `page_header`/`panel`, línea de alcance, pestañas de filtro, leyenda de estados, `decisions` (portada y sus alias), solicitudes, maquinaria, fuentes en tres bloques y `render_page` |
| `dashboard/analytics.py`, `dashboard/decision_analytics.py` | Relación solicitud/unidad, población filtrada, calendario y distribución por estado; `graph()` envuelve una figura Plotly del template `econ` |
| `dashboard/decision_priorities.py` | Un asunto con evidencia y siguiente paso por solicitud, sin puntajes de urgencia ni reloj |
| `dashboard/indicator_views.py` | Página `/indicadores`: el tablero de cifras arriba y después una pregunta activa, resultados de `compute_indicators`, filas visibles y comparación gráfica cuando procede; metodología y SLA separados. No recalcula reglas ni alimenta un segundo resumen en la portada |
| `dashboard/kpi_views.py` | Tablero de trece cifras de `/indicadores`, agrupadas por el área que decide (Logística, Proyectos, Mantenimiento, Información) sobre el contrato de `GET /api/v1/indicators` más `scope` y `ledger_coverage`. Presentación pura: no toca `app/services` ni `app/models`, no consulta proveedores ni `datetime.now` —el único «ahora» es `HubResponse.generated_at`—. Una cifra es un conteo de filas de una población publicada, el valor de una fila identificada o el motivo que publicó el servicio: la ausencia nunca es cero. Ver [tablero de KPIs](kpis-tablero.md) |
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
| `services/integration_trace.py`, `api/integration.py` | Traza de una solicitud para `/integracion` y `GET /api/v1/integration/{request_id}`: una sola derivación para la página y el endpoint |
| `dashboard/integration_views.py` | Diagrama de secuencia de `/integracion`: carriles de actores (`ACTORS`), una fila por interacción (`EXCHANGES`), banda de honestidad en tinta, JSON con `figcaption` que nombra su contrato y mapa de campos en dos tablas (lo que ECON reenvía y lo que no). No dibuja tráfico: una flecha es el contrato de interacción |
| `core/database.py`, `cli/sync_operations.py`, `cli/prune_snapshots.py` | Motor SQL y `cycle_lock` (`pg_try_advisory_lock`, un ciclo por proceso y por base); worker explícito y poda explícita de cortes (ADR 0006) |
| `dashboard/assets` | `style.css` (base) y las hojas por área `z-auth`, `z-flow`, `z-kpi`, `z-pages` y `z-shell`, Public Sans (OFL), iconos Tabler locales y logotipos ECON |

Se retiraron `icons.py`, `decision_views.py`, `equipment_views.py`, los SVG
locales, el menú clientside y el botón Actualizar: Mantine, los recursos locales
y el sondeo de `GET /api/v1/status` cubren esas funciones. El rediseño retiró
además `stepper()` y `STAGE_ICONS` de `integration_views.py` (los sustituye el
diagrama de secuencia), `indicator_insights` de `indicator_views.py` y el menú de
cuenta de la cabecera. La proyección
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

El CSS se registra con versión por contenido —la hoja base y cada hoja por
área— para servir estilos en rutas internas desde el primer arranque; el
mecanismo y su trampa están en [hojas de estilo](#hojas-de-estilo-y-su-registro-explícito).
Dash distribuye los componentes del navegador; el equipo mantiene los módulos
Python y sus assets locales.
