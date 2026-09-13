# Interfaz Dash y arquitectura del hub

La interfaz y la API se ejecutan en **un servicio Python** en `apps/api`: Dash,
Plotly y AG Grid Community sobre FastAPI. SQLModel, Alembic y PostgreSQL conservan
la operación. Las decisiones aceptadas están en
[ADR 0003](adr/0003-python-dash-hub.md) y
[ADR 0004](adr/0004-persistent-transfer-workflow.md).
No hay aplicación React, `apps/web` ni compilación o despliegue web separado.

## Navegación y presentación

| Ruta | Contenido |
| --- | --- |
| `/` y `/resumen` | Asuntos por revisar por solicitud, calendario de uso solicitado y distribución por estado desplegable |
| `/solicitudes` | Proyecto/solicitud, maquinaria, período, estado, traslado y recepción en seis columnas |
| `/solicitudes/{id}` | Asignación, evidencia, faltantes y preparación del movimiento |
| `/maquinaria` | Inventario consultado, incluidos equipos sin solicitud, con filtros y acceso por ID |
| `/maquinaria/{id}` | Comparación de evidencia por fuente, interpretación de estados y ubicación fechada |
| `/operaciones` y `/operaciones/{id}` | Planes guardados, envío, historial y declaración de recepción |
| `/fuentes` | Procedencia, alcance y estado de las consultas |

El sidebar contiene Resumen, Solicitudes, Maquinaria y Operaciones, con Fuentes como utilidad
secundaria. En móvil se abre con Menú y se cierra por botón, fondo, Escape o
navegación; conserva el foco dentro del menú abierto y lo devuelve al control.

La portada empieza por proyecto, revisión, evidencia y siguiente paso. No usa
cards de conteos, badges ni prioridad inventada. Los detalles técnicos, IDs
completos, mantenimiento, historial y preparación usan desplegables. Los estados
se presentan como texto, conservando las diferencias entre administración,
mantenimiento, tarea, ubicación y recepción.

La identidad usa Inter local, azul ECON `#144f81`, superficies claras y bordes
rectos. Se mantienen salto al contenido, foco visible, etiquetas, encabezados,
teclado de AG Grid y desplazamiento horizontal de tablas. Los gráficos Plotly
tienen tablas alternativas; ver [definiciones analíticas](analitica-decisiones.md).

La [revisión de interfaz](revision-frontend-2026-09-12.md) mejora la legibilidad
y la comparación de fuentes. Los iconos SVG locales acompañan texto en navegación
y acciones, con tamaño y trazo coherentes; no codifican estados ni sustituyen
etiquetas. Se reducen contenedores anidados sin ocultar campos ni evidencia.

## Servicios y módulos

FastAPI y Dash llaman al mismo servicio de lectura; no hay HTTP interno.
`create_app` administra conectores y motor SQL. Las lecturas y acciones bloqueantes
se ejecutan en threadpool. La función que presenta una página consume las
proyecciones ya consultadas.

| Módulo bajo `apps/api/app` | Responsabilidad |
| --- | --- |
| `dashboard/application.py` | Layout, callbacks, consultas, acciones y stores por navegador |
| `dashboard/context.py` | Parámetros URL validados y enlaces con IDs codificados |
| `dashboard/analytics.py`, `dashboard/views.py` | Relación solicitud/unidad, tablas, fichas y procedencia |
| `dashboard/equipment_views.py`, `dashboard/evidence_views.py` | Inventario completo de la consulta y comparación de hechos por origen |
| `dashboard/decision_priorities.py` | Un asunto con evidencia y siguiente paso por solicitud |
| `dashboard/decision_analytics.py`, `dashboard/decision_views.py` | Población filtrada, calendario y distribución por estado |
| `dashboard/workflow_forms.py`, `dashboard/workflow_views.py`, `dashboard/workflow_actions.py` | Preparación, registro de movimientos y recepción |
| `services/hub.py` | Proyección de lectura `HubResponse`, compartida con HTTP |
| `services/evidence.py` | Proyección de evidencia persistida mediante identidades y períodos compatibles |
| `services/workflow.py`, `services/ledger.py` | Reglas operativas, persistencia, cortes, eventos y cola transaccional |
| `dashboard/assets` | CSS, Inter con licencia OFL y recursos ECON |

Las relaciones usan IDs originales, fuente, entorno y evidencia compatibles.
Los movimientos que alimentan las decisiones deben corresponder también a la
asignación y período vigentes; el detalle conserva la evidencia histórica.
Una visita GPS o tarea completada no genera recepción. Esta requiere responsable,
instante con zona y referencia de constancia.

## Estado, errores y habilitaciones

La URL conserva `mode`, `q` y `filter`. Se rechazan modos desconocidos, parámetros
duplicados, filtros inválidos y búsquedas mayores de 100 caracteres. Aplicar
actualiza la URL; Atrás/Adelante sincroniza los controles.

Cada navegador guarda `HubResponse` en `dcc.Store(storage_type="memory")` con
clave `[modo, búsqueda]`. Cambiar página o filtro visual reutiliza esa lectura;
Actualizar vuelve a consultarla. Un store separado conserva `WorkflowOverview`
por modo. Los planes, cortes, eventos y recepciones persisten en PostgreSQL:
el store del navegador es una proyección, no el registro durable.

`WorkflowOverview.available` indica si se pudo leer el registro y `complete`
si todos los movimientos de ese modo/solicitud caben en la primera página.
Coincide con `coverage.is_complete`; el contrato incluye total y paginación HTTP
mediante `page` y `page_size` (hasta 500). Dash consulta la primera página de 100
movimientos y muestra su cobertura; todavía no tiene controles para otras páginas.
Un resultado parcial conserva los movimientos observados, pero no acredita la
ausencia de otros ni habilita recomendaciones que presuponen ese conocimiento.
Esto es independiente de la cobertura integrada de `HubResponse.scope`.

Pydantic valida las proyecciones antes de presentarlas. Una respuesta de otro
modo o búsqueda se oculta; un fallo de lectura no sirve el resultado anterior
como si fuera actual. Errores, fuentes no disponibles y cobertura parcial quedan
visibles. Las respuestas de API y callbacks usan `Cache-Control: no-store`;
mensajes de error omiten credenciales y cuerpos privados del proveedor.

`fixture` usa los cinco equipos y dos solicitudes del archivo suministrado;
`live` consulta datos actuales del sandbox. Ambos son sintéticos y no hay
fallback entre modos. La fecha documental no inventa un instante de observación,
tareas, GPS o recepciones.

No hay login de aplicación. Las lecturas remotas, escrituras remotas y gestión
local están deshabilitadas por defecto. La gestión exige habilitación del
servidor, petición local y origen correspondiente; los flags del navegador no
otorgan permisos. Las credenciales permanecen en el backend. La ejecución
periódica requiere iniciar el worker por CLI; navegar por el panel no lo inicia.

## Desarrollo y verificación

Los comandos vigentes están en [desarrollo](desarrollo.md),
[servicio Python](../apps/api/README.md) y
[guía operativa](solucion-integracion.md). Ejecutar `scripts/check.ps1` para cambios
de aplicación y `-Container` cuando corresponda validar la imagen. Los cambios de
interfaz requieren revisar escritorio, móvil, navegación por teclado, estados
vacío/error y preservación de filtros. Las capturas de versiones anteriores no
son evidencia visual de la portada actual.

El CSS se registra con versión por contenido para servir estilos en rutas
internas desde el primer arranque. Dash distribuye los componentes del navegador;
el equipo mantiene los módulos Python y sus assets locales.
