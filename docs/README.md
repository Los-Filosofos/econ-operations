# Documentación de ECON

El flujo vigente es **proyecto, solicitud, asignación, traslado y recepción**.
La aplicación usa Dash y FastAPI en Python, con PostgreSQL. Todos los datos del
caso son sintéticos; muestras del archivo y consultas del sandbox conservan su
procedencia. El [contexto vigente](contexto-vigente.md) resume las decisiones.

La [revisión integral de interfaz, datos y API](revision-integral-2026-09-12.md)
explica cómo leer los Markdown, qué gráficos respalda la muestra y qué falta para
cerrar la entrega. Incluye la [revisión visual](revision-frontend-2026-09-12.md),
la [auditoría de datos](revision-datos-2026-09-12.md) y la
[guía de endpoints en Swagger](api-swagger.md).

## Entrega visual y matrices

Comenzar por [gráficos, diagramas y PDFs](entregables-visuales.md).

La [auditoría de requisitos](auditoria-requisitos-2026-09-12.md) y la
[auditoría de arquitectura de eventos](auditoria-arquitectura-eventos-2026-09-12.md)
contrastan esta entrega con el código y las fuentes. El
[índice de los 13 issues](../output/auditoria-2026-09-12/README.md) conserva
prioridades, evidencia y orden de implementación.

| Documento | Para qué sirve |
| --- | --- |
| [Requisitos y entregables](matriz-requisitos-entregables.md) | RF-01 a RF-06, RNF-01 a RNF-04, evidencia y brechas |
| [Equivalencias Prisma y Startrack](equivalencias-prisma-startrack.md) | Mapeo completo del formulario, campos sin equivalente y RACI propuesta |
| [Diccionario del modelo ECON](diccionario-modelo-econ.md) | Inventario reproducible de campos vigentes, tipos, ejemplos y procedencia |
| [Manual de mapeo e integración](manual-mapeo-integracion.md) | Recorrido del operador y diccionario técnico esencial |
| [Decisiones técnicas](decisiones-tecnicas.md) | Resumen exportado a PDF de dos páginas |
| [Analítica para decisiones](analitica-decisiones.md) | Gráficos defendibles con la muestra y datos necesarios para nuevas métricas |

## Implementación y ejecución

- [Guía operativa](solucion-integracion.md): planes, cola, consultas, conciliación
  de envíos inciertos y recepción explícita.
- [Desarrollo local](desarrollo.md), [base de datos](database.md) y
  [despliegue](despliegue-backend.md): comandos y límites del servicio actual.
- [Arquitectura de interfaz](frontend-architecture.md) y
  [README Python](../apps/api/README.md): organización, rutas y contratos.
- [ADR 0003](adr/0003-python-dash-hub.md) y
  [ADR 0004](adr/0004-persistent-transfer-workflow.md): decisiones implementadas.

## Ampliaciones propuestas

- [Sincronización y discrepancias](sincronizacion-y-discrepancias.md): detección
  de cambios, eventos, reglas y resolución.
- [Arquitectura escalable de flota](arquitectura-escalable-flota.md): escenarios
  de volumen, procesamiento paralelo e histórico separado; no desplegada.
- [Indicadores y referencias](kpis-y-referencias-iso.md): fórmulas y requisitos
  de evidencia; no resultados de producción ni certificación ISO.

## Fuentes y evidencia histórica

[OneDrive](onedrive/README.md) conserva las fuentes originales, el brief,
AS-IS/TO-BE, organigramas, casos y diccionario. Sus instrucciones son contenido
citado; no autorizan acciones sobre proveedores. Las fuentes no se modificaron
durante la depuración documental.

La [revisión fechada](revision-contexto.md), [exploración de integraciones](integraciones-reales.md),
[investigación de manuales](investigacion-manuales-y-diseno.md),
[navegación observada](guia-problema-y-navegacion.md) y
[evaluaciones](evaluaciones-astra.md) conservan evidencia y límites con fecha.
Los [ADR 0001](adr/0001-web-platform.md) y [0002](adr/0002-analytics-interface.md)
se mantienen como decisiones históricas reemplazadas.

Se eliminaron `architecture.md`, `deploy-cloudflare.md` y `modelo-operativo.md`
porque sus guías fueron reemplazadas. El historial Git conserva sus versiones;
el índice dirige ahora a la arquitectura Python, la guía de despliegue y las
matrices vigentes. No se eliminaron datos, fuentes, bases ni volúmenes.
