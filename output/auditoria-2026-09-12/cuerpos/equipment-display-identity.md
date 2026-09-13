<!-- econ-audit:2026-09-12:equipment-display-identity -->

La etiqueta usa code or asset_number or name. En los ejemplos realmente suministrados, CF-01 tiene clave='-' y no_activo='CF-01', por lo que su etiqueta pasa a '-'. CF-02 muestra '200' en vez de su número de activo. La misma selección puede trasladarse al objetivo propuesto para Startrack. Los IDs canónicos permanecen correctos, pero la persona recibe una identificación poco útil o inconsistente.

**Prioridad:** P2. **Frente sugerido:** Frontend y contratos. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/dashboard/analytics.py:30](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/analytics.py#L30), [apps/api/app/services/transfers.py:142](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/transfers.py#L142) y [apps/api/app/dashboard/workflow_views.py:331](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/dashboard/workflow_views.py#L331). Comprobado en las muestras de `sandbox_samples.json`.

## Criterios de aceptación

- [ ] Definir una política de etiqueta común basada en el número de activo disponible, con fallback legible; conservar clave y no_activo como campos distintos.
- [ ] CF-01 se reconoce como CF-01 y nunca solo como '-'; mostrar por separado cualquier clave adicional relevante.
- [ ] Aplicar la política a tablas, detalles y borrador de objetivo de traslado sin cambiar UUIDs, payloads ya enviados ni correspondencias.
- [ ] Verificar ejemplos proporcionados, clave nula, activo ausente y valores no vacíos válidos.

## Relación con el backlog y alcance

Corrección puntual de presentación e identificación; conserva las reglas de identidad del mapa de [econ-protocol#1](https://github.com/Los-Filosofos/econ-protocol/issues/1).

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
