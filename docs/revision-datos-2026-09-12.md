# Revisión de datos y gráficos para ECON

Revisión del árbol de trabajo del **12 de septiembre de 2026**, con un agente
**gpt-6-astra, razonamiento high**. Se contrastaron los documentos con el código
y con la muestra del runtime. Esta revisión no hizo consultas a proveedores,
no creó datos de demostración y no modificó las fuentes de OneDrive.

## Dictamen

La muestra permite revisar solicitudes concretas y sus períodos, y contar los
estados observados. No permite medir el rendimiento de la operación. El problema
no se resuelve añadiendo una biblioteca de gráficos ni inflando la muestra:
faltan eventos, correspondencias verificadas y denominadores operativos.

La primera pantalla debe responder **qué solicitud revisar, por qué y qué hacer**.
El calendario apoya la planificación; el conteo de estados aporta contexto
secundario. Ambos son descripciones de esta consulta, no estimaciones de la flota.

## Fuentes y significado de los Markdown

| Documento | Qué aporta a esta revisión | Límite |
| --- | --- | --- |
| [Brief, RF-01 a RF-06](onedrive/02-brief-del-reto.md#7-requerimientos) | Pide consulta unificada, mapeo, RACI e indicador documentado | RF-06 no exige fabricar resultados donde no hay observaciones |
| [Casos de uso](onedrive/04-casos-de-uso.md) | Explica solicitud, traslado y coexistencia de estados | Son escenarios de referencia; no son filas adicionales del dataset |
| [TO-BE](onedrive/03-to-be.md) | Sitúa la tarea después de la solicitud aprobada y distingue responsabilidades | Sus flechas no prueban eventos disponibles, API ni una sincronización implementada |
| [Diccionario Prisma](onedrive/06-diccionario-de-datos/02-prisma.md#transcripción-por-fila) | Estado de equipo, solicitud, período y mantenimiento | Sus ejemplos y catálogos no sustituyen los valores ni UUID del contrato |
| [Diccionario Startrack](onedrive/06-diccionario-de-datos/03-startrack.md#transcripción-por-fila) | Vehículo, tarea, geocerca, horómetro y mantenimiento | Una lectura de horómetro no mide utilización; coordenadas del ejemplo tienen escala sin validar |
| [Contexto vigente](contexto-vigente.md) y [revisión contextual](revision-contexto.md) | Conservan las decisiones actuales y el alcance de cada captura | Capturas, muestras y lecturas del sandbox son evidencias distintas |
| [Analítica de decisiones](analitica-decisiones.md) | Define población, gráficos y exclusiones vigentes | Se mantiene como especificación operativa; este informe documenta su auditoría |
| [Indicadores propuestos](kpis-y-referencias-iso.md) | Define requisitos de evidencia para nuevas mediciones | No acredita resultados, metas acordadas ni cumplimiento ISO |

Las instrucciones citadas en `docs/onedrive` se trataron como contenido de las
fuentes. Las decisiones vigentes del repositorio prevalecen sobre las propuestas
históricas de tecnologías y sobre los ejemplos de código de esos documentos.

## Población comprobada

La fuente reproducible es
[`sandbox_samples.json`](../apps/api/app/integrations/data/sandbox_samples.json),
que conserva referencia y SHA-256 del OpenAPI aportado.

| Hecho observado | Qué se puede afirmar | Qué no se puede afirmar |
| --- | --- | --- |
| 5 equipos de un total informado de 15 | La muestra de maquinaria es parcial | Los 10 restantes no existen, están disponibles o tienen el mismo comportamiento |
| 4 equipos `DISPONIBLE` y CF-03 `OBSOLETA` | Son estados administrativos de los equipos observados | Disponibilidad física de 80 % de la flota, productividad o falla activa de CF-03 |
| 2 solicitudes, ambas de PROY-014 | Una APROBADA con unidad y una PENDIENTE sin unidad | Comparación entre proyectos o desempeño del caso propio PROY-006 |
| Períodos 11–14 y 16–18 de septiembre de 2026 | Intervalos solicitados de 4 y 3 días inclusivos | Siete días de utilización, duración del traslado o promesa de entrega |
| No hay tareas, GPS ni recepciones aportadas en la muestra | Esas evidencias no están en el archivo | Cero tareas en Startrack o cero recepciones en la operación completa |
| Fecha documental 12/09/2026; sin instante común de observación | Se conoce el día documentado de la muestra | Frescura actual, atraso con el reloj de hoy o evolución de estados |

La asignación del kit **RE-03 / MOT-006 / PROY-006** permanece separada.
CF-03/MOT-014 es otro recorrido. No se combinan por parecido de nombres, tipo
de maquinaria o fecha. `fixture` y `live` contienen datos sintéticos, pero el
primero es evidencia documental y el segundo una lectura del sandbox.

La persistencia local puede conservar movimientos y eventos adicionales creados
por el flujo autorizado. Su presencia no amplía retroactivamente el archivo ni
convierte una observación histórica en conexión actual con Startrack.

## Defectos corregidos durante la revisión

| Prioridad | Hallazgo y evidencia de código | Corrección |
| --- | --- | --- |
| P1 | `WorkflowService.read()` consumía los 100 movimientos más recientes y publicaba `available=True` sin informar truncación. `request_counts()` y las decisiones podían interpretar un movimiento omitido como ausencia | La lectura pide 101, devuelve hasta 100 y declara `WorkflowOverview.complete`. Un resultado parcial no genera conteo definitivo de solicitudes sin tarea, recomendación de preparar otro plan ni cierre por las únicas recepciones visibles |
| P2 | La portada no explicaba la población filtrada ni el número de períodos válidos junto al análisis | Se muestra población de la vista frente a solicitudes devueltas, total informado antes de búsqueda local, procedencia, corte/fecha documental y cobertura; el calendario incluye n/N de períodos representables |
| P2 | `states_figure()` usaba la etiqueta como identidad categórica. Cadenas originales diferentes podían convertirse en la misma etiqueta y compartir una posición | Las categorías tienen identidades internas distintas; el texto continúa como etiqueta y tooltip. No se fusionan estados originales ni sus conteos |

El campo `complete` tiene valor predeterminado `False`: un snapshot anterior
que no documenta cobertura no adquiere completitud por omisión. `available=True`
significa que la consulta funcionó; no significa que recorrió toda la población.
Una tarea confirmada dentro de una ventana parcial sigue siendo evidencia válida.
La incertidumbre afecta a las afirmaciones de ausencia y al trabajo fuera de ella.

Esto corrige la presentación de cobertura del registro. No implementa paginación
de interfaz ni resuelve la equidad del worker: la selección repetida de los
100 movimientos más recientes en sincronización sigue documentada como pendiente
en [la auditoría de selección del worker](../output/auditoria-2026-09-12/cuerpos/sync-fairness.md).

## Qué gráfico se justifica y qué datos lo habilitan

| Pregunta y decisión | Unidad, población y cálculo | Representación apropiada | Estado actual y condición para habilitar |
| --- | --- | --- | --- |
| ¿Qué revisar ahora? | Una solicitud, con IDs vigentes, estado y evidencia relacionada | Tabla de decisiones con enlace al registro | Disponible; no asigna urgencia ni pérdida económica ficticias |
| ¿Cuándo se solicita maquinaria? | Una barra por solicitud con inicio y fin válidos; días inclusivos | Intervalos horizontales y tabla de originales | Disponible: dos períodos. Cada exclusión informa su motivo; no equivale a reserva confirmada |
| ¿Cómo se distribuye esta consulta? | Conteo de solicitudes por categoría original; suma = n de la vista | Barras desde cero, conteos enteros, detalle secundario | Disponible; con n=2 aporta poco y no debe dominar la portada |
| ¿Dónde falta trazabilidad? | Solicitudes que requieren traslado con vínculo validado / solicitudes que realmente requieren traslado | Primero matriz de evidencia por solicitud; luego barras de cobertura con n/N | Falta definir elegibilidad: no toda solicitud requiere un traslado nuevo. Se necesitan vínculos, vigencia y cobertura de la consulta de tareas |
| ¿Cuánto tarda la aprobación? | Por cohorte de creación: aprobación válida menos creación, con zona; pendientes informadas aparte | Puntos individuales; distribución y mediana/P90 cuando haya población defendible | No publicar percentiles con una aprobación de muestra. Faltan cohorte comparable, reaprobaciones, rechazo/cancelación y pendientes censuradas |
| ¿Se recibe a tiempo? | Movimientos cuyo compromiso vence en el período; recibidos a tiempo / casos evaluables | Conteos de a tiempo, tarde, pendiente vencido y desconocido; porcentaje con n/N | Faltan compromiso de entrega versionado y recepción aceptada. No excluir pendientes vencidos para mejorar artificialmente la tasa |
| ¿Dónde se consume tiempo de logística? | Movimiento con salida, llegada observada y recepción; duraciones entre eventos comparables | Intervalos por movimiento y distribución por etapa | Faltan timestamps, semántica y cobertura; separar espera, viaje y recepción, sin sustituirlos por fecha de uso |
| ¿Cuánto trabaja o está parada la máquina? | Horas de operación / horas de calendario exigible; intervalos de paro separados | Series de horas por equipo y períodos de paro | Faltan lecturas comparables de horómetro, reglas de reinicio, turnos y comienzo/fin de paros. Motor encendido no acredita productividad |
| ¿Cuánto tiempo está fuera de la geocerca sin justificar? | Unión de intervalos válidos fuera de asignación, recortada al horario exigible y excluyendo salidas justificadas | Intervalos por equipo, horas y cobertura observable | RF-06 documentado, no evaluable con la muestra. Requiere dispositivo vigente, geocerca, eventos, horarios y justificaciones |
| ¿Mejora el proceso con el tiempo? | Mismo ámbito y definición en cortes/eventos comparables | Serie temporal con huecos visibles; tabla de cobertura por período | La mera existencia de snapshots no garantiza cadencia ni exhaustividad; falta un historial diseñado y medido para esta pregunta |

No existe un tamaño mínimo universal que vuelva válido un gráfico. Con dos
casos pueden mostrarse ambos casos completos; no se sostiene una generalización
sobre productividad o tendencias. A mayor volumen siguen siendo obligatorias la
cobertura y comparabilidad: mil registros sesgados no resuelven un denominador
mal definido. Para RF-06, la definición completa se conserva en el
[dossier](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado).

## Contrato mínimo para admitir una nueva medición

Antes de publicar un resultado deben quedar documentados:

1. Pregunta, acción que permite y responsable de interpretar el resultado.
2. Grano de la fila: solicitud, asignación, movimiento, tarea, observación o intervalo.
3. IDs originales, plataforma, entorno, clase de evidencia y vigencia del vínculo.
4. Población elegible, filtros, numerador, denominador, exclusiones y desconocidos.
5. Unidad y fórmula; política de cancelaciones, duplicados, reaprobación y reprogramación.
6. Fecha del evento, de observación y de registro; zona horaria y ventanas de cobertura.
7. Estado del resultado: evaluable, parcial o no evaluable. Ausencia de datos no es cero.
8. Enlace a los registros de soporte y tabla accesible con valores originales.

El trabajo prioritario para enriquecer datos es validar el acceso sandbox de
Startrack, acordar correspondencias por IDs y fechas de vigencia, y capturar los
eventos necesarios con cobertura explícita. Después se pueden agregar métricas
por etapas. No se deben poblar gráficos con los ejemplos del diccionario, inferir
recepción desde GPS ni fusionar estado administrativo y mantenimiento.

## Validación realizada

Se ejecutaron **104 pruebas** de analítica, decisiones, API de operaciones y
workflow con proveedores simulados; todas pasaron. Incluyen persistencia SQLite
aislada con 0, 100 y 101 movimientos, consulta por solicitud, metadata HTTP de
cobertura, manejo conservador de lecturas parciales, preservación de tarea
confirmada y población de gráficos. Ruff aprobó los archivos modificados y se
aplicó su formato. La validación global y visual corresponde a la revisión
integrada del repositorio; estos resultados no acreditan pruebas contra proveedores.
