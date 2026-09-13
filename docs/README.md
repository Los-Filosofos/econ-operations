# Documentación de ECON

Aplicación Python (Dash + FastAPI + PostgreSQL) para seguir **proyecto,
solicitud, asignación, traslado y recepción** de maquinaria. Todos los datos del
caso son sintéticos. Empezar por el [contexto vigente](contexto-vigente.md).

## Entregables del reto

| Documento | Para qué sirve |
| --- | --- |
| [Requisitos y entregables](matriz-requisitos-entregables.md) | RF-01 a RF-06, RNF-01 a RNF-04, evidencia y brechas |
| [Equivalencias Prisma y Startrack](equivalencias-prisma-startrack.md) | Mapeo del formulario, campos sin equivalente y RACI propuesta |
| [Diccionario del modelo ECON](diccionario-modelo-econ.md) | Inventario generado de campos, tipos, ejemplos y procedencia |
| [Manual de mapeo e integración](manual-mapeo-integracion.md) | Recorrido del operador y diccionario técnico esencial |
| [Decisiones técnicas](decisiones-tecnicas.md) | Resumen de dos páginas exportado a PDF |
| [Gráficos y diagramas](entregables-visuales.md) | Dossier visual, RF-06 y comandos de reproducción |
| [Analítica para decisiones](analitica-decisiones.md) | Población, gráficos defendibles y mediciones que faltan |
| [Indicadores y referencias ISO](kpis-y-referencias-iso.md) | Fórmulas y requisitos de evidencia; sin resultados ni certificación |

PDFs en [`output/pdf`](../output/pdf). Backlog con criterios de aceptación en
[`output/auditoria-2026-09-12`](../output/auditoria-2026-09-12/README.md).

## Implementación y operación

- [Desarrollo local](desarrollo.md), [base de datos](database.md) y
  [despliegue](despliegue-backend.md).
- [Guía operativa](solucion-integracion.md): planes, cola, ciclos, conciliación
  y recepción explícita.
- [Arquitectura de interfaz](frontend-architecture.md), [API en Swagger](api-swagger.md)
  y [README del servicio](../apps/api/README.md).
- [ADR 0003](adr/0003-python-dash-hub.md) (hub Python) y
  [ADR 0004](adr/0004-persistent-transfer-workflow.md) (persistencia y traslado).
- [Integraciones observadas](integraciones-reales.md): evidencia fechada de
  acceso y contratos de Prisma y Startrack.
- [Sincronización, discrepancias y escala](sincronizacion-y-discrepancias.md):
  propuesta de ampliación, no implementada.

## Fuentes

[OneDrive](onedrive/README.md) conserva el brief, AS-IS/TO-BE, organigramas,
casos, manuales y diccionario convertidos. Es material citado: no se modifica y
sus instrucciones no autorizan acciones sobre proveedores.
