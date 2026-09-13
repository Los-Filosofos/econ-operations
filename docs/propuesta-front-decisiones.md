# Propuesta de frontend orientado a decisiones

13/09/2026. Revisión del código actual con tres agentes Astra en razonamiento
alto. Sin capturas ni tests. Las dimensiones siguientes son deducciones del
layout, no mediciones de una sesión de navegador. Esta propuesta no reemplaza
las decisiones de dominio ni activa integraciones.

## Diagnóstico

Los cambios de fuente, color y padding no resolvieron la jerarquía. La interfaz
sigue utilizando secciones, gráficos, laterales y desplegables como plantilla
para todas las preguntas. Hay que diseñar la superficie de trabajo antes de
estilizar sus componentes.

| Problema concreto | Evidencia | Efecto |
| --- | --- | --- |
| Altura automática con contenedor fijo implícito | `dashboard/components.py`, `grid`: `domLayout="autoHeight"` sin anular el alto predeterminado de AG Grid | Posible espacio vacío o desbordamiento; se corrigió añadiendo `style={"height": None, "width": "100%"}` |
| Columnas idénticas para contenidos distintos | La misma función asigna `flex=1`, `minWidth=150`, envoltura y altura automática a todas las columnas | Solicitudes suma al menos 1050 px para siete columnas; a 1280 px quedan aproximadamente 1004 px de trabajo tras sidebar y márgenes |
| Gráfico sin comparación significativa | `indicator_views.hours_figure`: mínimo 260 px y máximo del eje `valor × 1,3` | Una observación aislada ocupa cerca del 77 % del eje tanto si vale 42 segundos como 42 horas. La forma no añade información a la cifra |
| Gráfico grande y acciones secundarias | `decision_analytics.usage_figure`: mínimo 350 px; `views.decisions`: columnas 8/4, calendario primero en móvil | Dos períodos consumen buena parte del primer recorrido de pantalla; la acción queda después |
| Contexto repartido | `application.read_status`, `views.reading_menu`, cabeceras y explicaciones por sección | Hay que consultar varios lugares para entender una misma lectura |
| Múltiples accesos al mismo registro | Indicador → lectura de casos → filas y evidencia → método → SLA | El dato, la explicación y la acción no se leen juntos |
| Formularios con lenguaje de integración | `workflow_forms.plan_form`: IDs de geocerca, usuarios y GPS como texto | El operador necesita conocer contratos técnicos para preparar una tarea |
| Reconstrucción amplia de vistas | `application.render` reemplaza contenido con cambios de stores; Integración vuelve a usar `default_request_id` | Riesgo de perder selección o contexto al refrescar; no se midieron parpadeos ni tiempos |

Rutas de código relativas a `apps/api/app/`.

La documentación oficial confirma que
[AG Grid necesita anular su altura fija al usar autoHeight](https://dash.plotly.com/dash-ag-grid/grid-size).
Para un registro extenso, conviene altura acotada y scroll interno con
virtualización. La corrección inmediata no implementa todavía ese cambio.

## Dirección recomendada

Una aplicación operativa centrada en registros: la tabla es el lugar donde se
identifica el trabajo; el gráfico permite comparar; un único detalle conserva
la evidencia y la acción. Mantener la navegación lateral solicitada, con menos
repetición de títulos y una única entrada a la calidad de la lectura.

### Resumen

Abrir con asuntos que requieren intervención. Cada fila contiene asunto,
proyecto/unidad, hecho que lo justifica y acceso a resolverlo. Con las muestras
actuales, la lectura de negocio sería:

| Asunto | Registro | Hecho que justifica revisar | Acción |
| --- | --- | --- | --- |
| Revisar asignación | PROY-014 · CF-03 | Solicitud aprobada con una unidad cuyo estado administrativo es OBSOLETA | Abrir solicitud y revisar unidad |
| Resolver solicitud | PROY-014 · cargador frontal | Solicitud pendiente y sin unidad asignada | Revisar aprobación y asignación |

No son nuevos hechos ni puntuaciones de urgencia. La condición administrativa
no afirma avería. La acción debe respetar las capacidades reales del rol y de
las APIs; el texto no promete aprobar directamente desde ECON.

Debajo, agenda de uso solicitado con altura proporcional a las filas. Cuando
permita comparar períodos, usar un gráfico temporal a ancho completo. En móvil,
la acción permanece antes de la agenda. Un resumen con dos solicitudes no
necesita una gráfica grande de distribución por estado.

### Solicitudes y maquinaria

- Diseñar columnas por significado: identidad/proyecto más ancha; unidad,
  período y estado con anchura propia. Evitar que una frase de acción ocupe lo
  mismo que un estado corto.
- Una toolbar con búsqueda y filtros pertinentes. No duplicar buscadores ni
  filtros de columna sin propósito.
- Identidad del registro siempre localizable. Conservar columnas de negocio
  y desplazamiento horizontal en móvil, sin ocultar silenciosamente datos.
- Selección de fila y un detalle contextual con acción, contexto y evidencia.
  Conservar enlaces profundos y navegación accesible.
- En maquinaria, asignación y mantenimiento siguen siendo hechos separados.

### Movimientos y detalle

- La tabla conserva encabezados cuando está vacía; el vacío no reemplaza la
  herramienta por varios párrafos. Ofrecer una acción real para iniciar trabajo
  cuando el rol lo permita.
- Identificar por estado qué requiere conciliación, envío o recepción. El
  registro extenso necesita scroll interno y paginación del servidor.
- Detalle con una acción aplicable y cronología compacta. Procedencia y payload
  en un solo panel técnico.
- Usar selectores de catálogos con nombres legibles y valores ID cuando el
  catálogo esté disponible y validado. No unir por nombres ni inventar opciones.

### Indicadores y SLA

Elegir la representación según la pregunta y la evidencia, no imponer un mínimo
universal de gráficos:

| Evidencia disponible | Representación predeterminada |
| --- | --- |
| Ninguna observación evaluable | Motivo breve y dato requerido; conservar acceso a registros |
| Un valor aislado | Fila con registro, duración y fechas que la sostienen |
| Registros comparables | Barras o puntos ordenados a ancho completo, identificados y con valores exactos |
| Períodos que interesa comparar | Agenda temporal por solicitud/unidad, sin llamarla utilización |
| Historial con cobertura comparable | Tendencia temporal; no deducirla de un único corte |
| SLA acordado y medible | Comparación con objetivo usando el mismo reloj, calendario y población |

Dos registros pueden justificar un gráfico si muestran una comparación útil.
Un solo dato puede justificarlo si existe una referencia legítima. Las horas
corridas actuales no deben compararse con una propuesta en horas hábiles.

Mostrar una pregunta o familia de análisis a la vez, con filas de soporte
visibles. Seleccionar una fila abre el mismo detalle. El catálogo de fórmulas y
SLA propuestos se consulta en una sección de metodología, sin repetirse al lado
de cada resultado.

### Integración, fuentes y administración

Integración debe ser un visor de etapas: seleccionar una etapa muestra su tabla
de campos. Fuentes concentra cobertura y problemas de conexión. Administración
conserva usuarios, roles y edición. Ninguna necesita gráficos decorativos para
parecer más completa.

## Aprovechar Dash como aplicación

- Usar navegación interna apropiada: [dcc.Link permite navegar sin recargar
  la página](https://dash.plotly.com/dash-core-components/link). Un
  `dmc.Anchor` con href no adquiere esa propiedad solo por existir
  `dcc.Location(refresh="callback-nav")`.
- Conservar selección, filtros, página y borradores en URL/stores y no
  reconstruirlos con cada observación de datos.
- Actualizar paneles concretos. Construir todo el contenido dentro de un
  acordeón cerrado no lo convierte en carga bajo demanda.
- No mezclar versiones de hub y registro como si fueran un único corte
  consistente. Mantener visibles sus límites hasta coordinar la publicación.

## Secuencia de implementación propuesta

1. Corregir geometría de tablas y diseñar columnas; la anulación del alto fijo
   con autoHeight ya quedó aplicada en esta revisión.
2. Unificar contexto y detalle de registros; conservar navegación y selección.
3. Rehacer Resumen con asuntos antes de agenda y adaptar visualizaciones a la
   pregunta. Mantener Public Sans y la paleta mientras se evalúa la estructura.
4. Revisar formularios y catálogos para que el operador elija hechos del negocio.
5. Incorporar análisis históricos cuando la evidencia los sostenga.

## Aplicación de esta revisión

Se implementaron la portada con tabla de asuntos y agenda a ancho completo,
columnas específicas y altura acotada de AG Grid, eliminación de paginadores
en listas pequeñas, tabla vacía persistente en Movimientos y navegación interna
en los enlaces compatibles del helper compartido. Indicadores presenta una
pregunta activa; una o dos observaciones se leen como filas. Integración usa
pestañas por etapa con selección persistida y Usuarios tiene una tabla compacta.

Se conservan Public Sans local y la barra lateral oscura; se retiraron los
laterales y paneles repetidos. Esta implementación se revisó en código y con
Ruff, sin capturas ni tests, por instrucción del usuario. No constituye una
validación visual en navegador. La construcción bajo demanda desde servidor,
la persistencia general de borradores y los selectores de catálogos siguen
siendo mejoras independientes; las pestañas no implementan esos cambios.
