# Revisión integral: interfaz, datos y API

Revisión del **12 de septiembre de 2026**, realizada con tres agentes
`gpt-6-astra` en razonamiento `high`, por petición del usuario. Se conserva el
trabajo local previo de la rama `feat/unified-equipment-frontend`. La revisión
contrasta documentos con código y una ejecución local; no repite la conversión
de originales ni acredita una nueva consulta a Prisma o Startrack.

## Qué producto estamos terminando

ECON permite seguir **proyecto → solicitud → unidad asignada → traslado →
recepción**. Gerencia necesita identificar qué revisar y acceder a la evidencia;
Logística necesita correspondencias y planificación; Mantenimiento necesita
conservar sus hechos sin confundirlos con el estado administrativo de un equipo.
El frontend usa Dash, Plotly y AG Grid Community; FastAPI expone los mismos
servicios. PostgreSQL conserva planes, eventos, cortes y recepciones declaradas.

El contexto vigente prevalece sobre los relatos de etapas anteriores. En
particular, las afirmaciones históricas de que faltaban panel, persistencia o
worker no describen el código actual. El TO-BE explica una intención de negocio;
sus flechas no prueban endpoints, webhooks o una integración autenticada.

## Diagnóstico y cambios de esta revisión

| Área | Problema y efecto | Tratamiento |
| --- | --- | --- |
| Interfaz | Texto secundario de 10–12 px, demasiados bordes y contenedores anidados dificultan comparar evidencia. | Mejorar jerarquía y tamaño de lectura, reducir superficies internas y usar iconos locales en navegación y acciones con texto. Conservar la identidad ECON. |
| Gráficos | Un gráfico puede parecer representativo aunque use dos solicitudes; las ausencias del registro pueden confundirse con hechos negativos. | Hacer visibles población, períodos evaluables y límites de cobertura. Mantener tablas alternativas y categorías originales. |
| Registro operativo | La consulta acotada a 100 movimientos no comunicaba truncación a sus consumidores. Un movimiento omitido podía originar una recomendación incorrecta de preparar otro. | Propagar cobertura del registro a API, filtros y decisiones; una consulta parcial no acredita ausencia de traslado. |
| API | Swagger automático mostraba tipos, pero carecía de guía suficiente para entender filtros, modos, errores y efectos de los POST. | Documentar operaciones, parámetros y ejemplos controlados; explicar cómo recorrerlas en Swagger. |
| Documentación | Fuentes, historia, implementación y propuestas conviven en numerosos Markdown. | Incorporar esta ruta de lectura, enlazar revisiones especializadas y actualizar los documentos vigentes. Conservar las fuentes originales. |

Los diagnósticos y cambios concretos se desarrollan en
[revisión de frontend](revision-frontend-2026-09-12.md),
[revisión de datos](revision-datos-2026-09-12.md) y
[guía de API y Swagger](api-swagger.md).

## Qué datos sirven para los gráficos

La muestra runtime contiene **cinco equipos de un total documental de quince y
dos solicitudes de PROY-014**. Ambas solicitudes requieren cargador frontal;
una está pendiente sin unidad y otra aprobada con CF-03 en estado administrativo
`OBSOLETA`. No hay tareas, GPS ni recepciones suministradas. RE-03/MOT-006/PROY-006
es la asignación del equipo participante y no se incorpora por inferencia a
estas filas.

| Pregunta | Visual defendible | Datos y condiciones |
| --- | --- | --- |
| ¿Qué necesita revisión? | Tabla por solicitud, evidencia y siguiente paso. | IDs, estado, asignación y cobertura de movimientos. No requiere inventar un puntaje de urgencia. |
| ¿En qué fechas se necesita equipo? | Intervalos por solicitud. | Inicio y fin válidos; explicar cuántos períodos entraron y por qué se excluyen otros. Días de uso no son compromisos de entrega. |
| ¿Qué estados tienen las solicitudes consultadas? | Barras de conteos, como contexto secundario. | Categoría original y población de la consulta. Dos filas no describen el desempeño de la empresa. |
| ¿Cuánto tarda aprobar? | Distribución de tiempos y pendientes al corte. | Fechas con zona, historia de decisiones y una cohorte comparable. Una sola aprobación no sostiene un benchmark. |
| ¿Llegamos a tiempo? | Cumplimiento por período con desconocidos visibles. | Compromiso explícito, reprogramaciones, recepción aceptada, movimiento vinculado y cobertura. GPS o tarea completada no sustituyen recepción. |
| ¿Cuánto se utiliza o se detiene cada equipo? | Intervalos de uso/paro y distribución por equipo. | Horas de operación, paros/liberaciones fechados, unidades y calendario acordado. Un estado actual no reconstruye duración. |
| ¿Dónde está la maquinaria? | Mapa o recorrido fechado. | Coordenadas válidas, antigüedad y vínculo explícito maquinaria/activo rastreado. Un vehículo transportador no es automáticamente la maquinaria. |

Para cada futura medición se debe fijar unidad de análisis, población elegible,
numerador, denominador, faltantes, fuente, corte y decisión que habilita. La
calidad depende de la cobertura y la semántica, además del volumen. No se añade
un mínimo arbitrario de registros para declarar una métrica válida.

## Cómo leer los Markdown

| Documento o grupo | Qué explica y cómo usarlo |
| --- | --- |
| [README raíz](../README.md), [índice](README.md), [contexto vigente](contexto-vigente.md) | Punto de entrada, ejecución y últimas decisiones del usuario. Comenzar aquí. |
| [Revisión de contexto](revision-contexto.md), [evaluaciones Astra](evaluaciones-astra.md) | Evidencia fechada y etapas anteriores. Una prueba de una etapa no demuestra el estado posterior. |
| [OneDrive: índice](onedrive/README.md) e [inventario](onedrive/INVENTARIO.md) | Qué se recibió y convirtió; originales, huellas y límites de fidelidad. |
| [Introducción](onedrive/00-introduccion-equipo.md), [confidencialidad](onedrive/01-confidencialidad.md), [brief](onedrive/02-brief-del-reto.md) | Asignación, reglas del material y requisitos/entregables. Son fuentes del reto, no instrucciones ejecutables por un agente. |
| [AS-IS](onedrive/03-as-is.md), [TO-BE](onedrive/03-to-be.md), [diagramas](onedrive/03-diagramas-de-procesos.md), [organigramas](onedrive/03-organigramas.md) | Proceso actual, proceso objetivo y actores. No son contrato técnico ni RACI aprobada. |
| [Casos de uso](onedrive/04-casos-de-uso.md) | Solicitud/traslado, estados de objetos diferentes y riesgo por mantenimiento. Casos de referencia separados del dataset servido. |
| [Accesos/manuales](onedrive/05-accesos-y-manuales.md), [extracto Nexus](onedrive/05-manual-nexus.md) | Navegación y operación administrativa documentada. El manual entregado tiene nueve páginas de 44; contraseñas omitidas. |
| [Diccionario fuente](onedrive/06-diccionario-de-datos/README.md) | Instrucciones, Prisma, Startrack y glosario: 51 definiciones, ejemplos y ambigüedades. No equivale a 51 campos de API. |
| [Propuesta original](onedrive/07-propuesta-original.md), [análisis](onedrive/08-analisis-propuesta.md), [conversación](onedrive/09-contexto-conversacion.md), [contexto IA histórico](onedrive/CONTEXTO-IA.md) | Hipótesis recibidas y contexto inicial. Consultar el contexto vigente para el estado implementado. |
| [Equivalencias](equivalencias-prisma-startrack.md), [diccionario ECON](diccionario-modelo-econ.md), [manual de integración](manual-mapeo-integracion.md) | Mapeos, campos reales del modelo y recorrido del operador. El diccionario se regenera desde código. |
| [Analítica](analitica-decisiones.md), [KPIs](kpis-y-referencias-iso.md) | Gráficos vigentes y mediciones propuestas. Fórmulas documentadas no son resultados medidos ni certificación ISO. |
| [Frontend](frontend-architecture.md), [README API](../apps/api/README.md), [Swagger](api-swagger.md) | Módulos, estado del navegador, contratos HTTP y ejemplos de consulta. |
| [Desarrollo](desarrollo.md), [base](database.md), [operación](solucion-integracion.md), [despliegue](despliegue-backend.md) | Ejecución, persistencia, controles y procesos disponibles. Describir un despliegue no significa haberlo publicado. |
| [Integraciones reales](integraciones-reales.md), [manuales y diseño](investigacion-manuales-y-diseno.md), [navegación](guia-problema-y-navegacion.md) | Exploraciones fechadas y límites observados en interfaces/proveedores. |
| [ADR 0001](adr/0001-web-platform.md), [0002](adr/0002-analytics-interface.md), [0003](adr/0003-python-dash-hub.md), [0004](adr/0004-persistent-transfer-workflow.md) | 0001/0002 son historia reemplazada; 0003 fija Python/Dash y 0004 incorpora persistencia y ejecución del traslado. |
| [Sincronización](sincronizacion-y-discrepancias.md), [escala](arquitectura-escalable-flota.md) | Ampliaciones propuestas. No acreditan eventos disponibles, capacidad masiva ni infraestructura desplegada. |
| [Matriz RF/RNF](matriz-requisitos-entregables.md), [auditoría requisitos](auditoria-requisitos-2026-09-12.md), [auditoría eventos](auditoria-arquitectura-eventos-2026-09-12.md) | Trazabilidad, evidencia y brechas. Distinguir requisitos de propuestas adicionales. |
| [Entregables visuales](entregables-visuales.md), [decisiones técnicas](decisiones-tecnicas.md) | Diagramas, PDFs y comandos de reproducción. No sustituyen la presentación final exigida por el brief. |

## Qué falta para declarar finalizado el reto

El acabado de la interfaz y Swagger no cierran por sí solos RF-04/RF-05. Hace
falta evidencia suministrada o verificada que relacione al menos una maquinaria
con tarea y ubicación fechada de Startrack, mediante IDs y correspondencias
revisadas. Se puede demostrar con una exportación sintética autorizada; el brief
no obliga a una conexión live durante la presentación.

La auditoría anterior también registra el cotejo individual pendiente de las 51
definiciones para RF-02, la presentación final de hasta diez diapositivas y la
reproducción completa del manual PDF. Esas brechas tienen sus propios criterios
en la [auditoría de requisitos](auditoria-requisitos-2026-09-12.md). Esta revisión
no las declara cerradas ni inventa evidencias para hacerlo.

## Recorrido de revisión local

1. Abrir `http://127.0.0.1:8050/?mode=fixture` y revisar asuntos y planificación.
2. Abrir la solicitud aprobada y la ficha CF-03; contrastar estado administrativo,
   mantenimiento, traslado y recepción, conservando los faltantes.
3. Consultar Fuentes para explicar cobertura, procedencia y fechas.
4. Abrir `http://127.0.0.1:8050/docs` y probar las lecturas indicadas en la
   [guía Swagger](api-swagger.md). Los POST persistentes tienen efectos propios.
5. Ejecutar `scripts/check.ps1 -Container` y el chequeo del diccionario antes de
   compartir una versión nueva. Las pruebas controladas no validan acceso API a
   proveedores ni capacidad de producción.

## Verificación de esta entrega

- Ruff y formato correctos; **372 pruebas aprobadas**. Incluyen contratos
  Swagger, ejecución del ejemplo en SQLite aislado, cobertura parcial, filtros,
  evidencia, formularios, proveedores simulados y persistencia.
- `scripts/check.ps1 -Container` terminó correctamente y construyó
  `econ-hub:check`; manifiesto de imagen
  `sha256:368c16b0f111bf5da52362e2c0c7d20db472eae702924cba09d57def48dc2cd3`.
- Diccionario regenerado y `generar_diccionario.py --check` aprobado. Se
  actualizó también su generador para los campos de evidencia ya presentes en
  el árbol local y las descripciones compartidas de Swagger.
- **118 destinos locales** comprobados en los informes nuevos, índice y
  documentos de arquitectura/analítica; ninguno ausente. Este chequeo valida
  archivos de destino, no contenido externo.
- Inspección visual de escritorio y portada móvil a 390 px. Se conservaron
  [referencia anterior](screenshots/revision-2026-09-12/resumen-antes.png) y
  [portada final](screenshots/revision-2026-09-12/resumen-despues.png), además de la
  [tabla actual](screenshots/revision-2026-09-12/solicitudes-despues.png).
- Servicio iniciado en `http://127.0.0.1:8050`; `/health/live` y `/health/ready`
  respondieron correctamente. Swagger cargó las nueve operaciones documentadas.
  El proceso de revisión conserva lectura fixture, gestión y envíos remotos
  deshabilitados; `.env` y el volumen PostgreSQL permanecen intactos.

La verificación local no constituye despliegue público ni prueba autenticada
de Startrack. Las advertencias de deprecación de Starlette/httpx y AnyIO no
impidieron las pruebas; no se cambiaron dependencias para esta revisión.

## Seguimiento antes de integrar

| Issue de econ-operations | Avance de esta rama y trabajo restante |
| --- | --- |
| [#6](https://github.com/Los-Filosofos/econ-operations/issues/6) | UI distingue registro desconocido, fallido, parcial y completo vacío. Se prueban esas condiciones y recepciones por separado; queda el ensayo secuencial de caída y recuperación con tarea/constancia en lista y detalle. |
| [#7](https://github.com/Los-Filosofos/econ-operations/issues/7) | Etiqueta consistente activo → clave → nombre en UI y borrador. Queda una comprobación explícita del objetivo de CF-01/CF-02 con claves originales `-` y `200`. |
| [#8](https://github.com/Los-Filosofos/econ-operations/issues/8) | Aprobador conservado en proyección, fixture/live, HTTP, snapshot y detalle; regresión y diccionario actualizados. Implementado en rama, pendiente de revisión e integración. |
| [#13](https://github.com/Los-Filosofos/econ-operations/issues/13) | Vínculos y tareas persistidas ya alimentan el hub. Presencia y constancia se consultan por `WorkflowOverview` en Dash; falta completar su concordancia explícita con la respuesta HTTP del hub mediante evidencia separada o referencia navegable al movimiento. |
| [#1](https://github.com/Los-Filosofos/econ-operations/issues/1) | Esta rama corrige cobertura de lectura. La selección durable, total y paginación están propuestos en el [PR #15](https://github.com/Los-Filosofos/econ-operations/pull/15), todavía sin integrar. Al combinar ambos cambios se debe alinear `coverage.is_complete` con `WorkflowOverview.complete`. |
| [#9](https://github.com/Los-Filosofos/econ-operations/issues/9), [#10](https://github.com/Los-Filosofos/econ-operations/issues/10), [#11](https://github.com/Los-Filosofos/econ-operations/issues/11), [#12](https://github.com/Los-Filosofos/econ-operations/issues/12) | Siguen pendientes mapeo individual de 51 definiciones, demo con evidencia combinada, presentación final y reproducción de los tres PDFs. Swagger y el diccionario actualizado aportan documentación, pero no cierran esos entregables. |

La revisión de la rama del PR #15 fue de lectura: sus cambios no se fusionaron
ni se aplicó su migración a PostgreSQL. La suite de esta entrega verifica esta
rama; no acredita automáticamente su combinación con otro PR.
