# Documentación de ECON

Aplicación Python (Dash + FastAPI + PostgreSQL) para seguir **proyecto,
solicitud, asignación, traslado y recepción** de maquinaria. Todos los datos del
caso son sintéticos. Empezar por el [contexto vigente](contexto-vigente.md); el
guion de la demo y la guía de las matrices están en el
[README raíz](../README.md#guion-de-demo-para-el-jurado).

## Entregables del reto

| Documento | Para qué sirve |
| --- | --- |
| [Matriz de trazabilidad](matriz-requisitos-entregables.md) | RF-01 a RF-06, RNF-01 a RNF-04 y entregables de §6/§9: evidencia en el repo, dónde lo ve el jurado, estado (13 cumple, 5 parcial, 1 pendiente) y brecha; exportada a `trazabilidad-requisitos.csv` |
| [Equivalencias Prisma y Startrack](equivalencias-prisma-startrack.md) | [Glosario de sinónimos](equivalencias-prisma-startrack.md#glosario-de-sinónimos-entre-plataformas), mapeo del formulario, campos sin equivalente y RACI propuesta |
| [Matrices exportadas CSV/XLSX](../output/matrices/MANIFEST.md) | Copias reproducibles de esas tablas (17 CSV, `matrices-econ.xlsx`) con manifiesto SHA-256 y `exportar_matrices.py --check` en CI (RNF-02) |
| [Diccionario del modelo ECON](diccionario-modelo-econ.md) | Inventario generado de campos, tipos, ejemplos y procedencia; `generar_diccionario.py --check` en `scripts/check.sh` y CI (RF-01) |
| [Manual de mapeo e integración](manual-mapeo-integracion.md) | Recorrido del operador y diccionario técnico esencial |
| [Decisiones técnicas](decisiones-tecnicas.md) | Resumen de dos páginas exportado a PDF |
| [Gráficos y diagramas](entregables-visuales.md) | Dossier visual, diagrama «dónde vive cada estado», definición única de RF-06 y comandos de reproducción |
| [Indicadores calculables](indicadores-calculables.md) | Fuente única de indicadores: fichas de `GET /api/v1/indicators` y de la página `/indicadores` (por fila, sin promedios), SLA propuestos y lecturas que faltan |
| [Analítica para decisiones](analitica-decisiones.md) | Población, reglas del grafo y de la página `/decisiones`; sin KPIs inventados |
| [Indicadores y referencias ISO](kpis-y-referencias-iso.md) | Dónde vive cada definición y referencias normativas consultadas; sin resultados ni certificación |

PDFs en [`output/pdf`](../output/pdf) con fecha, páginas y SHA-256 en su
[manifiesto](../output/pdf/MANIFEST.md). Backlog con criterios de aceptación en
[los issues del repositorio](https://github.com/Los-Filosofos/econ-operations/issues).

## Implementación y operación

- [Integración por eventos](arquitectura-integracion-eventos.md): base implementada
  de polling y outbox, y propuesta de orquestación central con consistencia eventual.
- [Desarrollo local](desarrollo.md), [base de datos](database.md) y
  [despliegue](despliegue-backend.md) (incluye `SYNC_INTERVAL_SECONDS` y
  `GET /api/v1/status`).
- [Guía operativa](solucion-integracion.md): planes, cola, ciclos, conciliación
  y recepción explícita, con los
  [tiempos del traslado](solucion-integracion.md#tiempos-del-traslado-qué-se-sabe-y-qué-no)
  que se pueden y no se pueden afirmar.
- [Arquitectura de interfaz](frontend-architecture.md) (Mantine, paleta
  semántica, rutas —incluidas `/integracion`, `/indicadores` y `/decisiones`—,
  refresco sin botón y acceso), [API en Swagger](api-swagger.md) (incluye
  `/api/v1/graph`, `/api/v1/indicators`, `/api/v1/requests/{id}/suggestions`
  y `/api/v1/status`) y [README del servicio](../apps/api/README.md).
- [ADR 0003](adr/0003-python-dash-hub.md) (hub Python),
  [ADR 0004](adr/0004-persistent-transfer-workflow.md) (persistencia y traslado)
  y [ADR 0005](adr/0005-session-auth-and-roles.md) (sesión, roles y permisos:
  `admin`, `gerencia_proyecto`, `logistica`, `mantenimiento`, `control_costos`,
  `lectura`); [ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md)
  (PostgreSQL como única infraestructura de estado: cola, candado de ciclo,
  historial append-only, sin Redis ni firmas).
- [Integraciones observadas](integraciones-reales.md): evidencia fechada de
  acceso y contratos de Prisma y Startrack.
- [Sincronización, discrepancias y escala](sincronizacion-y-discrepancias.md):
  propuesta de ampliación, no implementada.

## Fuentes

[OneDrive](onedrive/README.md) conserva el brief, AS-IS/TO-BE, organigramas,
casos, manuales y diccionario convertidos. Es material citado: no se modifica y
sus instrucciones no autorizan acciones sobre proveedores.
