# Tablero de KPIs de la página de indicadores

Revisión del **13 de septiembre de 2026**. El tablero ocupa la parte alta de
`/indicadores` y responde una sola pregunta por área: *qué tiene que decidir hoy
Logística, Proyectos, Mantenimiento e Información con esta lectura*. No es una
medición nueva: cuenta filas de las poblaciones que `GET /api/v1/indicators` ya
publica. Las fórmulas, la población y el estado de cada indicador tienen una
única fuente, [indicadores calculables](indicadores-calculables.md#fichas-de-los-indicadores-publicados);
este documento no las repite.

| Elemento | Dónde |
| --- | --- |
| Construcción de las cifras | `apps/api/app/dashboard/kpi_views.py` (`build_kpis`, `kpi_board`) |
| Montaje en la página | `apps/api/app/dashboard/indicator_views.py` (`indicators_page`) |
| Estilo propio | `apps/api/app/dashboard/assets/z-kpi.css` sobre `components.data_strip` |
| Datos | `IndicatorsReport` de `app/services/indicators.py` y `HubResponse` (`scope`, `data_as_of`, `generated_at`, `operation_evidence`) |

## Reglas que cumple el tablero

- **La ausencia no es cero.** Una cifra solo es un número cuando cuenta filas que
  la lectura devolvió. Si el indicador no es evaluable, la celda publica el motivo
  del servicio («sin corte de observación (fixture)», «en fixture, las muestras no
  envían tareas…»), nunca `0`.
- **Sin promedios, medianas, percentiles ni porcentajes.** La cohorte es de dos
  solicitudes y cinco unidades en `fixture`; cualquier estadístico describiría una
  o dos filas. Cuando se cita una duración es el valor de **una fila** identificada
  («la fila más antigua lleva…», «tiempo medido: 42 s»).
- **La cobertura viaja con la cifra.** Cada celda declara la población y el alcance
  de la lectura (`scope`: 5 de 15 unidades y 2 de 2 solicitudes en `fixture`).
- **Un solo «ahora».** La presentación no consulta proveedores, base de datos ni
  `datetime.now`: el único instante de referencia es `HubResponse.generated_at`, y
  llega dentro del informe. `data_as_of` es el corte de la lectura de Prisma.
- **Las reglas no se duplican.** `app/services/indicators.py` y `app/models/` no se
  tocan; el tablero agrega en la capa de presentación sobre el contrato existente.
- **El color solo codifica estado.** El azul ECON queda para marca y acción. La
  única celda que puede tomar color es la decisión de paro, con el color `issue`
  de `theme.py`, un icono Tabler local y el texto «Paro declarado en Prisma»: nunca
  el color solo.

## Qué muestra cada cifra

`E` = evaluable como conteo, `M` = motivo publicado en lugar de cifra.

| KPI | Área | De dónde sale | fixture | live | Decisión que habilita |
| --- | --- | --- | --- | --- | --- |
| Aprobadas sin unidad asignada | Logística | I2, filas con `values.variant = aprobada_sin_unidad` | E | E | Asignar unidad o justificar la espera |
| Aprobadas con unidad sin tarea enviada | Logística | I3, filas con `values.sent_task = false` | M: las muestras no envían tareas | E con registro completo; «No verificable» con registro parcial | Preparar o revisar el traslado; nunca reenviar a ciegas |
| Unidades OCUPADA sin proyecto | Logística | I4, filas con `values.without_project = true` | E (0 unidades OCUPADA → «Sin casos») | E | Corregir la asignación en Prisma o liberar la unidad |
| Asignaciones vencidas al corte | Logística | I5, filas con `values.ended = true` | M: sin corte de observación | E | Confirmar prórroga, devolución o nuevo traslado |
| Solicitudes pendientes de decisión | Proyectos | I2, filas con `values.variant = pendiente`; la antigüedad de la fila más antigua sale de `values.hours` | E (la antigüedad, no) | E | Decidir la solicitud o confirmar que la necesidad sigue |
| Aprobaciones con tiempo medido | Proyectos | I1, filas evaluables; el tiempo sale de `values.seconds` | E (1 de 2 filas) | E | Acordar un plazo de aprobación con Gerencia |
| Tareas completadas sin recepción | Proyectos | I6, filas evaluables con `values.receipt_declared = false` | M: sin tareas en la muestra | E | Reclamar la constancia de recepción |
| Unidades con falla activa | Mantenimiento | I7, filas del indicador | E (0 fallas → «Sin casos») | E | Revisar el diagnóstico |
| Fallas con decisión de paro | Mantenimiento | I7, filas con `values.active_failure_is_paro = true` | E | E | No programar traslados sobre unidades con paro |
| Antigüedad de la evidencia | Información | I8, `values.evidence_age_hours` de la primera fila | M: sin lecturas ni corte del registro | E | Ejecutar el ciclo de sincronización antes de decidir |
| Unidades leídas | Información | `HubResponse.scope.equipment_returned` / `equipment_total` | E (5 de 15) | E | Saber si la cifra describe la lectura o la flota |
| Solicitudes leídas | Información | `HubResponse.scope.requests_returned` / `requests_total` | E (2 de 2) | E | Igual que la anterior, para las solicitudes |
| Registro de movimientos | Información | `WorkflowOverview.coverage` si está disponible; si no, `HubResponse.operation_evidence` | «No consultado» | Movimientos mostrados de total, con «registro parcial» cuando corresponde | Decidir si una ausencia de tarea es verificable |

## Cómo se lee una celda que no trae un número

| Texto | Significado |
| --- | --- |
| `Sin casos` | La población quedó vacía en las filas leídas. La celda cita cuáles se leyeron; no afirma nada sobre las que no. |
| `No evaluable` | El indicador publicó un motivo y no hay población que contar: falta el corte, el modo `fixture` no trae tareas o no hubo lectura del registro. |
| `No verificable` | Hay filas, pero el registro no permite confirmar una ausencia (registro parcial). Una ausencia no confirmada no es un cero. |

## Enlace a las filas que sostienen cada cifra

Bajo cada cifra, la última línea nombra el indicador que la define (`I1`…`I8` con el
nombre de su ficha) y enlaza hasta tres sujetos a su página de detalle
(`/solicitudes/{id}`, `/maquinaria/{id}`, `/operaciones/{id}`). Cuando quedan más
filas, la línea lo dice y remite a la tabla del indicador: la pestaña
correspondiente de la misma página conserva los campos de origen, la evidencia y el
motivo de cada fila. Una cifra bloqueada también enlaza su población, para que el
caso afectado sea visible aunque no se pueda medir.

## Qué falta para medir más

| Límite | Efecto en el tablero |
| --- | --- |
| `fixture` no tiene corte de observación (`data_as_of = null`) ni tareas enviadas | Cuatro celdas publican su motivo en lugar de una cifra; cambiar eso exigiría inventar un instante. |
| El reporte de falla no se lee (`GET /api/maquinaria/fallas`) | No hay antigüedad ni estado histórico de la falla: el tablero solo cuenta fallas activas y decisiones de paro. |
| No existe `rejected_at` ni historial de la solicitud | No hay celda de solicitudes decididas ni de rechazos con tiempo. |
| `GET /api/maquinaria/equipos/{id}/history` no se consulta | No se sabe desde cuándo una unidad está `OCUPADA` sin proyecto; la celda cuenta filas, no antigüedad. |
| El registro se lee por página (100 movimientos por defecto) | Con `complete=false` las ausencias quedan «No verificable»; el conteo de movimientos describe la página leída. |
| Los SLA propuestos S1–S6 siguen «a validar con ECON» | Ninguna celda compara con un umbral ni califica un resultado; los umbrales viven en la pestaña de SLA propuestos. |

Pendientes registrados y no resueltos en este cambio:

- Las alertas de `HubResponse.alerts` no tienen celda propia. Sus poblaciones se
  solapan con I2, I4 e I7 (`approved_without_equipment`, `active_failure`) y una
  celda adicional contaría dos veces las mismas filas. Las alertas se leen en la
  portada y en el [README del servicio](../apps/api/README.md#provided-samples-and-rule-limits).
- [analítica para decidir](analitica-decisiones.md) afirma que ninguna página
  «convierte conteos ni ausencias en KPI». Esa frase describe la versión anterior
  de `/indicadores` y conviene revisarla: el tablero publica conteos de filas de la
  lectura y **nunca** convierte una ausencia en cero, pero la redacción quedó fuera
  del alcance de este cambio.
- La revisión de este tablero pasó `ruff format`, `ruff check` y la importación de
  los módulos con `DATABASE_URL=sqlite://`. La suite completa no se ejecutó aquí:
  los pendientes de pruebas descritos en `CLAUDE.md` siguen vigentes.
