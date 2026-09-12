# Modelo operativo inicial y matrices de trabajo

Contrato **`schema_version: "1.0"`**, revisión del **12 de septiembre de 2026**. Este documento describe el alcance implementado de `GET /api/v1/hub`, su vocabulario y matrices iniciales para RF-01, RF-02 y RF-03. Las responsabilidades y equivalencias de negocio son propuestas pendientes de validar con ECON; no son permisos de la aplicación.

La definición técnica está en [los modelos de FastAPI](../apps/api/app/models/hub.py), el [mapeo y las reglas](../apps/api/app/services/hub.py) y la [validación de las vistas Dash](../apps/api/app/dashboard/application.py). Las fuentes originales se conservan en [el diccionario](onedrive/06-diccionario-de-datos/README.md), [los casos](onedrive/04-casos-de-uso.md) y [la evidencia de integración](integraciones-reales.md).

## Identidad y relaciones

Una maquinaria puede tener **varias solicitudes y varios traslados**. `equipment[].transfers[]` es una lista; una solicitud puede ser referenciada por más de una tarea. El contrato no fuerza correspondencias uno a uno. Todavía no existen tablas persistentes de correspondencias, vigencias de asignación o validaciones humanas.

En lecturas Nexus, `equipment.id` usa `nexus:equipment:<id>` y `requests.id` usa `nexus:request:<id>`. `provenance.source_id` conserva el ID original. La relación interna solicitud–maquinaria se obtiene solamente de `maquinaria_id` exacto entre los registros consultados. Que coincida ese ID no demuestra asignación vigente, recepción o relación con Startrack.

En demostración, todos los identificadores del hub usan `fixture:`. Los recursos `RE-03`, `CF-03` y `EX-02` se utilizan en escenarios inventados locales. `relation_status=confirmed` significa que el ejemplo contiene una relación definida; no confirma esa relación en los sistemas externos. En modo real, los traslados y las ubicaciones de Startrack siguen ausentes.

`project_id` y los IDs de fallas se conservan como referencias del origen; todavía no representan entidades canónicas de una base unificada. Código, número de activo, empresa, nombre y motorista son datos descriptivos. No identifican por sí solos a una misma entidad entre proveedores.

## RF-01 — Inventario del contrato

`?` indica que el valor puede ser `null`; `[]`, una lista. Los ejemplos con prefijo `fixture:` son sintéticos. Los nombres en inglés son el contrato del hub, no una afirmación sobre nombres de campos externos. El inventario incluye renombres de datos originales y campos nuevos derivados o de procedencia.

### Respuesta, fuentes y alcance

| Campo | Tipo | Ejemplo | Significado |
| --- | --- | --- | --- |
| `schema_version` | literal de texto | `1.0` | Versión del contrato de lectura del hub |
| `mode` | `fixture / live` | `fixture` | Mecanismo seleccionado; no se infiere por disponibilidad |
| `generated_at` | fecha/hora con zona | `2026-09-12T15:02:00Z` | Instante de construcción de la respuesta |
| `data_as_of` | fecha/hora con zona? | `2026-09-12T15:00:00Z` | Corte del fixture o fin de la lectura Nexus; no es fecha de evento GPS |
| `sources` | `SourceStatus[]` | dos fuentes | Disponibilidad y mensajes por proveedor |
| `scope` | `HubScope` | alcance acotado | Cobertura y filtro de la respuesta |
| `summary` | `HubSummary` | conteos del conjunto | Derivaciones sobre los registros devueltos |
| `equipment` | `EquipmentRecord[]` | tres ejemplos | Maquinaria consultable |
| `requests` | `RequestRecord[]` | tres ejemplos | Solicitudes incluidas en la respuesta |
| `alerts` | `AlertRecord[]` | señales de revisión | Resultado de las reglas actuales |
| `sources[].id` | `nexus / startrack` | `nexus` | Identidad lógica del proveedor |
| `sources[].label` | texto | `Prisma / Nexus` | Nombre visible |
| `sources[].status` | catálogo | `partial` | Estado técnico, según la tabla siguiente |
| `sources[].environment` | `local / sandbox` | `local` | Entorno de procedencia |
| `sources[].observed_at` | fecha/hora con zona? | `2026-09-12T15:00:00Z` | Corte/lectura conocido; `null` si falta |
| `sources[].message` | texto | lectura deshabilitada | Explicación sanitizada, sin respuesta privada del proveedor |
| `scope.search` | texto | `RE-03` | Búsqueda aplicada localmente al conjunto consultado |
| `scope.bounded` | booleano | `true` | El conjunto está acotado |
| `scope.equipment_total` | entero? | `3` | Total informado antes del filtro; en vivo lo informa Nexus |
| `scope.requests_total` | entero? | `3` | Total de solicitudes antes del filtro |
| `scope.equipment_returned` | entero | `1` | Equipos presentes tras la búsqueda |
| `scope.requests_returned` | entero | `0` | Solicitudes presentes tras la búsqueda |
| `scope.complete` | booleano | `false` en vivo | Completitud del conjunto integrado; no se marca completa solo porque terminó Nexus |
| `scope.description` | texto | conteos de registros devueltos | Límite semántico de la respuesta |

| Estado de fuente | Interpretación |
| --- | --- |
| `fixture` | Ejemplos sintéticos locales |
| `connected` | Lectura Nexus correcta y paginación completa dentro de la consulta realizada |
| `partial` | Lectura útil pero incompleta por límite o cambios en la paginación |
| `disabled` | El servidor no habilita lecturas reales |
| `not_configured` | Falta la credencial/configuración necesaria |
| `error` | No se obtuvo una lectura válida; no hay sustitución por fixtures |

### Procedencia común

`provenance` acompaña maquinaria, solicitudes, traslados y ubicación.

| Campo | Tipo | Ejemplo | Significado |
| --- | --- | --- | --- |
| `provenance.source` | `nexus / startrack` | `nexus` | Fuente lógica que representa el dato |
| `provenance.source_id` | texto | `fixture:eq-re03` | Referencia original o ID del ejemplo |
| `provenance.environment` | `local / sandbox` | `local` | Origen del registro |
| `provenance.observed_at` | fecha/hora con zona | `2026-09-12T15:00:00Z` | Fecha de captura/corte del registro en el hub |
| `provenance.is_synthetic` | booleano | `true` | Tanto los fixtures como el sandbox del kit se identifican como sintéticos |

Una lectura `live` puede tener `is_synthetic=true`: conexión y naturaleza de datos son dimensiones distintas. Para ubicación, `location.observed_at` representa la observación física del ejemplo y puede ser anterior a `location.provenance.observed_at`. La captura reciente de una posición antigua no hace reciente la posición.

### Maquinaria, solicitudes, traslados y ubicación

| Campo | Tipo | Ejemplo | Significado |
| --- | --- | --- | --- |
| `equipment[].id` | texto | `fixture:eq-cf03` | Identidad del equipo dentro del contrato |
| `equipment[].code` | texto? | `CF-03` | Código descriptivo; puede faltar y no se usa como clave global |
| `equipment[].asset_number` | texto? | `ACT-EJ-001` | Número de activo del origen, separado del código; ejemplo sintético |
| `equipment[].name` | texto | `Cargador frontal 03` | Nombre del recurso |
| `equipment[].company` | texto? | `ECON · ejemplo` | Valor descriptivo del campo empresa |
| `equipment[].project_id` | texto? | `fixture:project-norte` | Referencia de proyecto informada |
| `equipment[].project_name` | texto? | `Proyecto Norte · ejemplo` | Nombre del proyecto |
| `equipment[].driver` | texto? | `Motorista de ejemplo A` | Etiqueta descriptiva; no es usuario de login ni ID conciliado |
| `equipment[].machinery_status` | texto | `OCUPADA` | Estado administrativo original |
| `equipment[].maintenance_failure_id` | texto? | `fixture:failure-01` | Referencia de falla activa |
| `equipment[].maintenance_status` | texto? | `ABIERTA` | Estado de esa falla, separado de asignación |
| `equipment[].maintenance_is_stopped` | booleano? | `true` | Decisión de paro; `null` significa desconocida |
| `equipment[].request_ids` | texto[] | `["fixture:request-01"]` | Solicitudes enlazadas dentro del conjunto |
| `equipment[].transfers` | `TransferRecord[]` | un ejemplo completado | Tareas relacionadas; admite varias |
| `equipment[].location` | `LocationObservation?` | `null` | Última observación conocida, si existe |
| `equipment[].relation_status` | `confirmed / candidate / unlinked` | `unlinked` | Calidad de relación con el traslado; actual a nivel de equipo |
| `equipment[].relation_note` | texto | vínculo no validado | Evidencia o limitación de esa relación |
| `equipment[].provenance` | `Provenance` | fuente Nexus local | Procedencia de la maquinaria |
| `requests[].id` | texto | `fixture:request-01` | Identidad de solicitud |
| `requests[].project_id` | texto? | `fixture:project-norte` | Referencia de proyecto solicitante |
| `requests[].project_name` | texto? | `Proyecto Norte · ejemplo` | Nombre del proyecto |
| `requests[].machinery_id` | texto? | `fixture:eq-cf03` | Referencia a maquinaria; puede faltar |
| `requests[].status` | texto | `APROBADA` | Estado original de la solicitud |
| `requests[].starts_on` | texto? | `2026-09-10` | Fecha de inicio original; se valida antes de comparar |
| `requests[].provenance` | `Provenance` | fuente Nexus local | Procedencia de la solicitud |
| `transfers[].id` | texto | `fixture:transfer-01` | Identidad de tarea |
| `transfers[].code` | texto | `TR-EJ-001` | Referencia visible de tarea |
| `transfers[].status` | texto | `COMPLETADA` | Estado de la tarea, no del equipo |
| `transfers[].request_id` | texto? | `fixture:request-01` | Solicitud relacionada |
| `transfers[].destination_project_id` | texto? | `fixture:project-norte` | Referencia de proyecto destino |
| `transfers[].destination_project_name` | texto? | `Proyecto Norte · ejemplo` | Destino administrativo; no posición GPS |
| `transfers[].driver` | texto? | `Motorista de ejemplo A` | Persona indicada para la tarea |
| `transfers[].provenance` | `Provenance` | fuente Startrack local | Procedencia de la tarea |
| `location.label` | texto | `Acceso del Proyecto Norte · ubicación simulada` | Descripción de la observación; no coordenadas inferidas |
| `location.observed_at` | fecha/hora con zona | `2026-09-12T14:42:00Z` | Fecha de la posición del ejemplo |
| `location.provenance` | `Provenance` | fuente Startrack local | Cuándo y de dónde se obtuvo la observación |

### Alertas y resumen

| Campo | Tipo | Ejemplo | Significado |
| --- | --- | --- | --- |
| `alerts[].id` | texto | `active-failure:fixture:eq-ex02` | Clave calculada para mostrar la señal; no ID de evento ni historial persistente |
| `alerts[].code` | texto | `active_failure` | Identificador de la regla aplicada |
| `alerts[].severity` | `info / warning / critical` | `warning` | Priorización del hub propuesta, no SLA aprobado |
| `alerts[].title` | texto | falla activa registrada | Mensaje breve de revisión |
| `alerts[].description` | texto | revisar diagnóstico y decisión de paro | Interpretación y acción sugerida |
| `alerts[].owner` | texto | `Mantenimiento` | Área funcional propuesta; no asignación autenticada de tarea |
| `alerts[].equipment_id` | texto? | `fixture:eq-ex02` | Equipo que origina la señal |
| `alerts[].request_id` | texto? | `fixture:request-02` | Solicitud que origina la señal, si se informa |
| `alerts[].evidence` | texto[] | `["active_failure_is_paro=true"]` | Hechos usados por la regla |
| `summary.equipment_count` | entero? | `3` | Cantidad de equipos devueltos |
| `summary.administratively_available` | entero? | `1` | Equipos devueltos cuyo estado es Disponible |
| `summary.active_failures` | entero? | `1` | Equipos devueltos con ID de falla activa |
| `summary.stopped_equipment` | entero? | `1` | Equipos devueltos con paro explícito `true` |
| `summary.unlinked_equipment` | entero? | `1` | Equipos cuya relación no es `confirmed`; incluye candidatos |
| `summary.alerts_count` | entero? | `4` | Señales calculadas sobre el conjunto devuelto |

Los números de ejemplo corresponden al fixture sin filtros. `alerts_count=0` significa que no se produjeron alertas con los datos devueltos; si falta una fuente no prueba ausencia de riesgos. Todos los conteos del resumen, incluido `alerts_count`, se devuelven como `null` cuando no se obtuvo una lectura, en lugar de producir un cero global engañoso.

## RF-02 — Mapeo implementado y ausencias

Esta matriz cubre el contrato inicial. No afirma que todos los campos del diccionario estén implementados. El conector usa rutas internas Nexus observadas; falta acordar un contrato de integración soportado con el proveedor.

| Origen Nexus | Destino en el hub | Transformación y límite |
| --- | --- | --- |
| Equipos: `id` | `equipment.id`, `provenance.source_id` | Prefijo `nexus:equipment:` para el ID del hub; original preservado en procedencia |
| Equipos: `clave`, `no_activo` | `code`, `asset_number` | Campos independientes, ambos pueden faltar; mostrar un valor alternativo no cambia su identidad |
| Equipos: `nombre`, `empresa` | `name`, `company` | Renombre, sin deducir unicidad ni entidad legal |
| Equipos: `estado` | `machinery_status` | Valor original; no se combina con GPS o mantenimiento |
| Equipos: `project_id`, `project_name` | `equipment.project_id`, `project_name` | Copia de referencia, sin deducir vigencia |
| Equipos: `active_failure_id` | `maintenance_failure_id` | Referencia de falla; existencia no equivale a paro |
| Equipos: `active_failure_status` | `maintenance_status` | Estado de la falla conservado por separado |
| Equipos: `active_failure_is_paro` | `maintenance_is_stopped` | Booleano estricto; ausente permanece desconocido |
| Solicitudes: `id` | `requests.id`, `provenance.source_id` | Prefijo `nexus:request:` y original preservado |
| Solicitudes: `project_id`, `project_name` | referencias del proyecto en la solicitud | Copia; el nombre puede faltar |
| Solicitudes: `maquinaria_id` | `requests.machinery_id`, `equipment.request_ids` | Prefijo de equipo y coincidencia exacta entre los registros consultados |
| Solicitudes: `status` | `requests.status` | No se transforma en estado de traslado |
| Solicitudes: `fecha_inicio` | `requests.starts_on` | Texto original; se evalúa solo si representa fecha ISO o instante con zona válido |
| Paginación: `total` | totales en `scope` | Antes del filtro local; sujeto a permisos y cambios del origen |
| Sin equivalente externo | `mode`, procedencia, calidad de relación, estado de fuente, resumen y alertas | Metadatos y derivaciones del hub |

`search` filtra localmente las páginas acotadas obtenidas. Un resultado vacío no demuestra inexistencia fuera de esas páginas. Un fin de paginación correcto tampoco demuestra que exista un traslado de Startrack relacionado.

| Concepto Startrack / diccionario | Destino previsto o situación | Estado actual |
| --- | --- | --- |
| Vehículo: descripción, tipo y referencia remota | Identidad candidata de maquinaria/vehículo | Sin respuesta API autenticada ni tabla de correspondencias; no se mapea por nombre |
| Vehículo: estado | Estado de seguimiento propio | No tiene equivalente directo en `machinery_status`; fuera del contrato inicial |
| Motorista/asignación | `equipment.driver` o `transfers[].driver` | Solo fixtures; falta conciliar IDs y vigencia |
| ID y estado de tarea | `transfers[].id`, `code`, `status` | Solo fixtures; falta verificar respuesta autenticada y catálogos |
| Referencia externa de tarea (`remote_id` documentado; IDR visto en UI) | Relación candidata con `requests[].id` | Coincidencia por validar junto con recurso, destino y período |
| Destino/geocerca | `destination_project_id`, `destination_project_name` | Solo fixtures; no se equipara geocerca con recepción |
| Última posición y fecha de reporte | `location` | Solo fixture fechado; falta comprobar API, unidad temporal y activo observado |
| Coordenadas enteras del Excel | Sin equivalente implementado | Escala no documentada; no se calculan coordenadas |
| Horómetro, odómetro, servicios, proveedor/mecánico | Sin equivalente implementado | Magnitudes y procesos distintos; fuera de la consulta inicial |

El diccionario aporta además clase, tipo solicitado, solicitante, período completo y otros atributos de vehículos/geocercas. No todos tienen un campo en esta versión del hub. Las bitácoras, costos, fechas de aprobación, recepciones, cancelaciones históricas y cambios de asignación tampoco se incorporan todavía. Documentar su ausencia evita atribuir al prototipo cobertura que no tiene.

## RF-03 — Responsabilidades funcionales propuestas

**R** ejecuta la revisión; **A** responde por su aprobación; **C** aporta contexto; **I** recibe información. La matriz propone un responsable de aprobación por actividad. Debe contrastarse con las gerencias reales; el [organigrama](onedrive/03-organigramas.md) no aprueba por sí mismo estas asignaciones. La app es de consulta y no ejecuta estas aprobaciones en los sistemas externos.

| Actividad | Técnica de Proyectos | Logística y Equipos | Mantenimiento | Tecnología / proveedores |
| --- | --- | --- | --- | --- |
| Confirmar necesidad, proyecto y fecha requerida | A/R | C | C | I |
| Verificar vínculo solicitud–maquinaria–traslado y destino | C | A/R | C | R para el soporte técnico del mapeo |
| Revisar solicitud aprobada sin unidad vinculada | C | A/R | C | I |
| Validar diagnóstico de falla y decisión de paro | I | C | A/R | I |
| Revisar traslado pendiente con equipo en paro | C | A/R | R | I |
| Definir evidencia de recepción y compromiso del proyecto | A/R | R | C | I |
| Validar definición, corte y cobertura de indicadores | A | R | C | R para la medición técnica |
| Mantener conectores, credenciales y observabilidad | I | C | C | A/R |

## RF-06 — Señales medibles en esta versión

| Señal | Regla implementada | Interpretación y límite |
| --- | --- | --- |
| Falla activa registrada | Un equipo tiene `maintenance_failure_id` | Revisar diagnóstico; no declarar paro sin booleano explícito |
| Solicitud pendiente con inicio alcanzado | Estado Pendiente y fecha válida anterior o igual al corte local | Priorizar asignación; no implica incumplimiento de recepción |
| Aprobada sin unidad vinculada | Estado Aprobada y `machinery_id` ausente | Revisar el vínculo, sin declarar que el registro es inválido |
| Traslado pendiente con falla y paro | Falla activa, paro explícito, relación confirmada y tarea Pendiente | Señal de revisión; los ejemplos son locales y falta incorporar vigencia/compromiso del traslado |

El corte de negocio utiliza **America/El_Salvador (UTC−06:00)**. En fixtures el corte es fijo para que los ejemplos sean reproducibles. Fechas ambiguas, inválidas o instantes sin zona no se convierten en una fecha prometida inventada. La última regla no decide por sí sola suspender una operación ni prueba atraso: esta versión no tiene fechas de cada traslado ni recepción validada.

Indicador documentado para evolucionar: `100 × solicitudes aprobadas sin unidad / solicitudes aprobadas`, siempre sobre el ámbito declarado y mostrando ambos conteos. Denominador cero: **sin casos evaluables**. La API actual entrega solicitudes y alertas; no publica aún ese porcentaje como KPI global. [Definiciones, cobertura y referencias ISO](kpis-y-referencias-iso.md).

La siguiente versión del modelo debe validar relaciones por tarea y período, incorporar evidencia de recepción y conservar historia antes de medir puntualidad, utilización o tiempos de reparación. No hay metas numéricas aprobadas ni certificación ISO demostrada por estas matrices.
