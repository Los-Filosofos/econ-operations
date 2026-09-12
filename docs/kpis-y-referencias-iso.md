# Qué consultar ahora, indicadores e ISO

> Propuesta de la etapa inicial. El [modelo operativo](modelo-operativo.md) registra las reglas implementadas después; la [investigación ampliada](investigacion-manuales-y-diseno.md) incorpora el manual HTML de MAIC y los estados documentados por Startrack. Los indicadores futuros de esta guía siguen sujetos a sus condiciones de evidencia.

Propuesta de trabajo para Los Filósofos, revisada el **12 de septiembre de 2026**. Parte de los manuales, la exploración web y las lecturas HTTP documentadas en [integraciones-reales.md](integraciones-reales.md). No se calcularon KPIs globales ni se implementó el panel durante esta revisión.

Para entender primero el problema y recorrer las plataformas, comenzar por [la guía de navegación](guia-problema-y-navegacion.md).

## Decisiones de esta etapa

La siguiente etapa es **definir una consulta operativa confiable y sus reglas de medición**. Ya existe una base FastAPI/PostgreSQL y Nexus respondió a lecturas reales del sandbox. Antes de ampliar el backend necesitamos confirmar qué registro representa cada paso, quién lo actualiza y qué decisión tomará el usuario con él.

### Lectura dirigida de los manuales

| Material | Qué consultar ahora | Decisión que permite tomar |
| --- | --- | --- |
| [Manual Nexus](onedrive/05-manual-nexus.md) | Inventario; solicitudes de maquinaria; maquinaria del proyecto | Diferenciar solicitud, aprobación, asignación y estado del equipo |
| [Casos de uso](onedrive/04-casos-de-uso.md) | Solicitud/traslado; estados de objetos distintos; mantenimiento | Definir las relaciones y condiciones que debe explicar el hub |
| [Diccionario](onedrive/06-diccionario-de-datos/README.md) | IDs, maquinaria, proyecto, motorista, estados y fechas | Preparar un mapa de campos y registrar los que no tienen equivalente |
| [API de tareas Startrack](https://support.gps-platform.com/api/jobs/) | Objeto de tarea, estados y referencias externas | Distinguir planificación, cierre administrativo y relación con una solicitud |
| [Ubicaciones Startrack](https://support.gps-platform.com/api/locations/) | Última posición y fecha del reporte | Identificar qué activo se observa y cuán antigua es la señal |
| Manual Nexus, bitácoras y control de costos | Consultar en una segunda fase | Entender horas registradas y aprobaciones antes de hablar de productividad o costos |

El PDF explica que aprobar una solicitud con unidad asignada cambia el inventario a **Ocupada**. Las capturas también contienen solicitudes aprobadas sin unidad; por eso hay que verificar ambos campos. La aprobación no es una prueba de salida, llegada ni recepción física. [Manual, solicitudes](onedrive/05-manual-nexus.md#pagina-2-del-pdf-pagina-38-del-manual).

### Preguntas concretas para los responsables

Estas consultas se proponen para una conversación con el equipo de ECON; no se enviaron mensajes a otras personas.

| Responsable funcional propuesto | Pregunta | Qué debe quedar definido |
| --- | --- | --- |
| Logística y equipo | ¿Qué ID une una solicitud con sus tareas y puede haber varios viajes? | Correspondencias y cardinalidad, sin depender del nombre del motorista |
| Logística y campo | ¿El GPS corresponde a la maquinaria o al vehículo que la transporta? | Activo observado y asignación vigente durante cada viaje |
| Proyectos | ¿Qué evento confirma recepción y cuál es la fecha/hora comprometida? | Evidencia de entrega, responsable receptor y plazo de servicio |
| Mantenimiento | ¿Qué significa Obsoleta en este entorno y qué falla obliga a parar? | Catálogo validado; no equiparar baja definitiva con reparación automáticamente |
| Calidad / procesos | ¿Qué normas, procedimientos, metas y calendarios utiliza ECON actualmente? | Alcance aplicable y objetivos aprobados, sin inventar una meta ISO |
| Tecnología / proveedores | ¿Qué API, cuenta de servicio, límites y exportaciones soportan? | Clave de Startrack; contrato de Nexus; acceso y continuidad de los conectores |

Los organigramas identifican áreas, pero no aprueban esta asignación de responsabilidades. Debe validarse con [los responsables reales](onedrive/03-organigramas.md).

## Indicadores para el primer panel

Un indicador debe conducir a una acción. Conviene comenzar con las tres alertas de Nexus de la tabla, agregar trazabilidad y antigüedad de ubicación cuando Startrack esté conectado, y validar las fechas antes de publicar tiempos de aprobación.

**Disponibilidad técnica:** «Campos observados» significa que la API devolvió esos campos en muestras; todavía hay que revisar sus valores y recorrer todas las páginas del ámbito autorizado. No equivale a un KPI implementado ni a tener todos los datos de la empresa.

| Indicador | Cálculo propuesto | Usuario y decisión | Evidencia y condiciones |
| --- | --- | --- | --- |
| **Solicitudes pendientes cuyo inicio ya llegó** | Contar solicitudes pendientes con fecha de inicio anterior o igual a la fecha local de corte | Proyectos / logística: priorizar revisión y asignación | Campos `status`, `fecha_inicio`, `project_id` observados en Nexus; confirmar valores del catálogo. No llamarlo incumplimiento de entrega |
| **Solicitudes aprobadas sin unidad vinculada** | `100 × aprobadas sin maquinaria_id / aprobadas`; mostrar también ambas cantidades | Logística: revisar el vínculo faltante y acordar si necesita corrección | `status` y `maquinaria_id` observados. Cero aprobadas significa «sin casos», no 0 % de errores. No presupone que el registro sea inválido |
| **Equipos con falla activa registrada** | Contar equipos distintos con `active_failure_id` presente; separar los que tienen `active_failure_is_paro=true` | Mantenimiento: revisar equipos afectados y la decisión de paro | Campos observados; un valor de paro ausente queda desconocido. Falla activa no equivale por sí sola a equipo detenido |
| **Tiempo registrado hasta aprobación** | Mediana y percentil 90 de `approved_at − created_at`, para solicitudes aprobadas en el período | Proyectos: detectar esperas administrativas y revisar el proceso | Campos observados; validar horas, zona y reaprobaciones. Publicar también pendientes y antigüedad para no ocultar solicitudes que siguen esperando |
| **Cobertura de vinculación solicitud–traslado** | `100 × solicitudes que requieren traslado y tienen vínculo validado / solicitudes que requieren traslado` | Logística / proyectos: localizar operaciones que aún necesitan conciliación | Requiere definir cuáles necesitan traslado y validar tarea, recurso y destino. No tomar todas las aprobadas como denominador automáticamente. Denominador cero: «sin casos evaluables» |
| **Antigüedad de la última posición** | `instante de corte − fecha del último reporte de posición`, por activo | Logística: saber si la ubicación sirve para tomar una decisión o debe verificarse por otro medio | Startrack documenta `epoch` en `/api/fleet/status`; pendiente probar con la API key, su unidad temporal y frecuencia esperada |

La [API de ubicaciones](https://support.gps-platform.com/api/locations/) sustenta el campo temporal documentado. Las rutas y campos Nexus efectivamente probados se enumeran en [la revisión de integración](integraciones-reales.md#nexus--maic-api-interna-comprobada). La cobertura de vinculación es una regla propuesta para nuestro hub, no un indicador entregado por el proveedor.

Como contexto adicional se puede mostrar la **distribución del estado administrativo del inventario**, siempre con su fecha. No debe llamarse disponibilidad física ni utilización. No excluir automáticamente `OBSOLETA` del denominador: el material presenta una ambigüedad entre baja y mantenimiento que debe resolverse primero.

### Indicador de resultado para una segunda etapa: puntualidad de recepción

La pregunta de negocio es si el proyecto recibió la maquinaria cuando la necesitaba. Definir primero la cohorte de traslados evaluables cuyo compromiso vence en el período. Propuesta: `100 × traslados de esa cohorte con recepción validada dentro del compromiso / total de traslados de esa cohorte`. Si está vacía, mostrar «sin casos evaluables».

Para calcularlo faltan un compromiso fechado, una regla de recepción, su evidencia y el vínculo correcto al traslado. Los casos pendientes que ya vencieron y tienen seguimiento suficiente son incumplimientos, no se eliminan del cálculo; los casos sin evidencia suficiente se muestran como desconocidos junto con la **cobertura de medición**. Las cancelaciones y cambios de plazo deben tener una política documentada y conservar su historia para que el indicador no mejore al borrar o reprogramar casos atrasados.

La tarea Startrack documenta `closed_date`, pero puede registrar cierre por completar o cancelar. `start_date` es planificación y `last_status_change_date` es un cambio de estado. No equivalen a recepción física; tampoco una entrada a geocerca demuestra por sí sola aceptación por el proyecto. [Contrato de tareas](https://support.gps-platform.com/api/jobs/).

## Reglas para que los números sean defendibles

- **Ámbito y corte:** organización, proyecto, tipo de equipo, período y fecha/hora de consulta. La fecha local de negocio es America/El_Salvador; conservar instantes con zona horaria y no convertir una fecha sin hora en una hora prometida inventada.
- **Cobertura:** cantidad de registros evaluados, excluidos y desconocidos, más numerador y denominador. Una respuesta parcial, falta de permisos o fuente caída no produce un cero global.
- **Procedencia:** separar conexión al sandbox, copia fechada y simulación local. Nunca completar un dato faltante con una cifra inventada sin indicarlo.
- **Tiempo:** diferenciar fecha del evento, recepción en el hub y planificación. Un reporte antiguo puede haberse sincronizado hace segundos; mostrar ambas edades. Fechas futuras o negativas por incoherencia no se convierten silenciosamente en cero.
- **Historia:** una consulta de estados actuales no reconstruye el mes anterior. Para tendencias se necesitan eventos o copias periódicas con fecha. El `updated_at` actual no reemplaza un historial.
- **Metas:** fijar umbrales con los responsables y una línea base representativa. No hay un porcentaje objetivo aprobado en los materiales revisados para estos indicadores; no atribuir 95 %, 98 % u otra cifra a ISO.
- **Acción:** cada tarjeta permite ver los casos que la forman, su responsable y la evidencia. Usar «sin información suficiente» cuando corresponda.

No derivar **tiempo muerto** del motor apagado, ni **productividad** de estar dentro de una geocerca. MTTR (tiempo medio de reparación) necesita eventos de inicio y fin válidos; OEE requiere datos de disponibilidad, rendimiento y calidad que no se han confirmado. Las horas de horómetro del manual tampoco equivalen automáticamente a horas productivas. [Bitácoras y limitaciones del manual](onedrive/05-manual-nexus.md).

## Normas ISO que conviene consultar

Se consultaron fichas públicas oficiales, no el texto completo de normas de pago ni una auditoría de ECON. Las siguientes aplicaciones son **propuestas de diseño del hub**. Un panel o una base de datos no acredita por sí solo conformidad o certificación. No se recibió confirmación de certificaciones vigentes de ECON ni de metas internas.

| Referencia | Qué aporta | Aplicación propuesta al hub |
| --- | --- | --- |
| **ISO 9001 — gestión de la calidad** | Enfoque sobre procesos, requisitos del servicio y mejora | Definir quién solicita, asigna y recibe; documentar la medición y revisar demoras con evidencia |
| **ISO 55001:2024 — gestión de activos** | Relacionar desempeño, riesgo y costo de los activos a lo largo de su ciclo de vida | Identidad estable del equipo, condición de mantenimiento e historial para decidir sobre asignaciones |
| **ISO/IEC 27001:2022 — seguridad de la información** | Gestión del riesgo sobre la confidencialidad, integridad y disponibilidad de información | Acceso por rol/proyecto, secretos en el servidor, auditoría y recuperación de información |
| **ISO 39001:2012 — seguridad vial** | Gestión de riesgos relacionados con muertes y lesiones graves en el tránsito | Validar restricciones de seguridad al planificar traslados; acompañar puntualidad con controles de seguridad definidos por ECON |

Fuentes oficiales para cada referencia y su alcance: [ISO 9001](https://www.iso.org/standard/9001), [ISO 55001:2024](https://www.iso.org/standard/83054.html), [ISO/IEC 27001:2022](https://www.iso.org/standard/27001), [ISO 39001:2012](https://www.iso.org/standard/44958.html). La última columna es nuestra interpretación aplicada al proyecto, no una lista literal de requisitos de esas normas.

**Precisión de versión al 12/09/2026:** ISO muestra 9001:2015 como edición publicada y su revisión de 2026 como **en publicación**, con reemplazo anunciado para el 16 de septiembre de 2026. No debe tratarse hoy la nueva edición como una norma ya publicada. Las fichas de 9001:2015, 27001:2022 y 39001:2012 también muestran una enmienda de 2024; para una evaluación formal hay que confirmar el conjunto aplicable con el responsable de calidad. [Edición publicada de 9001](https://www.iso.org/standard/62085.html), [estado de la nueva edición](https://www.iso.org/standard/9001).

Para esta etapa priorizar **9001 y 55001** como referencias de proceso y activos, incorporar desde el inicio controles básicos de acceso e historial, y consultar seguridad vial con el área competente antes de proponer indicadores de conducción. No incentivar velocidad ni evaluar individualmente a un motorista a partir de una señal incompleta o un atraso sin causa validada.

## Próximo resultado que debemos construir

Una consulta de una maquinaria seleccionable que muestre su solicitud, asignación, tarea relacionada, ubicación fechada y estado de mantenimiento. Para `RE-03`, un vínculo no encontrado debe quedar visible como tal. Mostrar estados originales, evidencia y procedencia precede a calcular indicadores integrados.

El trabajo siguiente sería: confirmar reglas con las tres áreas, documentar IDs y campos nuevos, construir el conector de lectura de Nexus, obtener la API key de Startrack y después añadir tres alertas iniciales más la información de actualización de las fuentes. Los casos simulados locales permiten verificar las reglas durante ese proceso; no prueban acceso a Startrack.

Para medir el impacto del hub, comparar en un piloto representativo el tiempo que tarda una persona en resolver la misma consulta operativa, la proporción de casos que consigue vincular y las incidencias que requieren seguimiento. Registrar tamaño de muestra y condiciones. Reducir consultas manuales y anticipar asignaciones son beneficios esperados; aún no hay evidencia para prometer porcentajes de ahorro o resultados financieros.
