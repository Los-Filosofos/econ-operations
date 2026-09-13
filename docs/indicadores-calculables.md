# Indicadores calculables con las lecturas existentes

Revisión del **13 de septiembre de 2026**. Este documento define los indicadores que
`GET /api/v1/indicators` publica hoy y las fichas de SLA que quedan propuestas
para Logística, Proyectos, Mantenimiento e Información. Cada ficha cumple los
puntos que exige el [contexto vigente](contexto-vigente.md#límites-de-los-datos)
antes de publicar una medición: pregunta y decisión, grano, población,
numerador y denominador, exclusiones y desconocidos, fechas con su nombre exacto,
unidad y estado evaluable / parcial / no evaluable. No hay gráficos: los
resultados son listas por fila.

Reglas que aplican a todo el documento y al contrato:

- **Por fila, sin promedios.** Ningún indicador publica media, mediana,
  percentil ni porcentaje. Cada fila es una diferencia entre dos instantes que
  una fuente documentó, o un hecho copiado de la fila. Las cohortes son
  pequeñas (dos solicitudes en fixture) y no hay política de cancelaciones ni
  reprogramaciones: agregar sería inventar una serie.
- **La ausencia no es cero.** Una fecha ausente deja la fila `not_evaluable`
  con el campo que falta; una población vacía es «sin casos evaluables», nunca
  `0`. Que el archivo no traiga tareas no significa que la operación no las tenga.
- **Fixture no tiene corte.** Las muestras del OpenAPI se documentaron el
  12/09/2026 sin instante común (`data_as_of = null`) y sin tareas enviadas: las
  antigüedades «al corte» y las ausencias «sin tarea» no se evalúan en ese modo.
  En `live` el corte es el instante en que terminó la lectura acotada de Prisma.
- **Nunca el reloj para hechos de origen.** El único «ahora» es
  `HubResponse.generated_at` y solo lo usa la antigüedad de la evidencia. El
  servicio `app/services/indicators.py` es puro: no consulta proveedores, base
  de datos ni `datetime.now`.
- **La cobertura viaja con el resultado.** Cada indicador cita el alcance de la
  lectura (`scope`: 5 de 15 unidades y 2 de 2 solicitudes en fixture) y el
  estado del registro de movimientos; los conteos describen esas filas, no la flota.

## Contrato

| Elemento | Dónde |
| --- | --- |
| Ruta | `GET /api/v1/indicators` con `mode` (`fixture` o `live`) y `search` (etiqueta «Indicadores», `Cache-Control: no-store`) |
| Modelos | `app/models/indicators.py`: `IndicatorSheet`, `IndicatorRow`, `IndicatorResult`, `IndicatorsReport` |
| Cálculo | `app/services/indicators.py`: `compute_indicators(hub, workflow)` sobre `read_hub` y `WorkflowService.read(mode, page_size=500)` |
| Pruebas | `apps/api/tests/test_indicators.py` |

`IndicatorsReport` lleva `mode`, `generated_at`, `data_as_of`, `scope`,
`registry` (estado del registro visto por el hub), `ledger_coverage`,
`ledger_available`, `last_registry_read_at`, la lista `indicators` y `notes`.
Cada `IndicatorResult` publica su `sheet`, `status`, `reason`, `rows` y los
conteos `evaluable_count`, `partial_count`, `not_evaluable_count`, que siempre
suman el número de filas. Cada `IndicatorRow` cita `subject_id` (`nexus:request:…`,
`nexus:equipment:…`, `econ:movement:…`), `source_id`, `values`, `evidence`,
`status` y `reason`.

## Qué es medible hoy

| Indicador | Grano | Para quién | fixture | live | Lo que falta para más |
| --- | --- | --- | --- | --- | --- |
| I1 Tiempo de aprobación | solicitud | Proyectos | sí (1 fila evaluable, 1 no) | sí | `rejected_at` no existe; sin historial de decisiones |
| I2 Antigüedad de la solicitud abierta al corte | solicitud | Logística | no (sin corte) | sí | Historial de reprogramaciones |
| I3 Aprobadas con unidad sin tarea enviada | solicitud | Logística | no (sin tareas) | sí, completo solo con registro completo | Tareas creadas fuera de ECON |
| I4 OCUPADA sin proyecto | unidad | Logística | sí (0 OCUPADA → sin casos) | sí | Motivo del estado (`history`) |
| I5 Asignación vigente vencida al corte | unidad | Logística | no (sin corte) | sí | Devolución real |
| I6 Tarea completada sin recepción | movimiento | Proyectos | no (sin tareas) | sí | Recepciones fuera de ECON |
| I7 Falla activa registrada | unidad | Mantenimiento | sí (0 fallas → sin casos) | sí | Edad y estados de la falla (`/fallas`) |
| I8 Antigüedad de la evidencia del registro | movimiento | Información | no (sin lecturas) | sí | — |

## Fichas de los indicadores publicados

Los nombres de campo son los del contrato de Prisma tal como los lee
`app/integrations/nexus.py` (`NexusEquipment`, líneas 52–76: `estado`,
`project_id`, `fecha_inicio_uso`, `fecha_fin_uso`, `active_failure_id`,
`active_failure_status`, `active_failure_is_paro`, `created_at`, `updated_at`;
`NexusRequest`, líneas 79–100: `status`, `maquinaria_id`, `fecha_inicio`,
`fecha_fin`, `created_at`, `updated_at`, `approved_at`), los del registro local
(`Movement`, `OperationEvent`, `ReceiptRecord`, `SourceSnapshot` en
`app/models/operations.py`) y el instante de tarea que escribe
`WorkflowService._observe` (`app/services/workflow.py`, línea 500:
`event_time = StartrackJob.last_status_change_date | closed_date | changed_date`,
solo si trae zona).

### I1 · Tiempo de aprobación de la solicitud (`approval_time`)

- **Para quién y decisión:** Proyectos y Gerencia revisan qué solicitudes esperan
  decisión y acuerdan un plazo de aprobación.
- **Pregunta:** ¿cuánto tardó cada solicitud en pasar de creada a aprobada?
- **Grano:** solicitud. **Población:** todas las solicitudes de la lectura.
- **Fórmula:** `Solicitud.approved_at − Solicitud.created_at`, en segundos
  (`values.seconds`; `values.minutes` cuando ≥ 60 s). **Denominador:** no aplica.
- **Exclusiones:** ninguna fila se oculta; las no aprobadas se publican como no
  evaluables con motivo.
- **Desconocidos:** cambios de decisión posteriores (Prisma no publica historial
  de la solicitud); instante de rechazo (`rejected_at` no existe en el contrato).
- **Fechas:** `Solicitud.created_at`, `Solicitud.approved_at` (ISO 8601 con zona).
- **Unidad:** segundos.
- **Estado:** evaluable con `APROBADA` y ambos instantes con zona; `PENDIENTE` →
  «sin approved_at»; `RECHAZADA` → «no existe rejected_at»; otro estado → no evaluable.
- **Fixture:** `46d2573e…` evaluable con 42.209783 s
  (`2026-09-12T00:59:19.326175Z` → `2026-09-12T01:00:01.535958Z`); `0cbbbd77…`
  no evaluable, sigue PENDIENTE. Indicador `partial`.

### I2 · Antigüedad de la solicitud abierta al corte (`open_request_age`)

- **Para quién y decisión:** Logística prioriza la asignación; Proyectos
  confirma si la necesidad sigue vigente.
- **Pregunta:** ¿cuánto lleva abierta cada solicitud pendiente o aprobada sin
  unidad al corte de la lectura, y cuántos días pasaron desde su inicio si ya llegó?
- **Grano:** solicitud. **Población:** `PENDIENTE` y `APROBADA` sin `maquinaria_id`.
- **Fórmula:** `PENDIENTE`: `data_as_of − created_at`; `APROBADA` sin unidad:
  `data_as_of − approved_at` (horas, `values.hours`). Con `fecha_inicio` ≤ día
  del corte en `America/El_Salvador` (`parse_day` de `app/services/intervals.py`):
  `values.days_since_start = corte − fecha_inicio`; un inicio futuro deja
  `start_reached=false` y `days_since_start=null`, nunca días negativos ni «atraso».
- **Exclusiones:** `APROBADA` con unidad (pasa al traslado); `RECHAZADA`.
- **Desconocidos:** reprogramaciones; si la unidad quedó fuera de la página leída.
- **Fechas:** `HubResponse.data_as_of`, `Solicitud.created_at`,
  `Solicitud.approved_at`, `Solicitud.fecha_inicio`.
- **Unidad:** horas; días para el inicio alcanzado.
- **Estado:** no evaluable sin corte (fixture: «sin corte de observación
  (fixture)»); no evaluable por fila si falta el instante de origen.

### I3 · Aprobadas con unidad sin tarea enviada (`approved_with_unit_without_sent_task`)

- **Para quién y decisión:** Logística prepara o revisa el traslado; nunca
  reenvía a ciegas.
- **Pregunta:** ¿qué solicitudes aprobadas con unidad no tienen una tarea de
  Startrack enviada desde ECON para esa misma asignación y período?
- **Grano:** solicitud. **Población:** `APROBADA` con `maquinaria_id` cuya
  unidad está en la lectura.
- **Fórmula:** lista. Una fila tiene tarea cuando existe un movimiento `sent`
  con `job_id` que `matching_current_movements` (`app/services/evidence.py`)
  relaciona con la solicitud, la unidad, el proyecto, el período y el
  `approved_at` vigentes. Con tarea se publica `values.hours_approved_to_sent =
  Movement.sent_at − Solicitud.approved_at`. **Denominador:** no aplica.
- **Exclusiones:** movimientos históricos (origen cambiado) y en
  draft/queued/sending/unknown/failed; unidad fuera de la página → fila no
  evaluable, no ausencia.
- **Desconocidos:** tareas creadas fuera de ECON (no se consulta Startrack);
  movimientos fuera de la página del registro.
- **Fechas:** `Solicitud.approved_at`, `Movement.sent_at`.
- **Estado:** **no evaluable en fixture**: las muestras no envían tareas y la
  ausencia en el archivo no es cero (la solicitud `46d2573e…` se lista con ese
  motivo). En live: `evaluable` solo con registro completo
  (`WorkflowOverview.complete`); `partial` cuando el registro está incompleto;
  no evaluable si no está disponible.

### I4 · Unidades OCUPADA sin proyecto (`occupied_without_project`)

- **Para quién y decisión:** Logística corrige la asignación en Prisma o libera
  la unidad.
- **Pregunta:** ¿qué unidades figuran `OCUPADA` sin `project_id`?
- **Grano:** unidad. **Población:** `Maquinaria.estado = OCUPADA`.
- **Fórmula:** `values.without_project = project_id is null`; se copian
  `fecha_inicio_uso` y `fecha_fin_uso`. **Denominador:** no aplica.
- **Exclusiones:** otros estados administrativos.
- **Desconocidos:** unidades fuera de la página; motivo del estado (la lista no
  lo publica; `history` no implementado).
- **Fechas:** ninguna (hecho administrativo de la fila).
- **Estado:** evaluable por fila; con 0 unidades `OCUPADA` → «sin casos
  evaluables: ninguna unidad OCUPADA entre las 5 filas leídas (5 de 15)», nunca 0.

### I5 · Asignación vigente vencida al corte (`assignment_ended`)

- **Para quién y decisión:** Logística y el proyecto confirman prórroga,
  devolución o nuevo traslado.
- **Pregunta:** ¿qué unidades siguen asignadas cuando `fecha_fin_uso` ya pasó al corte?
- **Grano:** unidad. **Población:** unidades con `project_id`.
- **Fórmula:** `values.days_since_end = día del corte (America/El_Salvador) −
  fecha_fin_uso` cuando es positivo (`ended=true`); una ventana no vencida deja
  `ended=false` y `days_since_end=null`. **Denominador:** no aplica.
- **Exclusiones:** unidades sin proyecto.
- **Desconocidos:** presencia física y devolución real.
- **Fechas:** `HubResponse.data_as_of`, `Maquinaria.fecha_fin_uso`.
- **Estado:** no evaluable sin corte (fixture: CF-03 se lista con
  `fecha_fin_uso = 2026-09-14` y motivo «sin corte»); no evaluable por fila sin
  `fecha_fin_uso` válida.

### I6 · Tarea completada sin recepción declarada (`completed_task_without_receipt`)

- **Para quién y decisión:** el proyecto declara la recepción o Logística
  investiga la entrega. Una tarea completada **no** es recepción; tampoco una
  visita GPS.
- **Pregunta:** ¿qué traslados tienen la tarea completada en Startrack y aún no
  tienen recepción declarada en ECON, y desde cuándo?
- **Grano:** movimiento. **Población:** movimientos `sent` con `job_id` cuyo
  último `task_state` (política `effective_event_sort_key`, `app/services/ledger.py`)
  tiene `workflow_role = '1'`.
- **Fórmula:** sin `receipt`: `values.hours_since_completion = data_as_of −
  OperationEvent.event_time` del último `task_state`. Con recepción:
  `receipt_declared=true`, `received_at` y `receipt_reference`, sin edad.
- **Exclusiones:** tareas pendientes (`'0'`) o canceladas (`'2'`); movimientos
  sin observación de tarea. Una observación pendiente posterior reabre la tarea
  y saca el movimiento de la población.
- **Desconocidos:** recepciones declaradas fuera de ECON.
- **Fechas:** `OperationEvent.event_time` (procede de
  `StartrackJob.last_status_change_date | closed_date | changed_date`, con zona),
  `ReceiptRecord.received_at`, `HubResponse.data_as_of`. `observed_at` se cita
  en la evidencia pero nunca sustituye a `event_time`.
- **Estado:** no evaluable en fixture; no evaluable por fila sin `event_time` o
  sin corte.

### I7 · Falla activa registrada por unidad (`active_failure_registered`)

- **Para quién y decisión:** Mantenimiento revisa el diagnóstico y la decisión
  de paro; Logística no programa traslados sobre unidades con paro.
- **Pregunta:** ¿qué unidades tienen una falla activa en Prisma y si implica paro?
- **Grano:** unidad. **Población:** unidades con `active_failure_id`.
- **Fórmula:** una fila por falla activa con `active_failure_status` y
  `active_failure_is_paro` copiados; `values.failure_age = null` siempre.
- **Desconocidos:** antigüedad de la falla (`created_at` del reporte no se lee),
  historial de estados (solo existe el `estado` vigente en `/api/maquinaria/fallas`).
- **Fechas:** ninguna leída.
- **Estado:** evaluable por fila con los campos de la lista; 0 fallas activas →
  «sin casos evaluables», nunca 0; la edad no es evaluable.

### I8 · Antigüedad de la evidencia del registro (`evidence_age`)

- **Para quién y decisión:** Información/TI decide si hay que ejecutar el ciclo
  de sincronización antes de decidir con esta lectura.
- **Pregunta:** ¿cuánto pasó desde la última lectura del registro de movimientos
  y cuándo se observó por última vez cada traslado enviado?
- **Grano:** movimiento. **Población:** movimientos `sent` del modo.
- **Fórmula:** `values.evidence_age_hours = HubResponse.generated_at −
  last_registry_read_at`, donde `last_registry_read_at =
  WorkflowOverview.last_sync_at = max(SourceSnapshot.recorded_at,
  SourceSnapshot.last_confirmed_at)` del último corte (`ledger.last_read_at`):
  es la **última lectura**, no el último cambio de contenido (un corte confirmado
  sin cambios mueve `last_confirmed_at`, no `recorded_at`). Por fila se publica
  además `movement_last_observed_at = max(OperationEvent.observed_at)` de sus
  `task_state`/`arrival`, porque el lote de observación de cada ciclo es acotado
  y un corte reciente no rejuvenece la evidencia de cada movimiento.
- **Fechas:** `HubResponse.generated_at`, `WorkflowOverview.last_sync_at`,
  `OperationEvent.observed_at`.
- **Unidad:** horas.
- **Estado:** no evaluable en fixture; no evaluable sin corte del registro. Es
  el único indicador que usa `generated_at` como «ahora».

## Fichas de SLA propuestas (no implementadas)

Umbrales **a validar con ECON**: son puntos de partida para la conversación con
cada área, no metas aprobadas ni referencias normativas. Ninguna se calcula hoy
como cumplimiento; los indicadores anteriores publican las diferencias por fila
que un SLA necesitaría, y la fórmula de cumplimiento solo tendría sentido con
población, exclusiones y política de reprogramaciones acordadas
([analítica](analitica-decisiones.md), [KPIs](kpis-y-referencias-iso.md)).

| SLA | Para quién | Pregunta | Grano y población | Fórmula con campos exactos | Unidad y umbral sugerido | Cobertura hoy | No evaluable cuando | Decisión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 Aprobación de la solicitud | Proyectos, Gerencia | ¿Se decide cada solicitud dentro del plazo? | solicitud; `APROBADA` (y las `PENDIENTE` vencidas si se acuerda) | `approved_at − created_at` (I1); pendientes: `data_as_of − created_at` (I2) | horas; **≤ 24 h hábiles, a validar con ECON** | I1 en fixture y live; I2 solo live | sin `approved_at` ni corte; `RECHAZADA` (sin `rejected_at`) | Escalar solicitudes sin decisión |
| S2 Asignación de unidad tras aprobar | Logística | ¿Cada aprobación recibe unidad a tiempo? | solicitud; `APROBADA` sin `maquinaria_id` | `data_as_of − approved_at` (I2, variante `aprobada_sin_unidad`) | horas; **≤ 8 h hábiles, a validar** | solo live | sin corte; `approved_at` ausente | Asignar o justificar la espera |
| S3 Envío de la tarea tras asignar | Logística, Información | ¿Se envía la tarea a Startrack poco después de aprobar con unidad? | solicitud; `APROBADA` con unidad en la lectura | `Movement.sent_at − Solicitud.approved_at` (I3, `hours_approved_to_sent`); sin tarea: fila abierta | horas; **≤ 4 h hábiles, a validar** | solo live con registro completo | fixture; registro parcial o no disponible | Preparar el traslado pendiente |
| S4 Recepción tras tarea completada | Proyectos | ¿El proyecto declara la recepción poco después de completarse la tarea? | movimiento; último `task_state` con `workflow_role='1'` | sin recepción: `data_as_of − event_time` (I6); con recepción: `ReceiptRecord.received_at − event_time` | horas; **≤ 24 h, a validar** | solo live | sin `event_time`; sin corte | Reclamar la constancia de recepción |
| S5 Atención de falla con paro | Mantenimiento | ¿Cuánto tarda una falla con paro en salir de `SIN_REVISAR` y en cerrarse? | falla; reportes con `is_paro=true` | `primer cambio de estado − created_at` y `FINALIZADO − created_at` del reporte (`/api/maquinaria/fallas/{id}`) | horas; **≤ 4 h para revisar, a validar** | **no calculable**: `/fallas` no se lee y no publica instantes por transición | siempre, hasta implementar la lectura y un historial de estados | Priorizar diagnóstico y decisión de paro |
| S6 Frescura de la evidencia | Información | ¿La lectura que sostiene una decisión es reciente y completa? | registro por modo (I8) | `generated_at − last_sync_at`; `WorkflowOverview.complete` | horas; **≤ 1 h con el worker activo, a validar** | solo live | fixture; sin corte del registro | Ejecutar el ciclo antes de decidir |

## Qué impide agregar hoy

| Límite | Efecto |
| --- | --- |
| Cohorte pequeña: 2 solicitudes en fixture, páginas acotadas en live | Una media o un percentil describiría una o dos filas; se publican las filas. |
| No existe `rejected_at` ni historial de la solicitud | La cohorte de «decididas» no se puede cerrar; las rechazadas quedan no evaluables. |
| No hay instantes por transición de falla (`/fallas` publica solo el `estado` vigente) | MTTR, tiempo en `ESPERA_REPUESTOS` o en `TRASLADO_STD` no se pueden medir. |
| Sin corte conjunto en fixture y sin política de reprogramaciones | Ninguna «antigüedad» ni «atraso» es defendible sobre el archivo. |
| Registro parcial (`complete=false`) o Startrack no consultado | Una ausencia no es verificable: la fila queda parcial, nunca cero. |
| Tarea completada, visita GPS y recepción son hechos distintos | Ningún SLA de entrega puede usar la tarea o la geocerca como recepción. |

## Lecturas no implementadas que habilitarían más indicadores (propuesta)

Ninguna de estas rutas se consulta hoy; se enumeran con sus campos documentados
en `econ-hackathon-openapi.json` para no inventar nombres.

| Lectura | Campos que aporta | Indicador que habilitaría |
| --- | --- | --- |
| `GET /api/maquinaria/equipos/{id}/history` (`project_id`, `limit`, `offset`) | `event_type` (`STATUS_CHANGED`, `OPERATOR_ASSIGNED`, `RATE_CHANGED`), `event_at`, `metadata.previous_status`/`next_status`, `metadata.occupied_without_project`, `metadata.next_operator_code` | Tiempo en cada estado administrativo; desde cuándo una unidad está `OCUPADA` sin proyecto; historial de asignaciones y operadores por unidad |
| `GET /api/maquinaria/equipos/{id}/actividad` | `tipo` (`CAMBIO_ESTADO`), `titulo`, `descripcion`, `created_at`, `user_id` | Motivo declarado de cada cambio de estado (p. ej. «mtto correctivo - faja» para `OBSOLETA`) |
| `GET /api/maquinaria/fallas` (+ `/counts`, `/filters`, `/{id}`) | `maquinaria_id`, `is_paro`, `operativa`, `estado` (`SIN_REVISAR`, `PENDIENTE_INTERVENCION`, `EN_PROCESO`, `ESPERA_REPUESTOS`, `TRASLADO_STD`, `EN_PRUEBAS`, `FINALIZADO`, `RECHAZADO`), `created_at`, `hour_meter`, `cod_trabajador`, `categoria_falla` | Edad de la falla activa (I7), fallas con paro por unidad y proyecto; S5 solo si además existiera un historial de estados con instantes |
| `GET /api/maquinaria/equipos/{id}/usage-trend` (`from_date`, `to_date`) | horas de uso diarias frente a `minimum_usage_hours` (el sandbox devuelve `items: []` y `minimum_usage_hours: null`) | Utilización por unidad, solo si el sandbox llegara a cargar datos |
| `GET /api/projects/{id}` | `start_date`, `end_date`, `status` | Solicitudes fuera del período del proyecto; asignaciones que exceden el fin del proyecto |
| Startrack `GET /api/job` (campos ya documentados, no leídos por `StartrackJob`) | `creation_date`, `duration` (segundos esperados), `assigned_user_remote_ids` | Desfase creación de tarea → salida programada; duración planificada frente a observada (nunca ETA) |

Estas lecturas exigen las mismas reglas del hub: conservar IDs y entorno,
separar fecha de evento, observación y registro, y declarar cobertura parcial.
Los límites temporales del traslado y lo que ningún contrato expone (ETA,
distancia, origen, fecha límite) están en
[tiempos del traslado](solucion-integracion.md#tiempos-del-traslado-qué-se-sabe-y-qué-no).
