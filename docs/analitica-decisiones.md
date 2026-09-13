# Analítica para decidir sobre la operación

La portada («Qué requiere atención») combina agenda de períodos de uso y
acciones por solicitud. `/resumen` y `/decisiones` son alias de esa misma vista.
La página `/indicadores` abre con el tablero de cifras por área
([tablero de KPI](kpis-tablero.md)) y presenta después los resultados de
`GET /api/v1/indicators` por fila, con gráficos de tiempos y detalle
metodológico desplegable. El tablero cuenta filas de la lectura y cita su
cobertura; **ninguna vista convierte una ausencia en cero ni promedia la
cohorte**: una cifra bloqueada publica el motivo del servicio, no un número.
Las definiciones siguientes
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
alcance de la consulta declara modo, cobertura, corte o fecha documental
y momento de consulta. Los detalles conservan procedencia y antigüedad.

La portada usa la lectura sin búsqueda ni filtros de listas. La búsqueda solo
aparece bajo el título de Solicitudes, Maquinaria y Operaciones; en Operaciones
afecta a la página cargada del registro. Navegar a otra sección conserva el modo
y limpia la búsqueda. Una consulta sin registros, una cobertura parcial y una fuente
indisponible son resultados distintos. No encontrar una tarea en una lectura
incompleta no prueba que no exista; tampoco una ausencia de alertas demuestra
ausencia de riesgo.

## Evidencia de la operación

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

Las fechas sin hora conservan el día calendario. Los instantes con zona se
convierten a `America/El_Salvador`; `generated_at` sólo fecha la consulta. Los
períodos ausentes, ambiguos, inválidos o invertidos no se completan ni se usan
para inferir relaciones.

## Página de decisiones

La portada y sus alias reutilizan la lectura del hub y el registro del navegador;
la función de presentación no consulta proveedores por su cuenta. Conservan
`mode` y no aplican `q` ni `filter`. Agenda y acciones comparten población y se
presentan con prioridad visual: agenda a todo el ancho y después la tabla de
asuntos. Cada franja conserva el ID de la solicitud, muestra proyecto, unidad
asignada (o su ausencia), estado e intervalo. Los datos originales se pueden
desplegar debajo de las acciones. No hay tarjetas de conteos ni gráfico de
distribución de estados en la portada. OBSOLETA sigue siendo una condición
administrativa que requiere revisar la asignación, no una afirmación de falla.

| Bloque | Qué muestra | Regla y límite |
| --- | --- | --- |
| Acciones por solicitud (`decision_priorities.py`) | Tabla con asunto, proyecto, unidad, hecho observado y acción; enlace al detalle de solicitud u operación | Un asunto por solicitud según reglas explícitas: incidentes de envío antes de proponer otro traslado; condición de unidad, aprobación, asignación y evidencia determinan el siguiente paso. Sin puntajes de urgencia ni reloj inferido; la ausencia de asuntos se limita a la lectura |
| Cobertura | Contexto breve de modo y alcance; fechas, total y explicación desplegables | `data_as_of` nulo en fixture: fecha documental sin instante común. Registro indisponible o parcial no acredita ausencia de traslado |
| Período de uso solicitado (`decision_analytics.usage_timeline`, `usage_figure`) | Una franja por solicitud entre `starts_on` y `ends_on`, días inclusivos, leyenda por texto y tabla «Ver datos de períodos» | No es duración del traslado, ventana de entrega ni utilización. Las solicitudes con fechas incompletas, ambiguas o invertidas se listan aparte con su motivo; las fechas con hora se representan por su día en El Salvador |
| Distribución por estado (`request_states`, `states_figure`), cuando se presenta | Conteo por `status` original de las solicitudes de la lectura, con tabla alternativa | Describe la vista, no el desempeño integrado ni la flota; `PENDIENTE` y `APROBADA` se muestran como vienen |

Los gráficos usan `figure()` de `dashboard/theme.py` (sin zoom, ejes fijos,
paleta cualitativa de estados) y siempre tienen tabla alternativa; el azul ECON
no codifica estado.

## Presentación de indicadores

La página presenta una pregunta activa con el gráfico antes de los registros,
que permanecen visibles; la evidencia técnica y el método se despliegan aparte.
Una aprobación aislada se representa como dos hitos unidos por una línea fina,
creado–aprobado, con la duración rotulada
y un eje de reloj en El Salvador redondeado a minutos completos. Varias duraciones
se comparan mediante barras. La escala usa segundos, minutos u horas según la
magnitud. Cada gráfico conserva acceso a sus filas y evidencia; no se promedian
registros ni se rellenan ausencias.

Los conteos y tablas conservan la población de la lectura. Indicadores sin casos
o sin evidencia suficiente muestran el motivo y el dato requerido; no se presentan
como cero problemas. Cobertura, definiciones y SLA propuestos se consultan aparte.
Los umbrales propuestos se presentan como tablas de referencia en una pestaña
separada. Siguen pendientes de acuerdo con ECON; no se grafican como resultados,
no se calcula cumplimiento ni se superponen como metas sobre otro tipo de reloj.
La portada no repite estas fichas ni sus explicaciones.

## Cobertura y recorrido de integración

Fuentes compara los registros leídos con el total informado de cada colección
de Prisma. Las barras apiladas al 100 % comparan la proporción consultada de cada
colección, con numerador y denominador junto a cada barra: 2/2 y 5/15 no son
colecciones del mismo tamaño. La parte rayada representa
registros fuera de la lectura, no equipos indisponibles. Un total ausente o menor
que los registros devueltos no genera un resto; se etiqueta como desconocido o
inconsistente, sin porcentaje. Una colección vacía (0/0) tampoco recibe un
porcentaje; 0/N con N positivo sí representa 0 %. Si Prisma no se pudo leer,
no se dibuja un gráfico de ceros.
La tabla alternativa conserva numerador, total y resto. Startrack no recibe un
denominador inventado ni se incorpora a esos conteos.

Integración abre con un recorrido de cuatro etapas. Cada etapa conserva el
estado que entrega `build_trace`; no se deduce un porcentaje de avance ni la
completitud de etapas previas. Los pendientes y el enlace a la solicitud se ven
antes del detalle técnico. Los instantes y duraciones siguen en la pestaña
Tiempos: la falta de eventos no produce una cronología ficticia.

## Elección del gráfico y del color

| Pregunta | Representación | Alternativas evaluadas |
| --- | --- | --- |
| ¿Cuándo se solicita usar cada unidad? | Intervalos de calendario por solicitud; naranja pendiente y verde aprobada, siempre rotulados | Una línea de tendencia implicaría observaciones sucesivas de una variable; un circular perdería las fechas y los solapamientos |
| ¿Cuánto tardó esta aprobación? | Hitos creado/aprobado unidos, duración exacta en el detalle | Una barra aislada no compara casos; velocímetro o semáforo exigirían una meta validada |
| ¿Qué registros llevan más tiempo? | Barras horizontales ordenadas, origen cero y unidad común; hasta diez filas identificadas | Puntos serían válidos para comparar posiciones, pero las barras permiten leer directamente las duraciones desde cero. Sin muestra suficiente, histograma o caja no describen una distribución útil |
| ¿Qué proporción de cada colección se consultó? | Barras al 100 % con conteos explícitos; grafito leído y trama gris fuera de la consulta | Dos circulares dificultan comparar coberturas; juntar solicitudes y equipos en un circular inventaría una población común |
| ¿Cuántos equipos tienen cada estado administrativo? | Barras ordenadas con conteos y estados originales | El circular sería posible solo para la lectura, pero categorías pequeñas o iguales se comparan mejor con longitudes; nunca representa la flota completa |
| ¿En qué etapa falta evidencia de integración? | Lista de etapas con estado y motivo | Un embudo o Sankey exigiría cantidades comparables y flujos observados entre etapas; no se infieren desde estados |

Las mediciones sin categoría de estado usan grafito (`MEASURE` en `theme.py`):
la longitud o posición expresa la magnitud. El azul ECON sigue en identidad y
acciones. Verde, naranja, violeta y rojo conservan su significado de estado;
no se usa rojo para una duración larga sin un límite de negocio validado.
La trama y las etiquetas distinguen datos fuera de la consulta incluso sin color.
Las escalas secuencial y divergente quedan para intensidad o desviación reales,
no para colorear arbitrariamente cada barra.

La revisión se apoya en la guía de la ONS sobre
[color según su función](https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts)
y la guía de Government Analysis Function sobre
[cuándo usar gráficos circulares](https://analysisfunction.civilservice.gov.uk/support/communicating-analysis/introduction-to-data-visualisation-e-learning/module-9-pie-charts/).

## Responsabilidad del código y futuras mediciones

`views.py` presenta el resumen de decisiones y las listas;
`indicator_views.py` presenta `/indicadores`.
Las reglas del contrato y de la evidencia permanecen en
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
La [integración por eventos con orquestación central](arquitectura-integracion-eventos.md)
propone observar cambios, conservar incidencias y emitir comandos por autoridad
de campo, sin confundir ejecución de Startrack con asignación o recepción.
