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
| `/login` | Formulario de inicio de sesión; `?next=` devuelve a la ruta pedida | Pública |
| `/` y `/resumen` | Asuntos por revisar por solicitud, calendario de uso solicitado y distribución por estado | `read` |
| `/solicitudes` | Proyecto/solicitud, maquinaria, período, estado, traslado y recepción | `read` |
| `/solicitudes/{id}` | Asignación, evidencia, faltantes y preparación del movimiento | `read`; guardar plan exige `manage_transfers` |
| `/maquinaria` | Inventario consultado, incluidos equipos sin solicitud, con filtros y acceso por ID | `read` |
| `/maquinaria/{id}` | Comparación de evidencia por fuente, interpretación de estados y ubicación fechada | `read` |
| `/operaciones` y `/operaciones/{id}` | Planes guardados, envío, historial y declaración de recepción | `read`; cola y sincronización exigen `manage_transfers`, recepción `declare_reception` |
| `/integracion` | Traza de una solicitud: datos leídos de Prisma, transformación de ECON, payload preparado para Startrack, respuesta del proveedor y tiempos del traslado | `read` |
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

## Presentación y paleta

La portada empieza por proyecto, revisión, evidencia y siguiente paso. No usa
cards de conteos, badges ni prioridad inventada. IDs completos, mantenimiento,
historial y preparación usan `Accordion`. Los estados se presentan como texto
con un punto de color y conservan las diferencias entre administración,
mantenimiento, tarea, ubicación y recepción.

`dashboard/theme.py` es la única fuente de color, compartida por Mantine, AG
Grid y el template Plotly `econ`:

| Uso | Valores | Regla |
| --- | --- | --- |
| Marca y acciones primarias | Azul ECON `#144f81` (`primaryColor: econ`, tono 7) | Solo identidad, enlaces y botón principal; **el azul no codifica estado** |
| Estados (cualitativa) | `pending #eb6834`, `active #199e70`, `busy #4a3aa7`, `issue #d03b3b`, `neutral #868e96` | `state_family` mapea `PENDIENTE/QUEUED/SENDING…`, `APROBADA/DISPONIBLE/SENT/COMPLETADA…`, `OCUPADA/ASIGNADA`, `FAILED/BLOCKED/RECHAZADA/UNKNOWN`; lo no reconocido es `neutral`. `issue` siempre va con icono y texto |
| Magnitudes | Secuencial azul `#86b6ef → #0d366b` (`SEQUENTIAL`) | Un solo tono; más oscuro es más |
| Desviación frente a meta | Divergente `#0d366b … #f0efec … #b3261e` (`DIVERGING`) | Neutro `#f0efec` en el cero; azul por debajo, rojo por encima |

Tipografía Inter (OFL) servida localmente; radios pequeños, superficies claras
y `focusRing: auto`. Los gráficos Plotly usan `figure()` del tema (sin zoom,
ejes fijos, leyenda por texto) y siempre tienen una tabla alternativa; ver
[definiciones analíticas](analitica-decisiones.md). Capturas de referencia
verificadas a 1280 y 390 px en `docs/screenshots/`
(`2026-09-13-<página>-<ancho>.png`).

Los iconos son Tabler locales (`app/dashboard/assets/icons/*.svg`, licencia MIT),
pintados con `mask-image` para heredar el color del texto. Acompañan texto en
navegación y acciones y nunca son el único portador de significado.

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
| `dashboard/views.py` | `PAGES`, navegación, línea de alcance, pestañas de filtro, resumen, solicitudes, maquinaria, fuentes y `render_page` |
| `dashboard/analytics.py`, `dashboard/decision_analytics.py` | Relación solicitud/unidad, población filtrada, calendario y distribución por estado |
| `dashboard/decision_priorities.py` | Un asunto con evidencia y siguiente paso por solicitud |
| `dashboard/evidence_views.py` | Comparación de hechos por origen, interpretación y cronología por solicitud |
| `dashboard/workflow_forms.py`, `dashboard/workflow_views.py`, `dashboard/workflow_actions.py` | Preparación, registro de movimientos, recepción y ejecución de acciones con permiso |
| `dashboard/auth_views.py`, `dashboard/admin_views.py` | Página `/login`, identidad en la cabecera, ayudas de permiso y página `/administracion`; las reglas viven en `api/users.py` |
| `core/auth.py`, `api/auth.py`, `api/users.py` | Roles, permisos, sesión, login/logout/me y administración de usuarios |
| `services/hub.py` | Proyección de lectura `HubResponse`, compartida con HTTP |
| `services/evidence.py` | Proyección de evidencia persistida mediante identidades y períodos compatibles |
| `services/workflow.py`, `services/ledger.py` | Reglas operativas, permiso por acción, persistencia, cortes, eventos y cola transaccional; `resolve` cierra un `unknown` como `failed` con actor |
| `services/intervals.py` | Intervalos por día (período de uso, asignación vigente, programación, observación) y comparación inclusiva; fecha ausente, parcial o sin zona → «no verificable», nunca «sin conflicto». Lo usan hub, transfers y suggestions |
| `services/graph.py`, `api/graph.py` | `GraphProjection` de `GET /api/v1/graph`: nodos tipados, aristas con evidencia y alcance, conflictos, tensiones y faltantes «no verificable»; la presencia cuelga del movimiento, no de la máquina; sin geometría ni ETA |
| `services/indicators.py`, `api/indicators.py` | `IndicatorsReport` de `GET /api/v1/indicators`: ocho fichas por fila, sin promedios; la ausencia no es cero; fixture sin corte |
| `services/suggestions.py`, `api/suggestions.py` | `AssignmentSuggestion` de `GET /api/v1/requests/{id}/suggestions`: candidatas por reglas R0–R8, sin GPS ni puntajes; recomendar no es asignar |
| `api/integration.py` | Traza de una solicitud para `/integracion` y `GET /api/v1/integration/{request_id}` |
| `core/database.py`, `cli/sync_operations.py`, `cli/prune_snapshots.py` | Motor SQL y `cycle_lock` (`pg_try_advisory_lock`, un ciclo por proceso y por base); worker explícito y poda explícita de cortes (ADR 0006) |
| `dashboard/assets` | `style.css` mínimo (skip link, foco, grid, impresión), Inter y logotipos ECON |

Se retiraron `icons.py`, `decision_views.py`, `equipment_views.py`, los SVG
locales y el menú clientside: Mantine e Iconify cubren esas funciones. Grafo,
indicadores y sugerencias no tienen página Dash propia: se consultan por HTTP y
Swagger; la tabla `PAGES` no cambió.

Las relaciones usan IDs originales, fuente, entorno y evidencia compatibles.
Los movimientos que alimentan las decisiones deben corresponder también a la
asignación y período vigentes; el detalle conserva la evidencia histórica.
Una visita GPS o tarea completada no genera recepción. Esta requiere
responsable, instante con zona y referencia de constancia.

## Estado, errores y habilitaciones

La URL conserva `mode`, `q` y `filter`. El **origen de datos (`mode`) se
conserva en la URL en todas las páginas**, incluidos los detalles, `/fuentes`,
`/integracion` y `/administracion`. El **buscador (`q`) solo se muestra en
Resumen, Solicitudes, Maquinaria y Operaciones**, que son las páginas con una
población filtrable; las páginas de detalle, `/integracion`, `/fuentes` y
`/administracion` no lo presentan, porque ahí no filtraba nada. Se rechazan
modos desconocidos, parámetros duplicados, filtros inválidos y búsquedas
mayores de 100 caracteres.
Aplicar (o Enter en Buscar) y las pestañas de filtro actualizan la URL;
Atrás/Adelante sincroniza los controles. Abrir un detalle desde una lista
conserva el modo pero no limita el registro por la búsqueda.

Cada navegador guarda `HubResponse` en `dcc.Store(storage_type="memory")` con
clave `[modo, búsqueda]`. Cambiar página o filtro reutiliza esa lectura;
Actualizar vuelve a consultarla. Un store separado conserva `WorkflowOverview`
por modo. Planes, cortes, eventos y recepciones persisten en PostgreSQL: el
store del navegador es una proyección, no el registro durable.

`WorkflowOverview.available` indica si se pudo leer el registro y `complete`
si todos los movimientos de ese modo/solicitud caben en la primera página
(100 movimientos; HTTP admite `page` y `page_size` hasta 500). Un resultado
parcial conserva lo observado, pero no acredita la ausencia de otros
movimientos. Esto es independiente de `HubResponse.scope`.

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

## Accesibilidad

- Enlace «Saltar al contenido» hacia `main#content` (`tabIndex=-1`), foco
  visible con `:focus-visible` y anillo de Mantine.
- `AppShell` con `nav[aria-label]`; el `Drawer` móvil se abre con el botón
  `burger` (`aria-controls`, `aria-expanded`), atrapa el foco, cierra con
  Escape, fondo o navegación y devuelve el foco al control.
- Todos los controles tienen etiqueta visible; pestañas de filtro con
  `aria-label`; mensajes de acción en una región `aria-live="polite"`.
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
