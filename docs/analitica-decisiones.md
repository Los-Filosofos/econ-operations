# Analítica para decidir sobre la operación

La portada muestra el recorrido proyecto → unidad asignada → traslado →
recepción como un grafo operativo. La página `/decisiones` («Qué requiere
atención») presenta un asunto por solicitud con su evidencia y siguiente paso,
el calendario de períodos de uso solicitado y la distribución por estado; la
página `/indicadores` presenta las fichas de `GET /api/v1/indicators` por fila.
Ninguna convierte conteos ni ausencias en KPI. Las definiciones siguientes
corresponden a la implementación vigente; el contexto de negocio está en
[contexto vigente](contexto-vigente.md) y las fórmulas de los indicadores, en
[indicadores calculables](indicadores-calculables.md), su única fuente.

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

Los límites de la muestra y los requisitos previos a cualquier medición nueva
están en [contexto vigente](contexto-vigente.md#límites-de-los-datos). El
indicador discreto del lienzo declara modo, cobertura, corte o fecha documental
y momento de consulta. El detalle de cada nodo conserva procedencia y antigüedad.

La búsqueda y los filtros usan la misma población en Resumen, Solicitudes y
Decisiones. Una consulta sin registros, una cobertura parcial y una fuente
indisponible son resultados distintos. No encontrar una tarea en una lectura
incompleta no prueba que no exista; tampoco una ausencia de alertas demuestra
ausencia de riesgo.

## Presentación del grafo

| Elemento | Regla de representación | Definición y límite |
| --- | --- | --- |
| Proyecto / obra | Un nodo por `project_id` | El nombre sólo etiqueta; nunca une identidades y una contradicción de nombres queda visible |
| Maquinaria | Un nodo por ID normalizado | La silueta específica requiere `equipment_class`; sin esa evidencia se usa el tipo genérico |
| Despliegue de maquinaria | Al seleccionar un lugar o durante un traslado activo | Sólo revela unidades con una relación exacta; una unidad sin vínculo no se atribuye a una base ni se supone disponible |
| Asignación | Segmento recto y fino | Sólo existe con `maquinaria_id` y `project_id` exactos, ya sea en la solicitud o la maquinaria normalizada |
| Traslado confirmado | Segmento recto dirigido | Sólo promueve una relación cuya evidencia ya coincide por IDs, entorno, asignación y período vigentes |
| Detalle contextual | Hechos y faltantes del nodo o conexión seleccionados | Expone fuente, observación, asignación, períodos, operadores, traslado, responsable disponible, incidentes, recepción, historia y contradicciones sin completar campos ausentes |

La trazabilidad por maquinaria cuenta IDs de proyecto distintos respaldados por
asignaciones, solicitudes, traslados o movimientos persistidos visibles. El
detalle los representa por códigos legibles y eventos con iconos; las claves
técnicas permanecen en el modelo, no en la ficha visual. Ese conteo no afirma
presencia física y no se presenta como historial completo cuando la cobertura es
parcial.

Las incidencias de envío se atienden antes de sugerir otro movimiento. Un envío
incierto requiere conciliación; una consulta del registro indisponible no se
convierte en cero movimientos ni en recomendación de duplicar el envío. Los
enlaces operativos exigen correspondencia de solicitud, asignación, procedencia
y período con el registro persistido.

La disponibilidad del registro no equivale a completitud: `complete=false`
también cubre lecturas truncadas a la página leída (100 movimientos por
defecto; Operaciones pagina el resto). La ausencia de una tarea y el cierre del
conjunto de movimientos no se deducen de esa ventana parcial. Los conteos que
dependen de esa ausencia permanecen desconocidos.

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

## Página de decisiones

`/decisiones` reutiliza la lectura del hub y el registro del navegador; no
consulta proveedores por su cuenta y respeta `mode`, `q` y `filter` de la URL.

| Bloque | Qué muestra | Regla y límite |
| --- | --- | --- |
| Asuntos por revisar (`decision_priorities.py`) | Una tarjeta por solicitud de la población filtrada: proyecto, tipo, período, estado, título del asunto, evidencia y enlace a la acción (detalle de la solicitud u operaciones) | Un asunto por solicitud, elegido por prioridad explícita: primero las incidencias de envío del registro (`unknown`, `failed`, `blocked`), después aprobada sin unidad, unidad con condición, traslado sin evidencia y pendiente; sin puntajes de urgencia ni reloj («no indican atraso» porque la muestra no tiene corte). Sin asuntos se dice «No se identificaron asuntos por revisar con la evidencia de esta consulta» |
| Lo que dicen los indicadores (`indicator_views.indicator_insights`) | Las tres lecturas más accionables de las ocho fichas de `compute_indicators`, con estado y una frase derivada de las filas, y el enlace «Ver los 8 indicadores y sus SLA propuestos» a `/indicadores` | Ninguna frase recalcula una regla ni compara con el reloj; en fixture se declara que las muestras no tienen corte de observación y, sin filas evaluables, se remite a la página de indicadores con el motivo de cada ficha |
| Nota de cobertura | Modo, «Datos sintéticos», solicitudes en la vista y devueltas, total informado por el origen, corte de lectura o fecha documental, registro disponible o parcial | `data_as_of` nulo en fixture: se muestra la fecha documental sin instante común; un registro no disponible o parcial se declara antes de concluir que un traslado no está preparado |
| Período de uso solicitado (`decision_analytics.usage_timeline`, `usage_figure`) | Una franja por solicitud entre `starts_on` y `ends_on`, días inclusivos, leyenda por texto y tabla «Ver datos de períodos» | No es duración del traslado, ventana de entrega ni utilización. Las solicitudes con fechas incompletas, ambiguas o invertidas se listan aparte con su motivo; las fechas con hora se representan por su día en El Salvador |
| Distribución por estado (`request_states`, `states_figure`) | Conteo por `status` original de las solicitudes devueltas y filtradas, con tabla «Ver datos de estados» | Describe la vista, no el desempeño integrado ni la flota; `PENDIENTE` y `APROBADA` se muestran como vienen |

Los gráficos usan `figure()` de `dashboard/theme.py` (sin zoom, ejes fijos,
paleta cualitativa de estados) y siempre tienen tabla alternativa; el azul ECON
no codifica estado.

## Responsabilidad del código y futuras mediciones

`app/dashboard/operations_graph.py` transforma `HubResponse` y
`WorkflowOverview` en nodos, aristas y detalle sin consultar proveedores;
`views.py` presenta esa proyección, la página de decisiones (`decisions`) y el
resto de listas; `indicator_views.py` presenta `/indicadores` y las tres
lecturas de `/decisiones`, y el asset local `operations-graph.js` sólo gestiona
zoom, pan y selección. Las reglas del contrato y de la evidencia permanecen en
`app/services/hub.py` y `app/services/evidence.py`; las fichas de indicadores,
en `app/services/indicators.py`. Los cambios deben mantener alineados los
modelos Pydantic y sus consumidores Dash; ver
[arquitectura de interfaz](frontend-architecture.md).

El indicador RF-06 (tiempo fuera de geocerca sin justificación) se define una
sola vez en [entregables visuales](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado);
este documento no repite su fórmula. Los indicadores que sí se calculan hoy, por
fila y sin promedios, sus SLA propuestos, lo que impide agregar y las lecturas
que habilitarían más mediciones están únicamente en
[indicadores calculables](indicadores-calculables.md). El grafo tipado de la
misma lectura está en `GET /api/v1/graph` y las candidatas para una solicitud
pendiente, en `GET /api/v1/requests/{id}/suggestions` y en el detalle de la
solicitud.

No se publican resultados de productividad, ahorro, cumplimiento ISO o variaciones
mensuales con estas muestras. Las ampliaciones de
[sincronización, discrepancias y escala](sincronizacion-y-discrepancias.md)
son propuestas pendientes de implementación.
