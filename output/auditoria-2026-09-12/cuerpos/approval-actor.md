<!-- econ-audit:2026-09-12:approval-actor -->

NexusRequest conserva approved_by_user_id del contrato suministrado, pero RequestRecord no lo declara y _map_live lo descarta. El ledger guarda la solicitud ya proyectada, de modo que pierde al actor de aprobación aunque conserve approved_at. La muestra aprobada permite reproducir la pérdida sin conectar proveedores.

**Prioridad:** P2. **Frente sugerido:** Backend y contratos. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/integrations/nexus.py:60](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/integrations/nexus.py#L60), [apps/api/app/models/hub.py:74](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/models/hub.py#L74), [apps/api/app/services/hub.py:144](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/hub.py#L144), [apps/api/app/integrations/fixtures.py:35](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/integrations/fixtures.py#L35) y [apps/api/app/services/ledger.py:234](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/ledger.py#L234).

## Criterios de aceptación

- [ ] Preservar el ID original del aprobador en la proyección y el snapshot, con nulabilidad explícita y fuente.
- [ ] Alinear Pydantic, lector fixture/live, serialización, documentación generada y consumidores Dash; no inferir nombre ni autoridad del receptor desde este ID.
- [ ] Mostrar el dato en evidencia técnica cuando corresponda, manteniendo el resumen gerencial simple.
- [ ] Prueba de round-trip desde ejemplo OpenAPI/adaptador hasta snapshot recuperado; ausencia permanece null.

## Relación con el backlog y alcance

Pérdida concreta de trazabilidad dentro del contrato existente, relacionada con [econ-protocol#1](https://github.com/Los-Filosofos/econ-protocol/issues/1) y [econ-protocol#6](https://github.com/Los-Filosofos/econ-protocol/issues/6).

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
