# Analítica para decidir sobre la operación

La portada **Resumen** muestra qué requiere revisión, en qué proyecto, con qué
evidencia y cuál es el siguiente paso. El recorrido es proyecto → solicitud →
unidad asignada → traslado → recepción. Las definiciones siguientes corresponden
a la implementación vigente; el contexto de negocio está en
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

La [revisión de datos](revision-datos-2026-09-12.md) detalla los hallazgos de esta
etapa y la evidencia necesaria para habilitar otras mediciones. Junto a los
gráficos se muestran solicitudes de la vista, filas devueltas, total informado
por el origen antes de búsqueda, procedencia y corte conocido. El calendario
declara cuántos períodos son representables sobre las solicitudes de la vista.

La búsqueda y los filtros usan la misma población en Resumen y Solicitudes.
Una consulta sin registros, una cobertura parcial y una fuente indisponible son
resultados distintos. No encontrar una tarea en una lectura incompleta no prueba
que no exista; tampoco una ausencia de alertas demuestra ausencia de riesgo.

## Presentación implementada

| Elemento | Decisión que apoya | Definición y límite |
| --- | --- | --- |
| Asuntos por revisar | Qué revisar y dónde continuar | Como máximo un asunto por solicitud, con hecho de origen y enlace al registro; orden estable por ID, sin puntajes de urgencia |
| Períodos de uso solicitado | En qué fechas se necesita maquinaria | Una barra por solicitud con inicio y fin originales; días inclusivos; no equivale a compromiso de entrega |
| Distribución por estado, desplegable | Cómo se distribuyen las solicitudes consultadas | Conteo por categoría original con eje desde cero; contexto secundario |

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

Los gráficos tienen etiquetas en español y datos alternativos en tablas. Los
IDs están en el detalle o tooltip; las barras se identifican internamente por ID
aunque sus etiquetas coincidan. Para incluir el último día solicitado, el final
dibujado es el día siguiente; tooltip y tabla conservan las fechas originales.

Las fechas sin hora conservan el día calendario. Los instantes con zona se
convierten a `America/El_Salvador`. Los períodos ausentes, ambiguos, inválidos o
invertidos se excluyen del gráfico y se informan con su motivo. El calendario
describe planificación; no reconstruye cambios históricos de estado.

## Responsabilidad del código y futuras mediciones

`app/dashboard/decision_priorities.py` deriva los asuntos por solicitud;
`decision_analytics.py` selecciona la población y prepara los gráficos;
`decision_views.py` los presenta. Las reglas del contrato compartido permanecen
en `app/services/hub.py`. Los cambios deben mantener alineados los modelos
Pydantic y sus consumidores Dash; ver [arquitectura de interfaz](frontend-architecture.md).

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
[sincronización y discrepancias](sincronizacion-y-discrepancias.md) y
[escala de flota](arquitectura-escalable-flota.md) son propuestas pendientes de implementación.
