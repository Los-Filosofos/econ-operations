# Analítica para decidir sobre la operación

La portada muestra el recorrido proyecto → unidad asignada → traslado →
recepción como un grafo operativo. No convierte conteos ni ausencias en KPI y
mantiene el detalle documental bajo interacción. Las definiciones siguientes
corresponden a la implementación vigente; el contexto de negocio está en
[contexto vigente](contexto-vigente.md).

## Población y evidencia

El modo `fixture` usa las muestras del OpenAPI suministrado: **cinco equipos y
dos solicitudes**, ambas de PROY-014. El archivo documenta quince equipos en total,
por lo que la cobertura de maquinaria es parcial. La asignación del kit
**RE-03 / MOT-006 / PROY-006** se conserva separada de estas muestras.

Las solicitudes tienen períodos del 11–14 y 16–18 de septiembre de 2026: una
APROBADA con CF-03 y otra PENDIENTE sin unidad. CF-03 figura `OBSOLETA`, sin falla
activa ni paro registrados; esto pide revisar la asignación, sin afirmar avería.
Las muestras no contienen tareas, ubicaciones ni recepciones. Los casos
inventados para verificar reglas solo pertenecen a pruebas aisladas.

Todo el caso utiliza datos sintéticos. `fixture` identifica muestras documentales;
`live`, consultas actuales del sandbox. No se sustituyen entre sí. El archivo
conserva fecha documental, pero no un instante común de observación: no permite
clasificar atrasos con el reloj actual. `generated_at` es el momento de armar la
respuesta, no una fecha de actualización de las fuentes.

Los límites de la muestra y la evidencia necesaria para otras mediciones están
en [contexto vigente](contexto-vigente.md#límites-de-los-datos). El indicador
discreto del lienzo declara modo, cobertura, corte o fecha documental y momento
de consulta. El detalle de cada nodo conserva procedencia y antigüedad.

La búsqueda y los filtros usan la misma población en Resumen y Solicitudes.
Una consulta sin registros, una cobertura parcial y una fuente indisponible son
resultados distintos. No encontrar una tarea en una lectura incompleta no prueba
que no exista; tampoco una ausencia de alertas demuestra ausencia de riesgo.

## Presentación del grafo

| Elemento | Regla de representación | Definición y límite |
| --- | --- | --- |
| Proyecto / obra | Un nodo por `project_id` | El nombre sólo etiqueta; nunca une identidades y una contradicción de nombres queda visible |
| Maquinaria | Un nodo por ID normalizado | La silueta específica requiere `equipment_class`; sin esa evidencia se usa el tipo genérico |
| Sin asignación | Agrupación visual sin aristas | Reúne las unidades que no tienen relación exacta en la lectura; permite consultar las `DISPONIBLE` sin afirmar una base o ubicación física |
| Asignación | Segmento recto y fino | Sólo existe con `maquinaria_id` y `project_id` exactos, ya sea en la solicitud o la maquinaria normalizada |
| Traslado confirmado | Segmento recto dirigido | Sólo promueve una relación cuya evidencia ya coincide por IDs, entorno, asignación y período vigentes |
| Detalle contextual | Hechos y faltantes del nodo o conexión seleccionados | Expone fuente, observación, asignación, períodos, operadores, traslado, responsable disponible, incidentes, recepción, historia y contradicciones sin completar campos ausentes |

Las incidencias de envío se atienden antes de sugerir otro movimiento. Un envío
incierto requiere conciliación; una consulta del registro indisponible no se
convierte en cero movimientos ni en recomendación de duplicar el envío. Los
enlaces operativos exigen correspondencia de solicitud, asignación, procedencia
y período con el registro persistido.

La disponibilidad del registro no equivale a completitud: `complete=false`
también cubre lecturas truncadas a 100 movimientos. La ausencia de una tarea y
el cierre del conjunto de movimientos no se deducen de esa ventana parcial.
Los conteos que dependen de esa ausencia permanecen desconocidos.

Estado administrativo, mantenimiento, envío, tarea, presencia GPS y recepción
describen hechos distintos. Una tarea completada o una visita de geocerca no
acredita recepción. Los planes y eventos guardados se muestran con su evidencia,
sin ampliar las muestras documentales ni presentarlos como observaciones actuales.

La geometría del grafo no representa coordenadas, distancia, avance ni tiempo.
Una máquina en traslado aparece una sola vez y la actividad de la línea expresa
estado, no posición. Sin una estimación existente se muestra «Tiempo no
disponible». Una geocerca del transportista, una tarea completada o una línea
visualmente corta no acreditan llegada o recepción.

Las fechas sin hora conservan el día calendario. Los instantes con zona se
convierten a `America/El_Salvador`; `generated_at` sólo fecha la consulta. Los
períodos ausentes, ambiguos, inválidos o invertidos no se completan ni se usan
para inferir relaciones.

## Responsabilidad del código y futuras mediciones

`app/dashboard/operations_graph.py` transforma `HubResponse` y
`WorkflowOverview` en nodos, aristas y detalle sin consultar proveedores.
`views.py` presenta esa proyección y el asset local `operations-graph.js` sólo
gestiona zoom, pan y selección. Las reglas del contrato y de la evidencia
permanecen en `app/services/hub.py` y `app/services/evidence.py`. Los módulos
analíticos anteriores se conservan para otras vistas o evolución posterior,
pero la portada ya no muestra cards, gráficos ni tablas. Los cambios deben
mantener alineados los modelos Pydantic y sus consumidores Dash; ver
[arquitectura de interfaz](frontend-architecture.md).

Antes de añadir una medición, documentar población, unidad, fórmula, fuente,
cobertura, fecha y acción que permite. La persistencia de planes, cortes y eventos
existe, pero por sí sola no acredita una serie histórica completa o comparable.

| Medición propuesta | Evidencia necesaria antes de publicarla |
| --- | --- |
| Evolución de solicitudes | Eventos o cortes comparables, población conocida y frecuencia de captura |
| Tiempo de aprobación o asignación | Fechas validadas, cambios de decisión y tratamiento de pendientes |
| Puntualidad de recepción | Compromiso de entrega, recepción aceptada y reglas de reprogramación/cancelación |
| Utilización o tiempo fuera de operación | Horas de uso, inicio/fin de paros y calendario operativo acordado |
| Comparación entre proyectos | IDs estables, cobertura comparable y denominadores pertinentes |

No se publican resultados de productividad, ahorro, cumplimiento ISO o variaciones
mensuales con estas muestras. Las ampliaciones de
[sincronización, discrepancias y escala](sincronizacion-y-discrepancias.md)
son propuestas pendientes de implementación.
