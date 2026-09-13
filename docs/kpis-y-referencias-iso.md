# Indicadores operativos y referencias ISO

Este documento separa las reglas de revisión existentes, los indicadores
propuestos y las referencias normativas consultadas el **12 de septiembre de
2026**. La portada vigente y sus gráficos están definidos en
[analítica de decisiones](analitica-decisiones.md). No hay KPIs globales de
productividad, ahorro o cumplimiento calculados con la muestra disponible.

## RF-06: indicador documentado

El requisito pide documentar al menos un indicador que la integración haría
visible; no exige inventar un resultado sin datos. El dossier define
[tiempo fuera de geocerca sin justificación](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado),
por equipo y período, en horas.

Su cálculo usa la unión de intervalos válidos fuera de la geocerca asignada,
dentro del horario exigible y excluyendo salidas justificadas. Requiere identidad
y vigencia del dispositivo, asignación, eventos, horario y justificaciones.
Los huecos de señal permanecen sin clasificar y se informa la cobertura.
La muestra no permite calcularlo: el resultado es **no evaluable**, no cero.

La definición completa, sus condiciones y la referencia al brief se mantienen
en el dossier para evitar fórmulas distintas entre entregables. Estar fuera de
geocerca no demuestra tiempo muerto, uso indebido ni pérdida económica.

## Qué puede mostrar la implementación

La muestra suministrada contiene cinco equipos y dos solicitudes, sin tareas,
ubicaciones ni recepciones. Es parcial y carece de un instante conjunto de
observación. La portada muestra asuntos por solicitud y períodos de uso; no
presenta tarjetas de conteos ni interpreta los períodos como compromisos de entrega.

Las siguientes reglas existen en el servicio de lectura, aunque la muestra no
aporta todas sus condiciones. Son señales para revisar registros, no KPIs globales:

| Regla existente | Evidencia y límite |
| --- | --- |
| Solicitud pendiente cuyo inicio llegó al corte | Estado, fecha válida y corte conocido; no se evalúa con el reloj actual sobre muestras documentales sin corte |
| Solicitud aprobada sin unidad | Aprobación e ID de maquinaria ausente; no confundir con una unidad que quedó fuera de la página consultada |
| Equipo con falla activa | Referencia de falla; la decisión de paro se conserva por separado |
| Paro y traslado pendiente | Paro explícito, tarea pendiente y vínculo confirmado; no se deduce de motor apagado o estado administrativo |

Un registro de operaciones no disponible no se transforma en cero movimientos.
Las incidencias de envío requieren consultar evidencia y conciliar resultados
inciertos. El backend ya conserva planes, cortes, eventos y recepción declarada;
eso no asegura una serie temporal completa ni una integración autenticada
validada con Startrack.

## Mediciones propuestas

| Medición | Cálculo propuesto | Condiciones pendientes |
| --- | --- | --- |
| Aprobadas sin unidad | Cantidad y porcentaje sobre las aprobadas del ámbito | Cobertura y catálogo validados; denominador cero significa sin casos evaluables |
| Tiempo hasta aprobación | Mediana y percentil 90 de aprobación menos creación | Horas con zona, cambios de decisión y cohorte; mostrar también las pendientes |
| Cobertura solicitud–traslado | Solicitudes con vínculo validado sobre solicitudes que requieren traslado | Definir el denominador y comprobar recurso, destino, período y cardinalidad |
| Antigüedad de posición | Corte menos instante del reporte del activo | Acceso API validado, unidad temporal, dispositivo vinculado y antigüedad aceptable |
| Puntualidad de recepción | Recepciones validadas dentro del compromiso sobre traslados evaluables cuyo compromiso vence en el período | Compromiso de entrega, recepción, política de cancelación/reprogramación y cobertura |
| Impacto del hub | Comparación del tiempo necesario para resolver una consulta operativa antes y durante un piloto | Casos comparables, muestra y condiciones registradas; sin porcentajes de ahorro supuestos |

Los plazos de uso solicitado, programación de tarea y compromiso de entrega son
datos diferentes. Una tarea completada o una visita GPS no sustituye la recepción.
Para puntualidad, los pendientes vencidos con evidencia suficiente permanecen en
la cohorte; los casos desconocidos se informan junto con la cobertura.

## Condiciones de medición y decisión

- Identificar organización, proyecto, población, unidad, fórmula, corte y fuente.
  Conservar la fecha original y usar `America/El_Salvador` para el día de negocio.
- Informar registros evaluados, excluidos y desconocidos. Una fuente caída,
  lectura parcial o falta de permisos no produce un cero global.
- Distinguir muestras del archivo y lecturas actuales del sandbox; ambos son
  sintéticos. Los casos inventados para probar reglas quedan solo en tests.
- Separar fecha del evento, observación y registro. Una sincronización reciente
  no rejuvenece la posición ni reconstruye eventos intermedios ausentes.
- Permitir llegar a los registros que sostienen la decisión. Responsables,
  umbrales y metas requieren acuerdo de las áreas, sin rankings artificiales.

La disponibilidad administrativa no acredita disponibilidad física o utilización.
Motor apagado no equivale a paro; horómetro no equivale a horas productivas.
MTTR necesita intervalos de reparación válidos y OEE requiere datos de
disponibilidad, rendimiento y calidad que no aporta esta muestra.

Los acuerdos pendientes corresponden a Logística, Proyectos y Mantenimiento:
identidad del activo observado, vigencia de correspondencias, definición de
`OBSOLETA`, restricciones, recepción y plazos exigibles. La
[matriz de equivalencias](equivalencias-prisma-startrack.md) y el
[manual de integración](manual-mapeo-integracion.md) describen el trabajo disponible;
no hace falta reconstruir el conector ni la persistencia ya implementados.

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
con el responsable de calidad. Ninguna referencia autoriza añadir login al hub,
evaluar conductores con evidencia incompleta ni atribuir a ISO una meta de 95 %,
98 % u otra cifra. La política actual mantiene credenciales en el servidor y
acceso remoto deshabilitado por defecto.
