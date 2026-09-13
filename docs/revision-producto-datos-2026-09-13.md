# Revisión de producto, pantallas y datos — 13/09/2026

Este documento conserva el diagnóstico anterior a la reorganización de interfaz.
La implementación posterior de layouts, búsqueda y gráficos está descrita en
[arquitectura frontend](frontend-architecture.md); la propuesta de sincronización,
en [integración por eventos](arquitectura-integracion-eventos.md).

Revisión estática del código y documentación de trabajo, con tres agentes Astra en razonamiento alto y consolidación del agente principal. Sin capturas, ejecución de tests, consultas a proveedores ni cambios de aplicación. Se preservaron los cambios existentes. Las referencias corresponden al árbol de trabajo revisado, no necesariamente a HEAD. No se comprobó la configuración del despliegue.

## Dictamen

La sobrecarga señalada es real. ECON expone simultáneamente la operación, la auditoría del dato y el catálogo metodológico de indicadores. La ausencia de evidencia ocupa más espacio que la decisión. Cambiar cada párrafo por un gráfico no resolvería la falta de observaciones: primero hay que ordenar el producto y luego representar lo que se puede sostener.

Los datos de entrada del caso son sintéticos; los cálculos, permisos, persistencia y reglas del flujo sí tienen implementación. `fixture` son cinco equipos y dos solicitudes documentales; `live` consulta el sandbox actual, que también es sintético. La muestra fixture contiene cinco de quince equipos reportados y no aporta historial operacional completo para inferir desempeño. No se comprobó cuántos equipos devuelve live actualmente.

La interfaz diaria debería contestar: **qué requiere atención, sobre qué registro, qué acción corresponde y qué evidencia la sostiene**. Modo, cobertura y frescura deben seguir visibles de forma breve. Fórmulas, UUID, nombres de campos, payloads y explicaciones extensas pueden consultarse bajo demanda.

## Revisión por pantalla

| Pantalla | Hallazgo en código | Cambio propuesto |
| --- | --- | --- |
| Cabecera y navegación | `views.py:168` muestra modo, solicitudes, cobertura, equipos y enlaces en todas las vistas del hub. `PAGES` (`views.py:1036`) coloca herramientas operativas y de diagnóstico casi al mismo nivel. | Una línea breve de entorno y calidad de lectura. Detalle por fuente en un desplegable. Agrupar Integración y Fuentes como herramientas de soporte, manteniendo sus permisos actuales. Personalizar el orden de trabajo por rol sin confundir navegación con autorización. |
| `/`, `/resumen` | `overview()` devuelve `decisions()` (`views.py:457`): no hay diferencia de contenido respecto a Decisiones. Tarjeta extensa por solicitud, sin paginación (`views.py:226`). | Una sola portada de atención. Bandeja acotada de excepciones con acción y enlace al registro; calendario de uso cuando aporte contexto. Mantener las rutas antiguas como alias si se simplifica el menú. |
| `/decisiones` | La misma portada. Acciones/calendario usan `requests_in_scope` (`views.py:304`), pero los insights calculan sobre el hub sin aplicar el filtro de visualización (`indicator_views.py:996`). | Consolidar con Resumen. Corregir la población de los indicadores de solicitudes o declarar explícitamente su alcance general; equipos y movimientos requieren su propio alcance. Un filtro no debe producir conclusiones aparentemente sobre otra población. |
| `/solicitudes` | La celda de traslado acumula estados, conteos, llegada y advertencias (`views.py:481`). | Tabla de proyecto, unidad, período, estado y siguiente acción. Traslado y recepción compactos; evidencia en detalle. El calendario responde mejor a planificación que un gráfico de dos estados con dos registros. |
| `/solicitudes/{id}` | Sugerencias, conflictos, interpretación, unidad, workflow, traslado, recepción, evidencia y alertas se encadenan (`views.py:792`). | Estado, impedimento principal y acción primero. Recorrido de hitos debajo. Una sola sección de excepciones; candidatas al entrar en la tarea de asignación; procedencia e historial consultables. |
| `/maquinaria` | Repite por fila disponibilidad no verificada, ausencia de vínculo y ubicación sin fecha (`views.py:624`). | Unidad, proyecto, estado administrativo y mantenimiento separados. Contexto común para faltantes; seguimiento y ubicación al detalle salvo excepción. Barras de estados posibles sobre equipos leídos, sin afirmar utilización o disponibilidad física. |
| `/maquinaria/{id}` | Comparación de fuentes y luego solicitudes, recepciones y movimientos (`views.py:887`). Startrack ausente genera muchos campos vacíos (`evidence_views.py:287`). | Hechos principales separados y excepción prioritaria. Un bloque breve cuando una fuente no está disponible. Cronología con eventos existentes; comparación completa de fuentes bajo demanda. |
| `/operaciones` | Registro y sincronización manual, sin bandeja específica de trabajo (`workflow_views.py:438`). La búsqueda filtra solo la página cargada (`workflow_views.py:368`). | Bandejas de conciliación, bloqueos, envío y recepción. Búsqueda/filtros en servidor, estado del proceso automático y última ejecución. Agregados del registro completo antes de añadir gráficos de volumen. |
| `/operaciones/{id}` | La comparación extensa de fuentes precede a programación y acción (`workflow_views.py:619`); encolar queda más abajo (`:720`). | Acción aplicable e impedimento arriba; hitos y fechas después. Programación editable cuando corresponda; referencia, payload y comparación técnica en detalle. |
| `/indicadores` | Siempre renderiza ocho fichas (`indicator_views.py:943`), incluso no evaluables. Cada ficha combina narrativa, evidencia, tabla y SLA (`:881`). Los SLA incluyen cinco campos metodológicos (`:822`), S1 aparece dos veces y hasta la ausencia de SLA recibe tarjeta (`:846`). | Resultados que se pueden interpretar primero. Los no evaluables en un bloque compacto con causa y requisito faltante. Definiciones y SLA propuestos en metodología, sin ocultar problemas de cobertura. Evitar ocho secciones vacías de utilidad operacional. |
| `/integracion` | Expande etapas, tiempos y mapeo de campos (`integration_views.py:281`); las etapas incluyen reglas técnicas (`:150`). | Conservarla como diagnóstico por solicitud. Mostrar etapa alcanzada y bloqueo antes de tablas y payload. No presentarla como destino principal de gerencia. |
| `/fuentes` | Expone procedencia, cobertura y estado de consultas (`views.py:923`), información repetida también en otras vistas. La muestra documental usa la misma familia de color activo que una fuente conectada (`:938`). | Tabla compacta de fuente, entorno, disponibilidad, alcance, última lectura válida y problema. Muestra documental con semántica neutral. La cabecera enlaza aquí sin repetir todo el contenido. |
| `/administracion` | Lista, alta y modal de edición tienen un propósito concreto (`admin_views.py:172`). El shell agrega selector de origen aunque los usuarios no pertenecen a fixture/live (`application.py:839`). `load_snapshot` tampoco omite esta ruta (`:675`). | Mantener tabla y edición. Alta bajo acción “Crear usuario”. Quitar el contexto de proveedores de esta pantalla y evitar lecturas del hub que no necesita. Preservar acceso exclusivo de administración. |
| `/login` | Formulario breve de correo/contraseña y errores (`auth_views.py:98`). | Mantenerlo. No hay motivo de producto para añadir gráficos o información operacional a una pantalla de acceso. |

Las rutas de código de esta tabla son relativas a `apps/api/app/dashboard/`.

## Problemas que empeoran con más datos

1. **Narrativas sin límite.** `_approval_time` y `_open_request_age` cuentan cada fila (`indicator_views.py:368`). Limitar a tres indicadores en `top_insights` no limita el tamaño de sus textos. Con volumen crecerá el texto y el coste de construir la vista. Proponer una frase por insight y enlace a una población paginada; no esconder faltantes relevantes.
2. **Gráficos limitados por evidencia.** `hours_figure` requiere al menos tres magnitudes evaluables (`indicator_views.py:660`); la muestra tiene una aprobación medible. La ausencia del gráfico obedece a una condición explícita. Un dato de 42 segundos puede verse en una fila; no necesita un gráfico para parecer analítico.
3. **Página del registro no equivale a población operacional.** El servicio publica cobertura, pero tablas e indicadores consumen una ventana del registro. Búsqueda, filtros y agregados deben resolverse sobre el alcance completo autorizado en servidor. La paginación de visualización no puede decidir el denominador de una métrica de negocio.
4. **SLA propuesto no equivale a cumplimiento calculado.** Las propuestas están en `indicator_views.py:150`. Hay horas hábiles sin calendario de cálculo y falta historial de fallas. S3 usa aprobación → envío aunque habla de envío tras asignar; sin evento `assigned_at`, esa duración no demuestra demora desde la asignación.
5. **Cobertura global poco informativa.** `services/hub.py:425` construye `HubScope.complete=False` incluso si Prisma terminó sus páginas. Esto conserva el límite de la integración, pero no distingue decisiones posibles con Prisma de decisiones bloqueadas por Startrack. Mostrar cobertura por fuente y por población, manteniendo la limitación global.

## Automatización e internalización

Interpreto “internalizar” como incorporar ECON a la operación interna con datos reales. No hace falta cambiar Dash/FastAPI/PostgreSQL para corregir estos problemas.

**Existe base útil:** registro durable, eventos, cola, permisos, conciliación de envíos inciertos, worker y scheduler. El proceso web crea `SyncScheduler` si está configurado (`app/main.py:93`). `sync_interval_seconds=0` y `auto_queue_transfers=False` son valores por defecto (`app/core/config.py:25,33`); no prueban la configuración efectiva del servidor. El sondeo del navegador cada 15 segundos no prueba que las fuentes estén siendo sincronizadas.

**Hay dos problemas de arquitectura de lectura:**

- `dashboard/application.py:675` llama `read_hub` por navegador, búsqueda o cambio de versión. En live, `services/hub.py:398` llama al conector; el worker también lee (`services/workflow.py:722`). Por tanto, añadir usuarios puede multiplicar lecturas remotas aunque el filtro de búsqueda sea local. Propuesta: ingesta central programada → observaciones persistidas y proyecciones de lectura → API/Dash. Navegar y filtrar deben consultar esas proyecciones. La revalidación antes de una escritura remota sigue siendo necesaria.
- `services/workflow.py:342` excluye la confirmación de una lectura sin cambios de la versión del registro; `services/ledger.py:64` excluye `data_as_of` de la huella del contenido. El navegador recarga por cambio de versión (`application.py:100`). Por inspección, un panel abierto puede conservar indicadores calculados con un corte viejo aunque el servidor vuelva a confirmar los mismos registros. Deben distinguirse versión del contenido, confirmación de lectura y momento de evaluación. No fabricar un corte nuevo con el reloj del navegador cuando el proveedor no confirmó los datos.

**Producción requiere un entorno explícito:** los conectores apuntan a orígenes del sandbox (`integrations/nexus.py:21`, `integrations/startrack.py:36`) y el contrato del hub acepta `local`/`sandbox` (`models/hub.py:15`). Startrack declara evidencia sintética (`integrations/startrack.py:230`). No se convierte en producción con el selector de modo: necesita conectores/configuración y contratos de procedencia coherentes, identidad por entorno, cobertura verificable e historial suficiente. No se consultaron secretos ni se habilitaron accesos.

Automatizar lecturas, validaciones, cola y seguimiento debe reducir trabajo repetido. La declaración de recepción sigue siendo un acto de una persona autorizada; GPS o tarea completada no la sustituyen. Conservar estado administrativo, mantenimiento, movimiento y ubicación como hechos distintos evita insights engañosos.

## Orden de ejecución recomendado

1. **Simplificación inmediata:** unificar portada/Decisiones; reducir metadatos repetidos; compactar indicadores no evaluables; trasladar fórmulas y SLA a metodología; acción primero en detalles. Conservar límites de evidencia y accesibilidad.
2. **Corrección funcional:** alinear filtros e insights, acotar narrativas y paginar las bandejas. Separar páginas de usuarios y operación de las consultas de datos que no necesitan.
3. **Lecturas automáticas consistentes:** centralizar ingesta, servir proyecciones persistidas y corregir actualización temporal sin cambios de contenido. Búsqueda y agregación completas en servidor.
4. **Analítica útil:** calendario de uso por unidad/proyecto, excepciones accionables, antigüedades por solicitud con corte válido e hitos por traslado. Tendencias solo al disponer de historial comparable; SLA solo con eventos y calendarios acordados.

La primera entrega de simplificación no necesita inventar más muestras ni sumar bibliotecas. Necesita reducir la cantidad de información que el usuario debe interpretar antes de actuar.
