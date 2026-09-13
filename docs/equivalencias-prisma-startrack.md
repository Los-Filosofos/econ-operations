# Equivalencias de datos entre Prisma, ECON y Startrack

Revisión: **12 de septiembre de 2026**. Alcance: sandbox sintético, formulario de
tarea suministrado por el usuario y código vigente. Este documento responde a
RF-01, RF-02 y RF-03 del [brief](onedrive/02-brief-del-reto.md).

**Una solicitud de Prisma no es una tarea de Startrack.** Prisma aporta el
proyecto, el requerimiento, su aprobación y la maquinaria asignada. Logística
debe completar la programación del movimiento y confirmar las correspondencias
con geocerca y usuarios de Startrack. ECON conserva ambos lados y su evidencia;
no iguala sus estados ni sus identificadores.

## Cómo leer las matrices

| Clasificación | Significado |
| --- | --- |
| Directa | Conserva el mismo hecho y valor. Puede cambiar el nombre del campo dentro de ECON. |
| Transformada | Deriva un valor mediante una regla explícita; no demuestra identidad entre plataformas. |
| Manual | Requiere una decisión o correspondencia confirmada por una persona. Que exista un catálogo no resuelve esa decisión. |
| Sin equivalente | El dato describe otro objeto o no está disponible en la fuente consultada. |
| No soportado | El flujo de ECON no lo implementa o el contrato público consultado no expone la opción del formulario. Se distingue cuál de estos límites aplica. |

**Implementado** significa presente en el código y comprobado con transporte
simulado; no significa validado contra la cuenta de Startrack. **Documentado**
significa publicado en el contrato citado. **Pendiente de validación autenticada**
incluye permisos, IDs, valores de catálogo y respuesta real de esa cuenta.

En las tablas, `Solicitud` y `Equipo` son los objetos devueltos por
`/api/maquinaria/requests` y `/api/maquinaria/equipos`; sus detalles usan `/{id}`.
`Proyecto` corresponde a `/api/projects`; `Operador`, a
`/api/maquinaria/operadores`. Los nombres de campo proceden del
[OpenAPI suministrado](../econ-hackathon-openapi.json), contrastado con el
[PDF del sandbox](../Prisma-Sandbox-API.pdf), especialmente páginas 1–2, 12,
14–15 y 20–23. El [diccionario Prisma](onedrive/06-diccionario-de-datos/02-prisma.md)
y el [diccionario Startrack](onedrive/06-diccionario-de-datos/03-startrack.md)
explican las etiquetas de negocio, pero no sustituyen esos contratos.

## Identidad y cardinalidad

| Relación | Cardinalidad y decisión necesaria | Implementación vigente |
| --- | --- | --- |
| Proyecto → solicitudes | Un proyecto puede tener varias solicitudes. Cada solicitud conserva su `project_id`. | Unión por UUID, nunca por `project_name`. |
| Solicitud → maquinaria | Cada registro tiene cero o una `maquinaria_id`; una máquina puede figurar en varias solicitudes a lo largo del tiempo. | Sin unidad no se prepara el traslado. El tipo solicitado no identifica una unidad. |
| Solicitud → movimientos → tareas | Una solicitud puede requerir varios movimientos. Cada movimiento local tiene cero o un `job_id` confirmado. | La referencia distingue movimientos; no se fuerza una tarea por proyecto ni una tarea por solicitud. |
| Proyecto ↔ geocerca | No hay relación 1:1 acreditada por las muestras. Un proyecto podría requerir distintos destinos. | Cada movimiento guarda explícitamente `project_source_id` y `poi_id`. No existe un catálogo maestro de equivalencias con vigencias independientes. |
| Maquinaria ↔ vehículo rastreado | No hay identidad automática. El GPS puede estar en la máquina o en el transportador. | `Movement.tracked_vehicle_id` es una elección separada; no se envía como campo de Job. |
| Operador Prisma ↔ conductor ↔ usuario Startrack | Son entidades e identificadores distintos. La tarea admite varios usuarios. | Se eligen `assigned_user_ids`; no se deducen de nombres, código MOT, solicitante o conductor del vehículo. |

`RequestRecord.id` y `EquipmentRecord.id` añaden los prefijos
`nexus:request:` y `nexus:equipment:`. El UUID original sigue en
`provenance.source_id`; los campos `*_source_id` del mapeo usan ese original.
`Movement.id` es un ID local. `Job.id` es el ID asignado por Startrack.
`movement_reference` es una referencia creada en ECON y enviada a
`Job.remote_id`; **no es un UUID de solicitud renombrado**. La base impone
unicidad local por modo, entorno y referencia, sin atribuir esa garantía al
proveedor. Ver [modelos de lectura](../apps/api/app/models/hub.py),
[operaciones](../apps/api/app/models/operations.py) y
[preparación](../apps/api/app/services/transfers.py).

La unicidad documentada de `POI.remote_id` por cliente no debe trasladarse a
`Job.remote_id`, cuyo contrato no publica esa garantía. `GEO-014`, `MOT-014`,
`CF-03` o el número ilustrativo `24` del diccionario tampoco acreditan IDs API
de la cuenta. [Contrato de geocercas](https://support.gps-platform.com/api/pois/),
[contrato de tareas](https://support.gps-platform.com/api/jobs/).

## Matriz completa del formulario de tarea suministrado

Las filas cubren las pestañas, controles y columnas visibles de ese formulario.
Una opción visible en Startrack puede usar un contrato interno distinto del API
público; su existencia visual no autoriza a inventar una clave de integración.
La columna API usa únicamente nombres publicados. La decisión de enviar o
conservar cada dato se contrasta con
[`StartrackTaskDraft`](../apps/api/app/integrations/startrack.py),
[`TransferMapping` y `prepare_transfer`](../apps/api/app/services/transfers.py)
y el [formulario actual de ECON](../apps/api/app/dashboard/workflow_forms.py).

### Identificación, contenido y estado

| Campo del formulario | Prisma: campo exacto o ausencia | Modelo normalizado / regla de ECON | Campo API de Startrack | Clasificación y alcance |
| --- | --- | --- | --- | --- |
| Detalles | No es un dato de Prisma. | Sección de presentación. | Ninguno. | Sin equivalente; pestaña, no propiedad de Job. |
| Título * | `Equipo.clave`, `no_activo`, `nombre`; `Solicitud.project_name`, `project_id`. | `EquipmentRecord.code`, `asset_number`, `name`; `RequestRecord.project_name`, `project_id` → texto «Traslado de … a …», máximo 255 caracteres. | `objective` | Transformada; implementada. El texto ayuda a leer, no se usa para unir fuentes. |
| ID remoto | No hay referencia de movimiento en la solicitud. | `TransferMapping.movement_reference` → `StartrackTaskDraft.remote_id`. | `remote_id` | Manual; implementada. Obligatoria en ECON, sin unicidad remota garantizada. |
| Descripción | `Solicitud.comentarios` y los UUID de solicitud, maquinaria y proyecto. | `RequestRecord.comments` conserva comentarios. El borrador actual genera una descripción con los tres UUID y la referencia del movimiento; **no copia los comentarios**. | `description` | Transformada; implementada para trazabilidad. Trasladar observaciones del PM sería una ampliación. |
| Tipo | `Solicitud.tipo` es clase de maquinaria; no categoría de tarea. | `RequestRecord.machinery_type` queda separado. `TransferMapping.job_type_id` se elige del catálogo de tareas. | `job_type_id` | Manual; opcional en API de ECON/SDK, sin control visible en el formulario simplificado actual. «Cargador frontal» no se convierte en tipo «Traslado». |
| Estado / Pendiente | `Solicitud.status`; `Equipo.estado`. | Se conservan en `RequestRecord.status` y `EquipmentRecord.machinery_status`. El retorno de Startrack va a `Movement.status` y `workflow_role`. | `status` | Sin equivalencia de valores; lectura implementada. ECON no envía `status` al crear ni fuerza el «Pendiente» mostrado en la captura. |
| Adjuntos | Ningún adjunto de solicitud en el contrato leído. | Sin campo de borrador ni carga de archivos en ECON. | `files` | Documentado en Job; no soportado por el flujo actual. No equivale automáticamente a evidencia de recepción. |
| Actividad | El historial de maquinaria tiene `event_type`, `event_at`, `actor_user_id`, entre otros; no es actividad de una tarea. | `OperationEvent` registra eventos propios y observaciones; no importa el historial completo de ninguna plataforma. | Sin una colección de actividad de Job en el contrato consultado. | Sin equivalente directo; no se copia historial de maquinaria como actividad de traslado. |

### Programación y ubicación

| Campo del formulario | Prisma: campo exacto o ausencia | Modelo normalizado / regla de ECON | Campo API de Startrack | Clasificación y alcance |
| --- | --- | --- | --- | --- |
| Fecha programada | `Solicitud.fecha_inicio` inicia el uso solicitado, no la ejecución del traslado. | `RequestRecord.starts_on` queda separado; `TransferMapping.scheduled_date` debe indicarse expresamente. | `start_date` | Manual; implementada, fecha `AAAA-MM-DD`. |
| Hora de fecha programada | La solicitud no tiene hora de traslado. | `TransferMapping.scheduled_time`; la UI acepta `HH:MM` y la acción normaliza segundos. | `start_time` | Manual; implementada, opcional, `HH:MM:SS`. |
| Completar antes de | `Solicitud.fecha_fin` finaliza el uso solicitado. No establece un plazo de traslado. | `RequestRecord.ends_on` no se convierte en vencimiento. | No documentado en Job. | Sin equivalente y no soportado. No inventar `end_date` ni `deadline`. |
| Hora de Completar antes de | No disponible. | Sin campo normalizado para ese plazo. | No documentado en Job. | No soportado; requiere contrato y decisión de negocio. |
| Origen | `Equipo.project_id` es asignación administrativa; no prueba el punto de salida actual. | No hay origen en `TransferMapping` ni `StartrackTaskDraft`. | No documentado como origen de Job. | Sin equivalente y no soportado. No inventar `origin_poi_id`; una segunda tarea exigiría modelar otra operación expresamente. |
| Destino | `Solicitud.project_id`, `project_name`; opcionalmente `Proyecto.id`, `name`. | `RequestRecord.project_id` + correspondencia explícita `TransferMapping.poi_id`. | `poi_id` | Manual; implementada. ECON valida presencia en catálogo, no deduce el vínculo por nombre. |
| El usuario debe estar en la Geocerca para completar la tarea | No existe esa condición en la solicitud. | Sin campo de mapeo/borrador. | No documentado en Job. | No soportado. `required_form_ids` no activa esta condición. |
| Latitud | No está en Solicitud/Proyecto consultados. El historial de maquinaria sí documenta `gps_latitude`, nullable, para otro evento. | No hay coordenada de destino en el mapeo. `StartrackPoi` actual tampoco conserva geometría. | `POI.y` para geocerca; `Job.completed_lat` / `Job.y` corresponden a finalización, no a destino planificado. | Sin equivalente directo; geometría no implementada. No copiar una coordenada histórica ni de cierre al destino. |
| Longitud | Mismo límite; el historial puede contener `gps_longitude`, nullable. | Sin coordenada normalizada de destino. | `POI.x` para geocerca; `Job.completed_lon` / `Job.x` corresponden a finalización. | Sin equivalente directo; geometría no implementada. |
| Dirección o referencia | `Proyecto.description` puede ser solo una ciudad. `Solicitud.comentarios` no es una dirección estructurada. | `NexusProject.description` es lectura opcional; no pasa al borrador. | `address` | Manual; documentado, no soportado por el borrador actual. No geocodificar por suposición. |
| Ventana horaria de entrega: de | No disponible; inicio de uso no fija una ventana de llegada. | Sin campo. | No documentado en Job. | No soportado. No reutilizar `start_time` con otro significado. |
| Ventana horaria de entrega: a | No disponible; fin de uso no fija una ventana de llegada. | Sin campo. | No documentado en Job. | No soportado. |
| Duración / Minutos | No hay duración estimada del traslado. `minimum_usage_hours` pertenece al uso del equipo. | Sin campo en borrador; una futura conversión tendría que aplicar minutos × 60. | `duration` | Transformada si se incorpora; hoy solo documentada. La unidad API es segundos, no horas de uso ni diferencia entre fechas de solicitud. |

Los nombres de Job y sus límites se contrastaron con el
[API público de tareas](https://support.gps-platform.com/api/jobs/).
La interpretación de coordenadas de geocerca procede del
[API de POI](https://support.gps-platform.com/api/pois/).
Las opciones marcadas como no documentadas son lagunas del contrato consultado,
no una afirmación de que la interfaz de Startrack carezca de ellas.

### Asignación y formularios

| Campo del formulario | Prisma: campo exacto o ausencia | Modelo normalizado / regla de ECON | Campo API de Startrack | Clasificación y alcance |
| --- | --- | --- | --- | --- |
| Asignar a | `Operador.id`, `nombre`, `cod_trabajador`; el detalle de equipo incluye `associated_operators`. `Solicitud.requested_by_user_id` identifica al solicitante. | `NexusOperator` permite lectura de catálogo. La preparación exige `TransferMapping.assigned_user_ids` confirmado independientemente. | `assigned_user_ids` | Manual; implementada. No usar UUID de operador o solicitante como ID de usuario Startrack. |
| Formularios | No hay IDs de formularios Startrack en Prisma. | `StartrackTaskDraft.form_ids` y `required_form_ids` existen; `TransferMapping` no los recibe y `prepare_transfer` no los propaga. | `form_ids`, `required_form_ids` | Manual; soporte de SDK, pendiente en preparación/UI y selección de catálogo. No hay un formulario de recepción elegido por defecto. |

El catálogo de [usuarios Startrack](https://support.gps-platform.com/api/users/)
identifica usuarios asignables; no demuestra la correspondencia con un operador
Prisma. `Vehicle.driver_id` identifica un conductor, no necesariamente uno de
esos usuarios. El adaptador conserva esos IDs como hechos separados.

### Artículos y valores económicos

| Campo del formulario | Prisma: campo exacto o ausencia | Modelo normalizado / regla de ECON | Campo API de Startrack | Clasificación y alcance |
| --- | --- | --- | --- | --- |
| Artículos | No existe una lista de artículos de entrega en la solicitud de maquinaria. | Sin colección de artículos. | No documentada en Job. | Sin equivalente y no soportado. La existencia de APIs de pedidos/productos no documenta su vínculo con esta tarea. |
| Cant. | Una `maquinaria_id` no es cantidad comercial; una solicitud por tipo tampoco autoriza inventar una unidad entregada. | Sin campo. | No documentado en Job. | Sin equivalente y no soportado. |
| Descripción del artículo | `Equipo.nombre` describe una máquina, no una línea de pedido. | `EquipmentRecord.name` queda en maquinaria. | No documentado como artículo de Job. | Sin equivalente directo; no confundir con `Job.description`. |
| SKU | `clave` y `no_activo` identifican el equipo en su dominio; no son un SKU acreditado. | `code` y `asset_number` separados. | No documentado en Job. | Sin equivalente y no soportado. |
| Volumen m³ | No disponible en el contrato leído de maquinaria/solicitud. | Sin campo. | No documentado en Job. | Sin equivalente y no soportado; no estimar por clase de máquina. |
| Peso kg | No disponible en el contrato leído de maquinaria/solicitud. | Sin campo. | No documentado en Job. | Sin equivalente y no soportado; no estimar por nombre/modelo. |
| Precio unitario | `precio_x_hora`, `current_project_rate.precio_x_hora`, `effective_precio_x_hora` son tarifas por hora de equipo. | No están en `EquipmentRecord` ni en el borrador. | No documentado como precio de artículo de Job. | Sin equivalente y no soportado. No convertir tarifa horaria en precio de transporte o de artículo. |
| Total GTQ | La solicitud no aporta total de artículos ni moneda acreditada para su tarifa horaria. | Sin cálculo ni conversión monetaria. | No documentado en Job. | Sin equivalente y no soportado. GTQ es la etiqueta de esa pantalla; no fija la moneda de Prisma. |

### Contacto y notificaciones

| Campo del formulario | Prisma: campo exacto o ausencia | Modelo normalizado / regla de ECON | Campo API de Startrack | Clasificación y alcance |
| --- | --- | --- | --- | --- |
| Contacto: Nombre | `requested_by_name` es solicitante; `manager_name` es gerente, sin confirmar quién recibe. | `RequestRecord.requested_by` no se convierte en contacto. | `contact_name` | Manual; documentado, no soportado por el borrador actual. |
| Contacto: Teléfono | No disponible en el objeto de solicitud leído. | Sin campo. | `phone_number` | Manual; documentado, no soportado. No se obtiene del código MOT. |
| Contacto: Email | No disponible en el objeto de solicitud leído. | Sin campo. | `contact_email` | Manual; documentado, no soportado. No usar correo de autenticación. |
| Notificaciones de estado: Emails | No hay destinatarios aprobados para la tarea en Prisma. | Sin campo de destinatarios. | `notification_emails_csv` | Manual; documentado, no soportado por ECON. |
| Notificaciones de estado: Teléfonos | No hay destinatarios aprobados para la tarea en Prisma. | Sin campo de destinatarios. | `notification_phone_numbers_csv` | Manual; documentado, no soportado por ECON. El máximo de cinco y el prefijo de país son instrucciones visibles del formulario; requieren validar además las restricciones API. |
| Activación de aviso al contacto | No deriva de aprobar la solicitud. | `StartrackTaskDraft.notify_contact=False`; transporte envía `0`. | `notify_contact` | Decisión explícita implementada: ECON no solicita avisos al contacto ni envía listas de destinatarios. Las reglas propias de la cuenta deben verificarse aparte. |

Los campos de contacto y avisos pertenecen al
[contrato de Job](https://support.gps-platform.com/api/jobs/). Su disponibilidad
documental no significa que el flujo actual los acepte. Tampoco se reutiliza la
notificación al PM descrita en el manual de Prisma como autorización para enviar
mensajes desde ECON.

## Otros campos API de tarea que no deben perder su significado

Esta tabla completa los campos de Job no cubiertos por controles editables en
la captura. La referencia técnica es el
[objeto Job publicado](https://support.gps-platform.com/api/jobs/); la selección
efectiva de lectura/escritura está en
[el adaptador](../apps/api/app/integrations/startrack.py).

| Campo Startrack | Origen y modelo en ECON | Estado / equivalencia |
| --- | --- | --- |
| `id` | Retorno de Startrack → `StartrackJob.id` → `Movement.job_id`. | Lectura implementada; no se envía el ID Prisma como ID de tarea. |
| `client_id` | Cuenta propietaria Startrack. | Sin equivalente con `Solicitud.org_id`; fuera del DTO mínimo. |
| `created_by` | Autor Startrack. | No es `requested_by_user_id` ni `approved_by_user_id`; fuera del DTO mínimo. |
| `creation_date` | `StartrackJob.creation_date`. | Lectura implementada; no copia `Solicitud.created_at`. |
| `changed_date` | `StartrackJob.changed_date`; evidencia de cambio remota. | Lectura implementada; ECON no la escribe. No equivale a `Solicitud.updated_at`. |
| `closed_date` | `StartrackJob.closed_date`; conservada en la observación. | Lectura implementada; cierre no acredita recepción. |
| `last_status_change_date` | `StartrackJob.last_status_change_date`; conservada en la observación. | Lectura implementada; fecha de estado de tarea, no fecha de aprobación. |
| `assigned_user_remote_ids` | No utilizado; la preparación exige IDs técnicos Startrack. | Documentado, no soportado. No suponer que contiene códigos MOT o UUID Prisma. |
| `job_type_remote_id` | No utilizado; se acepta `job_type_id`. | Documentado, no soportado. |
| `poi_name` | Nombre remoto de geocerca. | Documentado, fuera del DTO de Job. El catálogo conserva `StartrackPoi.name`; no se envía para resolver un nombre ambiguo. |
| `custom_fields` | Sin esquema de cuenta acordado ni modelo normalizado. | Documentado, no soportado. No usarlo como contenedor arbitrario para suplir todas las lagunas del formulario. |

## Inventario Prisma que se conserva y que no viaja a la tarea

La normalización está implementada en
[`_map_live`](../apps/api/app/services/hub.py) y los DTO de
[Nexus](../apps/api/app/integrations/nexus.py). La correspondencia directa de un
campo Prisma con ECON **no implica** que tenga equivalente en Startrack.

| Campo Prisma | Modelo de ECON | Relación real con Startrack |
| --- | --- | --- |
| `Solicitud.id` | `RequestRecord.provenance.source_id`; `id` con prefijo; `Movement.request_source_id`. | Trazabilidad en descripción y almacenamiento local; no es `Job.id`. |
| `Solicitud.project_id`, `project_name` | `RequestRecord.project_id`, `project_name`. | Destino solo mediante mapeo a POI; nombre para presentación. |
| `Solicitud.maquinaria_id` | `RequestRecord.machinery_id` con prefijo. | Vincula el equipo por UUID; no asigna un `vehicle_id` a Job. |
| `Solicitud.maquinaria_no_activo`, `maquinaria_nombre`, `maquinaria_clave` | Campos expandidos de la respuesta, no una segunda entidad normalizada. ECON consulta el equipo por su UUID. | No resuelven identidad Startrack por texto. |
| `Solicitud.tipo` | `RequestRecord.machinery_type`. | Clase solicitada; no `job_type_id`. |
| `Solicitud.fecha_inicio`, `fecha_fin` | `RequestRecord.starts_on`, `ends_on`. | Período de uso; no fechas de entrega. |
| `Solicitud.requested_by_user_id`, `requested_by_name` | `RequestRecord.requested_by_id`, `requested_by`. | Solicitante; no usuario ejecutor, autor de Job ni receptor. |
| `Solicitud.status` | `RequestRecord.status`. | Aprobación como condición previa; no traducción a estado de tarea. |
| `Solicitud.comentarios` | `RequestRecord.comments`. | Contexto preservado; el borrador actual no lo transmite. |
| `Solicitud.created_at`, `updated_at`, `approved_at` | Mismos nombres en `RequestRecord`. | Instantes de Prisma, distintos de creación/cierre del Job. |
| `Solicitud.approved_by_user_id`, `approved_by_name` | El DTO admite el ID del aprobador, pero `RequestRecord` no lo conserva; el nombre no está en el DTO. | Brecha de trazabilidad del aprobador; no sustituirlo por solicitante. |
| `Solicitud.org_id` / `Equipo.org_id` | Fuera de los DTO mínimos. | No equivale a `Startrack.client_id`; actualmente la operación se acota por proveedor y sandbox. |
| `Equipo.id`, `clave`, `no_activo`, `nombre` | `provenance.source_id`, `code`, `asset_number`, `name`. | UUID técnico separado de las etiquetas; texto derivado para título. `clave=null` permanece distinto de `no_activo`. |
| `Equipo.empresa`, `clase_equipo` | `company`, `equipment_class`. | No son cliente, grupo, etiqueta ni tipo de tarea Startrack. |
| `Equipo.project_id`, `project_name` | Mismos nombres en `EquipmentRecord`. | Asignación administrativa. No demuestran presencia en una geocerca. |
| `Equipo.estado` | `EquipmentRecord.machinery_status`. | Sin equivalencia con `Job.status` ni con estado GPS. |
| `Equipo.active_failure_id`, `active_failure_status`, `active_failure_is_paro` | `maintenance_failure_id`, `maintenance_status`, `maintenance_is_stopped`. | Restricción de mantenimiento independiente del traslado. `null`/ausente no se convierte en `false`. |
| `Equipo.created_at`, `updated_at` | Mismos nombres en `EquipmentRecord`. | No son observación GPS ni lectura actual. |
| `Equipo.marca`, `modelo`, `anio` | Fuera del DTO actual. | Posibles atributos descriptivos de un vehículo; solo después de confirmar identidad. No se sincronizan. |
| `Equipo.fecha_inicio_uso`, `fecha_fin_uso`, `observaciones_asignacion` | Fuera del DTO actual. | Hechos de asignación; no programación del traslado. |
| `Equipo.line_item_id`, `assigned_line_item`, `assigned_personnel` | Fuera del DTO actual. | Partida/personal de obra; no artículos, formularios o asignados de Job. |
| `Equipo.associated_operators` del detalle | Fuera de `NexusEquipment`. El catálogo `NexusOperator` se lee por separado. | No hay mapeo operador/conductor/usuario vigente. |
| `Equipo.precio_x_hora`, `minimum_usage_hours`, `catalog_precio_x_hora`, `current_project_rate`, `project_rates`, `effective_precio_x_hora` | Fuera del DTO actual. | Tarifas y vigencias; no precio de artículo, duración del Job ni costo de traslado. |
| `Equipo.motivo_baja`, `fecha_baja`, `mantenimiento_fecha_inicio`, `mantenimiento_fecha_fin`, `mantenimiento_notas`, `occupied_without_project`, `fallas_count` | Fuera del DTO actual; algunos aparecen solo en listado o detalle. | Información adicional de inventario/mantenimiento; no debe reducirse a estado de tarea. |
| `Proyecto.id`, `name`, `status`, `description`, `start_date`, `end_date`, `project_manager_user_id`, `manager_name`, fechas de auditoría/archivo | `NexusProject` en lectura opcional; no forma parte del `read()` habitual del hub. | Catálogo administrativo; correspondencia con POI requiere decisión independiente. |
| Presupuestos, avance, cliente, notas e indicadores de Proyecto | Fuera de `NexusProject`. | Sin destino definido en Job; no se fabrican costos de artículos ni porcentajes operativos. |
| `Operador.id`, `nombre`, `cod_trabajador`, `is_active`, `created_at`, `updated_at` | `NexusOperator`; lectura opcional. | No prueba usuario Startrack asignable ni conductor del activo rastreado. |
| Historial: `gps_latitude`, `gps_longitude`, `gps_accuracy_meters`, `gps_captured_at` | Ruta documentada de historial, no leída por el conector actual. Ejemplo con valores nulos. | Posición de un evento de Prisma; no origen actual ni recepción. |

El catálogo de [vehículos Startrack](https://support.gps-platform.com/api/vehicles/vehicles/)
se lee con `id`, `description`, `vin`, `driver_id` y fechas/activación. `vin` se
documenta allí como identificador remoto; no se supone igual a `no_activo` o al
UUID de maquinaria. Estado, grupo, etiquetas, marca y mantenimiento mostrados
en el diccionario requieren sus propios contratos y correspondencias, no campos
inventados en el payload de tarea.

## Fechas, unidades y estados separados

| Hecho | Campo y tratamiento |
| --- | --- |
| Período de uso | `fecha_inicio`/`fecha_fin` se conservan como fechas. No se desplazan por conversión UTC ni se consideran vencimiento de entrega. |
| Programación del movimiento | Fecha y hora explícitas de `TransferMapping`. La UI las interpreta en `America/El_Salvador`; hay que confirmar que la zona de la cuenta Startrack coincide, pues `start_time` no lleva zona. |
| Evento del proveedor | Se mantiene el texto original y, cuando contiene zona, su instante. Una hora sin zona no acredita una llegada temporalmente válida. |
| Observación | `provenance.observed_at` es cuándo se leyó el dato; `event_time` es cuándo ocurrió; `recorded_at`, cuándo se almacenó. `generated_at` solo ensambla la respuesta. |
| Documento de muestra | `observed_on` puede conservar el día documental. No inventa un instante conjunto para el dataset ni actualiza los datos al reloj actual. |
| Duración | UI del usuario en minutos; Job en segundos. Horómetro en horas, odómetro en distancia y tarifa por hora son magnitudes independientes. |
| Coordenadas | POI en grados; radio en metros. Los enteros `133376152` y `-878486967` del diccionario no tienen escala acreditada y no se dividen para producir una ubicación. |
| Respuestas de formulario | `date`, `server_date`, `gps_epoch` conservan enteros de época en segundos; son instantes diferentes. Las preguntas se identifican por ID, no por texto de etiqueta. |

| Estado | Fuente / modelo | Regla |
| --- | --- | --- |
| Administrativo de solicitud | Prisma `status` → `RequestRecord.status`. | Solo `APROBADA`/`APPROVED` habilitan la preparación actual. Otros valores se conservan y no se consideran aprobación. |
| Administrativo de maquinaria | Prisma `estado` → `machinery_status`. | `OCUPADA` no significa GPS en destino; `OBSOLETA` no se sustituye automáticamente por un código de falla. |
| Mantenimiento | `active_failure_*` → `maintenance_*`. | Un paro explícito bloquea preparación. Desconocer el paro genera advertencia, no certifica disponibilidad. |
| Envío de integración | `Movement.state`: `draft`, `blocked`, `queued`, `sending`, `sent`, `unknown`, `failed`. | `sent` confirma una tarea asociada, no ejecución ni entrega. `unknown` no permite otro POST automático. |
| Tarea | `Job.status` es un ID; catálogo `JobStatus.workflow_role` agrupa pendiente/completada/cancelada. | No interpretar un ID personalizado por su parecido con `0`, `1` o `2`; consultar su rol. Conservar desconocidos. |
| Presencia | Visita de vehículo a POI, con IDs y tiempo. | Evidencia espacial acotada, separada de tarea y máquina transportada. |
| Recepción | `ReceiptRecord` declarado expresamente. | Requiere receptor, instante con zona y referencia de constancia. Ni GPS, tarea completada ni formulario genérico generan recepción automática. |

La separación de estados responde al [manual Nexus](onedrive/05-manual-nexus.md)
y al [caso de consistencia](onedrive/04-casos-de-uso.md). El catálogo de tareas
y la lógica efectiva se pueden contrastar en
[Startrack](../apps/api/app/integrations/startrack.py) y
[seguimiento](../apps/api/app/services/workflow.py).

## De la aprobación a la tarea: contrato frente a implementación

1. **Crear proyecto y solicitud ocurre en Prisma.** El contrato suministrado no
   expone POST de creación de proyectos/solicitudes. ECON no inventa esas rutas
   ni replica las muestras dentro del proveedor.
2. **Aprobar/asignar es una operación administrativa.** El OpenAPI documenta
   `PATCH /api/maquinaria/requests/{id}/approve`: `maquinaria_id` obligatorio;
   `fecha_inicio`, `fecha_fin`, `operator_id` y `precio_x_hora` opcionales.
   ECON no ejecuta esa escritura. La respuesta publicada carece de esquema
   operativo suficiente para asumir cómo devuelve todos esos campos.
3. **Preparar un movimiento exige una correspondencia explícita.** Se comprueban
   solicitud aprobada, unidad exacta, proyecto, entorno y clase de evidencia;
   se incorporan destino, asignados, referencia y fecha. Tener un proyecto o
   una solicitud pendiente no crea una tarea.
4. **Enviar requiere revalidación actual.** El servicio vuelve a leer solicitud
   y equipo por sus UUID, valida IDs de catálogos y busca tareas previas por
   referencia. Catálogo incompleto o ambiguo impide certificar una equivalencia.
   Un nombre coincidente no sustituye esa validación.
5. **La creación tiene un solo intento POST.** El SDK usa formulario
   `application/x-www-form-urlencoded`, serializa arrays como JSON y desactiva
   avisos al contacto. El formato real de arrays y la respuesta de la cuenta
   siguen pendientes de prueba autenticada. Una respuesta insuficiente, como
   solo `{id}` sin los campos exigidos por el DTO actual, queda incierta.
6. **Un resultado incierto se concilia por lectura.** La coincidencia exige un
   único resultado en la búsqueda agotada y referencia, destino, título, fecha,
   asignados y campos opcionales enviados coherentes. La referencia sola no
   basta; no se repite automáticamente el POST.
7. **Seguimiento y recepción siguen separados.** El worker consulta tareas y
   visitas; la constancia de recepción se registra de manera explícita en ECON.
   Nada de esto actualiza inventario, solicitud o aprobación en Prisma.

Este comportamiento está implementado en
[preparación](../apps/api/app/services/transfers.py),
[workflow](../apps/api/app/services/workflow.py) y
[ledger](../apps/api/app/services/ledger.py). La configuración mantiene lecturas,
gestión local y escrituras remotas deshabilitadas por defecto. Credenciales solo
en el servidor; el navegador no habilita proveedores. Los hosts del adaptador
son el sandbox de Prisma y `https://staging.gps.gt`. La autenticación de
Startrack utiliza API key y contraseña mediante Basic; una sesión de navegador
no acredita ese acceso. [Autenticación API](https://support.gps-platform.com/api/intro/).

No se ha realizado una creación autenticada de tarea como parte de esta revisión.
El acceso de lectura Nexus comprobado históricamente fue acotado; no acredita
todas las rutas ni todos los registros. Ver [contexto vigente](contexto-vigente.md)
y [guía operativa](solucion-integracion.md).

## Evidencia de retorno y cobertura

| Información de Startrack | Implementado | Límite |
| --- | --- | --- |
| Tareas y catálogos de POI, usuarios, vehículos, tipos/estados | Lecturas acotadas en SDK. La fachada ofrece los catálogos necesarios para el mapeo. | Que un ID exista no demuestra equivalencia de negocio, permisos completos ni vigencia de un vínculo entre sistemas. |
| Visitas | SDK y worker; correlación exacta de vehículo elegido, POI y tiempo. | El reporte no proporciona un `job_id` que certifique causalidad. El worker mira como máximo los últimos siete días y no reconstruye toda la historia. |
| Formularios respondidos | SDK, con `form_id`, fechas explícitas y filtros de tarea/usuarios. | No se consultan ni persisten todavía desde el worker. Falta elegir formulario, preguntas y criterio de recepción. |
| Actividad y adjuntos completos de tarea | No implementados. | El historial de ECON conserva sus eventos, no promete ser una copia de la pestaña Actividad. |
| Webhooks | No implementados. | El contrato Prisma no publica aprobación por webhook. La documentación Startrack consultada reenvía información de vehículos, no acredita un callback de aprobación o cierre de Job. |

Las lecturas de [visitas](https://support.gps-platform.com/api/reports/poi-visits/)
y [formularios](https://support.gps-platform.com/api/reports/form-responses/)
usan ventanas y límites explícitos. El SDK aplica hasta siete días por consulta
de reporte; una lectura vacía o parcial no prueba ausencia histórica. Los
[webhooks documentados](https://support.gps-platform.com/admin/api/webhooks/)
no sustituyen una integración de eventos de negocio confirmada.

## Ejemplo fiel: PROY-014 / CF-03

Los siguientes valores son **ejemplos proporcionados del sandbox**, no una
consulta actual ni una tarea creada por ECON. Se conservan los UUID del
[OpenAPI](../econ-hackathon-openapi.json) y del
[dataset de muestras](../apps/api/app/integrations/data/sandbox_samples.json).

| Dato | Valor suministrado | Uso correcto |
| --- | --- | --- |
| Proyecto | `39723f32-8bb5-4158-a415-2a3d49b0993b` — PROY-014 - The Hub - Proyecto Xi - La Unión | Identidad Prisma; todavía falta el `poi_id` de destino confirmado. |
| Solicitud aprobada | `46d2573e-08d3-4855-971d-2fbf9564e135` | `APROBADA`; solicita Cargador frontal del 11 al 14 de septiembre de 2026. |
| Maquinaria asignada | `66faacde-728c-4378-8b46-dbfb38254e03` | `no_activo=CF-03`, `clave=null`, `nombre=Cargador frontal 03`. |
| Estado de maquinaria | `OBSOLETA` | Se conserva aunque la solicitud esté aprobada; no se corrige a `OCUPADA` para hacer coincidir el relato del manual. |
| Mantenimiento en las respuestas suministradas | El listado trae `active_failure_is_paro=false` y falla nula; el detalle omite esos campos. | Son coberturas distintas; al reconsultar el detalle, el DTO conserva desconocido. No inventar un paro ni certificar disponibilidad física. |
| Solicitante | `98bf9d4d-fb00-4680-9883-6a72cf0bae0e` — María José López Ramírez | No es automáticamente usuario asignado o contacto en Startrack. |
| Aprobación | `2026-09-12T01:00:01.535958+00:00` | Instante de aprobación en Prisma, no salida o llegada. |
| Operador asociado en el detalle de maquinaria | `7753f3fe-cffc-4032-9d3e-b77c3b04ca00`, `cod_trabajador=MOT-015` | El ejemplo de detalle es distinto de MOT-014 del walkthrough. No confirma un usuario Startrack para la tarea. |
| Segunda solicitud | `0cbbbd77-4593-4791-9be5-afd46b06c888` | Mismo proyecto/tipo, 16–18 de septiembre de 2026, `PENDIENTE`, `maquinaria_id=null`; no se prepara su traslado. |

Para la primera solicitud, el título derivable sería «Traslado de CF-03 a
PROY-014 - The Hub - Proyecto Xi - La Unión». **Eso no constituye un payload
listo para enviar**: faltan geocerca, usuarios, referencia y programación del
movimiento confirmados. No se rellenan con `24`, `GEO-014`, `MOT-014` o una
fecha tomada del período de uso. El vehículo rastreado, cuando se utilice, exige
otra confirmación. La muestra cubre cinco equipos de un total declarado de
quince y dos solicitudes; no es un inventario integrado de toda la flota.

La asignación del kit **RE-03 / MOT-006 / PROY-006** permanece aparte. Una captura
posterior muestra PROY-006, Cargador frontal, 11–26 de septiembre de 2026,
Pendiente y sin maquinaria, pero no su UUID. No se intercambian sus IDs con los
de PROY-014/CF-03 para completar la demostración. Ver
[identidad y muestras](contexto-vigente.md#identidad-y-muestras) y
[casos suministrados](onedrive/04-casos-de-uso.md).

## Responsabilidades propuestas para confirmar

Esta matriz deriva del [TO-BE](onedrive/03-to-be.md) y del
[manual](onedrive/05-manual-nexus.md); **es una propuesta de RACI**, no una
asignación firmada ni permisos de API implementados. R realiza la acción;
A responde por su aprobación; C debe ser consultado; I recibe información.
Una misma persona podría ejercer distintos roles, sin que los IDs se fusionen.

| Decisión o dato | R | A | C | I |
| --- | --- | --- | --- | --- |
| Proyecto, tipo y período de uso solicitados | Gerencia de Proyecto | Gerencia de Proyecto | Logística y Equipo | Control de Costos |
| Aprobación, unidad, operador y tarifa en Prisma | Logística y Equipo | Gerencia de Logística y Equipo | Gerencia de Proyecto; Mantenimiento | Operador; Control de Costos |
| Correspondencias POI/usuario/vehículo y programación del traslado | Logística y Equipo | Gerencia de Logística y Equipo | Responsable del destino; operador; soporte de integración | Gerencia de Proyecto |
| Habilitación técnica, validación de contrato y envío conforme al plan | Soporte de integración | Gerencia de Logística y Equipo | Administrador Startrack; Mantenimiento si hay restricción | Gerencia de Proyecto |
| Ejecución y evidencias de la tarea | Operador o motorista confirmado | Gerencia de Logística y Equipo | Responsable del destino | Gerencia de Proyecto |
| Paro, diagnóstico y liberación de mantenimiento | Mantenimiento | Gerencia de Mantenimiento | Logística; operador | Gerencia de Proyecto; Control de Costos |
| Recepción de la máquina y constancia | Responsable receptor del proyecto | Gerencia de Proyecto | Logística; operador | Control de Costos |
| Validación económica posterior | Control de Costos | Responsable de Control de Costos | Proyecto; Logística | Gerencia correspondiente |

La recepción actual guarda una declaración y su referencia. El acuerdo de quién
puede recibir y qué documento lo acredita sigue siendo una decisión operativa.
<!-- TODO(auth): indicar si el usuario autenticado que registra la recepción queda vinculado a la declaración. -->

## Lagunas que deben resolverse antes de ampliar la equivalencia

1. Confirmar en la cuenta los IDs técnicos y sus correspondencias, permisos,
   zona horaria, catálogos activos y formato de arrays/respuesta de creación.
   Conservar evidencia fechada; no interpretar un catálogo parcial como mapeo.
2. Obtener contrato soportado para las opciones de pantalla sin campo público:
   origen, plazo, ventana de entrega, restricción de geocerca y artículos.
3. Incorporar al modelo normalizado la identidad del aprobador si debe auditarse.
   `NexusRequest.operador_id` es una tolerancia del DTO actual sin ese campo en
   el esquema de lectura suministrado; el cuerpo de aprobación usa **`operator_id`**.
   Tampoco se conserva `associated_operators`. No presentar estas rutas como
   una asignación de operador completamente integrada.
4. Acordar el tratamiento del estado `OBSOLETA` y la revalidación de mantenimiento:
   el bloqueo actual depende de paro explícito y no de equiparar etiquetas.
   El detalle puede omitir campos presentes en el listado.
5. Definir quién aprueba y mantiene las equivalencias y su vigencia histórica;
   hoy se almacenan por movimiento, sin maestro independiente versionado.
6. Elegir el formulario y criterio empresarial de recepción antes de integrar
   respuestas; ampliar preparación y worker de forma coherente. Lo mismo aplica
   a comentarios, adjuntos, duración, contactos y artículos si entran en alcance.

La comprobación de esta matriz fue documental y de código. No se usaron
credenciales, no se modificaron registros de los proveedores y no se agregaron
datos operativos para completar equivalencias ausentes.
