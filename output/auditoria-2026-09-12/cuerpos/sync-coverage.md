<!-- econ-audit:2026-09-12:sync-coverage -->

Las visitas se consultan solo desde max(fecha_programada, hoy−6 días), sin cursor de recuperación. Una interrupción superior a siete días deja evidencia antigua fuera del seguimiento automático. Además, last_sync_at sale del snapshot Prisma guardado antes de consultar Startrack: un fallo posterior queda solo en el mensaje del ciclo y desaparece al recargar.

**Prioridad:** P1. **Frente sugerido:** Integraciones y backend. Asignación personal pendiente de reparto del equipo.

## Evidencia

[apps/api/app/services/workflow.py:125](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L125), [apps/api/app/services/workflow.py:380](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L380), [apps/api/app/services/workflow.py:430](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L430) y [apps/api/app/services/workflow.py:473](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/apps/api/app/services/workflow.py#L473).

## Criterios de aceptación

- [ ] Persistir intento, último éxito, ventana cubierta, progreso, completitud y error saneado por fuente y movimiento.
- [ ] Recuperar ventanas omitidas según límites y retención soportados por el proveedor; marcar explícitamente los huecos irrecuperables.
- [ ] No avanzar el cursor de éxito si falló o quedó parcial la ventana; deduplicar solapamientos.
- [ ] Mostrar al recargar que Prisma respondió y Startrack falló, conservando la evidencia anterior con su fecha.
- [ ] Probar caída superior a siete días, respuesta parcial, reinicio y error seguido de recarga; respetar el límite de visitas de 10 peticiones por IP cada cinco minutos.

## Relación con el backlog y alcance

Corrección focal del worker actual sobre [econ-protocol#7](https://github.com/Los-Filosofos/econ-protocol/issues/7). Límite oficial: [visitas a geocercas](https://support.gps-platform.com/api/reports/poi-visits/).

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
