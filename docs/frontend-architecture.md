# Interfaz Dash y arquitectura del hub

## Interfaz vigente: sidebar y resumen operativo

La navegación lateral contiene **Resumen**, **Solicitudes**, **Operaciones** y
**Fuentes** como utilidad secundaria. `/` y `/resumen` muestran decisiones por
solicitud antes del contexto analítico; `/solicitudes` la lista y
`/solicitudes/{id}` su detalle.
`/maquinaria/{id}` conserva una ficha de
evidencia accesible desde el recorrido. Las pantallas generales anteriores ya no
forman parte de la navegación ni se renderizan como páginas operativas.

`dashboard/analytics.py` prepara cada fila relacionando `request.machinery_id`
con `equipment.id` y la tarea con `request.id`, sin coincidencias por nombre.
`dashboard/views.py` concentra las tablas en seis columnas: proyecto/solicitud,
maquinaria, período, estado de solicitud, traslado y recepción. El detalle conserva
destino, llegada y faltantes. No infiere llegada o recepción desde una
posición o una tarea completada. El detalle conserva mantenimiento como contexto
de la unidad asignada, y la procedencia conserva los IDs completos. UUIDs,
referencias de integración, condición mecánica, historial y preparación del
traslado usan desplegables; las señales necesarias para decidir permanecen visibles.

El sidebar de escritorio usa una columna de 236 píxeles, marca ECON, estado
activo y acceso inferior a Fuentes. En móvil se abre con Menú y se cierra por
botón, fondo, Escape o navegación. El foco se lleva al control de cierre y vuelve
al menú. Las referencias del navegador no habilitan acciones de proveedor.

`decision_priorities.py` deriva una revisión por solicitud, con hecho y siguiente
paso, sin ranking artificial. `decision_analytics.py` conserva alcance y períodos.
`decision_views.py` empieza por esa agenda, sin cards ni conteos destacados. El
calendario de uso aparece debajo y la distribución por estado es desplegable.
Ambos gráficos Plotly tienen datos alternativos en tabla.
No hay indicadores de productividad, puntualidad ni series históricas fabricadas.
Los asuntos y el calendario respetan los filtros compartidos con la lista.

El selector «Muestras proporcionadas» mantiene `mode=fixture` para el contrato.
Ahora lee las muestras entregadas con OpenAPI, sin casos inventados. La hora de
observación y `data_as_of` son nulos; `observed_on` registra la fecha documental.
Fuente, naturaleza y cobertura diferencian estas muestras de lecturas actuales.

Se mantienen FastAPI/Dash, estado por navegador, validación URL/Pydantic, callbacks
en threadpool, AG Grid Community, foco de teclado, CSS/Inter/logos ECON y el
desplazamiento horizontal de las tablas. No se incorporan dependencias nuevas.
`workflow_forms.py`, `workflow_views.py` y `workflow_actions.py` presentan planes,
historial y recepción. Un store por navegador conserva la proyección tipada
`WorkflowOverview`; los datos persistidos se consultan mediante `WorkflowService`
y se relacionan por ID original, origen y entorno. Las acciones de gestión se
ejecutan en threadpool y vuelven a validar el contexto local del servidor.
Ningún flag del navegador habilita proveedores. Las credenciales siguen en el backend.

El frontend distingue muestras del archivo y datos actuales del sandbox; ambos
son sintéticos. Los movimientos guardados alimentan la tabla y el detalle.
Una tarea enviada, una visita GPS y una constancia de recepción tienen evidencia
y fechas independientes. Ver [solución implementada](solucion-integracion.md).

Ver [contexto vigente](contexto-vigente.md), [desarrollo](desarrollo.md) y
[evaluaciones de Astra](evaluaciones-astra.md). Las capturas y referencias de la
portada con gráficos que siguen son históricas.

## Registro de la implementación anterior

Migración del **12 de septiembre de 2026**, solicitada para desarrollar en
Python. [ADR 0003](adr/0003-python-dash-hub.md) reemplaza las decisiones de
interfaz anteriores.

## Un servicio y un contrato

FastAPI sirve Dash de forma nativa. API y callbacks llaman a
`app/services/hub.py`: no hay HTTP interno ni dos versiones de las reglas.
Se conserva `HubResponse`. Los routers de API y salud preceden a la interfaz.
`create_app` administra el conector Nexus y el motor SQL. La lectura síncrona
de proveedores se ejecuta en threadpool; presentar una página no consulta APIs.

| Módulo | Responsabilidad |
| --- | --- |
| `dashboard/application.py` | Layout, cuatro callbacks, consulta y resultados |
| `dashboard/context.py` | URL validada y enlaces codificados |
| `dashboard/analytics.py` | Agrupaciones y figuras Plotly |
| `dashboard/views.py` | Seis secciones, ficha, tablas y procedencia |
| `dashboard/assets/style.css` | Identidad, móvil y foco |
| `services/hub.py` | Proyección común para Dash y HTTP |

Se usa `dcc.Location` y `dcc.Link` con callbacks por instancia, permitiendo
servidores aislados en pruebas sin un registro global de páginas. Dash AG Grid
Community aporta ordenación, filtros, paginación y enlaces hacia IDs codificados;
no requiere Enterprise ni ejecuta código de proveedores.

## Estado y errores

La URL conserva `mode`, `q` y `filter`. Se rechazan modos desconocidos,
parámetros duplicados, filtros inválidos y búsquedas mayores a 100 caracteres.
Aplicar actualiza la URL; Atrás/Adelante sincroniza los controles.

Cada navegador guarda un corte en `dcc.Store(storage_type="memory")` con el
contrato público y clave `[modo, búsqueda]`. No hay estado operativo mutable
compartido. Cambiar filtro visual o página reutiliza ese corte; Actualizar
vuelve a leerlo. Esto no es sincronización ni caché global. Una respuesta de
otro origen/búsqueda se oculta; un error descarta el resultado anterior.

Pydantic valida el estado del navegador para presentarlo; ese estado nunca
autoriza conectores ni escrituras. API y callbacks envían `no-store`. Los
errores de proveedores se sanitizan; los fallos inesperados de lectura se
presentan con mensaje genérico y reintento manual.

## Analítica e identidad

Los indicadores enlazan a cohortes de alertas del servicio. Las barras cuentan
estados administrativos; las columnas cuentan inicios previstos alrededor del
corte. No representan utilización, puntualidad ni historial. Fechas inválidas
y fuera del período se cuentan aparte. Se agrupan alertas por equipo o solicitud,
conservando causas y responsables. La ficha vincula tareas a solicitudes por ID
y mantiene ubicación, mantenimiento y estados como hechos separados.
Ver [definiciones analíticas](analitica-decisiones.md).

Se conserva Inter local, azul ECON `#144f81`, superficies claras, bordes rectos
y estados en texto. Hay salto al contenido, foco visible, encabezados,
etiquetas, tablas alternativas para gráficos y navegación móvil. AG Grid
conserva teclado y desplazamiento horizontal.

Los logos se trasladaron a los assets Python sin modificación. El logo conserva
SHA-256 `f4299912e5967fdafa32cfc531fc63c5206e074f80a7c521a6b610a7a95fe212`
y el icono `eab8457fef6decac21496ad79f2d3ee2f8fd35b9d9e954b95c8ddefa8d12c326`.
Proceden del [logo ECON](https://econ.com.sv/wp-content/uploads/2024/09/LOGO1_ECON.png)
y [favicon ECON](https://econ.com.sv/wp-content/uploads/2025/01/cropped-logo_Mesa-de-trabajo-1-1-32x32.png).
El CSS se registra explícitamente con una versión por contenido para que las rutas
internas tengan estilos desde el primer arranque, antes del escaneo automático
de assets del backend FastAPI de Dash. Una prueba cubre ese caso.
Se conserva la licencia OFL junto a Inter WOFF2. Dash distribuye sus componentes
de navegador; el equipo no mantiene una segunda aplicación JavaScript.

## Referencias y verificación

Ejecutar `scripts/check.ps1` y el recorrido de `docs/desarrollo.md`.
Documentación oficial consultada el 12/09/2026:
[backend FastAPI](https://dash.plotly.com/server-backends),
[navegación](https://dash.plotly.com/urls),
[estado](https://dash.plotly.com/sharing-data-between-callbacks),
[AG Grid](https://dash.plotly.com/dash-ag-grid/getting-started),
[assets locales](https://dash.plotly.com/external-resources).

Capturas verificadas con ejemplos locales: [vista general](screenshots/dash-overview-desktop.png)
y [móvil](screenshots/dash-overview-mobile.png). No contienen accesos ni datos de proveedores.
