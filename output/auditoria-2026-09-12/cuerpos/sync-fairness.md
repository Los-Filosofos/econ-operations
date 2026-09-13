<!-- econ-audit:2026-09-12:sync-fairness -->

El worker usa dos veces `ledger.list("live")`, cuya selección devuelve como máximo 100 movimientos por creación descendente. Al existir 100 registros posteriores, una operación antigua queda fuera de revalidación y seguimiento en todos los ciclos. Aumentar el límite solo desplaza el problema. La reclamación de envíos tiene su propia selección; este hallazgo se refiere a revalidación y observación.

**Prioridad:** P1. **Frente sugerido:** Backend e integraciones. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/services/ledger.py:185](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/ledger.py#L185) y [apps/api/app/services/workflow.py:440](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L440) / [apps/api/app/services/workflow.py:462](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L462). Reproducción estructural: guardar más de 100 movimientos, dejar uno antiguo pendiente de seguimiento y ejecutar varios ciclos; la misma página reciente vuelve a seleccionarse.

## Criterios de aceptación

- [ ] Seleccionar trabajo por próxima revisión/estado con progreso durable y orden estable; mantener un presupuesto acotado por ciclo.
- [ ] Un movimiento antiguo elegible vuelve a revisarse dentro de un número acotado de ciclos aunque se creen movimientos nuevos.
- [ ] Persistir el progreso entre reinicios y evitar hidratación de todo el historial para seleccionar el trabajo.
- [ ] Exponer paginación, total y cobertura de la lista de operaciones; no presentar 100 registros como población completa.
- [ ] Prueba aislada con más de 100 movimientos, nuevas inserciones y reinicio, preservando la reclamación segura y los modos fixture/live.

## Relación con el backlog y alcance

Corrección concreta sobre el worker implementado; desarrolla la garantía de recuperación de [econ-protocol#7](https://github.com/Los-Filosofos/econ-protocol/issues/7), sin recrear el sincronizador.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
