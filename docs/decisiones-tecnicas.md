# Decisiones técnicas para la entrega

13 de septiembre de 2026. Este resumen se exporta a un PDF independiente de
**dos páginas**. Describe el prototipo actual y separa las ampliaciones propuestas.

## Página 1: alcance y correspondencias

El prototipo conserva Prisma como origen de proyectos, solicitudes y asignaciones;
Startrack como origen de tareas y seguimiento; y ECON como registro del traslado,
sus correspondencias y evidencia. El caso usa exclusivamente datos sintéticos.

| Decisión | Aplicación |
| --- | --- |
| Identidad por fuente | Preservar UUID de Prisma e IDs de Startrack, cuenta/entorno y fechas. No unir por nombre, matrícula no validada o motorista. |
| Cardinalidad explícita | Un proyecto contiene solicitudes; una solicitud puede necesitar varios movimientos. Cada movimiento conserva su referencia y el ID de tarea confirmado. |
| Mapeo selectivo | Unidad/proyecto/solicitud conservan identidad; título y descripción se derivan; geocerca, usuarios y programación requieren correspondencias revisadas. |
| Estados separados | Estado administrativo, mantenimiento, tarea, ubicación y recepción describen hechos distintos. Ocupada y Completada pueden coexistir. |
| Campos fuera del envío actual | No se inventan equivalencias para origen, plazo de entrega, ventana horaria, artículos ni restricción de completar dentro de geocerca. La matriz completa distingue contrato y soporte del hub. |
| Tecnología vigente | Dash, Plotly, AG Grid Community y FastAPI en Python; SQLModel/Alembic y PostgreSQL como única infraestructura de estado (cola, bloqueos, historial append-only; ADR 0006), sin Redis ni firmas. |

La muestra suministrada contiene cinco equipos de un total declarado de quince y
dos solicitudes. Ambas solicitudes pertenecen a PROY-014; una está aprobada con
CF-03 y otra pendiente sin unidad. No contiene tareas, posiciones ni recepciones
para vincular. La asignación RE-03/MOT-006/PROY-006 del equipo no se sustituye por
esos ejemplos.

RF-04 y RF-05 requieren una demostración combinada defendible. La interfaz y las
reglas existen, pero no acreditan por sí mismas la consulta de una tarea y un GPS
vinculados al caso. La ausencia de esa evidencia se presenta explícitamente.

Referencias: [matriz de equivalencias](equivalencias-prisma-startrack.md),
[muestra original](../apps/api/app/integrations/data/sandbox_samples.json) y
[brief](onedrive/02-brief-del-reto.md).

## Página 2: ejecución, errores y evolución

La creación de proyecto no dispara por sí sola una tarea. Primero se comprueba
solicitud aprobada, unidad asignada y datos del movimiento. Guardar el plan local
y enviarlo son pasos diferentes. El trabajador revalida y reclama cada envío en
una transacción; una respuesta incierta se concilia por lectura sin repetir
automáticamente el POST. Llegada observada y recepción declarada se conservan
separadas.

La ejecución periódica actual es explícita mediante CLI. No hay un receptor de
webhook de aprobaciones Prisma ni cambios de tarea Startrack confirmado. Se
mantienen consultas acotadas, credenciales en servidor y habilitaciones remotas
desactivadas por defecto. La aceptación autenticada del contrato de creación
Startrack en esta cuenta sigue pendiente.

| Límite | Tratamiento y ampliación |
| --- | --- |
| Fuente incompleta o caída | Mostrar cobertura y último dato conocido; no sustituir datos live por muestras ni ausencia por cero. |
| Cambio después del envío | Proponer comparación del origen con la versión enviada, incidencia y revisión; no modificar proveedores ciegamente. |
| Volumen masivo | Propuesta de recepción desacoplada, Kafka, trabajadores paralelos e histórico analítico separado. No está desplegada ni tiene capacidad demostrada. |
| Tiempo muerto | Requiere jornada, intervalos y causas confirmadas, mantenimiento y señal adecuada al tipo de equipo. Velocidad cero no acredita inactividad. |
| Responsabilidades | RACI propuesta para Mantenimiento, Logística y Técnica de Proyectos. Roles y permisos de sesión implementados (ADR 0005); el actor autenticado queda vinculado a planes, cola y recepción desde la migración 0004; la RACI empresarial sigue pendiente de validación. |

La validación funcional se ejecuta con `scripts/check.sh` o `scripts/check.ps1`
(Ruff, formato, pytest y contenedor). Esta entrega visual verifica fuentes,
cálculos y documentos; no equivale a pruebas de carga ni a validación de proveedores. Para escalar se
deben medir eventos/segundo, retraso, recuperación y consultas concurrentes con
generadores aislados y contratos de entrega acordados.

El indicador RF-06 se documenta como propuesta medible: tiempo fuera de geocerca
sin justificación, con identidad, intervalos válidos y cobertura explícita. Su
valor no se calcula con la muestra actual. No se afirman ahorros, cumplimiento
ISO ni resultados de producción.

Referencias: [guía implementada](solucion-integracion.md),
[sincronización y escala propuestas](sincronizacion-y-discrepancias.md).
