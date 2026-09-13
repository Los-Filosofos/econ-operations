# Backlog de la auditoría del 12 de septiembre de 2026

Issues abiertos en [Los-Filosofos/econ-operations](https://github.com/Los-Filosofos/econ-operations/issues)
a partir de la auditoría de requisitos y arquitectura de eventos. Los cuerpos
publicados están en `cuerpos/`; el registro de creación con URLs en
[issues-creados.json](issues-creados.json). Las prioridades son de ejecución
propuesta, no incidentes de producción.

| Issue | Prioridad | Trabajo | Estado |
| --- | --- | --- | --- |
| [#1](https://github.com/Los-Filosofos/econ-operations/issues/1) | P1 | Selección durable del worker fuera de los 100 movimientos más recientes | Cerrado: `next_review_at` y migración `0002` |
| [#2](https://github.com/Los-Filosofos/econ-operations/issues/2) | P1 | Orden temporal determinista y actualización atómica de observaciones | Abierto |
| [#3](https://github.com/Los-Filosofos/econ-operations/issues/3) | P1 | Detectar cambios de Prisma posteriores al envío y conservar discrepancias | Abierto |
| [#4](https://github.com/Los-Filosofos/econ-operations/issues/4) | P1 | Persistir cobertura por fuente y recuperar ventanas de visitas omitidas | Abierto |
| [#5](https://github.com/Los-Filosofos/econ-operations/issues/5) | P1 | Bandeja durable de eventos con deduplicación, procesamiento y replay | Abierto |
| [#6](https://github.com/Los-Filosofos/econ-operations/issues/6) | P1 | Mostrar evidencia desconocida cuando el registro no está disponible | Abierto; la UI ya distingue desconocido, fallido, parcial y vacío |
| [#7](https://github.com/Los-Filosofos/econ-operations/issues/7) | P2 | Identificación legible y consistente de maquinaria sin perder clave ni activo | Abierto |
| [#8](https://github.com/Los-Filosofos/econ-operations/issues/8) | P2 | Conservar `approved_by_user_id` en contrato y snapshots | Cerrado |
| [#9](https://github.com/Los-Filosofos/econ-operations/issues/9) | P1 | RF-02: correspondencia explícita de las 51 definiciones del diccionario | Abierto |
| [#10](https://github.com/Los-Filosofos/econ-operations/issues/10) | P1 | RF-04/RF-05 con evidencia vinculada de Prisma y Startrack | Abierto |
| [#11](https://github.com/Los-Filosofos/econ-operations/issues/11) | P1 | Presentación final de hasta diez diapositivas | Abierto |
| [#12](https://github.com/Los-Filosofos/econ-operations/issues/12) | P2 | Reproducir los tres PDFs desde sus fuentes editables | Abierto |
| [#13](https://github.com/Los-Filosofos/econ-operations/issues/13) | P1 | Reflejar en el hub los vínculos y la evidencia que conserva el worker | Abierto; `services/evidence.py` proyecta ya la evidencia persistida |

Orden sugerido: #2 y #4 (corrección); #3 y #13 (trazabilidad; #7 independiente);
#5 (eventos, reutiliza #2/#4); #9, #12, #10 y #11 (cierre del reto). Los
antecedentes de `econ-protocol` (#2, #7, #8, #10, #14) siguen siendo referencia;
sus issues sobre login, React y cards requieren triage frente a las decisiones
actuales del [contexto vigente](../../docs/contexto-vigente.md).
