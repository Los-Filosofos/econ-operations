<!-- econ-audit:2026-09-12:rf04-rf05-demo -->

Los ejemplos de ejecución contienen cinco equipos y dos solicitudes de Prisma, sin tareas ni posiciones Startrack. La implementación y sus pruebas controladas no demuestran todavía estado/ubicación unificados ni comparación explicada de estados de ambas fuentes. El brief permite una exportación autorizada; no exige obligatoriamente API live.

**Prioridad:** P1. **Frente sugerido:** Integraciones y aceptación. Asignación personal pendiente de reparto del equipo.

## Evidencia

[docs/onedrive/02-brief-del-reto.md:217](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/02-brief-del-reto.md#L217), [docs/onedrive/02-brief-del-reto.md:258](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/02-brief-del-reto.md#L258), [docs/onedrive/02-brief-del-reto.md:457](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/02-brief-del-reto.md#L457) y [apps/api/app/integrations/fixtures.py:16](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/integrations/fixtures.py#L16). RF-04/05 permanecen abiertos en la matriz local de requisitos.

## Criterios de aceptación

- [ ] Conseguir evidencia proporcionada/exportada o consultada del sandbox de ambas fuentes con IDs, entorno, fechas y alcance explícitos; identificar toda la operación como sintética.
- [ ] Validar correspondencias de solicitud, unidad, proyecto, tarea y activo rastreado; RE-03/MOT-006/PROY-006 conserva su identidad y no hereda CF-03/MOT-014.
- [ ] Permitir seleccionar registros del alcance declarado y mostrar estados originales y ubicación legible fechada, separando máquina y transportador.
- [ ] Demostrar al menos un caso de estados diferentes y explicar si es compatible o requiere revisión; geocerca y tarea completada no acreditan recepción.
- [ ] Entregar un guion reproducible con evidencia de ejecución y límites. No agregar tareas/posiciones fabricadas al dataset para aparentar integración.
- [ ] Si el acceso API sigue pendiente, distinguir la demostración con exportación de la validación autenticada del SDK y mantener esta última abierta.

## Relación con el backlog y alcance

Entregable RF específico apoyado en [econ-protocol#8](https://github.com/Los-Filosofos/econ-protocol/issues/8), [econ-protocol#10](https://github.com/Los-Filosofos/econ-protocol/issues/10) y [econ-protocol#14](https://github.com/Los-Filosofos/econ-protocol/issues/14); no duplica el trabajo de crear un SDK ni la solicitud de credenciales de [econ-protocol#2](https://github.com/Los-Filosofos/econ-protocol/issues/2).

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
