<!-- econ-audit:2026-09-12:event-ordering -->

La consulta del último evento ordena por `event_time DESC, observed_at DESC`, pero la comparación posterior usa `event_time or observed_at`. Son órdenes incompatibles cuando falta la fecha del hecho. Reproducción confirmada con el ledger real en SQLite en memoria: evento 18:00 → A; evento sin event_time observado 20:00 → B; evento tardío 19:00 → C. El estado termina en C después de haber promovido B usando las 20:00. Además, lectura y actualización de la proyección no usan control de versión/bloqueo por entidad.

**Prioridad:** P1. **Frente sugerido:** Backend y datos. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/services/ledger.py:647](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/ledger.py#L647) y [apps/api/tests/test_ledger.py:359](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/tests/test_ledger.py#L359). La prueba existente cubre fechas conocidas en secuencia. La reproducción se ejecutó en SQLite; no se presenta como prueba PostgreSQL.

## Criterios de aceptación

- [ ] Documentar una política única para fecha del hecho desconocida, empates, versiones de fuente y eventos tardíos; no afirmar actualidad desde una fecha de lectura.
- [ ] Conservar los eventos tardíos en el historial y aplicar la misma política al seleccionar y actualizar la proyección.
- [ ] Aplicar por entidad con bloqueo o actualización condicional/versionada dentro de una transacción.
- [ ] Probar secuencias mezcladas con fecha nula, empates y dos escritores; ejecutar las garantías de orden e integridad en PostgreSQL aislado además de SQLite.
- [ ] Mantener deduplicación de evidencia y evitar que replay provoque envíos remotos.

## Relación con el backlog y alcance

Defecto específico de la implementación actual, relacionado con [econ-protocol#7](https://github.com/Los-Filosofos/econ-protocol/issues/7). No exige event sourcing completo.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
