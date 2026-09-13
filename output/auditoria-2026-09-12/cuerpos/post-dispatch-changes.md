<!-- econ-audit:2026-09-12:post-dispatch-changes -->

Los planes draft/blocked se revalidan y el envío comprueba el origen, pero los movimientos sent/unknown no vuelven a comparar la solicitud de Prisma con la versión usada al preparar la tarea. Una reasignación, cancelación o cambio de proyecto/período puede dejar un traslado vigente incompatible sin una incidencia persistida.

**Prioridad:** P1. **Frente sugerido:** Integraciones y negocio. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/services/workflow.py:441](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L441) y [apps/api/app/services/workflow.py:347](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L347). La ampliación ya está descrita como propuesta local en `docs/sincronizacion-y-discrepancias.md`, no implementada.

## Criterios de aceptación

- [ ] Consultar por ID exacto los movimientos afectados y comparar unidad, proyecto, período, estado de solicitud y otros campos cuya responsabilidad haya sido acordada.
- [ ] Preservar la versión enviada y cada cambio posterior con fuente, entorno, fechas y evidencia.
- [ ] Crear una incidencia estable por regla/ocurrencia, con responsable funcional, siguiente acción, estado y resolución auditables; repetir el evento no crea otra incidencia.
- [ ] Tratar falta de datos como no evaluable; no resolver incidencias por desaparición de una página parcial.
- [ ] Probar reasignación, cancelación, evento repetido y fuente caída. Ningún caso modifica Prisma, cancela tareas o crea un segundo traslado automáticamente.

## Relación con el backlog y alcance

La sincronización histórica de [econ-protocol#7](https://github.com/Los-Filosofos/econ-protocol/issues/7) no incluía esta gestión de discrepancias posterior al envío. Complementa el flujo persistente actual.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
