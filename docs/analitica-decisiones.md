# Analítica para decidir sobre la operación

Revisión del **12 de septiembre de 2026**. Esta guía reemplaza el enfoque de la vista general como inventario de widgets. Define qué comunica cada elemento a Gerencia de Logística y Equipos, Mantenimiento y Técnica de Proyectos. Separa el problema empresarial de la evidencia disponible en el prototipo.

## Qué necesita ECON

El [brief, secciones 5–7](onedrive/02-brief-del-reto.md#5-el-reto), describe coordinación manual entre plataformas: conocer el equipo, su disponibilidad y el cumplimiento de lo planificado. Los [casos de uso](onedrive/04-casos-de-uso.md) concretan tres necesidades: consultar una operación completa, interpretar estados de objetos distintos y detectar un traslado afectado por mantenimiento. Los diagramas [AS-IS](onedrive/03-as-is.md) y [TO-BE](onedrive/03-to-be.md) muestran que la decisión requiere coordinación entre áreas.

La pregunta principal del panel es **qué necesita intervención y con qué evidencia**. Después aporta contexto para planificar: cómo se distribuyen los estados consultados y en qué fechas se requiere maquinaria. El estado administrativo disponible no confirma que un equipo sea apto para una asignación particular: faltan tipo requerido, condición mecánica, ubicación y compromisos vigentes.

El objetivo empresarial es real. La demostración local contiene **tres equipos y tres solicitudes inventados**, identificados como ejemplos. La lectura del sandbox tiene su propio ámbito y cobertura; ninguno de esos conjuntos representa automáticamente la flota completa de ECON. No se agregaron registros para que los gráficos parezcan más convincentes.

## Qué mediciones pueden sostenerse

| Pregunta de decisión | Unidad y cálculo defendible | Límite |
| --- | --- | --- |
| ¿Qué solicitudes requieren revisión por su fecha? | Solicitudes pendientes cuyo inicio previsto es anterior o igual al corte local, identificadas por la regla de la API | No acredita incumplimiento de entrega ni tiempo de espera desde creación |
| ¿Qué asignaciones necesitan revisión? | Solicitudes aprobadas sin identificador de maquinaria | No confundir con unidades fuera de una página de resultados |
| ¿Qué equipos necesitan atención mecánica? | Equipos distintos con referencia de falla activa; decisión de paro separada | Un registro de falla no prueba indisponibilidad física |
| ¿Dónde coinciden restricciones y un traslado pendiente? | Evidencia de paro, tarea pendiente y relación confirmada, conservando los IDs afectados | Las categorías reales de Startrack deben validarse antes de ampliar las reglas |
| ¿Cuántos asuntos requieren intervención? | Agrupación de alertas por ID de equipo y, en su ausencia, por solicitud o alerta | Tres alertas del mismo equipo no son tres equipos distintos. La agrupación conserva cada motivo y responsable |

Los indicadores usan la población devuelta por la consulta y su búsqueda activa. Una fuente no disponible significa **sin datos para evaluar**. Una consulta válida sin registros es un conjunto vacío. La cobertura parcial nunca se presenta como censo de la flota, ni la ausencia de alertas como garantía de ausencia de riesgo.

Las cohortes de solicitudes se seleccionan por los códigos de alerta y `request_id` de la API. El frontend no debe duplicar la regla de elegibilidad con un segundo catálogo de estados o una interpretación distinta de las fechas.

### Derivaciones locales y unidades

Estas derivaciones pertenecen a la presentación Python; no amplían el contrato HTTP `1.0` ni crean nuevos campos en los proveedores.

| Salida | Tipo y ejemplo local | Procedencia |
| --- | --- | --- |
| Solicitudes por atender | Entero o `null`; `1` solicitud | IDs de solicitudes de la alerta `pending_request_started` dentro de la respuesta |
| Aprobadas sin unidad | Entero o `null`; `1` solicitud | IDs de solicitudes de `approved_without_equipment` |
| Equipos con falla activa | Entero o `null`; `1` equipo | `summary.active_failures`, con disponibilidad de la fuente |
| Distribución: `status`, `count` | Texto y entero; `OCUPADA`, `1` equipo | Conteo de registros de maquinaria por estado administrativo |
| Calendario: fecha y conteo en `days` | Fecha y entero; `2026-09-11`, `1` solicitud | Fecha prevista de las solicitudes recibidas, dentro de la ventana declarada |
| Calendario: `undated`, `outside` | Enteros; `0`, `0` | Registros sin fecha válida y registros fechados fuera de la ventana |
| Grupo: `key`, `severity`, `alerts`, `owners` | Clave con tipo e ID, prioridad máxima y listas de evidencia/responsables | Alertas de la API agrupadas por identidad; sin asignar una responsabilidad nueva |

Con los ejemplos locales actuales, cada indicador principal vale `1`. Los tres estados tienen un equipo cada uno. Las fechas 10, 11 y 13 de septiembre tienen una solicitud cada una. Cuatro alertas forman **dos asuntos**: EX-02 conserva tres señales; la solicitud aprobada sin unidad conserva la restante. Son expectativas para verificar la implementación, no conclusiones sobre la operación real de ECON.

## Elección de gráficos

| Visual | Qué comunica | Criterio analítico |
| --- | --- | --- |
| Barras horizontales por estado administrativo | Comparación de cantidades entre categorías del inventario consultado | Longitud desde cero, cantidades enteras y categorías textuales. No es utilización, disponibilidad técnica ni una distribución de tiempos |
| Columnas por fecha de inicio prevista | Concentración de solicitudes según la fecha en que se pide maquinaria | Eje temporal ordenado, intervalos equivalentes y conteos de solicitudes. No son salidas, llegadas ni una tendencia histórica del desempeño |
| Tabla de asuntos para revisar | Equipo o solicitud, condición que requiere atención, responsables propuestos y acceso a evidencia | Permite decidir y profundizar sin repetir las tablas completas de inventario, solicitudes y traslados en la portada |

Las [guías de ONS para columnas](https://service-manual.ons.gov.uk/data-visualisation/chart-types/column-chart) distinguen períodos temporales de categorías, para las que prefieren barras horizontales. Sus [guías de ejes](https://service-manual.ons.gov.uk/data-visualisation/guidance/axes-and-gridlines) orientan la dirección temporal y el tratamiento de categorías. Se usa una escala común desde cero, sin ejes dobles, perspectiva, degradados ni áreas que exageren diferencias.

Una fecha prevista es una propiedad del registro actual. Agrupar esas fechas no reconstruye cómo cambió el estado de la operación en días anteriores. La guía de [líneas de ONS](https://service-manual.ons.gov.uk/data-visualisation/chart-types/line-chart) reserva las líneas para tendencias y recomienda considerar columnas con pocos puntos. En este caso no hay un historial persistido que justifique una línea de evolución de disponibilidad, atrasos o productividad.

Las fechas sin hora mantienen su día calendario. Los instantes con zona se convierten a **America/El_Salvador**. Fechas inexistentes, ambiguas o ausentes se contabilizan aparte; no se interpretan silenciosamente según la zona del navegador. Las observaciones excluidas de una ventana temporal deben permanecer contabilizadas. El período del gráfico describe planificación, no el período en que se obtuvieron los registros.

La ventana inicial abarca **14 días: seis anteriores al corte, el día del corte y siete posteriores**. El marcador se denomina «Corte», porque una copia fechada no equivale a hoy. Cada columna cuenta solicitudes devueltas con ese inicio previsto, de cualquier estado. Un cero significa que no se recibió una solicitud para ese día; no demuestra ausencia de demanda en la empresa. Los registros fuera de la ventana y sin fecha válida se informan por separado.

## Presentación y componentes

La portada conserva una jerarquía corta: contexto de lectura, indicadores accionables, gráficos y asuntos por revisar. La navegación y la búsqueda permiten llegar al registro. La procedencia completa, las definiciones y los accesos a plataformas viven en sus vistas correspondientes.

Se eliminan badges, numeración decorativa, grupos de iconos, tarjetas anidadas, avisos duplicados y el pie dedicado a la asignación del equipo participante. Los estados se leen como texto. Se usa Inter para lectura, títulos y datos; el azul identifica acciones y series, y los colores de riesgo se reservan para condiciones con significado operativo.

La interfaz implementada usa Dash, gráficos Plotly y tablas AG Grid Community. Los gráficos conservan etiquetas y una alternativa tabular de los datos. Las derivaciones se mantienen en `app/dashboard/analytics.py`; cada navegador conserva su consulta en un `dcc.Store` de memoria, sin estado global de usuario. El servicio de lectura compartido conserva la validación Pydantic. Véase [ADR 0003](adr/0003-python-dash-hub.md).

## Qué falta para mostrar tendencias y resultados

| Medición futura | Evidencia necesaria antes de publicarla |
| --- | --- |
| Evolución de solicitudes pendientes | Eventos de creación/cambio/cancelación o cortes persistidos comparables, con población y frecuencia conocidas |
| Tiempo de asignación o aprobación | Fechas de creación y decisión validadas; tratamiento de reaprobaciones y solicitudes aún pendientes |
| Puntualidad de recepción | Compromiso fechado, recepción aceptada, vínculo al traslado y reglas para cancelaciones y reprogramaciones |
| Tiempo fuera de operación | Inicio y fin de paro/reparación con causas y calendario de operación acordados |
| Comparación entre proyectos | IDs estables, alcance comparable y un denominador útil; no comparar solo conteos absolutos de proyectos de tamaños distintos |

La lectura actual no sostiene variaciones porcentuales respecto al mes pasado, metas de cumplimiento, ahorro ni productividad. El detalle de fórmulas propuestas y condiciones permanece en [KPIs y referencias](kpis-y-referencias-iso.md). Una siguiente ampliación debe obtener primero esos datos y validar la interpretación con las áreas responsables.
