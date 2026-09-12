# Interfaz Dash y arquitectura del hub

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
