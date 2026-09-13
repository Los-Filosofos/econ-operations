# Indicadores operativos y referencias ISO

Este documento fija dónde vive cada definición de indicador y conserva las
referencias normativas consultadas el **12 de septiembre de 2026**. No repite
fórmulas: las fichas, los SLA y los límites de agregación tienen una única
fuente. No hay KPIs globales de productividad, ahorro o cumplimiento calculados
con la muestra disponible (cinco equipos y dos solicitudes, sin tareas,
ubicaciones ni recepciones).

## Dónde vive cada definición

| Qué | Fuente única | Qué contiene |
| --- | --- | --- |
| RF-06: tiempo fuera de geocerca sin justificación | [entregables visuales](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado) | Unidad (horas por equipo y período), cálculo por unión de intervalos, datos necesarios, decisión y resultado **no evaluable** con la muestra, no cero |
| Indicadores I1 a I8 de `GET /api/v1/indicators` y de la página `/indicadores` | [indicadores calculables](indicadores-calculables.md#fichas-de-los-indicadores-publicados) | Pregunta, grano, población, fórmula con los campos exactos del contrato, exclusiones, desconocidos, fechas, unidad y estado evaluable, parcial o no evaluable; por fila, sin promedios |
| SLA propuestos S1 a S6 (aprobación, asignación, envío de tarea, recepción, atención de falla con paro, frescura de evidencia) | [fichas de SLA](indicadores-calculables.md#fichas-de-sla-propuestas-no-implementadas) | Fórmula por campo, unidad, umbral sugerido «a validar con ECON», cobertura hoy, cuándo no es evaluable y decisión que habilita |
| Qué impide agregar y qué lecturas no implementadas habilitarían más | [indicadores calculables](indicadores-calculables.md#qué-impide-agregar-hoy) | Cohorte pequeña, `rejected_at` inexistente, sin instantes por transición de falla, sin corte conjunto en fixture; rutas `history`, `actividad`, `fallas`, `usage-trend` con sus campos |
| Requisitos antes de publicar una medición nueva | [contexto vigente](contexto-vigente.md#límites-de-los-datos) | Pregunta y decisión, grano, IDs y vigencia, población y denominador, fechas con zona, estado, enlace a los registros |
| Reglas de revisión de la lectura (`alerts` del hub) | [README del servicio](../apps/api/README.md#provided-samples-and-rule-limits) | Falla activa, paro con tarea pendiente confirmada, solicitud pendiente cuyo inicio llegó al corte, aprobada sin unidad; las que dependen de fecha exigen corte conocido |

Un registro de operaciones no disponible no se transforma en cero movimientos.
Una tarea completada o una visita GPS no sustituye la recepción. La
disponibilidad administrativa no acredita disponibilidad física ni utilización:
motor apagado no equivale a paro y horómetro no equivale a horas productivas.
MTTR necesita intervalos de reparación válidos y OEE requiere datos de
disponibilidad, rendimiento y calidad que ninguna lectura actual aporta. Los
acuerdos pendientes corresponden a Logística, Proyectos y Mantenimiento:
identidad del activo observado, vigencia de correspondencias, definición de
`OBSOLETA`, restricciones, recepción y plazos exigibles.

## Referencias ISO de la revisión del 12/09/2026

La investigación anterior consultó fichas públicas oficiales, no el texto
completo de normas ni una auditoría de ECON. Se conservan como referencias
documentales de aquella revisión, sin afirmar que sus ediciones sean hoy las
vigentes. No son exigencias del brief, metas aprobadas ni certificaciones
acreditadas de ECON.

| Referencia registrada | Tema usado como orientación en la revisión |
| --- | --- |
| [ISO 9001:2015](https://www.iso.org/standard/62085.html) | Procesos, requisitos del servicio y revisión de resultados |
| [ISO 55001:2024](https://www.iso.org/standard/83054.html) | Identidad, desempeño, riesgo y costo de los activos |
| [ISO/IEC 27001:2022](https://www.iso.org/standard/27001) | Confidencialidad, integridad y disponibilidad de información |
| [ISO 39001:2012](https://www.iso.org/standard/44958.html) | Riesgos y controles de seguridad vial |

Esas aplicaciones son interpretaciones de diseño, no una lista literal de
requisitos. Una evaluación formal debe confirmar la edición, enmiendas y alcance
con el responsable de calidad. Ninguna referencia autoriza evaluar conductores
con evidencia incompleta ni atribuir a ISO una meta de 95 %, 98 % u otra cifra.
La política actual mantiene credenciales en el servidor y acceso remoto
deshabilitado por defecto.
