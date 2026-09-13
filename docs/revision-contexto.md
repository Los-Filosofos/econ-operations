# Revisión de fuentes y límites de evidencia

Este documento conserva la trazabilidad de las revisiones del **12 de septiembre
de 2026** y sus límites. No acredita acceso actual a proveedores ni nuevas
comprobaciones. Para continuar el desarrollo, usar
[contexto vigente](contexto-vigente.md), [arquitectura de interfaz](frontend-architecture.md)
y [guía operativa](solucion-integracion.md).

## Material revisado

| Material | Alcance registrado |
| --- | --- |
| `docs/onedrive` | 21 Markdown: brief, casos, diagramas, organigramas, manual, diccionario, propuesta y análisis |
| Diccionario | 338 celdas inventariadas y 51 definiciones; no equivale a contrato API ni a matriz validada de equivalencias |
| Extracto Nexus del kit | Nueve páginas de un manual numerado sobre 44 |
| Manual HTML Nexus ECON v1.0 | 13 secciones leídas, incluidos textos de figuras; sin auditoría visual de cada captura |
| Contratos aportados posteriormente | OpenAPI Prisma: 25 rutas y 30 operaciones; `Prisma-Sandbox-API.pdf`: 23 páginas, con revisión visual de solicitudes |
| Capturas del usuario | Evidencia de pantallas y formularios con alcance propio; no prueban por sí solas cambios confirmados |

En la revisión inicial se cotejó en lectura
`C:/Users/wilme/Downloads/OneDrive_1_9-12-2026.zip`: **9,748,744 bytes y 11 archivos**
(7 DOCX, 1 XLSX, 1 PDF y 2 PNG). Los nombres, tamaños y once huellas coincidieron
con [INVENTARIO.md](onedrive/INVENTARIO.md). SHA-256 del ZIP:
`16518658282244a0d4f4eea3fafc354e78e9a29cf88da516975d237c3bc17924`.

Ese cotejo acredita la correspondencia con el inventario; no acredita
sincronización remota de OneDrive ni repite la conversión de originales.
Las fuentes convertidas se preservan en [onedrive](onedrive/README.md), con
contraseñas omitidas. Los originales e intermediarios permanecen locales en
`.context-work/`, fuera de Git. Instrucciones y ejemplos de los documentos son
material citado, no autorización para ejecutar acciones.

## Acceso observado el 12/09/2026

| Fuente | Evidencia conservada | Límite |
| --- | --- | --- |
| Prisma / Nexus | Login y lecturas HTTP autenticadas; prueba del conector a las **19:05:50 UTC** | Ventana acotada, no sincronización completa ni garantía de estabilidad del contrato |
| Startrack | Acceso web; API sin credenciales respondió `401` y exigió Basic; detalle propio respondió `403` | No se obtuvo ni validó API key para esta cuenta |

La prueba del conector Prisma consultó una página de un registro por colección:
equipos devolvió uno de un total informado de quince y solicitudes uno de dos.
Conservó cobertura parcial. La muestra confirmó que `clave` puede ser `null`
mientras `no_activo` contiene texto; `code` y `asset_number` permanecen separados.
El acceso detallado se documentó en [exploración de integraciones](integraciones-reales.md).

Estas comprobaciones fueron de lectura. No crearon registros operativos ni
regeneraron claves, y no habilitaron permanentemente live. El contrato Prisma
aportado después amplió la evidencia disponible: sus consultas y aprobación
están documentadas, pero no publica creación de proyectos/solicitudes ni webhooks
de aprobación. La autenticación observada mediante cookie no debe sustituirse
por una suposición derivada del esquema.

El acceso web a Startrack no demuestra acceso a su API. La validación autenticada
del SDK y del formato efectivo de creación de tareas de esta cuenta sigue
pendiente. Las capacidades documentadas y el comportamiento comprobado se
distinguen en [equivalencias Prisma–Startrack](equivalencias-prisma-startrack.md).

## Hechos que deben conservarse

- La asignación del kit es **RE-03 / MOT-006 / PROY-006**. CF-03 y MOT-014
  pertenecen a otro recorrido; no se mezclan sus identidades.
- La búsqueda inicial sin solicitud de PROY-006 solo describe esa consulta.
  Una captura posterior muestra una solicitud pendiente de ese proyecto,
  Cargador frontal, del 11 al 26 de septiembre, sin unidad ni UUID visible.
  Seleccionar maquinaria en un modal no prueba una asignación guardada.
- Estado administrativo, mantenimiento, tarea, ubicación y recepción son hechos
  distintos. Aprobar con unidad puede cambiar el inventario a Ocupada; una tarea
  completada puede coexistir con ese estado. La geocerca no acredita recepción.
- Conservar UUIDs, IDs externos, entorno y fechas originales. El nombre de una
  persona o proyecto, una clave repetida o un ID remoto aislado no valida el vínculo.
  Una solicitud puede tener varios movimientos y el GPS puede ser del transportador.
- La tarea histórica cuyo IDR coincidía con una solicitud tenía destino distinto
  y estaba cancelada: fue una candidata para revisar, no una equivalencia aprobada.
- El diccionario contiene tipos y ejemplos inconsistentes, coordenadas sin escala
  documentada y una definición duplicada. No convertir esos ejemplos en
  restricciones o posiciones geográficas supuestas. Ver
  [observaciones del diccionario](onedrive/06-diccionario-de-datos/README.md).

## Estado implementado y pendientes

La aplicación vigente usa Dash/FastAPI y PostgreSQL, conforme a
[ADR 0003](adr/0003-python-dash-hub.md) y
[ADR 0004](adr/0004-persistent-transfer-workflow.md). Ya existen planes persistidos,
cortes, eventos, cola de envío, worker explícito y recepción declarada. Los
registros antiguos de ausencia de estas funciones o de una aplicación React
describen etapas reemplazadas y permanecen en el historial Git.

El runtime usa cinco equipos y dos solicitudes proporcionados, sin tareas,
ubicaciones ni recepciones inventadas. Todo el caso es sintético; las muestras
documentales y las lecturas actuales del sandbox mantienen procedencia distinta.
No hay login de aplicación; los defaults deshabilitan gestión local y acceso
remoto. Se conservan Compose y su volumen PostgreSQL.

Falta validar la API de Startrack con acceso autorizado, correspondencias del
caso propio, catálogos de mantenimiento, responsabilidades, criterios de recepción
y compromisos de entrega. Tampoco hay mediciones que acrediten capacidad de flota
masiva, productividad o cumplimiento ISO. Las ampliaciones de
[sincronización y discrepancias](sincronizacion-y-discrepancias.md) y
[arquitectura escalable](arquitectura-escalable-flota.md) son propuestas, no
funcionalidades implementadas. Para ejecutar el servicio usar
[desarrollo](desarrollo.md) y [despliegue](despliegue-backend.md).
