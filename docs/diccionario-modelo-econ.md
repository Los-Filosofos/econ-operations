# Diccionario del modelo vigente de ECON

Inventario generado del código local para **RF-01**, con revisión semántica del flujo.
Cubre **53 modelos y 579 campos declarados** (incluidos campos heredados de entradas).
No representa las 51 definiciones del diccionario de proveedores ni acredita un mapeo completo.

Las tablas usan JSONPath relativo a cada modelo (`$` es su raíz). Los objetos anidados
se describen en su propia tabla; no se repiten todos los caminos posibles. Los modelos
SQLModel incluyen columnas internas que no se exponen en sus proyecciones públicas.

**Ejemplos:** los campos de CF-03 y de su solicitud provienen de las muestras proporcionadas
del OpenAPI. Los conteos se derivan de cinco equipos y dos solicitudes, sin filtro.
Los demás valores están rotulados como estructura técnica, defecto o constante; no son
movimientos, tareas, ubicaciones, recepciones ni IDs del sandbox. `null` conserva lo desconocido
cuando el contrato lo admite. `{}` y `[]` ilustran contenedores; no son objetos completos
válidos si un modelo anidado exige campos. Una fila no constituye un payload listo para enviar.

La muestra no tiene un instante de corte común. El ejemplo técnico `2000-01-01T00:00:00Z`
solo ilustra una fecha con zona y nunca se usa para evaluar la operación.

## Alcance y reproducción

Se incluyen todos los modelos propios de `models/hub.py`, `models/operations.py`,
`models/workflow.py`, `models/graph.py`, `models/indicators.py` y
`models/suggestions.py`, además de `TransferMapping`, `TransferPreparation`,
`StartrackTaskDraft` y las entradas de la API de operaciones. Se enumeran sus campos
públicos/declarados; propiedades, validadores y restricciones de servicio se explican abajo.
Se excluyen configuración/secretos, modelos genéricos del transporte y DTO de proveedores
que no crean vocabulario del hub; su correspondencia está en la matriz de equivalencias.

Desde la raíz, con las dependencias ya instaladas:

```powershell
uv run --project apps/api python scripts/docs/generar_diccionario.py
uv run --project apps/api python scripts/docs/generar_diccionario.py --check
```

El generador importa únicamente declaraciones de modelos y el lector de muestras locales.
Extrae las cuatro entradas HTTP por AST sin importar rutas ni dependencias. No carga settings,
no abre la base, no inicia clientes y no consulta proveedores. `--check` verifica que este
archivo coincida con las declaraciones y anotaciones del generador.

| Fuente del código | SHA-256 |
| --- | --- |
| [apps/api/app/api/workflow.py](../apps/api/app/api/workflow.py) | `a2ac11f9e1b67ea498611aff3cb3a1ca733ad388ed2715c3b8afc85acf65283e` |
| [apps/api/app/integrations/startrack.py](../apps/api/app/integrations/startrack.py) | `cc1b7d1dfa083be905475411edc9e09ac08cfb0f44d16038ec3fd6e13c13729f` |
| [apps/api/app/models/graph.py](../apps/api/app/models/graph.py) | `e075109d4b0cbb2100c00f7476b86494476d14b1bcdf681520bfdf9fc83de41a` |
| [apps/api/app/models/hub.py](../apps/api/app/models/hub.py) | `921fdd5495c6f843f511c49229efe2149aefaf1fedfe8bdfd2d131e9380cb9ee` |
| [apps/api/app/models/indicators.py](../apps/api/app/models/indicators.py) | `b89a05ff8ac375e110c21576d4077f7674c36f494fb41623f58bd42709bbe80b` |
| [apps/api/app/models/operations.py](../apps/api/app/models/operations.py) | `e5f2df1e9c19ba9aa7f3ec81de21cb252de6b747321793d7c8ac2b1b2d0bb55b` |
| [apps/api/app/models/suggestions.py](../apps/api/app/models/suggestions.py) | `c0acb3d35caae54b7956e2a4bc7b34226b2de424ce9679860dfab977f97f22a4` |
| [apps/api/app/models/workflow.py](../apps/api/app/models/workflow.py) | `f192c4b9c89ad4c5b730022ecaa3fb4c0ca5fda7828aa3379c5abac7b5cebd90` |
| [apps/api/app/services/transfers.py](../apps/api/app/services/transfers.py) | `37a88828ee2e6411addd5729bcbc309d31dfdf03dfbea863ea37901c7877b687` |

## Inventario estructurado

### Provenance

Procedencia: ECON añade metadatos al dato Prisma/Startrack. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.source` | enum(nexus, startrack) | Sí | `"nexus"` — muestra normalizada | Fuente de la evidencia; en ReceiptRecord identifica declaración manual. | Derivación o metadato ECON |
| `$.source_id` | texto / null | Sí | `"46d2573e-08d3-4855-971d-2fbf9564e135"` — muestra normalizada | ID original del proveedor; conservar separado del ID local y de etiquetas. | Derivación o metadato ECON |
| `$.environment` | enum(local, sandbox) | Sí | `"sandbox"` — muestra normalizada | Entorno de la evidencia o movimiento; no acredita datos de producción. | Derivación o metadato ECON |
| `$.observed_at` | date-time / null | Sí | `null` — muestra normalizada | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Derivación o metadato ECON |
| `$.is_synthetic` | booleano | Sí | `true` — muestra normalizada | Naturaleza sintética de los datos; independiente de fixture/live. | Derivación o metadato ECON |
| `$.evidence_kind` | enum(live_read, provided_sample, test_case) | No | `"provided_sample"` — muestra normalizada | Clase de evidencia: muestra proporcionada, lectura actual o caso interno de prueba. | Derivación o metadato ECON |
| `$.source_reference` | texto / null | No | `"econ-hackathon-openapi.json#/paths/~1api~1maquinaria~1requests/get/responses/200/content/application~1json/example/items/1"` — muestra normalizada | Referencia documental que permite localizar la muestra de origen. | Derivación o metadato ECON |
| `$.observed_on` | date / null | No | `"2026-09-12"` — muestra normalizada | Día documentado sin inventar una hora de observación. | Derivación o metadato ECON |

### SourceStatus

Procedencia: ECON: disponibilidad y cobertura del conector. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | enum(nexus, startrack) | Sí | `"nexus"` — ejemplo técnico de catálogo, no observación | Identidad lógica nexus/startrack del proveedor. | Derivación o metadato ECON |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la fuente o ubicación; no clave de unión. | Derivación o metadato ECON |
| `$.status` | enum(fixture, connected, partial, not_configured, not_queried, disabled, error) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Estado técnico de fuente, distinto del estado de maquinaria o traslado. | Derivación o metadato ECON |
| `$.environment` | enum(local, sandbox) | Sí | `"local"` — ejemplo técnico de catálogo, no observación | Entorno de la evidencia o movimiento; no acredita datos de producción. | Derivación o metadato ECON |
| `$.observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Derivación o metadato ECON |
| `$.observed_on` | date / null | No | `null` — valor por defecto del modelo | Día documentado sin inventar una hora de observación. | Derivación o metadato ECON |
| `$.configured` | booleano / null | No | `null` — valor por defecto del modelo | Configuración de acceso disponible en el servidor; no demuestra conexión ni consulta exitosa. | Derivación o metadato ECON |
| `$.last_evidence_at` | date-time / null | No | `null` — valor por defecto del modelo | Observación más reciente de evidencia local del proveedor; no renueva sus hechos al consultar el panel. | Derivación o metadato ECON |
| `$.message` | texto | Sí | `"<message-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible de disponibilidad/cobertura, sin cuerpos privados ni secretos. | Derivación o metadato ECON |

### ReceiptSummary

Procedencia: Proyección de la recepción declarada en el registro local; sin muestra proporcionada. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.receiver` | texto | Sí | `"<receiver-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre declarado del receptor; no acredita identidad autenticada. | Derivación o metadato ECON |
| `$.received_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante declarado de recepción; el servicio exige zona horaria. | Derivación o metadato ECON |
| `$.reference` | texto | Sí | `"<reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de constancia declarada; no adjunto ni comprobación automática del documento. | Derivación o metadato ECON |
| `$.recorded_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante en que ECON almacena la evidencia o declaración. | Derivación o metadato ECON |
| `$.note` | texto / null | No | `null` — valor por defecto del modelo | Nota opcional de la declaración de recepción. | Derivación o metadato ECON |

### TransferRecord

Procedencia: Proyección de evidencia persistida del traslado; sin tareas en la muestra proporcionada. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección de Startrack prevista; sin muestra |
| `$.code` | texto | Sí | `"<code-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Código descriptivo de equipo/tarea o identificador de regla según el modelo. | Proyección de Startrack prevista; sin muestra |
| `$.status` | texto | Sí | `"<status-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Estado del traslado en la proyección de lectura, separado de maquinaria. | Proyección de Startrack prevista; sin muestra |
| `$.request_id` | texto / null | No | `null` — valor por defecto del modelo | Referencia a la solicitud en el contrato de lectura, normalmente con prefijo nexus:request:. | Proyección de Startrack prevista; sin muestra |
| `$.destination_project_id` | texto / null | No | `null` — valor por defecto del modelo | Referencia de proyecto destino; no prueba presencia ni recepción. | Proyección de Startrack prevista; sin muestra |
| `$.destination_project_name` | texto / null | No | `null` — valor por defecto del modelo | Nombre descriptivo del destino; no resuelve su identidad. | Proyección de Startrack prevista; sin muestra |
| `$.driver` | texto / null | No | `null` — valor por defecto del modelo | Etiqueta de motorista, sin equivalencia automática a usuario o conductor Startrack. | Proyección de Startrack prevista; sin muestra |
| `$.movement_id` | texto / null | No | `null` — valor por defecto del modelo | ID local del movimiento al que pertenece el evento. | Proyección de Startrack prevista; sin muestra |
| `$.workflow_role` | texto / null | No | `null` — valor por defecto del modelo | Rol remoto del catálogo de estado de tarea; no es rol de usuario. | Proyección de Startrack prevista; sin muestra |
| `$.event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante del hecho informado por el origen, si puede interpretarse con zona. | Proyección de Startrack prevista; sin muestra |
| `$.recorded_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante en que ECON almacena la evidencia o declaración. | Proyección de Startrack prevista; sin muestra |
| `$.evidence_current_assignment` | booleano | No | `true` — valor por defecto del modelo | El movimiento corresponde a la asignación y período vigentes de la solicitud; false conserva evidencia histórica. | Proyección de Startrack prevista; sin muestra |
| `$.evidence_origin` | enum(task_observation, creation_acknowledgment) | No | `"task_observation"` — valor por defecto del modelo | Observación de tarea o acuse de creación: un acuse no demuestra consulta posterior del estado. | Proyección de Startrack prevista; sin muestra |
| `$.source_data` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Campos conservados de la observación de tarea; vacío si solo existe acuse de creación. | Proyección de Startrack prevista; sin muestra |
| `$.provenance` | Provenance | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Procedencia del objeto o evento; ver Provenance. | Proyección de Startrack prevista; sin muestra |
| `$.arrival_observed` | booleano | No | `false` — valor por defecto del modelo | Existe una visita GPS a la geocerca de destino vinculada al movimiento; no acredita recepción. | Proyección de Startrack prevista; sin muestra |
| `$.arrival_event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante de la última visita a la geocerca de destino, según Startrack; null sin visita. | Proyección de Startrack prevista; sin muestra |
| `$.arrival_observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante en que ECON leyó la visita de llegada; nunca sustituye a arrival_event_time. | Proyección de Startrack prevista; sin muestra |
| `$.arrival_poi_id` | texto / null | No | `null` — valor por defecto del modelo | ID de la geocerca de destino donde se observó la llegada; null sin visita. | Proyección de Startrack prevista; sin muestra |
| `$.arrival_evidence_origin` | texto / null | No | `null` — valor por defecto del modelo | Origen de la evidencia de llegada (visit_observation); null sin visita. | Proyección de Startrack prevista; sin muestra |
| `$.receipt` | ReceiptSummary / null | No | `null` — valor por defecto del modelo | Declaración explícita de recepción; nunca generada por GPS o cierre de tarea. | Proyección de Startrack prevista; sin muestra |

### LocationObservation

Procedencia: Proyección de ubicación; sin muestra proporcionada. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la fuente o ubicación; no clave de unión. | Proyección de Startrack prevista; sin muestra |
| `$.observed_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de la posición; puede ser anterior a provenance.observed_at. | Proyección de Startrack prevista; sin muestra |
| `$.provenance` | Provenance | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Procedencia del objeto o evento; ver Provenance. | Proyección de Startrack prevista; sin muestra |

### EquipmentOperator

Procedencia: Prisma associated_operators del detalle de equipo; código MOT-xxx compartido con Startrack. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Derivación o metadato ECON |
| `$.name` | texto / null | No | `null` — valor por defecto del modelo | Nombre descriptivo de la maquinaria. | Derivación o metadato ECON |
| `$.worker_code` | texto / null | No | `null` — valor por defecto del modelo | Código MOT-xxx del operador; clave documentada compartida con el conductor de Startrack, nunca unir por nombre. | Derivación o metadato ECON |
| `$.is_active` | booleano / null | No | `null` — valor por defecto del modelo | El operador sigue activo en Prisma. | Derivación o metadato ECON |

### EquipmentRate

Procedencia: Prisma current_project_rate del detalle de equipo; tarifa por proyecto y vigencia. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.project_id` | texto / null | No | `null` — valor por defecto del modelo | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Derivación o metadato ECON |
| `$.hourly_rate` | número / null | No | `null` — valor por defecto del modelo | Prisma precio_x_hora de la tarifa vigente. | Derivación o metadato ECON |
| `$.effective_from` | texto / null | No | `null` — valor por defecto del modelo | Inicio de vigencia de la tarifa según Prisma. | Derivación o metadato ECON |
| `$.effective_to` | texto / null | No | `null` — valor por defecto del modelo | Fin de vigencia de la tarifa; null si sigue vigente. | Derivación o metadato ECON |

### EquipmentRecord

Procedencia: Prisma → normalización ECON; fixtures.py / hub.py. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"` — muestra normalizada | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Prisma: id + prefijo ECON |
| `$.code` | texto / null | Sí | `null` — muestra normalizada | Prisma clave; conservar null aunque exista no_activo. | Prisma: clave |
| `$.asset_number` | texto / null | No | `"CF-03"` — muestra normalizada | Número de activo Prisma no_activo, separado de clave y UUID. | Prisma: no_activo |
| `$.name` | texto | Sí | `"Cargador frontal 03"` — muestra normalizada | Nombre descriptivo de la maquinaria. | Prisma: nombre |
| `$.company` | texto / null | No | `"The Hub"` — muestra normalizada | Valor original de empresa; no se interpreta como identidad legal. | Prisma: empresa |
| `$.equipment_class` | texto / null | No | `"Cargador frontal"` — muestra normalizada | Clase de maquinaria del origen, distinta del tipo de tarea. | Prisma: clase_equipo |
| `$.project_id` | texto / null | No | `"39723f32-8bb5-4158-a415-2a3d49b0993b"` — muestra normalizada | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Prisma: project_id |
| `$.project_name` | texto / null | No | `"PROY-014 - The Hub - Proyecto Xi - La Unión"` — muestra normalizada | Nombre de proyecto del origen; solo presentación. | Prisma: project_name |
| `$.assignment_starts_on` | texto / null | No | `"2026-09-11"` — muestra normalizada | Prisma fecha_inicio_uso: inicio de la asignación del equipo al proyecto; no es programación del traslado. | Derivación o metadato ECON |
| `$.assignment_ends_on` | texto / null | No | `"2026-09-14"` — muestra normalizada | Prisma fecha_fin_uso: fin de la asignación del equipo al proyecto. | Derivación o metadato ECON |
| `$.assignment_note` | texto / null | No | `"Solicitud aprobada: Cargador frontal"` — muestra normalizada | Prisma observaciones_asignacion: texto de la asignación tal como lo informa Prisma. | Derivación o metadato ECON |
| `$.machinery_status` | texto | Sí | `"OBSOLETA"` — muestra normalizada | Estado administrativo de maquinaria Prisma, conservado literalmente. | Prisma: estado |
| `$.maintenance_failure_id` | texto / null | No | `null` — muestra normalizada | Referencia de falla activa, si está disponible. | Prisma: active_failure_id |
| `$.maintenance_status` | texto / null | No | `null` — muestra normalizada | Estado de falla/mantenimiento, separado del estado administrativo. | Prisma: active_failure_status |
| `$.maintenance_is_stopped` | booleano / null | No | `false` — muestra normalizada | Paro explícito: true/false; null significa desconocido. | Prisma: active_failure_is_paro |
| `$.operators` | lista<EquipmentOperator> / null | No | `null` — muestra normalizada | Operadores asociados según el detalle de Prisma; null si la lectura acotada no lo cubrió, [] si no informa ninguno. | Derivación o metadato ECON |
| `$.project_rate` | EquipmentRate / null | No | `null` — muestra normalizada | Tarifa por hora vigente para el proyecto asignado (current_project_rate); no es costo de traslado. | Derivación o metadato ECON |
| `$.request_ids` | lista<texto> | No | `["nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"]` — muestra normalizada | Solicitudes de la consulta vinculadas por maquinaria_id exacto. | Derivación o metadato ECON |
| `$.transfers` | lista<TransferRecord> | No | `[]` — muestra normalizada | Lista de traslados del contrato de lectura; no hay ejemplos Startrack en la muestra. | Derivación o metadato ECON |
| `$.location` | LocationObservation / null | No | `null` — muestra normalizada | Observación de ubicación fechada; ausente en el dataset proporcionado. | Derivación o metadato ECON |
| `$.relation_status` | enum(confirmed, candidate, unlinked) | Sí | `"unlinked"` — muestra normalizada | Calidad de relación: confirmada, candidata o sin vínculo; no equivalencia por nombre. | Derivación o metadato ECON |
| `$.relation_note` | texto | Sí | `"Muestra del OpenAPI entregado. Las solicitudes se relacionan por maquinaria_id exacto. No hay traslado de Startrack ni recepción documentados para esta unidad."` — muestra normalizada | Evidencia o límite de la relación con el traslado. | Derivación o metadato ECON |
| `$.provenance` | Provenance | Sí | `{}` — ver Provenance; muestra normalizada | Procedencia del objeto o evento; ver Provenance. | Derivación o metadato ECON |
| `$.created_at` | date-time / null | No | `"2026-09-12T00:05:09.853492Z"` — muestra normalizada | Creación en Prisma para equipo/solicitud; creación local para movimiento. | Prisma: created_at |
| `$.updated_at` | date-time / null | No | `"2026-09-12T16:04:16.407630Z"` — muestra normalizada | Actualización en Prisma para equipo/solicitud; última actualización local del movimiento. | Prisma: updated_at |

### RequestRecord

Procedencia: Prisma → normalización ECON; fixtures.py / hub.py. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"` — muestra normalizada | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Prisma: id + prefijo ECON |
| `$.project_id` | texto / null | No | `"39723f32-8bb5-4158-a415-2a3d49b0993b"` — muestra normalizada | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Prisma: project_id |
| `$.project_name` | texto / null | No | `"PROY-014 - The Hub - Proyecto Xi - La Unión"` — muestra normalizada | Nombre de proyecto del origen; solo presentación. | Prisma: project_name |
| `$.machinery_id` | texto / null | No | `"nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"` — muestra normalizada | ID normalizado de maquinaria asignada; conserva prefijo del contrato del hub. | Prisma: maquinaria_id + prefijo ECON |
| `$.machinery_name` | texto / null | No | `"Cargador frontal 03"` — muestra normalizada | Prisma maquinaria_nombre expandido en la solicitud; la identidad sigue siendo machinery_id. | Derivación o metadato ECON |
| `$.machinery_asset_number` | texto / null | No | `"CF-03"` — muestra normalizada | Prisma maquinaria_no_activo expandido en la solicitud. | Derivación o metadato ECON |
| `$.machinery_code` | texto / null | No | `null` — muestra normalizada | Prisma maquinaria_clave expandido en la solicitud; puede ser null. | Derivación o metadato ECON |
| `$.status` | texto | Sí | `"APROBADA"` — muestra normalizada | Estado original del flujo de solicitud en Prisma. | Prisma: status |
| `$.starts_on` | texto / null | No | `"2026-09-11"` — muestra normalizada | Inicio del uso solicitado, conservado como texto; no ventana de entrega. | Prisma: fecha_inicio |
| `$.ends_on` | texto / null | No | `"2026-09-14"` — muestra normalizada | Fin del uso solicitado, conservado como texto; no vencimiento del traslado. | Prisma: fecha_fin |
| `$.machinery_type` | texto / null | No | `"Cargador frontal"` — muestra normalizada | Clase solicitada en Prisma; no identifica por sí sola una unidad. | Prisma: tipo |
| `$.requested_by` | texto / null | No | `"María José López Ramírez"` — muestra normalizada | Nombre del solicitante Prisma; no receptor ni usuario Startrack asignado. | Prisma: requested_by_name |
| `$.requested_by_id` | texto / null | No | `"98bf9d4d-fb00-4680-9883-6a72cf0bae0e"` — muestra normalizada | UUID del solicitante Prisma; no se transforma en ID de otro proveedor. | Prisma: requested_by_user_id |
| `$.comments` | texto / null | No | `"Solicito un Cargador Frontal en el Proyecto 14 - The Hub"` — muestra normalizada | Comentarios de solicitud preservados; el borrador actual no los copia. | Prisma: comentarios |
| `$.created_at` | date-time / null | No | `"2026-09-12T00:59:19.326175Z"` — muestra normalizada | Creación en Prisma para equipo/solicitud; creación local para movimiento. | Prisma: created_at |
| `$.updated_at` | date-time / null | No | `"2026-09-12T01:00:01.535958Z"` — muestra normalizada | Actualización en Prisma para equipo/solicitud; última actualización local del movimiento. | Prisma: updated_at |
| `$.approved_at` | date-time / null | No | `"2026-09-12T01:00:01.535958Z"` — muestra normalizada | Instante de aprobación informado por Prisma; no salida, llegada o recepción. | Prisma: approved_at |
| `$.approved_by_user_id` | texto / null | No | `"98bf9d4d-fb00-4680-9883-6a72cf0bae0e"` — muestra normalizada | ID original del usuario que aprobó en Prisma, cuando la fuente lo aporta. | Prisma: approved_by_user_id |
| `$.approved_by` | texto / null | No | `"María José López Ramírez"` — muestra normalizada | Prisma approved_by_name: nombre del aprobador tal como lo informa la fuente. | Derivación o metadato ECON |
| `$.provenance` | Provenance | Sí | `{}` — ver Provenance; muestra normalizada | Procedencia del objeto o evento; ver Provenance. | Derivación o metadato ECON |

### AlertRecord

Procedencia: ECON: services/hub.py evaluate_alerts. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Derivación o metadato ECON |
| `$.code` | texto | Sí | `"<code-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Código descriptivo de equipo/tarea o identificador de regla según el modelo. | Derivación o metadato ECON |
| `$.severity` | enum(info, warning, critical) | Sí | `"info"` — ejemplo técnico de catálogo, no observación | Categoría propuesta de una regla de alerta; no SLA ni puntaje de riesgo. | Derivación o metadato ECON |
| `$.title` | texto | Sí | `"<title-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Texto de la señal de revisión. | Derivación o metadato ECON |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación de alerta o contenido generado del borrador, según modelo. | Derivación o metadato ECON |
| `$.owner` | texto | Sí | `"<owner-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Área funcional propuesta para revisar la alerta; no asignación autenticada. | Derivación o metadato ECON |
| `$.equipment_id` | texto / null | No | `null` — valor por defecto del modelo | Referencia a maquinaria en el contrato normalizado de lectura. | Derivación o metadato ECON |
| `$.request_id` | texto / null | No | `null` — valor por defecto del modelo | Referencia a la solicitud en el contrato de lectura, normalmente con prefijo nexus:request:. | Derivación o metadato ECON |
| `$.evidence` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que sostienen la regla de alerta, como lista de textos. | Derivación o metadato ECON |

### HubScope

Procedencia: ECON: límites de lectura y filtrado local. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.search` | texto | Sí | `""` — derivado de muestra / alcance | Búsqueda local sobre el conjunto acotado recibido. | Derivación o metadato ECON |
| `$.bounded` | booleano | No | `true` — derivado de muestra / alcance | Indica que la consulta tiene límites; no es censo irrestricto. | Derivación o metadato ECON |
| `$.equipment_total` | entero / null | No | `15` — derivado de muestra / alcance | Total de equipos informado por el origen antes del filtro local. | Derivación o metadato ECON |
| `$.requests_total` | entero / null | No | `2` — derivado de muestra / alcance | Total de solicitudes informado por el origen antes del filtro local. | Derivación o metadato ECON |
| `$.equipment_returned` | entero | No | `5` — derivado de muestra / alcance | Equipos incluidos tras aplicar la búsqueda local. | Derivación o metadato ECON |
| `$.requests_returned` | entero | No | `2` — derivado de muestra / alcance | Solicitudes incluidas tras aplicar la búsqueda local. | Derivación o metadato ECON |
| `$.complete` | booleano | Sí | `false` — derivado de muestra / alcance | Completitud del ámbito consultado según el modelo, no simple éxito de una llamada. | Derivación o metadato ECON |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación de la población y límites de cobertura de la consulta. | Derivación o metadato ECON |

### HubSummary

Procedencia: ECON: conteos sobre registros devueltos. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.equipment_count` | entero / null | No | `5` — derivado de muestra / alcance | Conteo de equipos devueltos; null si no se obtuvo lectura evaluable. | Derivación o metadato ECON |
| `$.administratively_available` | entero / null | No | `4` — derivado de muestra / alcance | Equipos devueltos cuyo estado administrativo es Disponible; no disponibilidad física. | Derivación o metadato ECON |
| `$.active_failures` | entero / null | No | `0` — derivado de muestra / alcance | Equipos devueltos con referencia de falla activa. | Derivación o metadato ECON |
| `$.stopped_equipment` | entero / null | No | `0` — derivado de muestra / alcance | Equipos devueltos con paro explícito true. | Derivación o metadato ECON |
| `$.unlinked_equipment` | entero / null | No | `5` — derivado de muestra / alcance | Equipos devueltos cuya relación no es confirmed; incluye candidatos. | Derivación o metadato ECON |
| `$.alerts_count` | entero / null | No | `null` — valor por defecto del modelo | Alertas sobre los datos evaluados; cero no certifica ausencia global de riesgo. | Derivación o metadato ECON |

### OperationEvidenceStatus

Procedencia: ECON: cobertura del registro local consultado por services/evidence.py. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.status` | enum(not_queried, available, partial, disabled, error) | No | `"not_queried"` — valor por defecto del modelo | Estado del objeto del modelo; ver separación semántica de estados. | Derivación o metadato ECON |
| `$.checked_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de consulta del registro local; no fecha de actualización de sus evidencias. | Derivación o metadato ECON |
| `$.movements_returned` | entero / null | No | `null` — valor por defecto del modelo | Cantidad de movimientos locales en la ventana consultada; null si no se pudo evaluar. | Derivación o metadato ECON |
| `$.complete` | booleano | No | `false` — valor por defecto del modelo | Completitud del ámbito consultado según el modelo, no simple éxito de una llamada. | Derivación o metadato ECON |
| `$.message` | texto | No | `"El registro de movimientos no se ha consultado."` — valor por defecto del modelo | Explicación legible de disponibilidad/cobertura, sin cuerpos privados ni secretos. | Derivación o metadato ECON |

### HubResponse

Procedencia: ECON: ensamblaje del contrato de consulta. [Código](../apps/api/app/models/hub.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.schema_version` | "1.0" | No | `"1.0"` — valor por defecto del modelo | Versión del contrato de lectura de ECON. | Derivación o metadato ECON |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — derivado de muestra / alcance | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Derivación o metadato ECON |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Derivación o metadato ECON |
| `$.data_as_of` | date-time / null | No | `null` — derivado de muestra / alcance | Corte de lectura, cuando existe; null en muestras sin instante común. | Derivación o metadato ECON |
| `$.sources` | lista<SourceStatus> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Estados técnicos y cobertura de las fuentes. | Derivación o metadato ECON |
| `$.scope` | HubScope | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Población, filtros y límites de la respuesta; ver HubScope. | Derivación o metadato ECON |
| `$.summary` | HubSummary | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Conteos sobre la población devuelta; ver HubSummary. | Derivación o metadato ECON |
| `$.operation_evidence` | OperationEvidenceStatus | No | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Disponibilidad y cobertura de movimientos usados por la proyección; ver OperationEvidenceStatus. | Derivación o metadato ECON |
| `$.equipment` | lista<EquipmentRecord> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Equipos de la proyección de lectura; ver EquipmentRecord. | Derivación o metadato ECON |
| `$.requests` | lista<RequestRecord> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Solicitudes de la proyección de lectura; ver RequestRecord. | Derivación o metadato ECON |
| `$.alerts` | lista<AlertRecord> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Señales derivadas de hechos disponibles; ver AlertRecord. | Derivación o metadato ECON |

### Movement

Procedencia: ECON: registro SQLModel de plan/envío/evidencia. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.mode` | texto | Sí | `"<mode-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Registro local ECON; significado según campo |
| `$.environment` | texto | Sí | `"<environment-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Entorno de la evidencia o movimiento; no acredita datos de producción. | Registro local ECON; significado según campo |
| `$.movement_reference` | texto | Sí | `"<movement_reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de correlación creada en ECON; se envía como remote_id, sin unicidad remota garantizada. | Registro local ECON; significado según campo |
| `$.request_source_id` | texto | Sí | `"<request_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de solicitud Prisma, sin prefijo local. | Registro local ECON; significado según campo |
| `$.machinery_source_id` | texto | Sí | `"<machinery_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de maquinaria Prisma, sin prefijo local. | Registro local ECON; significado según campo |
| `$.project_source_id` | texto | Sí | `"<project_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original del proyecto Prisma. | Registro local ECON; significado según campo |
| `$.tracked_vehicle_id` | texto / null | No | `null` — valor por defecto del modelo | ID de activo rastreado elegido por separado; puede ser el transportador. | Registro local ECON; significado según campo |
| `$.tracked_vehicle_kind` | texto / null | No | `null` — valor por defecto del modelo | Declarado por el operador (machine_device o transporter); no verificado: el catálogo de vehículos de Startrack no tiene tipo. Requiere tracked_vehicle_id. | Registro local ECON; significado según campo |
| `$.mapping` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Correspondencias explícitas y programación; estructura de TransferMapping. | Registro local ECON; significado según campo |
| `$.source_request` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Copia normalizada de solicitud usada como evidencia del movimiento. | Registro local ECON; significado según campo |
| `$.source_equipment` | objeto JSON / null | No | `null` — valor por defecto del modelo | Copia normalizada de maquinaria usada como evidencia, si existe. | Registro local ECON; significado según campo |
| `$.source_request_hash` | texto | Sí | `"0000000000000000000000000000000000000000000000000000000000000000"` — estructura técnica SHA-256, no huella calculada | SHA-256 de la copia normalizada de solicitud con JSON canónico local. | Registro local ECON; significado según campo |
| `$.source_equipment_hash` | texto / null | No | `null` — valor por defecto del modelo | SHA-256 de la copia normalizada de maquinaria, cuando existe. | Registro local ECON; significado según campo |
| `$.identity_hash` | texto | Sí | `"0000000000000000000000000000000000000000000000000000000000000000"` — estructura técnica SHA-256, no huella calculada | SHA-256 de mapping, payload y tracked_vehicle_id; distingue contenido del plan bajo su referencia local. | Registro local ECON; significado según campo |
| `$.payload` | objeto JSON / null | No | `null` — valor por defecto del modelo | Cuerpo preparado para Job; null si no hay borrador válido. No acredita envío. | Registro local ECON; significado según campo |
| `$.preparation` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Resultado estructurado de preparación; ver TransferPreparation. | Registro local ECON; significado según campo |
| `$.state` | texto | Sí | `"<state-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Estado local del envío; separado del estado remoto de tarea y de recepción. | Registro local ECON; significado según campo |
| `$.job_id` | texto / null | No | `null` — valor por defecto del modelo | ID de tarea confirmado por Startrack; ausente en muestras proporcionadas. | Startrack → registro ECON |
| `$.status` | texto / null | No | `null` — valor por defecto del modelo | ID/texto de estado remoto de la tarea Startrack; no estado de envío local. | Startrack → registro ECON |
| `$.workflow_role` | texto / null | No | `null` — valor por defecto del modelo | Rol remoto del catálogo de estado de tarea; no es rol de usuario. | Startrack → registro ECON |
| `$.reason_code` | texto / null | No | `null` — valor por defecto del modelo | Código local de motivo/bloqueo/fallo; detalle en eventos y preparación. | Registro local ECON; significado según campo |
| `$.created_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Creación en Prisma para equipo/solicitud; creación local para movimiento. | Registro local ECON; significado según campo |
| `$.updated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Actualización en Prisma para equipo/solicitud; última actualización local del movimiento. | Registro local ECON; significado según campo |
| `$.next_review_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Marca durable para ordenar revisiones del worker; no modifica la fecha de observación del proveedor. | Registro local ECON; significado según campo |
| `$.queued_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local de ingreso en cola, si ocurrió. | Registro local ECON; significado según campo |
| `$.sending_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local de reclamación/inicio de envío, si ocurrió. | Registro local ECON; significado según campo |
| `$.sent_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local en que se confirmó asociación de tarea; no ejecución ni llegada. | Registro local ECON; significado según campo |
| `$.receipt` | objeto JSON / null | No | `null` — valor por defecto del modelo | Declaración explícita de recepción; nunca generada por GPS o cierre de tarea. | Registro local ECON; significado según campo |

### OperationEvent

Procedencia: ECON: services/ledger.py y services/workflow.py. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.movement_id` | texto | Sí | `"<movement_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID local del movimiento al que pertenece el evento. | Registro local ECON; significado según campo |
| `$.kind` | texto | Sí | `"<kind-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Tipo de evento local: transición, observación, evidencia o recepción según el productor. | Registro local ECON; significado según campo |
| `$.state` | texto / null | No | `null` — valor por defecto del modelo | Estado local del envío; separado del estado remoto de tarea y de recepción. | Registro local ECON; significado según campo |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Registro local ECON; significado según campo |
| `$.evidence_hash` | texto / null | No | `null` — valor por defecto del modelo | SHA-256 de kind/source_id/event_time/data/provenance, sin provenance.observed_at; deduplica task_state/arrival. | Registro local ECON; significado según campo |
| `$.event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante del hecho informado por el origen, si puede interpretarse con zona. | Registro local ECON; significado según campo |
| `$.observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Registro local ECON; significado según campo |
| `$.recorded_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante en que ECON almacena la evidencia o declaración. | Registro local ECON; significado según campo |
| `$.data` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Contenido del evento local/observación; objeto JSON de estructura según kind. | Registro local ECON; significado según campo |
| `$.provenance` | objeto JSON / null | No | `null` — valor por defecto del modelo | Procedencia del objeto o evento; ver Provenance. | Registro local ECON; significado según campo |
| `$.actor_user_id` | texto / null | No | `null` — valor por defecto del modelo | ID del usuario de sesión que causó la transición; null con actor de proceso o sesión desconocida, nunca inventado. | Registro local ECON; significado según campo |
| `$.actor_role` | texto / null | No | `null` — valor por defecto del modelo | Rol de sesión del actor en el momento de la transición; null sin sesión. | Registro local ECON; significado según campo |
| `$.actor_kind` | texto / null | No | `null` — valor por defecto del modelo | session (usuario autenticado), local_dev (AUTH_REQUIRED=false sin login) o cli_worker (proceso); null en filas anteriores a la migración 0004. | Registro local ECON; significado según campo |

### SourceSnapshot

Procedencia: ECON: conservación explícita de cortes. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.mode` | texto | Sí | `"<mode-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Registro local ECON; significado según campo |
| `$.recorded_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante en que ECON almacena la evidencia o declaración. | Registro local ECON; significado según campo |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Registro local ECON; significado según campo |
| `$.data_as_of` | date-time / null | No | `null` — valor por defecto del modelo | Corte de lectura, cuando existe; null en muestras sin instante común. | Registro local ECON; significado según campo |
| `$.content_hash` | texto | Sí | `"0000000000000000000000000000000000000000000000000000000000000000"` — estructura técnica SHA-256, no huella calculada | SHA-256 del HubResponse completo, incluidos tiempos/cobertura; no huella exclusiva de hechos de negocio. | Registro local ECON; significado según campo |
| `$.content` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Respuesta del hub serializada que se conserva como corte. | Registro local ECON; significado según campo |
| `$.last_confirmed_at` | date-time / null | No | `null` — valor por defecto del modelo | Última relectura cuya huella estable coincidió con este corte; con recorded_at forma la última lectura (last_sync_at). Null si nunca se confirmó. | Registro local ECON; significado según campo |

### Actor

Procedencia: ECON: quién ejecuta una transición del registro (sesión, desarrollo local o worker). [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.user_id` | texto / null | No | `null` — valor por defecto del modelo | Identificador del usuario autenticado; obligatorio con kind=session y prohibido en actores sin sesión. | Sesión autenticada o proceso local; nunca fabricado |
| `$.email` | texto / null | No | `null` — valor por defecto del modelo | Correo del usuario de sesión, copiado como dato; nunca se usa para unir con proveedores. | Sesión autenticada o proceso local; nunca fabricado |
| `$.role` | texto / null | No | `null` — valor por defecto del modelo | Rol de sesión (ADR 0005) con el que se ejecutó la acción; no es rol de Startrack ni de la RACI aprobada. | Sesión autenticada o proceso local; nunca fabricado |
| `$.kind` | enum(session, local_dev, cli_worker) | Sí | `"session"` — ejemplo técnico de catálogo, no observación | session, local_dev o cli_worker; determina si puede llevar usuario, correo y rol. | Sesión autenticada o proceso local; nunca fabricado |

### ReceiptRecord

Procedencia: Declaración manual → registro local ECON. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.receiver` | texto | Sí | `"<receiver-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre declarado del receptor; no acredita identidad autenticada. | Entrada explícita; metadatos de registro en ECON |
| `$.received_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante declarado de recepción; el servicio exige zona horaria. | Entrada explícita; metadatos de registro en ECON |
| `$.reference` | texto | Sí | `"<reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de constancia declarada; no adjunto ni comprobación automática del documento. | Entrada explícita; metadatos de registro en ECON |
| `$.recorded_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante en que ECON almacena la evidencia o declaración. | Entrada explícita; metadatos de registro en ECON |
| `$.note` | texto / null | No | `null` — valor por defecto del modelo | Nota opcional de la declaración de recepción. | Entrada explícita; metadatos de registro en ECON |
| `$.source` | "manual_declaration" | No | `"manual_declaration"` — valor por defecto del modelo | Fuente de la evidencia; en ReceiptRecord identifica declaración manual. | Entrada explícita; metadatos de registro en ECON |
| `$.declared_by_user_id` | texto / null | No | `null` — valor por defecto del modelo | ID del usuario autenticado que registró la recepción (migración 0004); null sin sesión. No sustituye a receiver. | Entrada explícita; metadatos de registro en ECON |
| `$.declared_by_email` | texto / null | No | `null` — valor por defecto del modelo | Correo del usuario que registró la recepción; null sin sesión. | Entrada explícita; metadatos de registro en ECON |
| `$.declared_by_role` | texto / null | No | `null` — valor por defecto del modelo | Rol de sesión de quien registró la recepción; no acredita autoridad empresarial para recibir. | Entrada explícita; metadatos de registro en ECON |

### MovementEventRecord

Procedencia: Proyección de OperationEvent para consumo. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.kind` | texto | Sí | `"<kind-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Tipo de evento local: transición, observación, evidencia o recepción según el productor. | Registro local ECON; significado según campo |
| `$.state` | enum(draft, blocked, queued, sending, sent, unknown, failed) / null | No | `null` — valor por defecto del modelo | Estado local del envío; separado del estado remoto de tarea y de recepción. | Registro local ECON; significado según campo |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Registro local ECON; significado según campo |
| `$.event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante del hecho informado por el origen, si puede interpretarse con zona. | Registro local ECON; significado según campo |
| `$.observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Registro local ECON; significado según campo |
| `$.recorded_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante en que ECON almacena la evidencia o declaración. | Registro local ECON; significado según campo |
| `$.data` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Contenido del evento local/observación; objeto JSON de estructura según kind. | Registro local ECON; significado según campo |
| `$.provenance` | Provenance / null | No | `null` — valor por defecto del modelo | Procedencia del objeto o evento; ver Provenance. | Registro local ECON; significado según campo |
| `$.actor_user_id` | texto / null | No | `null` — valor por defecto del modelo | ID del usuario de sesión que causó la transición; null con actor de proceso o sesión desconocida, nunca inventado. | Registro local ECON; significado según campo |
| `$.actor_role` | texto / null | No | `null` — valor por defecto del modelo | Rol de sesión del actor en el momento de la transición; null sin sesión. | Registro local ECON; significado según campo |
| `$.actor_kind` | enum(session, local_dev, cli_worker) / null | No | `null` — valor por defecto del modelo | session (usuario autenticado), local_dev (AUTH_REQUIRED=false sin login) o cli_worker (proceso); null en filas anteriores a la migración 0004. | Registro local ECON; significado según campo |

### MovementRecord

Procedencia: Proyección de Movement y su historial local. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Registro local ECON; significado según campo |
| `$.environment` | texto | Sí | `"<environment-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Entorno de la evidencia o movimiento; no acredita datos de producción. | Registro local ECON; significado según campo |
| `$.movement_reference` | texto | Sí | `"<movement_reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de correlación creada en ECON; se envía como remote_id, sin unicidad remota garantizada. | Registro local ECON; significado según campo |
| `$.request_source_id` | texto | Sí | `"<request_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de solicitud Prisma, sin prefijo local. | Registro local ECON; significado según campo |
| `$.machinery_source_id` | texto | Sí | `"<machinery_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de maquinaria Prisma, sin prefijo local. | Registro local ECON; significado según campo |
| `$.project_source_id` | texto | Sí | `"<project_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original del proyecto Prisma. | Registro local ECON; significado según campo |
| `$.tracked_vehicle_id` | texto / null | No | `null` — valor por defecto del modelo | ID de activo rastreado elegido por separado; puede ser el transportador. | Registro local ECON; significado según campo |
| `$.tracked_vehicle_kind` | enum(machine_device, transporter) / null | No | `null` — valor por defecto del modelo | Declarado por el operador (machine_device o transporter); no verificado: el catálogo de vehículos de Startrack no tiene tipo. Requiere tracked_vehicle_id. | Registro local ECON; significado según campo |
| `$.mapping` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Correspondencias explícitas y programación; estructura de TransferMapping. | Registro local ECON; significado según campo |
| `$.source_request` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Copia normalizada de solicitud usada como evidencia del movimiento. | Registro local ECON; significado según campo |
| `$.source_equipment` | objeto JSON / null | Sí | `null` — sin muestra; null permitido | Copia normalizada de maquinaria usada como evidencia, si existe. | Registro local ECON; significado según campo |
| `$.source_request_hash` | texto | Sí | `"0000000000000000000000000000000000000000000000000000000000000000"` — estructura técnica SHA-256, no huella calculada | SHA-256 de la copia normalizada de solicitud con JSON canónico local. | Registro local ECON; significado según campo |
| `$.source_equipment_hash` | texto / null | Sí | `null` — sin muestra; null permitido | SHA-256 de la copia normalizada de maquinaria, cuando existe. | Registro local ECON; significado según campo |
| `$.payload` | objeto JSON / null | Sí | `null` — sin muestra; null permitido | Cuerpo preparado para Job; null si no hay borrador válido. No acredita envío. | Registro local ECON; significado según campo |
| `$.preparation` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Resultado estructurado de preparación; ver TransferPreparation. | Registro local ECON; significado según campo |
| `$.state` | enum(draft, blocked, queued, sending, sent, unknown, failed) | Sí | `"draft"` — ejemplo técnico de catálogo, no observación | Estado local del envío; separado del estado remoto de tarea y de recepción. | Registro local ECON; significado según campo |
| `$.job_id` | texto / null | No | `null` — valor por defecto del modelo | ID de tarea confirmado por Startrack; ausente en muestras proporcionadas. | Startrack → registro ECON |
| `$.status` | texto / null | No | `null` — valor por defecto del modelo | ID/texto de estado remoto de la tarea Startrack; no estado de envío local. | Startrack → registro ECON |
| `$.workflow_role` | texto / null | No | `null` — valor por defecto del modelo | Rol remoto del catálogo de estado de tarea; no es rol de usuario. | Startrack → registro ECON |
| `$.reason_code` | texto / null | No | `null` — valor por defecto del modelo | Código local de motivo/bloqueo/fallo; detalle en eventos y preparación. | Registro local ECON; significado según campo |
| `$.created_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Creación en Prisma para equipo/solicitud; creación local para movimiento. | Registro local ECON; significado según campo |
| `$.updated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Actualización en Prisma para equipo/solicitud; última actualización local del movimiento. | Registro local ECON; significado según campo |
| `$.next_review_at` | date-time / null | No | `null` — valor por defecto del modelo | Marca durable para ordenar revisiones del worker; no modifica la fecha de observación del proveedor. | Registro local ECON; significado según campo |
| `$.queued_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local de ingreso en cola, si ocurrió. | Registro local ECON; significado según campo |
| `$.sending_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local de reclamación/inicio de envío, si ocurrió. | Registro local ECON; significado según campo |
| `$.sent_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local en que se confirmó asociación de tarea; no ejecución ni llegada. | Registro local ECON; significado según campo |
| `$.receipt` | ReceiptRecord / null | No | `null` — valor por defecto del modelo | Declaración explícita de recepción; nunca generada por GPS o cierre de tarea. | Registro local ECON; significado según campo |
| `$.events` | lista<MovementEventRecord> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Historial local de eventos; no copia completa de la actividad de los proveedores. | Registro local ECON; significado según campo |

### SnapshotRecord

Procedencia: Proyección de SourceSnapshot. [Código](../apps/api/app/models/operations.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Registro local ECON; significado según campo |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Registro local ECON; significado según campo |
| `$.recorded_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante en que ECON almacena la evidencia o declaración. | Registro local ECON; significado según campo |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Registro local ECON; significado según campo |
| `$.data_as_of` | date-time / null | No | `null` — valor por defecto del modelo | Corte de lectura, cuando existe; null en muestras sin instante común. | Registro local ECON; significado según campo |
| `$.content_hash` | texto | Sí | `"0000000000000000000000000000000000000000000000000000000000000000"` — estructura técnica SHA-256, no huella calculada | SHA-256 del HubResponse completo, incluidos tiempos/cobertura; no huella exclusiva de hechos de negocio. | Registro local ECON; significado según campo |
| `$.content` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Respuesta del hub serializada que se conserva como corte. | Registro local ECON; significado según campo |
| `$.last_confirmed_at` | date-time / null | No | `null` — valor por defecto del modelo | Última relectura cuya huella estable coincidió con este corte; con recorded_at forma la última lectura (last_sync_at). Null si nunca se confirmó. | Registro local ECON; significado según campo |

### OperationsCoverage

Procedencia: ECON: población y cobertura de la página de operaciones. [Código](../apps/api/app/models/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.total` | entero | No | `0` — valor por defecto del modelo | Total de movimientos locales del modo y filtro, antes de paginar; evaluar available antes de interpretarlo. | Derivación o metadato ECON |
| `$.displayed` | entero | No | `0` — valor por defecto del modelo | Número de movimientos devueltos en esta página. | Derivación o metadato ECON |
| `$.page` | entero | No | `1` — valor por defecto del modelo | Página solicitada del registro local, comenzando en 1. | Derivación o metadato ECON |
| `$.page_size` | entero | No | `100` — valor por defecto del modelo | Máximo de movimientos por página; 100 por defecto y hasta 500. | Derivación o metadato ECON |
| `$.total_pages` | entero | No | `1` — valor por defecto del modelo | Número de páginas de la población filtrada, con mínimo 1 incluso vacía. | Derivación o metadato ECON |
| `$.has_more` | booleano | No | `false` — valor por defecto del modelo | Existen páginas posteriores; false no significa que esta página contenga toda la población. | Derivación o metadato ECON |
| `$.is_complete` | booleano | No | `true` — valor por defecto del modelo | La primera página contiene todos los movimientos del modo y filtro; coincide con WorkflowOverview.complete. | Derivación o metadato ECON |
| `$.note` | texto | No | `""` — valor por defecto del modelo | Texto de cobertura de la página: filas devueltas, total y página; no describe recepción. | Derivación o metadato ECON |

### WorkflowOverview

Procedencia: ECON: resumen de operaciones consultadas. [Código](../apps/api/app/models/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.available` | booleano | Sí | `false` — ejemplo técnico de tipo, no observación | Disponibilidad de consulta del registro local de operaciones. | Derivación o metadato ECON |
| `$.message` | texto | Sí | `"<message-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible de disponibilidad/cobertura, sin cuerpos privados ni secretos. | Derivación o metadato ECON |
| `$.complete` | booleano | No | `false` — valor por defecto del modelo | La primera página contiene todos los movimientos locales del modo/solicitud; coincide con coverage.is_complete. False ante lectura parcial, fallo o cobertura desconocida. No certifica cobertura de proveedores. | Derivación o metadato ECON |
| `$.management_enabled` | booleano | No | `false` — valor por defecto del modelo | Capacidad de gestión habilitada por servidor y contexto local; no autorización desde navegador. | Derivación o metadato ECON |
| `$.sending_enabled` | booleano | No | `false` — valor por defecto del modelo | Habilitación de envío evaluada por servidor; no demuestra conectividad ni permisos remotos. | Derivación o metadato ECON |
| `$.movements` | lista<MovementRecord> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Movimientos locales de la ventana consultada; ausencia solo evaluable con available=true y complete=true. | Derivación o metadato ECON |
| `$.last_sync_at` | date-time / null | No | `null` — valor por defecto del modelo | recorded_at del último SourceSnapshot por modo; no acredita sincronización exitosa de todas las fuentes. | Derivación o metadato ECON |
| `$.total` | entero | No | `0` — valor por defecto del modelo | Total de movimientos locales del modo y filtro, antes de paginar; evaluar available antes de interpretarlo. | Derivación o metadato ECON |
| `$.page` | entero | No | `1` — valor por defecto del modelo | Página solicitada del registro local, comenzando en 1. | Derivación o metadato ECON |
| `$.page_size` | entero | No | `100` — valor por defecto del modelo | Máximo de movimientos por página; 100 por defecto y hasta 500. | Derivación o metadato ECON |
| `$.total_pages` | entero | No | `1` — valor por defecto del modelo | Número de páginas de la población filtrada, con mínimo 1 incluso vacía. | Derivación o metadato ECON |
| `$.coverage` | OperationsCoverage / null | No | `null` — valor por defecto del modelo | Cobertura de la página local; null cuando no se pudo consultar el registro. | Derivación o metadato ECON |

### MappingCatalogs

Procedencia: Startrack SDK → catálogos acotados de ECON. [Código](../apps/api/app/models/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.observed_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Startrack SDK; metadatos de consulta ECON |
| `$.complete` | booleano | No | `false` — valor por defecto del modelo | Completitud del ámbito consultado según el modelo, no simple éxito de una llamada. | Startrack SDK; metadatos de consulta ECON |
| `$.message` | texto | No | `"Catálogos acotados; vincula por ID y confirma el destino y responsable."` — valor por defecto del modelo | Explicación legible de disponibilidad/cobertura, sin cuerpos privados ni secretos. | Startrack SDK; metadatos de consulta ECON |
| `$.pois` | lista<objeto JSON> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Catálogo acotado de geocercas para elegir IDs; no maestro de equivalencias aprobado. | Startrack SDK; metadatos de consulta ECON |
| `$.users` | lista<objeto JSON> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Catálogo acotado de usuarios Startrack asignables; separado de operadores Prisma. | Startrack SDK; metadatos de consulta ECON |
| `$.vehicles` | lista<objeto JSON> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Catálogo acotado de activos rastreados. | Startrack SDK; metadatos de consulta ECON |
| `$.job_types` | lista<objeto JSON> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Catálogo acotado de tipos de tarea; distinto de clase de maquinaria. | Startrack SDK; metadatos de consulta ECON |

### EvidenceRef

Procedencia: ECON: services/graph.py, procedencia de cada hecho del grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.origin` | enum(nexus, startrack, econ_ledger, econ_declaration) | Sí | `"nexus"` — ejemplo técnico de catálogo, no observación | Sistema del que procede la evidencia: nexus, startrack, econ_ledger o econ_declaration. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.provenance` | Provenance / null | No | `null` — valor por defecto del modelo | Procedencia del objeto o evento; ver Provenance. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.environment` | texto / null | No | `null` — valor por defecto del modelo | Entorno de la evidencia o movimiento; no acredita datos de producción. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence_kind` | enum(live_read, provided_sample, test_case) / null | No | `null` — valor por defecto del modelo | Clase de evidencia: muestra proporcionada, lectura actual o caso interno de prueba. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante del hecho informado por el origen, si puede interpretarse con zona. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.observed_on` | date / null | No | `null` — valor por defecto del modelo | Día documentado sin inventar una hora de observación. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.recorded_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante en que ECON almacena la evidencia o declaración. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.reference` | texto / null | No | `null` — valor por defecto del modelo | Referencia local que localiza la evidencia (movimiento, evento, constancia). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.note` | texto / null | No | `null` — valor por defecto del modelo | Nota de interpretación de la evidencia (por ejemplo «Declarado por el operador; no verificado»). | Proyección ECON de lectura y registro; procedencia en evidence |

### NodeBase

Procedencia: ECON: base de los nodos del grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | enum(machine, project, place, request, movement, incident) | Sí | `"machine"` — ejemplo técnico de catálogo, no observación | Tipo de nodo: machine, project, place, request, movement o incident. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación del nodo; nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef que sostienen el nodo; vacía en nodos solo referenciados. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |

### MachineNode

Procedencia: Proyección de EquipmentRecord en el grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "machine" | No | `"machine"` — valor por defecto del modelo | Constante machine; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la unidad (activo o nombre); nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef de la lectura de Prisma que sostiene el nodo. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.asset_number` | texto / null | No | `null` — valor por defecto del modelo | Número de activo Prisma no_activo, separado de clave y UUID. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.code` | texto / null | No | `null` — valor por defecto del modelo | Código descriptivo de equipo/tarea o identificador de regla según el modelo. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.name` | texto / null | No | `null` — valor por defecto del modelo | Nombre descriptivo de la maquinaria. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.company` | texto / null | No | `null` — valor por defecto del modelo | Valor original de empresa; no se interpreta como identidad legal. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.equipment_class` | texto / null | No | `null` — valor por defecto del modelo | Clase de maquinaria del origen, distinta del tipo de tarea. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.machinery_status` | texto / null | No | `null` — valor por defecto del modelo | Estado administrativo de maquinaria Prisma, conservado literalmente. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.project_id` | texto / null | No | `null` — valor por defecto del modelo | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.assignment_starts_on` | texto / null | No | `null` — valor por defecto del modelo | Prisma fecha_inicio_uso: inicio de la asignación del equipo al proyecto; no es programación del traslado. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.assignment_ends_on` | texto / null | No | `null` — valor por defecto del modelo | Prisma fecha_fin_uso: fin de la asignación del equipo al proyecto. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.assignment_note` | texto / null | No | `null` — valor por defecto del modelo | Prisma observaciones_asignacion: texto de la asignación tal como lo informa Prisma. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.maintenance_failure_id` | texto / null | No | `null` — valor por defecto del modelo | Referencia de falla activa, si está disponible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.maintenance_status` | texto / null | No | `null` — valor por defecto del modelo | Estado de falla/mantenimiento, separado del estado administrativo. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.maintenance_is_stopped` | booleano / null | No | `null` — valor por defecto del modelo | Paro explícito: true/false; null significa desconocido. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.relation_status` | texto / null | No | `null` — valor por defecto del modelo | Calidad de relación: confirmada, candidata o sin vínculo; no equivalencia por nombre. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.last_observed` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Instante del hecho por tipo (administrative, task, presence, receipt), cada uno con su propia última observación; presence es del vehículo rastreado, no de la máquina. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.last_read` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Instante de lectura o registro de cada hecho; no sustituye al instante del hecho. | Proyección ECON de lectura y registro; procedencia en evidence |

### ProjectNode

Procedencia: Referencia de proyecto derivada de project_id; no se lee de Prisma. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "project" | No | `"project"` — valor por defecto del modelo | Constante project; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre o ID de proyecto para presentación; nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Vacía: el proyecto solo se referencia por ID, no se lee de Prisma. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.name` | texto / null | No | `null` — valor por defecto del modelo | Nombre de proyecto tal como lo referencian solicitudes o equipos; solo presentación. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.presence` | "referenced_only" | No | `"referenced_only"` — valor por defecto del modelo | Siempre referenced_only: el proyecto no se lee de Prisma, solo se referencia por project_id. | Proyección ECON de lectura y registro; procedencia en evidence |

### PlaceNode

Procedencia: Geocerca del mapeo (poi_id) y nombre observado en Startrack si coincide. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "place" | No | `"place"` — valor por defecto del modelo | Constante place; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de la geocerca (nombre observado o poi_id); nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef del mapeo declarado y, si coincide el poi_id, de la tarea observada. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.poi_id` | texto | Sí | `"<poi_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID Startrack de destino confirmado explícitamente; no inferido del nombre de proyecto. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.name` | texto / null | No | `null` — valor por defecto del modelo | Nombre observado en Startrack para ese mismo poi_id; null si no se leyó. Nunca unido por nombre. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.geometry` | null | No | `null` — valor por defecto del modelo | Siempre null: ECON no conserva coordenadas ni radio de la geocerca. | Proyección ECON de lectura y registro; procedencia en evidence |

### RequestNode

Procedencia: Proyección de RequestRecord en el grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "request" | No | `"request"` — valor por defecto del modelo | Constante request; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la solicitud; nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef de la lectura de Prisma que sostiene el nodo. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.status` | texto / null | No | `null` — valor por defecto del modelo | Estado original del flujo de solicitud en Prisma. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.project_id` | texto / null | No | `null` — valor por defecto del modelo | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.machinery_id` | texto / null | No | `null` — valor por defecto del modelo | ID normalizado de maquinaria asignada; conserva prefijo del contrato del hub. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.machinery_type` | texto / null | No | `null` — valor por defecto del modelo | Clase solicitada en Prisma; no identifica por sí sola una unidad. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.starts_on` | texto / null | No | `null` — valor por defecto del modelo | Inicio del uso solicitado, conservado como texto; no ventana de entrega. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.ends_on` | texto / null | No | `null` — valor por defecto del modelo | Fin del uso solicitado, conservado como texto; no vencimiento del traslado. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.approved_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de aprobación informado por Prisma; no salida, llegada o recepción. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.requested_by_id` | texto / null | No | `null` — valor por defecto del modelo | UUID del solicitante Prisma; no se transforma en ID de otro proveedor. | Proyección ECON de lectura y registro; procedencia en evidence |

### MovementNode

Procedencia: Proyección de MovementRecord y sus observaciones en el grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "movement" | No | `"movement"` — valor por defecto del modelo | Constante movement; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación del movimiento (referencia); nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef del registro local (ledger_recorded) y de las observaciones vinculadas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.movement_id` | texto | Sí | `"<movement_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID local del movimiento al que pertenece el evento. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.state` | enum(draft, blocked, queued, sending, sent, unknown, failed) | Sí | `"draft"` — ejemplo técnico de catálogo, no observación | Estado local del envío; separado del estado remoto de tarea y de recepción. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.movement_reference` | texto | Sí | `"<movement_reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de correlación creada en ECON; se envía como remote_id, sin unicidad remota garantizada. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.request_source_id` | texto | Sí | `"<request_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de solicitud Prisma, sin prefijo local. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.machinery_source_id` | texto | Sí | `"<machinery_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de maquinaria Prisma, sin prefijo local. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.project_source_id` | texto | Sí | `"<project_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original del proyecto Prisma. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.job_id` | texto / null | No | `null` — valor por defecto del modelo | ID de tarea confirmado por Startrack; ausente en muestras proporcionadas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.task_ref` | texto / null | No | `null` — valor por defecto del modelo | startrack:job:{job_id} cuando la tarea está confirmada; null en borradores y envíos sin ID. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.status` | texto / null | No | `null` — valor por defecto del modelo | ID/texto de estado remoto de la tarea Startrack; no estado de envío local. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.workflow_role` | texto / null | No | `null` — valor por defecto del modelo | Rol remoto del catálogo de estado de tarea; no es rol de usuario. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.reason_code` | texto / null | No | `null` — valor por defecto del modelo | Código local de motivo/bloqueo/fallo; detalle en eventos y preparación. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.scheduled_date` | texto / null | No | `null` — valor por defecto del modelo | Fecha explícita de programación del movimiento; no copia automática del inicio de uso. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.scheduled_time` | texto / null | No | `null` — valor por defecto del modelo | Hora explícita HH:MM:SS sin zona en payload; confirmar zona de la cuenta. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.poi_id` | texto / null | No | `null` — valor por defecto del modelo | ID Startrack de destino confirmado explícitamente; no inferido del nombre de proyecto. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.tracked_vehicle_id` | texto / null | No | `null` — valor por defecto del modelo | ID de activo rastreado elegido por separado; puede ser el transportador. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.tracked_vehicle_kind` | enum(machine_device, transporter) / null | No | `null` — valor por defecto del modelo | Declarado por el operador (machine_device o transporter); no verificado: el catálogo de vehículos de Startrack no tiene tipo. Requiere tracked_vehicle_id. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.tracked_vehicle_kind_verification` | "declared" / null | No | `null` — valor por defecto del modelo | Siempre declared cuando hay tipo: lo declaró el operador y ninguna fuente lo verifica. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.arrival_event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante de la última visita a la geocerca de destino, según Startrack; null sin visita. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.arrival_observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante en que ECON leyó la visita de llegada; nunca sustituye a arrival_event_time. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.receipt` | ReceiptSummary / null | No | `null` — valor por defecto del modelo | Recepción declarada del movimiento; null mientras nadie la declare. Ni GPS ni tarea completada la generan. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.relation_scope` | enum(current, historical, unverifiable, not_applicable) | Sí | `"current"` — ejemplo técnico de catálogo, no observación | current si solicitud y unidad almacenadas coinciden con la lectura vigente; historical si el origen cambió; unverifiable si la contraparte no está en la lectura; not_applicable si no procede. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.created_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Creación en Prisma para equipo/solicitud; creación local para movimiento. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.updated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Actualización en Prisma para equipo/solicitud; última actualización local del movimiento. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.sent_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante local en que se confirmó asociación de tarea; no ejecución ni llegada. | Proyección ECON de lectura y registro; procedencia en evidence |

### IncidentNode

Procedencia: Falla activa informada por Prisma en el equipo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | "incident" | No | `"incident"` — valor por defecto del modelo | Constante incident; discriminador de GraphNode. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la falla; nunca clave de unión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | No | `[]` — ejemplo técnico de lista; no conteo operativo | EvidenceRef de la lectura de Prisma del equipo afectado. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que esta lectura no cubre para el objeto; cada uno queda «no verificable», nunca ausente ni cero. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.failure_id` | texto | Sí | `"<failure_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de la falla activa informada por Prisma; identidad de la incidencia, no de la máquina. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.equipment_id` | texto | Sí | `"<equipment_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia a maquinaria en el contrato normalizado de lectura. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.status` | texto / null | No | `null` — valor por defecto del modelo | Estado de la falla en Prisma (active_failure_status), separado del estado administrativo. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.is_stopped` | booleano / null | No | `null` — valor por defecto del modelo | Paro explícito informado por Prisma: true/false; null significa desconocido, no «sin paro». | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphEdge

Procedencia: ECON: services/graph.py, relación con evidencia y alcance. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.kind` | enum(assigned_to, requested_for, assigned_unit, transfer_of, for_request, destination, observed_at_place, received_by, affects) | Sí | `"assigned_to"` — ejemplo técnico de catálogo, no observación | Tipo de relación: assigned_to, requested_for, assigned_unit, transfer_of, for_request, destination, observed_at_place, received_by o affects. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.source` | texto | Sí | `"<source-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID del nodo origen de la arista. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.target` | texto | Sí | `"<target-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID del nodo destino de la arista. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.verification` | enum(source_observed, ledger_recorded, declared, referenced_only) | Sí | `"source_observed"` — ejemplo técnico de catálogo, no observación | Cómo se sostiene el hecho: source_observed (leído del proveedor), ledger_recorded (registro local), declared (persona) o referenced_only (solo ID, no leído). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.scope` | enum(current, historical, unverifiable, not_applicable) | Sí | `"current"` — ejemplo técnico de catálogo, no observación | Alcance de la relación: current, historical, unverifiable o not_applicable; heredado del movimiento para sus aristas. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<EvidenceRef> | Sí | `["<id-tecnico-por-confirmar>"]` — ejemplo técnico de estructura, no ID operativo | Al menos una EvidenceRef con procedencia intacta; una arista sin evidencia no existe. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.attributes` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Atributos escalares de la arista (por ejemplo visit_id, tracked_asset_kind, receiver); nunca geometría ni distancias. | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphConflict

Procedencia: ECON: services/graph.py, hechos incompatibles. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.code` | enum(assignment_project_mismatch, movement_source_changed, task_destination_differs, overlapping_approved_requests, status_role_unknown) | Sí | `"assignment_project_mismatch"` — ejemplo técnico de catálogo, no observación | Código cerrado del conflicto: assignment_project_mismatch, movement_source_changed, task_destination_differs, overlapping_approved_requests o status_role_unknown. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.node_ids` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | IDs de los nodos involucrados en el conflicto o la tensión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.edge_ids` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | IDs de las aristas involucradas, si las hay. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible del conflicto con los hechos citados. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que sostienen la regla de alerta, como lista de textos. | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphTension

Procedencia: ECON: services/graph.py, hechos que piden revisión. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.code` | enum(administrative_status_vs_task, obsolete_with_approved_request, stopped_with_pending_task, arrival_without_receipt, receipt_without_arrival) | Sí | `"administrative_status_vs_task"` — ejemplo técnico de catálogo, no observación | Código cerrado de la tensión: administrative_status_vs_task, obsolete_with_approved_request, stopped_with_pending_task, arrival_without_receipt o receipt_without_arrival. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.node_ids` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | IDs de los nodos involucrados en el conflicto o la tensión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible de por qué los hechos piden revisión. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.evidence` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que sostienen la regla de alerta, como lista de textos. | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphGap

Procedencia: ECON: services/graph.py, faltante siempre «no verificable». [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | texto | Sí | `"<id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.code` | texto | Sí | `"<code-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Código del faltante (machine_location, project_not_read, record_not_in_reading, startrack_not_queried…). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.node_id` | texto / null | No | `null` — valor por defecto del modelo | Nodo al que pertenece el faltante; null si afecta a toda la lectura. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.edge_kind` | enum(assigned_to, requested_for, assigned_unit, transfer_of, for_request, destination, observed_at_place, received_by, affects) / null | No | `null` — valor por defecto del modelo | Tipo de arista que no pudo establecerse por el faltante; null si no aplica. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.fact` | texto | Sí | `"<fact-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Hecho concreto que falta o se cita, en texto; no un valor inferido. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible del faltante y de por qué no se infiere. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.status` | "no verificable" | No | `"no verificable"` — valor por defecto del modelo | Siempre «no verificable»: un faltante nunca se publica como ausencia ni como correcto. | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphCoverage

Procedencia: ECON: cobertura compuesta de la proyección de grafo. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.scope` | HubScope | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Población, filtros y límites de la respuesta; ver HubScope. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.sources` | lista<SourceStatus> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Estados técnicos y cobertura de las fuentes. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.operation_evidence` | OperationEvidenceStatus | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Disponibilidad y cobertura de movimientos usados por la proyección; ver OperationEvidenceStatus. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.ledger` | OperationsCoverage / null | No | `null` — valor por defecto del modelo | Cobertura de la página del registro local usada por la proyección; null si no se pudo consultar. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.ledger_available` | booleano | Sí | `false` — ejemplo técnico de tipo, no observación | El registro local pudo consultarse; false no significa cero movimientos. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.ledger_message` | texto | Sí | `"<ledger_message-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación de disponibilidad y cobertura del registro local. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.nodes_by_kind` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Conteo de nodos por tipo en esta lectura; describe la proyección, no la flota. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.edges_by_kind` | objeto JSON | Sí | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Conteo de aristas por tipo en esta lectura. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.referenced_only` | entero | Sí | `0` — ejemplo técnico de tipo, no medición | Nodos presentes solo por referencia de ID (proyectos, unidades fuera de la página), no leídos. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.complete` | booleano | Sí | `false` — ejemplo técnico de tipo, no observación | true solo con Prisma y Startrack conectados en live y registro completo; false en fixture y mientras Startrack no se consulte. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.description` | texto | Sí | `"<description-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación de la población, las fuentes y los límites de la proyección. | Proyección ECON de lectura y registro; procedencia en evidence |

### GraphProjection

Procedencia: ECON: respuesta de GET /api/v1/graph. [Código](../apps/api/app/models/graph.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.schema_version` | "1.0" | No | `"1.0"` — valor por defecto del modelo | Versión del contrato de lectura de ECON. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.data_as_of` | date-time / null | No | `null` — valor por defecto del modelo | Corte de lectura, cuando existe; null en muestras sin instante común. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.nodes` | lista<MachineNode &#124; ProjectNode &#124; PlaceNode &#124; RequestNode &#124; MovementNode &#124; IncidentNode> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Nodos tipados (machine, project, place, request, movement, incident), cada uno con evidencia y faltantes. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.edges` | lista<GraphEdge> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Relaciones con evidencia y alcance; la presencia cuelga del movimiento, nunca de la máquina. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.conflicts` | lista<GraphConflict> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos documentados incompatibles entre sí (por ejemplo, el origen cambió tras el envío). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.tensions` | lista<GraphTension> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que coexisten y piden revisión sin ser contradicción (por ejemplo, llegada sin recepción). | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.gaps` | lista<GraphGap> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que la lectura no cubre; siempre «no verificable», nunca ausencia comprobada. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.alerts` | lista<AlertRecord> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Señales derivadas de hechos disponibles; ver AlertRecord. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.coverage` | GraphCoverage | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Cobertura de la página local; null cuando no se pudo consultar el registro. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.notes` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Advertencias y límites de interpretación de la proyección. | Proyección ECON de lectura y registro; procedencia en evidence |
| `$.remote_writes` | false | No | `false` — valor por defecto del modelo | Siempre false: preparar el borrador no escribe en los proveedores. | Proyección ECON de lectura y registro; procedencia en evidence |

### IndicatorSheet

Procedencia: ECON: services/indicators.py, ficha documentada en indicadores-calculables.md. [Código](../apps/api/app/models/indicators.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.id` | enum(approval_time, open_request_age, approved_with_unit_without_sent_task, occupied_without_project, assignment_ended, completed_task_without_receipt, active_failure_registered, evidence_age) | Sí | `"approval_time"` — ejemplo técnico de catálogo, no observación | Identificador cerrado del indicador (approval_time, open_request_age, …). | Cálculo ECON por fila sobre instantes de origen |
| `$.name` | texto | Sí | `"<name-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre del indicador en español. | Cálculo ECON por fila sobre instantes de origen |
| `$.question` | texto | Sí | `"<question-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Pregunta que responde cada fila del indicador. | Cálculo ECON por fila sobre instantes de origen |
| `$.decision` | texto | Sí | `"<decision-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Decisión que habilita el indicador y quién la toma. | Cálculo ECON por fila sobre instantes de origen |
| `$.owner` | texto | Sí | `"<owner-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Área responsable de actuar sobre el resultado; no asignación autenticada. | Cálculo ECON por fila sobre instantes de origen |
| `$.grain` | enum(request, equipment, movement) | Sí | `"request"` — ejemplo técnico de catálogo, no observación | Grano de la fila: solicitud, unidad o movimiento. | Cálculo ECON por fila sobre instantes de origen |
| `$.population` | texto | Sí | `"<population-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Registros de la lectura acotada que forman la población; no la flota. | Cálculo ECON por fila sobre instantes de origen |
| `$.numerator` | texto | Sí | `"<numerator-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Fórmula por fila con los campos exactos de origen. | Cálculo ECON por fila sobre instantes de origen |
| `$.denominator` | texto | Sí | `"<denominator-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Denominador; «no aplica» cuando el indicador se publica por fila. | Cálculo ECON por fila sobre instantes de origen |
| `$.exclusions` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Registros excluidos por regla explícita de la ficha. | Cálculo ECON por fila sobre instantes de origen |
| `$.unknowns` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Lo que la lectura no permite saber; se publica junto al resultado. | Cálculo ECON por fila sobre instantes de origen |
| `$.dates` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Nombres exactos de los campos de fecha usados por la ficha. | Cálculo ECON por fila sobre instantes de origen |
| `$.unit` | texto | Sí | `"<unit-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Unidad del valor por fila (segundos, horas, días o hecho); sin promedios. | Cálculo ECON por fila sobre instantes de origen |
| `$.status_rule` | texto | Sí | `"<status_rule-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Cuándo la fila y el indicador son evaluable, partial o not_evaluable. | Cálculo ECON por fila sobre instantes de origen |
| `$.measurable_in` | lista<enum(fixture, live)> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Modos en los que hoy existe alguna fila evaluable (fixture y/o live). | Cálculo ECON por fila sobre instantes de origen |

### IndicatorRow

Procedencia: ECON: fila calculada con las fechas de origen del registro. [Código](../apps/api/app/models/indicators.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.subject_id` | texto | Sí | `"<subject_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID del hub de la fila: nexus:request:…, nexus:equipment:… o econ:movement:…. | Cálculo ECON por fila sobre instantes de origen |
| `$.source_id` | texto / null | No | `null` — valor por defecto del modelo | ID original del proveedor; conservar separado del ID local y de etiquetas. | Cálculo ECON por fila sobre instantes de origen |
| `$.label` | texto / null | No | `null` — valor por defecto del modelo | Etiqueta legible de la fila (activo, código); nunca clave de unión. | Cálculo ECON por fila sobre instantes de origen |
| `$.values` | objeto JSON | No | `{}` — ejemplo técnico de objeto; ver significado y modelo anidado | Valores calculados de la fila a partir de sus propias fechas; null conserva lo desconocido. | Cálculo ECON por fila sobre instantes de origen |
| `$.evidence` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos de origen citados por la fila, como lista de textos. | Cálculo ECON por fila sobre instantes de origen |
| `$.status` | enum(evaluable, partial, not_evaluable) | Sí | `"evaluable"` — ejemplo técnico de catálogo, no observación | evaluable, partial o not_evaluable para esta fila. | Cálculo ECON por fila sobre instantes de origen |
| `$.reason` | texto / null | No | `null` — valor por defecto del modelo | Por qué la fila o el indicador no es evaluable o es parcial, con el campo que falta. | Cálculo ECON por fila sobre instantes de origen |

### IndicatorResult

Procedencia: ECON: resultado por ficha, sin promedios. [Código](../apps/api/app/models/indicators.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.sheet` | IndicatorSheet | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Ficha completa del indicador publicada con el resultado. | Cálculo ECON por fila sobre instantes de origen |
| `$.status` | enum(evaluable, partial, not_evaluable) | Sí | `"evaluable"` — ejemplo técnico de catálogo, no observación | Estado del indicador completo; not_evaluable con población vacía («sin casos evaluables»). | Cálculo ECON por fila sobre instantes de origen |
| `$.reason` | texto / null | No | `null` — valor por defecto del modelo | Por qué la fila o el indicador no es evaluable o es parcial, con el campo que falta. | Cálculo ECON por fila sobre instantes de origen |
| `$.rows` | lista<IndicatorRow> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Filas evaluadas de esta lectura; una lista vacía describe la lectura, no la operación. | Cálculo ECON por fila sobre instantes de origen |
| `$.evaluable_count` | entero | No | `0` — valor por defecto del modelo | Filas evaluable; junto con partial y not_evaluable suma el total de filas. | Cálculo ECON por fila sobre instantes de origen |
| `$.partial_count` | entero | No | `0` — valor por defecto del modelo | Filas partial (registro local incompleto u otra cobertura parcial). | Cálculo ECON por fila sobre instantes de origen |
| `$.not_evaluable_count` | entero | No | `0` — valor por defecto del modelo | Filas not_evaluable; la ausencia de dato no se convierte en cero. | Cálculo ECON por fila sobre instantes de origen |
| `$.coverage_note` | texto | Sí | `"<coverage_note-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Población, alcance de la lectura (por ejemplo 5 de 15 unidades) y límites. | Cálculo ECON por fila sobre instantes de origen |

### IndicatorsReport

Procedencia: ECON: respuesta de GET /api/v1/indicators. [Código](../apps/api/app/models/indicators.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.schema_version` | "1.0" | No | `"1.0"` — valor por defecto del modelo | Versión del contrato de lectura de ECON. | Cálculo ECON por fila sobre instantes de origen |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Cálculo ECON por fila sobre instantes de origen |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Cálculo ECON por fila sobre instantes de origen |
| `$.data_as_of` | date-time / null | No | `null` — valor por defecto del modelo | Corte de lectura, cuando existe; null en muestras sin instante común. | Cálculo ECON por fila sobre instantes de origen |
| `$.scope` | HubScope | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Población, filtros y límites de la respuesta; ver HubScope. | Cálculo ECON por fila sobre instantes de origen |
| `$.registry` | OperationEvidenceStatus | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Estado del registro local de movimientos visto por el hub; ver OperationEvidenceStatus. | Cálculo ECON por fila sobre instantes de origen |
| `$.ledger_coverage` | OperationsCoverage / null | No | `null` — valor por defecto del modelo | Cobertura de la página del registro local usada; null si no se consultó. | Cálculo ECON por fila sobre instantes de origen |
| `$.ledger_available` | booleano | No | `false` — valor por defecto del modelo | El registro local pudo consultarse; false no significa cero movimientos. | Cálculo ECON por fila sobre instantes de origen |
| `$.last_registry_read_at` | date-time / null | No | `null` — valor por defecto del modelo | Última lectura del registro (max(recorded_at, last_confirmed_at) del corte); único «ahora» permitido, solo para evidence_age. | Cálculo ECON por fila sobre instantes de origen |
| `$.indicators` | lista<IndicatorResult> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Resultados por ficha; sin promedios, percentiles ni porcentajes. | Cálculo ECON por fila sobre instantes de origen |
| `$.notes` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Advertencias de cobertura y de modo (por ejemplo, live deshabilitado sin fallback). | Cálculo ECON por fila sobre instantes de origen |
| `$.remote_writes` | false | No | `false` — valor por defecto del modelo | Siempre false: preparar el borrador no escribe en los proveedores. | Cálculo ECON por fila sobre instantes de origen |

### SuggestionEvidence

Procedencia: ECON: services/suggestions.py, hecho administrativo citado. [Código](../apps/api/app/models/suggestions.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.fact` | texto | Sí | `"<fact-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Hecho concreto que falta o se cita, en texto; no un valor inferido. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.source` | enum(nexus, startrack, econ) | Sí | `"nexus"` — ejemplo técnico de catálogo, no observación | Sistema que registró el hecho: nexus, startrack o econ. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.field` | texto | Sí | `"<field-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Campo(s) exacto(s) de origen que sostienen el hecho citado. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.nature` | "administrative" | No | `"administrative"` — valor por defecto del modelo | Siempre administrative: solo hechos registrados en la fuente, nunca presencia GPS. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.event_time` | date-time / null | No | `null` — valor por defecto del modelo | Instante del hecho informado por el origen, si puede interpretarse con zona. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.observed_at` | date-time / null | No | `null` — valor por defecto del modelo | Instante de observación/lectura conocido; no sustituye la fecha del evento. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.observed_on` | date / null | No | `null` — valor por defecto del modelo | Día documentado sin inventar una hora de observación. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.reference` | texto / null | No | `null` — valor por defecto del modelo | Referencia local (movimiento, evento o marca de origen) del hecho citado. | Sugerencia ECON de solo lectura; Prisma asigna |

### CandidateUnit

Procedencia: ECON: unidad candidata evaluada por reglas R0–R8. [Código](../apps/api/app/models/suggestions.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.equipment_id` | texto | Sí | `"<equipment_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia a maquinaria en el contrato normalizado de lectura. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.equipment_source_id` | texto / null | Sí | `null` — sin muestra; null permitido | UUID original de la unidad en Prisma, sin prefijo. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.label` | texto | Sí | `"<label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Etiqueta de presentación de la unidad candidata; nunca clave de unión. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.requested_class` | texto / null | Sí | `null` — sin muestra; null permitido | Clase solicitada (machinery_type) tal como se comparó, sin normalizar. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.equipment_class` | texto / null | Sí | `null` — sin muestra; null permitido | Clase de maquinaria del origen, distinta del tipo de tarea. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.class_match` | booleano | Sí | `false` — ejemplo técnico de tipo, no observación | true solo con igualdad exacta de clases tras quitar espacios; similar_classes no lo altera. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.machinery_status` | texto | Sí | `"<machinery_status-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Estado administrativo de maquinaria Prisma, conservado literalmente. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.project_id` | texto / null | Sí | `null` — sin muestra; null permitido | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.project_name` | texto / null | No | `null` — valor por defecto del modelo | Nombre de proyecto del origen; solo presentación. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.assignment_starts_on` | texto / null | Sí | `null` — sin muestra; null permitido | Prisma fecha_inicio_uso: inicio de la asignación del equipo al proyecto; no es programación del traslado. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.assignment_ends_on` | texto / null | Sí | `null` — sin muestra; null permitido | Prisma fecha_fin_uso: fin de la asignación del equipo al proyecto. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.maintenance_failure_id` | texto / null | Sí | `null` — sin muestra; null permitido | Referencia de falla activa, si está disponible. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.maintenance_status` | texto / null | Sí | `null` — sin muestra; null permitido | Estado de falla/mantenimiento, separado del estado administrativo. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.maintenance_is_stopped` | booleano / null | Sí | `null` — sin muestra; null permitido | Paro explícito: true/false; null significa desconocido. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.eligibility` | enum(eligible, review_required, excluded) | Sí | `"eligible"` — ejemplo técnico de catálogo, no observación | eligible, review_required o excluded según las reglas R0–R8; no es un puntaje. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.reasons` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Motivos por regla que sostienen el nivel de la candidata. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.review_reasons` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que exigen revisión humana antes de asignar. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.exclusion_reasons` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Reglas que excluyen a la candidata (paro, solapamiento, clase distinta…). | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.missing` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Hechos que la lectura acotada no cubre (ubicación física, operadores, tarifa); cada uno «no verificable». | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.overlapping_requests` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | IDs de solicitudes aprobadas cuyo período de uso se cruza con el solicitado. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.overlapping_movements` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | IDs de movimientos abiertos de la unidad (draft, queued, sending, sent sin recepción o unknown). | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.same_project_evidence` | SuggestionEvidence / null | No | `null` — valor por defecto del modelo | Asignación administrativa vigente al mismo project_id que termina antes del período; continuidad administrativa, no ubicación observada. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.operators_known` | booleano | No | `false` — valor por defecto del modelo | false significa lectura acotada sin operadores, no «sin operadores». | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.provenance` | Provenance | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Procedencia del objeto o evento; ver Provenance. | Sugerencia ECON de solo lectura; Prisma asigna |

### AssignmentSuggestion

Procedencia: ECON: respuesta de GET /api/v1/requests/{id}/suggestions. [Código](../apps/api/app/models/suggestions.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.schema_version` | "1.0" | No | `"1.0"` — valor por defecto del modelo | Versión del contrato de lectura de ECON. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.generated_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante de ensamblaje de la respuesta; no antigüedad del dato de origen. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.data_as_of` | date-time / null | No | `null` — valor por defecto del modelo | Corte de lectura, cuando existe; null en muestras sin instante común. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.request_id` | texto | Sí | `"<request_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID de la solicitud en el modelo de lectura (nexus:request:…). | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.request_source_id` | texto / null | Sí | `null` — sin muestra; null permitido | UUID original de solicitud Prisma, sin prefijo local. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.request_status` | texto | Sí | `"<request_status-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Estado original de la solicitud en Prisma; solo PENDIENTE sin unidad es aplicable. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.project_id` | texto / null | Sí | `null` — sin muestra; null permitido | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.project_label` | texto | Sí | `"<project_label-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre de proyecto para presentación; la identidad sigue en project_id. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.requested_class` | texto / null | Sí | `null` — sin muestra; null permitido | Clase solicitada (machinery_type) tal como se comparó, sin normalizar. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.requested_starts_on` | texto / null | Sí | `null` — sin muestra; null permitido | Inicio del período de uso solicitado, como texto; no fecha de traslado. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.requested_ends_on` | texto / null | Sí | `null` — sin muestra; null permitido | Fin del período de uso solicitado, como texto; no vencimiento. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.applicable` | booleano | Sí | `false` — ejemplo técnico de tipo, no observación | false cuando la solicitud no está pendiente o ya tiene unidad; entonces no hay candidatas. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.message` | texto | Sí | `"<message-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Explicación legible de la aplicabilidad y de la cobertura de la sugerencia. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.rules` | lista<texto> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Reglas R0–R8 aplicadas, en texto; sin puntajes, distancias ni ETA. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.scope` | HubScope | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Población, filtros y límites de la respuesta; ver HubScope. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.registry` | OperationEvidenceStatus | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Estado del registro local de movimientos visto por el hub; ver OperationEvidenceStatus. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.candidates` | lista<CandidateUnit> | Sí | `[]` — ejemplo técnico de lista; no conteo operativo | Unidades candidatas ordenadas por nivel, evidencia de mismo proyecto e ID; cero elegibles no afirma que no exista una unidad. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.similar_classes` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Clases de la lectura con grafía cercana a la solicitada; informativo, no une registros. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.authority_note` | texto | No | `"Recomendar no es asignar: la asignación se registra en Prisma (PATCH /api/maquinaria/requests/{id}/approve). ECON no asigna, no consulta proveedores para esta sugerencia y no estima distancias, tiempos de ruta ni ETA."` — valor por defecto del modelo | Recomendar no es asignar: la asignación se registra en Prisma. | Sugerencia ECON de solo lectura; Prisma asigna |
| `$.remote_writes` | false | No | `false` — valor por defecto del modelo | Siempre false: preparar el borrador no escribe en los proveedores. | Sugerencia ECON de solo lectura; Prisma asigna |

### TransferMapping

Procedencia: Correspondencias y programación proporcionadas explícitamente. [Código](../apps/api/app/services/transfers.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.request_source_id` | texto | Sí | `"<request_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de solicitud Prisma, sin prefijo local. | Entrada explícita; metadatos de registro en ECON |
| `$.machinery_source_id` | texto | Sí | `"<machinery_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original de maquinaria Prisma, sin prefijo local. | Entrada explícita; metadatos de registro en ECON |
| `$.project_source_id` | texto | Sí | `"<project_source_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | UUID original del proyecto Prisma. | Entrada explícita; metadatos de registro en ECON |
| `$.poi_id` | texto | Sí | `"<poi_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID Startrack de destino confirmado explícitamente; no inferido del nombre de proyecto. | Entrada explícita; metadatos de registro en ECON |
| `$.assigned_user_ids` | lista<texto> | Sí | `["<id-tecnico-por-confirmar>"]` — ejemplo técnico de estructura, no ID operativo | IDs de usuarios Startrack elegidos explícitamente, sin duplicados. | Entrada explícita; metadatos de registro en ECON |
| `$.movement_reference` | texto | Sí | `"<movement_reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de correlación creada en ECON; se envía como remote_id, sin unicidad remota garantizada. | Entrada explícita; metadatos de registro en ECON |
| `$.scheduled_date` | date | Sí | `"2000-01-01"` — fecha técnica ilustrativa, no programación | Fecha explícita de programación del movimiento; no copia automática del inicio de uso. | Entrada explícita; metadatos de registro en ECON |
| `$.scheduled_time` | texto / null | No | `null` — valor por defecto del modelo | Hora explícita HH:MM:SS sin zona en payload; confirmar zona de la cuenta. | Entrada explícita; metadatos de registro en ECON |
| `$.job_type_id` | texto / null | No | `null` — valor por defecto del modelo | ID opcional del tipo de tarea Startrack. | Entrada explícita; metadatos de registro en ECON |

### TransferPreparation

Procedencia: ECON: services/transfers.py prepare_transfer. [Código](../apps/api/app/services/transfers.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.request_id` | texto | Sí | `"<request_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia a la solicitud en el contrato de lectura, normalmente con prefijo nexus:request:. | Derivación o metadato ECON |
| `$.machinery_id` | texto / null | Sí | `null` — sin muestra; null permitido | ID normalizado de maquinaria asignada; conserva prefijo del contrato del hub. | Derivación o metadato ECON |
| `$.project_id` | texto / null | Sí | `null` — sin muestra; null permitido | UUID de proyecto Prisma asociado al objeto; no equivale a poi_id. | Derivación o metadato ECON |
| `$.request_provenance` | Provenance | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Procedencia de la solicitud revisada para preparar el movimiento. | Derivación o metadato ECON |
| `$.equipment_provenance` | Provenance / null | Sí | `null` — sin muestra; null permitido | Procedencia de la maquinaria revisada, si existe. | Derivación o metadato ECON |
| `$.status` | enum(missing_information, review_required, draft_prepared) | Sí | `"missing_information"` — ejemplo técnico de catálogo, no observación | Resultado local: faltan datos, requiere revisión o borrador preparado. | Derivación o metadato ECON |
| `$.missing_fields` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Datos necesarios que faltan para preparar el borrador. | Derivación o metadato ECON |
| `$.blocking_reasons` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Razones que impiden preparar el borrador. | Derivación o metadato ECON |
| `$.notes` | lista<texto> | No | `[]` — ejemplo técnico de lista; no conteo operativo | Advertencias y límites de interpretación de la preparación. | Derivación o metadato ECON |
| `$.draft` | StartrackTaskDraft / null | No | `null` — valor por defecto del modelo | Propuesta local de tarea; ver StartrackTaskDraft. | Derivación o metadato ECON |
| `$.remote_writes` | false | No | `false` — valor por defecto del modelo | Siempre false: preparar el borrador no escribe en los proveedores. | Derivación o metadato ECON |

### StartrackTaskDraft

Procedencia: ECON prepara campos del contrato Job; no acredita aceptación. [Código](../apps/api/app/integrations/startrack.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.objective` | texto | Sí | `"<objective-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Título generado con etiquetas de unidad/proyecto, hasta 255 caracteres; no clave de unión. | Borrador ECON para contrato Job |
| `$.start_date` | date | Sí | `"2000-01-01"` — fecha técnica ilustrativa, no programación | Fecha explícita del traslado en Job; diferente del período de uso Prisma. | Borrador ECON para contrato Job |
| `$.remote_id` | texto | Sí | `"<remote_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia local de movimiento enviada para correlación; no idempotencia garantizada. | Borrador ECON para contrato Job |
| `$.poi_id` | texto | Sí | `"<poi_id-tecnico>"` — ejemplo técnico de texto; no hecho operativo | ID Startrack de destino confirmado explícitamente; no inferido del nombre de proyecto. | Borrador ECON para contrato Job |
| `$.assigned_user_ids` | lista<texto> | Sí | `["<id-tecnico-por-confirmar>"]` — ejemplo técnico de estructura, no ID operativo | IDs de usuarios Startrack elegidos explícitamente, sin duplicados. | Borrador ECON para contrato Job |
| `$.description` | texto / null | No | `null` — valor por defecto del modelo | Texto generado con UUID de solicitud, maquinaria, proyecto y referencia; no copia comentarios. | Borrador ECON para contrato Job |
| `$.start_time` | texto / null | No | `null` — valor por defecto del modelo | Hora programada HH:MM:SS del Job; el campo no contiene zona. | Borrador ECON para contrato Job |
| `$.job_type_id` | texto / null | No | `null` — valor por defecto del modelo | ID opcional del tipo de tarea Startrack. | Borrador ECON para contrato Job |
| `$.form_ids` | lista<texto> / null | No | `null` — valor por defecto del modelo | IDs de formularios asociados al borrador; soporte SDK, no propagados por preparación actual. | Borrador ECON para contrato Job |
| `$.required_form_ids` | lista<texto> / null | No | `null` — valor por defecto del modelo | Subconjunto de formularios obligatorios; no define por sí solo recepción empresarial. | Borrador ECON para contrato Job |
| `$.notify_contact` | false | No | `false` — valor por defecto del modelo | Siempre false en este borrador; no solicita avisos al contacto. | Borrador ECON para contrato Job |

### PlanInput

Procedencia: Entrada de gestión local → TransferMapping. [Código](../apps/api/app/api/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Entrada explícita; metadatos de registro en ECON |
| `$.mapping` | TransferMapping | Sí | `{}` — estructura técnica; campos en la tabla del modelo referenciado | Correspondencias explícitas y programación; estructura de TransferMapping. | Entrada explícita; metadatos de registro en ECON |
| `$.tracked_vehicle_id` | texto / null | No | `null` — valor por defecto del modelo | ID de activo rastreado elegido por separado; puede ser el transportador. | Entrada explícita; metadatos de registro en ECON |
| `$.tracked_vehicle_kind` | enum(machine_device, transporter) / null | No | `null` — valor por defecto del modelo | Declarado por el operador (machine_device o transporter); no verificado: el catálogo de vehículos de Startrack no tiene tipo. Requiere tracked_vehicle_id. | Entrada explícita; metadatos de registro en ECON |

### SyncInput

Procedencia: Entrada de gestión local para seleccionar modo. [Código](../apps/api/app/api/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Entrada explícita; metadatos de registro en ECON |

### ReceiptInput

Procedencia: Entrada de declaración manual de recepción. [Código](../apps/api/app/api/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.mode` | enum(fixture, live) | Sí | `"fixture"` — ejemplo técnico de catálogo, no observación | Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox. | Entrada explícita; metadatos de registro en ECON |
| `$.receiver` | texto | Sí | `"<receiver-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Nombre declarado del receptor; no acredita identidad autenticada. | Entrada explícita; metadatos de registro en ECON |
| `$.received_at` | date-time | Sí | `"2000-01-01T00:00:00Z"` — instante técnico ilustrativo, no evento del sandbox | Instante declarado de recepción; el servicio exige zona horaria. | Entrada explícita; metadatos de registro en ECON |
| `$.reference` | texto | Sí | `"<reference-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Referencia de constancia declarada; no adjunto ni comprobación automática del documento. | Entrada explícita; metadatos de registro en ECON |
| `$.note` | texto / null | No | `null` — valor por defecto del modelo | Nota opcional de la declaración de recepción. | Entrada explícita; metadatos de registro en ECON |

### ResolveInput

Procedencia: Entrada de decisión del operador para cerrar un movimiento incierto. [Código](../apps/api/app/api/workflow.py).

| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |
| --- | --- | --- | --- | --- | --- |
| `$.reason_code` | texto | Sí | `"<reason_code-tecnico>"` — ejemplo técnico de texto; no hecho operativo | Código cerrado de SAFE_REASON_CODES con que el operador cierra un movimiento unknown como failed; sin texto libre. | Derivación o metadato ECON |

## Reglas que el tipo por sí solo no expresa

| Concepto | Regla implementada y límite | Evidencia de código |
| --- | --- | --- |
| Identidad de lectura | `nexus:request:` y `nexus:equipment:` distinguen objetos internos. El UUID original permanece en procedencia; código, activo y nombre no reemplazan la clave. | [fixtures.py](../apps/api/app/integrations/fixtures.py), [hub.py](../apps/api/app/services/hub.py) |
| Identidad de movimiento | `Movement.id` es local; `movement_reference` correlaciona el plan y Job.remote_id. La unicidad local es modo + entorno + referencia. No se atribuye unicidad de remote_id al proveedor. | [operations.py](../apps/api/app/models/operations.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Estado por objeto | `RequestRecord.status` describe solicitud; `machinery_status`, máquina; `maintenance_*`, falla/paro; `Movement.state`, envío; `status`/`workflow_role`, tarea. Presencia y recepción siguen independientes. | [transfers.py](../apps/api/app/services/transfers.py), [workflow.py](../apps/api/app/services/workflow.py) |
| Envío incierto | `unknown` necesita conciliación por lectura. `sent` acredita una tarea vinculada, no ejecución o recepción. La recepción no se deriva automáticamente de una tarea completada. | [workflow.py](../apps/api/app/services/workflow.py) |
| Fechas | `created_at`/`updated_at` del origen, `approved_at`, `event_time`, `observed_at`, `recorded_at` y `generated_at` son hechos distintos. Una fecha sin hora sigue siendo fecha; no adquiere una zona o plazo inventado. | [hub.py](../apps/api/app/services/hub.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Corte de muestra | `data_as_of=null` y `observed_at=null`; `observed_on=2026-09-12` conserva el día documental. El reloj actual no permite clasificar atraso con estas muestras. | [fixtures.py](../apps/api/app/integrations/fixtures.py) |
| Última sincronización | `last_sync_at` usa la última instantánea por modo. Se guarda antes del seguimiento Startrack; puede coexistir con errores parciales y no certifica la vigencia de cada tarea. | [workflow.py](../apps/api/app/services/workflow.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Huellas internas | `identity_hash` y `evidence_hash` no salen en las proyecciones públicas; `source_request_hash` y `source_equipment_hash` sí. Se calculan sobre JSON normalizado, no sobre cuerpos HTTP originales. | [ledger.py](../apps/api/app/services/ledger.py) |
| Eventos repetidos o tardíos | Repetir una observación equivalente conserva su primera lectura. Se registran hechos tardíos, pero no reemplazan una proyección de tarea más reciente. Los eventos públicos se ordenan por recorded_at e ID. | [ledger.py](../apps/api/app/services/ledger.py) |
| Recepción | El servicio exige receptor y referencia no vacíos e instante con zona. El nombre declarado no es identidad autenticada; la referencia no carga ni valida un archivo de constancia. | [api/workflow.py](../apps/api/app/api/workflow.py), [workflow.py](../apps/api/app/services/workflow.py) |
| Correspondencias | Los identificadores deben ser cadenas no vacías sin espacios; los asignados no se repiten. POI, usuarios y activo rastreado se eligen explícitamente; proyecto, solicitante y motorista no se unen por nombres. | [transfers.py](../apps/api/app/services/transfers.py), [startrack.py](../apps/api/app/integrations/startrack.py) |
| Borrador | Fecha explícita YYYY-MM-DD; hora HH:MM:SS; objetivo no vacío y máximo 255 caracteres. Formularios obligatorios son subconjunto de formularios asociados. `notify_contact=false`. Preparación no certifica aceptación remota. | [startrack.py](../apps/api/app/integrations/startrack.py) |
| JSON interno | `mapping`, `source_request`, `source_equipment`, `preparation`, `payload`, `receipt`, `content` y `data` se tipan como JSON en persistencia. Sus estructuras operativas se revisan contra los modelos y productores; el esquema SQL no valida por sí solo toda su semántica. | [ledger.py](../apps/api/app/services/ledger.py) |
| Actor y autoría | `actor_*` en eventos y `declared_by_*` en la recepción se copian de la sesión firmada (ADR 0005) o quedan nulos; un actor sin sesión no puede declarar usuario, correo ni rol. `receiver` sigue siendo el nombre escrito en la constancia. | [operations.py](../apps/api/app/models/operations.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Exclusividad en vuelo y unicidad de tarea | Índices parciales `uq_operation_movements_inflight_machine` (un movimiento `queued`/`sending`/`unknown` por máquina, modo y entorno) y `uq_operation_movements_job_identity` (un `job_id` por modo y entorno); el prechequeo en Python solo mejora el mensaje. `operation_events` es append-only por trigger en PostgreSQL. | [0004_movement_guards_actors_and_indexes.py](../apps/api/migrations/versions/0004_movement_guards_actors_and_indexes.py), [ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md) |
| Grafo | La presencia (`observed_at_place`) cuelga del movimiento y de su vehículo rastreado, nunca de la máquina; los proyectos son `referenced_only`; un faltante es un `GraphGap` «no verificable». `coverage.complete` es false en fixture y mientras Startrack no se consulte. | [graph.py](../apps/api/app/services/graph.py) |
| Indicadores y sugerencias | Cada fila es una diferencia entre dos instantes documentados o un hecho copiado; sin promedios ni porcentajes; la ausencia no es cero. Las sugerencias no usan GPS ni puntajes: recomendar no es asignar. | [indicators.py](../apps/api/app/services/indicators.py), [suggestions.py](../apps/api/app/services/suggestions.py) |

## Derivaciones de presentación vigentes

Estas estructuras pertenecen a Dash y no se agregan como campos de los proveedores.
Los ejemplos numéricos usan exclusivamente la muestra sin filtros; los textos de
decisión son resultados de reglas locales y no acontecimientos externos nuevos.

| Campo o término | Tipo | Ejemplo / evidencia | Significado y procedencia |
| --- | --- | --- | --- |
| `QueryContext.mode` | fixture/live | `fixture` · selección técnica | Origen escogido en URL; no habilita proveedores. |
| `QueryContext.query` | texto | `""` · selección técnica | Búsqueda; máximo 100 caracteres, bajo `q` en URL. |
| `QueryContext.filter` | catálogo de filtros | `all` · selección técnica | Filtro visible validado; no autorización. |
| `QueryContext.read_key` | lista de textos | `["fixture", ""]` · selección técnica | Clave derivada de modo y búsqueda para asociar la lectura. |
| `RequestCounts.total` | entero/null | `2` · derivado de muestra | Solicitudes de la población filtrada. |
| `RequestCounts.unassigned` | entero/null | `1` · derivado de muestra | Solicitudes sin ID de maquinaria; no unidades ausentes por paginación. |
| `RequestCounts.without_confirmed_task` | entero/null | `null` · registro de operaciones sin consultar | Solo calcula ausencia de vínculo si el registro local está disponible; requiere tarea enviada con ID confirmado. |
| `UsagePeriod.request` | RequestRecord | ver solicitud CF-03 | Registro original para preservar identidad. |
| `UsagePeriod.starts_on`, `ends_on` | fecha | `2026-09-11`, `2026-09-14` · muestra | Fechas de uso válidas; no fechas del traslado. |
| `UsagePeriod.calendar_days` | entero | `4` · derivado de muestra | Diferencia de días + 1; longitud del intervalo dibujado, no utilización. |
| `ExcludedPeriod.request`, `reason` | RequestRecord, texto | sin ejemplo excluido en la muestra | Registro y motivo de exclusión por fechas faltantes, inválidas o invertidas. |
| `UsageTimeline.periods`, `excluded` | tuplas de períodos/exclusiones | 2 períodos, 0 exclusiones · muestra | Resultado de validar y ordenar intervalos. |
| `request_states`: estado, cantidad | texto, entero | `APROBADA: 1`, `PENDIENTE: 1` · muestra | Conteo por categoría original en la misma población filtrada. |
| `DecisionItem.request`, `equipment` | RequestRecord, EquipmentRecord/null | solicitud aprobada y CF-03 · muestra | Registros enlazados por ID y procedencia compatible. |
| `DecisionItem.title` | texto | `Revisar la asignación` · regla sobre muestra | Acción de revisión porque CF-03 figura OBSOLETA; no declara avería. |
| `DecisionItem.evidence` | texto | estado administrativo OBSOLETA · regla sobre muestra | Explica los hechos disponibles y los faltantes del registro de movimientos. |
| `DecisionItem.action`, `href` | textos | `Revisar solicitud` y ruta derivada del ID | Etiqueta y navegación al registro; no ejecución automática de la acción. |

Fuentes: [context.py](../apps/api/app/dashboard/context.py),
[decision_analytics.py](../apps/api/app/dashboard/decision_analytics.py),
[decision_priorities.py](../apps/api/app/dashboard/decision_priorities.py).
Este apartado cubre las derivaciones de decisión y calendario vigentes; no enumera
cada propiedad visual de Plotly, AG Grid, HTML ni utilidades de presentación históricas.

## Uso con las matrices del reto

Este inventario reemplaza el vocabulario de la primera versión del modelo operativo.
La [matriz de equivalencias](equivalencias-prisma-startrack.md) explica el mapeo por
fuente, las cardinalidades y lo no soportado; la
[matriz de requisitos](matriz-requisitos-entregables.md) conserva brechas de la entrega.
Un inventario de tipos no acredita API autenticada, identidad entre plataformas,
recepción física, cobertura total de la flota ni cumplimiento ISO.
