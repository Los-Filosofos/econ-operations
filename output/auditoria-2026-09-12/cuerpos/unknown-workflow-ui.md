<!-- econ-audit:2026-09-12:unknown-workflow-ui -->

En Solicitudes, matching_current_movements devuelve [] si workflow no está disponible; la tabla convierte ese resultado en “Sin traslado vinculado” y “Sin constancia”. Si falla PostgreSQL mientras Prisma responde, desconocimiento de evidencia se presenta como ausencia de traslado/recepción.

**Prioridad:** P1. **Frente sugerido:** Frontend. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/dashboard/decision_analytics.py:44](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/decision_analytics.py#L44) y [apps/api/app/dashboard/views.py:266](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/views.py#L266) / [apps/api/app/dashboard/views.py:286](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/views.py#L286) / [apps/api/app/dashboard/views.py:301](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/views.py#L301).

## Criterios de aceptación

- [ ] Distinguir registro consultado sin evidencia, registro no disponible y evidencia parcial/desactualizada.
- [ ] Con Prisma válido y workflow no disponible, las celdas afectadas indican registro no disponible/sin confirmar; no concluyen ausencia.
- [ ] Conservar estados originales, etiquetas accesibles y el diseño sobrio; no depender solo del color.
- [ ] Probar caída de workflow y recuperación con tarea/constancia existentes, incluyendo lista y detalle sin regresión de recepción explícita.

## Relación con el backlog y alcance

Regresión semántica específica de la tabla actual, relacionada con los escenarios de aceptación de [econ-protocol#14](https://github.com/Los-Filosofos/econ-protocol/issues/14).

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
