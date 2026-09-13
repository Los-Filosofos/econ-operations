<!-- econ-audit:2026-09-12:hub-persisted-evidence -->

La proyección live de hub asigna siempre relation_status='unlinked' y Startrack='not_configured', con texto de credenciales pendientes. No consulta el ledger, aunque el flujo de operaciones ya pueda tener tarea vinculada, llegada o constancia. Esto deja dos lecturas del mismo caso que no concuerdan y mantiene como diagnóstico fijo una condición que puede haber cambiado.

**Prioridad:** P1. **Frente sugerido:** Backend y frontend. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/services/hub.py:177](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/hub.py#L177), [apps/api/app/services/hub.py:302](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/hub.py#L302), [apps/api/app/services/hub.py:310](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/hub.py#L310) y [apps/api/app/services/workflow.py:347](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L347).

## Criterios de aceptación

- [ ] Incorporar evidencia persistida mediante un servicio de lectura compartido usando IDs exactos, modo/entorno y vigencia compatibles.
- [ ] Distinguir evidencia histórica existente de conectividad actual, credenciales ausentes y cobertura incompleta; no llamar conectada a una fuente solo por tener un snapshot.
- [ ] Hub HTTP, Fuentes, ficha de equipo y solicitudes concuerdan sobre vínculos confirmados, tarea, presencia y constancia, sin colapsar sus estados.
- [ ] Actualizar modelos y consumidores juntos; conservar varias operaciones por solicitud y no inferir ubicación actual desde una visita antigua.
- [ ] Probar movimiento persistido con tarea/recepción, proveedor caído, cambio de maquinaria y ambientes distintos, sin consultas reales.

## Relación con el backlog y alcance

Corrección del diagnóstico fijo introducido en el hub actual. La proyección durable completa y la eliminación de consultas por petición siguen cubiertas por [econ-protocol#8](https://github.com/Los-Filosofos/econ-protocol/issues/8); este issue se limita a reflejar evidencia ya guardada correctamente.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
