<!-- econ-audit:2026-09-12:dictionary-51-mapping -->

La matriz actual cubre ampliamente el formulario y los contratos, pero no resuelve individualmente todas las definiciones priorizadas del libro: por ejemplo Color, Proveedor, Mecanico y las dos filas Anadir tipo de servicio. El anexo transcribe las definiciones; transcripción no equivale a mapeo. La matriz local de requisitos reconoce RF-02 como parcial.

**Prioridad:** P1. **Frente sugerido:** Integraciones y documentación. Asignación personal pendiente de reparto del equipo.

## Evidencia

[docs/onedrive/02-brief-del-reto.md:182](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/02-brief-del-reto.md#L182) / [docs/onedrive/02-brief-del-reto.md:215](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/02-brief-del-reto.md#L215), [docs/onedrive/06-diccionario-de-datos/02-prisma.md:28](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/06-diccionario-de-datos/02-prisma.md#L28), [docs/onedrive/06-diccionario-de-datos/03-startrack.md:28](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/onedrive/06-diccionario-de-datos/03-startrack.md#L28) y [docs/equivalencias-prisma-startrack.md:216](https://github.com/Los-Filosofos/econ-operations/blob/e851c7ec01890eda54d736d4d9eeaa161a8a8fce/docs/equivalencias-prisma-startrack.md#L216). `docs/matriz-requisitos-entregables.md` es evidencia local aún no versionada al corte de auditoría.

## Criterios de aceptación

- [ ] Inventariar 51 referencias de origen (12 Prisma y 39 Startrack), preservando por separado las filas duplicadas 44/45.
- [ ] Para cada fila indicar destino o ausencia explícita, transformación/cardinalidad, motivo de exclusión, evidencia contractual y estado de validación.
- [ ] No inventar endpoints de mantenimiento ni convertir coordenadas sin escala validada.
- [ ] Comprobar automáticamente cobertura por referencias de origen sin omisiones y conservar tabla editable con PDF legible.
- [ ] Actualizar la declaración de cobertura RF-02 al terminar; conservar el RACI y RF-06 ya documentados.

## Relación con el backlog y alcance

Entrega residual concreta de [econ-protocol#1](https://github.com/Los-Filosofos/econ-protocol/issues/1); no rehace el mapa ni solicita otra RACI.

Auditoría del árbol de trabajo de `feat/operations-hub-foundation`, base `e851c7ec01890eda54d736d4d9eeaa161a8a8fce`, con tres agentes Astra. La auditoría general pasó Ruff, formato, 308 pruebas e imagen Docker; esto no acredita validación de estas brechas ni conectividad de proveedores. La creación de este issue registra trabajo pendiente y no ejecuta cambios remotos.
