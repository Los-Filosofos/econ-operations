# Manual práctico de mapeo e integración

**ECON · Prisma · Startrack — 12 de septiembre de 2026**

Esta guía explica cómo preparar y revisar un movimiento sin confundir solicitud,
tarea, ubicación y recepción. Complementa la
[matriz de equivalencias](equivalencias-prisma-startrack.md); allí se detalla cada
campo del formulario de Startrack, incluso los no soportados por ECON.

## 1. Qué fuente acredita cada dato

**Prisma** acredita proyecto, solicitud, aprobación y unidad asignada. Su contrato
no documenta creación de proyectos o solicitudes mediante POST; esas operaciones
se realizan en la aplicación existente. **Startrack** acredita IDs de geocercas,
usuarios y activos GPS, además de tareas y observaciones. **ECON** conserva la
correspondencia revisada, el envío y la declaración explícita de recepción.

No unir registros por nombre. Una solicitud puede necesitar varios movimientos;
cada uno tiene su referencia. El GPS puede pertenecer al transportador. Una tarea
completada o una visita de geocerca no acreditan recepción física.

`fixture` identifica muestras del archivo proporcionado; `live`, consultas
actuales del sandbox sintético. No se intercambian ni se cargan las muestras en
Prisma. El ejemplo de esta guía se revisa localmente, sin modificar proveedores.

## 2. Diccionario técnico esencial

«Sí» significa requerido por el modelo indicado; «null» conserva un dato ausente.
Un campo nullable de lectura puede resultar indispensable para preparar el
traslado. Los nombres abreviados corresponden a los
[modelos del hub](../apps/api/app/models/hub.py).

### Identidad y hechos de origen

| Campo ECON | Tipo | Requisito | Procedencia | Regla |
| --- | --- | --- | --- | --- |
| `Request.id`, `Equipment.id` | Texto | Sí | Adaptador Prisma | ID interno con prefijo de entidad; no enviarlo como UUID original. |
| `provenance.source_id` | Texto/null | Lectura nullable | ID del proveedor | Los campos `*_source_id` usan este original. |
| `Request.project_id` | Texto/null | Necesario para plan | `Solicitud.project_id` | Proyecto por UUID, no por etiqueta. |
| `Request.machinery_id` | Texto/null | Necesario para plan | `Solicitud.maquinaria_id` | Referencia interna a `Equipment.id`; null significa sin unidad asignada. |
| `Request.status` | Texto | Sí | `Solicitud.status` | Aprobación y asignación se verifican juntas; estados desconocidos requieren revisión. |
| `Request.starts_on`, `ends_on` | Texto/null | Conserva ausencia | `fecha_inicio`, `fecha_fin` | Período de uso solicitado; no fechas de entrega. |
| `Request.approved_at` | Fecha-hora/null | Nullable | Aprobación Prisma | No sustituir por creación ni fecha de lectura. |
| `Equipment.code`, `asset_number` | Texto/null | Nullable | `clave`, `no_activo` | Campos distintos; ninguno reemplaza el UUID. |
| `Equipment.machinery_status` | Texto | Sí | `Equipo.estado` | Estado administrativo; no prueba disponibilidad física. |
| `maintenance_failure_id`, `maintenance_is_stopped` | Texto/null; bool/null | Nullable | Falla y paro Prisma | Falla, paro y estado administrativo permanecen separados. |

### Entradas del movimiento

El contrato es [`TransferMapping`](../apps/api/app/services/transfers.py).
Los tres IDs Prisma se muestran como referencias de solo lectura en la UI.

| Campo ECON | Tipo | Requisito | Procedencia | Regla |
| --- | --- | --- | --- | --- |
| `request_source_id` | Texto | Sí | UUID de solicitud | Coincidir con la solicitud seleccionada. |
| `machinery_source_id` | Texto | Sí | UUID de maquinaria | Coincidir con su unidad asignada. |
| `project_source_id` | Texto | Sí | UUID de proyecto | Coincidir con el proyecto solicitado. |
| `poi_id` | Texto | Sí | Geocerca Startrack | Destino confirmado por el operador; no deducido del nombre. |
| `assigned_user_ids` | Tupla de textos | Uno o más | Usuarios Startrack | IDs distintos; no son UUIDs de operadores Prisma. |
| `movement_reference` | Texto | Sí | Decisión local | Referencia de este movimiento; se envía como `remote_id`. |
| `scheduled_date` | Fecha | Sí | Programación explícita | `AAAA-MM-DD`; no copiar automáticamente el inicio de uso. |
| `scheduled_time` | Texto/null | Opcional | Programación explícita | Modelo `HH:MM:SS`; UI admite `HH:MM`. |
| `job_type_id` | Texto/null | Opcional | Catálogo Startrack | Disponible en API; sin control en el formulario simplificado. |
| `tracked_vehicle_id` | Texto/null | Opcional | Activo GPS Startrack | Entrada adicional al mapeo; queda en el movimiento, no en Job. |

Los identificadores requieren texto no vacío y sin espacios. Para el
seguimiento, los filtros de informes requieren IDs numéricos confirmados.
Sin activo GPS mapeado, ECON no atribuye visitas al movimiento.

### Persistencia y evidencia

Referencias: [operaciones](../apps/api/app/models/operations.py),
[registro transaccional](../apps/api/app/services/ledger.py) y
[estado de consulta](../apps/api/app/models/workflow.py).

| Campo ECON | Tipo | Requisito | Procedencia | Regla |
| --- | --- | --- | --- | --- |
| `Movement.id`, `mode`, `environment` | Textos | Sí | ECON/origen | ID local; modos y entornos separados. |
| `mapping`, `source_request` | JSON | Sí | Plan y lectura | Conservan correspondencias y procedencia. |
| `source_equipment`, `payload` | JSON/null | Nullable | Lectura/preparación | Ausencias o bloqueo no se rellenan artificialmente. |
| `source_request_hash`, `source_equipment_hash` | Texto; texto/null | Según fuente | SHA-256 local | Trazan el contenido seleccionado; no certifican al proveedor. |
| `state` | Enumeración | Sí | Cola ECON | `draft`, `blocked`, `queued`, `sending`, `sent`, `unknown`, `failed`. |
| `job_id` | Texto/null | Nullable hasta vínculo | ID de tarea Startrack | No equivale al ID de solicitud ni a `remote_id`. |
| `status`, `workflow_role` | Texto/null | Nullable | Tarea/catálogo | Estado remoto separado del estado de envío. |
| `provenance` | Objeto | En registros fuente | Adaptador | Fuente, ID, entorno, evidencia y naturaleza sintética. |
| `observed_at`, `observed_on` | Fecha-hora/null; fecha/null | Según evidencia | Lectura/documento | Una fecha documental no inventa una hora de observación. |
| `event_time`, `recorded_at` | Fecha-hora/null; fecha-hora | Evento nullable | Proveedor/ECON | Momento del hecho separado del momento de registro. |
| `available`, `last_sync_at` | Bool; fecha-hora/null | Estado de consulta | Registro ECON | No equivalen a cobertura total ni frescura de cada posición. |
| `receipt` | Objeto/null | Declaración explícita | Proyecto receptor | Solo movimiento live enviado con `job_id`. |
| `receipt.receiver`, `reference` | Texto | Sí al recibir | Persona/constancia | Receptor y folio no vacíos. |
| `receipt.received_at`, `note` | Fecha-hora; texto/null | Fecha sí; nota opcional | Declaración | Fecha con zona; fuente fija `manual_declaration`. |

## 3. Recorrido del operador

1. **Verificar en Prisma.** Para una operación autorizada, comprobar que Logística
   haya aprobado la solicitud y asignado una unidad concreta. Revisar paro y
   condición administrativa. ECON no convierte una selección visual pendiente
   de guardar en una aprobación confirmada.
2. **Abrir ECON → Solicitudes.** Elegir el origen correcto y abrir la solicitud.
   Revisar proyecto, unidad, estado y período. Si falta la maquinaria o su ID,
   completar primero esa información en Prisma; no inventarla en ECON.
3. **Desplegar “Preparar traslado”.** Revisar “Referencias de integración”.
   Completar geocerca, usuarios, referencia y fecha programada; opcionalmente hora
   y activo GPS. En usuarios, separar IDs con comas. Confirmar las correspondencias
   con los catálogos: que un ID exista no demuestra que sea el destino correcto.
4. **Pulsar “Guardar plan local”.** Abrir el movimiento resultante y revisar
   “Contenido preparado para Startrack”. El título y la descripción se generan
   con la unidad, proyecto, UUIDs y referencia; no se copian automáticamente todos
   los comentarios de Prisma. Guardar no envía la tarea.
5. **Pulsar “Poner traslado en cola”**, únicamente cuando el envío live esté
   habilitado. El servidor vuelve a consultar aprobación, unidad, catálogos y
   tareas previas. Una búsqueda incompleta no demuestra ausencia de duplicados.
6. **En Operaciones, pulsar “Sincronizar operación”.** El ciclo reclama la cola,
   confirma la transacción local y realiza el envío. En fixture, el botón se llama
   “Guardar corte local” y conserva muestras; no crea tareas.
7. **Revisar evidencia.** Consultar tarea, llegada y “Historial y evidencia del
   movimiento”. `sent` significa tarea vinculada; `arrival` significa presencia
   GPS vinculada. Ninguno significa maquinaria recibida.
8. **Registrar recepción cuando exista constancia.** Completar persona, fecha,
   hora, referencia y observación opcional; pulsar “Registrar recepción”. La UI
   interpreta la hora en El Salvador. No se requiere inventar GPS para registrar
   una recepción explícita ni se permiten recepciones sobre muestras.

Las etiquetas y validaciones están en los
[formularios](../apps/api/app/dashboard/workflow_forms.py) y
[acciones](../apps/api/app/dashboard/workflow_actions.py).

## 4. Ejemplo documentado: CF-03

La muestra contiene solicitud `46d2573e-08d3-4855-971d-2fbf9564e135`, maquinaria
`66faacde-728c-4378-8b46-dbfb38254e03` y proyecto
`39723f32-8bb5-4158-a415-2a3d49b0993b` — **PROY-014**. La solicitud está APROBADA,
asignada a CF-03, con uso solicitado del **11 al 14 de septiembre de 2026**.

CF-03 conserva **OBSOLETA**, sin referencia de falla activa y con paro explícito
`false`. Esto requiere revisar la condición administrativa; no permite inventar
una avería. No corresponde a la asignación del kit RE-03/MOT-006/PROY-006.

La muestra no proporciona una geocerca API confirmada, usuarios asignables,
referencia/programación del movimiento ni activo GPS vinculado. Dejarlos
pendientes. No copiar 11/09 como fecha de traslado ni fabricar un `job_id` o una
recepción para completar la pantalla. Esta revisión puede terminar sin guardar
un plan: todavía faltan decisiones e IDs.

## 5. Validaciones y diagnóstico

- Confirmar mismo origen, modo, entorno, solicitud, proyecto y unidad. Una
  recepción de otra asignación o período no resuelve el movimiento actual.
- Distinguir `null`, `false` y cero: información desconocida no equivale a ausencia
  de paro, tareas o riesgo.
- Conservar fechas originales. Sin corte conjunto no se clasifica atraso por
  comparación con el reloj actual; uso solicitado no es compromiso de entrega.
- Si aparece **preparación bloqueada**, leer los faltantes y contradicciones;
  corregir el origen o revisar la correspondencia antes de volver a validar.
- Si aparece **referencia existente**, revisar el movimiento guardado y las tareas
  previas. Una referencia idéntica con otro contenido produce conflicto.
- Ante **resultado incierto**, conciliar por lectura; no volver a enviar. Una
  reclamación antigua pasa a `unknown`, no automáticamente a la cola. Un fallo
  también requiere revisión antes de proponer otro intento.

## 6. Condiciones técnicas de operación

La base necesita la migración explícita `alembic upgrade head`; el arranque no
crea tablas. **Registro no disponible** exige comprobar conexión y esquema, no
interpretar cero movimientos. El [manual de operación](solucion-integracion.md)
detalla instalación, ciclos CLI y límites de cobertura.

`ALLOW_LOCAL_MANAGEMENT` permite gestión local; `ALLOW_LIVE_READS`, lecturas;
`ALLOW_LIVE_WRITES`, envío; `AUTO_QUEUE_TRANSFERS`, encolado automático de planes
válidos. Inicialmente son `false`. La UI no concede esos permisos. No se habilitan
credenciales ni se ejecutan escrituras por seguir este documento. La gestión
permanece local y live no debe publicarse por defecto.

La creación autenticada en Startrack continúa pendiente de validar credenciales,
permisos, IDs y codificación de listas aceptada por la cuenta. Las pruebas locales
con respuestas simuladas verifican reglas, no acreditan aceptación real del API.
