# Matriz de requisitos, entregables y evidencia

Revisión: **13 de septiembre de 2026**. Esta matriz conecta cada requisito del
[brief](onedrive/02-brief-del-reto.md) (sección 7: seis RF y cuatro RNF), los
entregables de la sección 9 y el alcance obligatorio y deseable de la sección 6
con la evidencia que existe en el repositorio, con la pantalla o el documento
donde el jurado la ve y con la brecha que queda. No otorga una calificación ni
declara completa la integración. Se exporta sin cambios a
[`output/matrices/trazabilidad-requisitos.csv`](../output/matrices/MANIFEST.md)
y a la hoja «Trazabilidad requisitos» de `matrices-econ.xlsx` con
`scripts/docs/exportar_matrices.py` (`--check` en `scripts/check.sh` y CI).

Todo dato operativo del caso es **sintético**. `fixture` distingue muestras
proporcionadas en archivos (`apps/api/app/integrations/data/sandbox_samples.json`:
cinco equipos de quince declarados y dos solicitudes de PROY-014; sin tareas,
ubicaciones GPS ni recepciones); `live`, lecturas actuales del sandbox. Ninguno
significa producción. El día del documento no constituye un instante de
observación común.

## Fuentes y criterio de lectura

Se leyeron íntegros el [brief](onedrive/02-brief-del-reto.md), el
[AS-IS](onedrive/03-as-is.md), el [TO-BE](onedrive/03-to-be.md), los
[tres casos de uso](onedrive/04-casos-de-uso.md) y las cuatro hojas del
[diccionario](onedrive/06-diccionario-de-datos/README.md), incluidos sus registros
de celdas. Los [organigramas](onedrive/03-organigramas.md) permiten distinguir
actores documentados de responsabilidades propuestas. El contraste de estado
actual usa el [contexto vigente](contexto-vigente.md), las
[equivalencias](equivalencias-prisma-startrack.md), el
[README del servicio](../apps/api/README.md), la tabla de páginas `PAGES` de
[`apps/api/app/dashboard/views.py`](../apps/api/app/dashboard/views.py) y los
modelos de [lectura](../apps/api/app/models/hub.py),
[operaciones](../apps/api/app/models/operations.py),
[grafo](../apps/api/app/models/graph.py),
[indicadores](../apps/api/app/models/indicators.py) y
[sugerencias](../apps/api/app/models/suggestions.py).

El brief contiene **seis RF y cuatro RNF**, todos en su sección 7. No aparecen
RF-07, RNF-05 ni requisitos ISO. La sección 6 define alcance (obligatorio y
deseable); la 9 define entregables; la 13 contiene una rúbrica propuesta,
sujeta a validación. Esos apartados no se renumeran como requisitos nuevos:
en la matriz llevan el prefijo `§6` o `§9`. Los comentarios editoriales del
Word se conservan como comentarios y no se aplican silenciosamente.

Estados de la matriz: **cumple** significa que la evidencia existe en el
repositorio, se puede abrir o ejecutar y se verifica (pruebas, `--check` o
manifiesto con SHA-256); **parcial**, que la capacidad o el documento existe
pero falta evidencia, validación o un formato exigido; **pendiente**, que no
existe en el repositorio. Una prueba con transporte HTTP controlado no acredita
una respuesta autenticada de Startrack, y la ausencia de tareas en la muestra
no es cero tareas en la operación.

## Matriz de trazabilidad

Las rutas de la aplicación se abren tras iniciar sesión en `/login`
(`http://127.0.0.1:8050` con `./scripts/dev.sh`); todas conservan `mode` en la
URL y los IDs originales viajan codificados (`nexus:equipment:…`,
`nexus:request:…`). Los apartados `§7` transcriben el texto del brief; `§6` y
`§9` lo resumen sin añadir obligaciones.

| Requisito | Qué exige el brief | Evidencia en el repo (archivo o ruta exacta) | Dónde lo ve el jurado (URL de la app o documento) | Estado | Brecha y acción |
| --- | --- | --- | --- | --- | --- |
| RF-01 | Inventario de cualquier campo o término nuevo generado a partir del diccionario y dataset sandbox de Prisma y Startrack: nombre de campo, tipo de dato y ejemplo de valor. | `docs/diccionario-modelo-econ.md`, generado por `scripts/docs/generar_diccionario.py` desde `apps/api/app/models/hub.py`, `operations.py`, `workflow.py`, `graph.py`, `indicators.py` y `suggestions.py` (nombre o JSONPath, tipo JSON, obligatorio, ejemplo con clase de evidencia, significado, procedencia); `--check` en `scripts/check.sh` y `.github/workflows/ci.yml`. Nombres equivalentes en el glosario de `docs/equivalencias-prisma-startrack.md` (`output/matrices/glosario-sinonimos.csv`, 36 conceptos). | Documento `docs/diccionario-modelo-econ.md`; Swagger `/docs` (esquemas `HubResponse`, `GraphProjection`, `IndicatorsReport`, `AssignmentSuggestion` con descripción por campo); `output/matrices/glosario-sinonimos.csv`. | cumple | El inventario cubre los modelos propios y sus derivaciones, no los DTO de los proveedores ni las 51 definiciones del kit (esas se cotejan en RF-02). Acción: regenerar con `generar_diccionario.py` tras cada cambio de modelo; CI falla si no coincide. |
| RF-02 | Matriz de mapeo que conecte cada campo relevante de una plataforma con su equivalente en la otra, marcando explícitamente los campos sin equivalente directo. | `docs/equivalencias-prisma-startrack.md`: clasificaciones directa, transformada, manual, sin equivalente y no soportada; formulario de tarea en cinco secciones; otros campos API del Job; inventario Prisma que no viaja; identidad y cardinalidad; inconsistencias del kit. Exportada a 16 CSV y `output/matrices/matrices-econ.xlsx` (manifiesto con SHA-256). Traza campo a campo en `apps/api/app/services/integration_trace.py` (`field_map`, tratamiento Conservado, Transformado, Manual o Sin equivalente) con pruebas en `apps/api/tests/test_integration_trace.py`. | `/integracion?mode=fixture` (bloque «Mapeo campo a campo»); `GET /api/v1/integration/{request_id}` (`field_map`); `output/matrices/formulario-tarea-completo.csv` y `otros-campos-api-tarea.csv`; dossier `output/pdf/ECON-entregables-visuales.pdf`. | parcial | Falta el cotejo fila a fila de las 51 definiciones del diccionario del kit (12 Prisma, 39 Startrack) contra la matriz, y las correspondencias proyecto a geocerca, máquina a vehículo y operador a usuario no están validadas en la cuenta (la clave API de Startrack respondió 403). Acción: tabla de cotejo por fila del kit incluida en la exportación y validación autenticada; no inventar correspondencias. |
| RF-03 | Matriz de responsabilidades que defina, para al menos tres roles funcionales, quién es Responsable, quién Aprueba, a quién se Consulta y a quién se Informa sobre el estado de un equipo (formato RACI recomendable). | RACI de nueve decisiones en `docs/equivalencias-prisma-startrack.md` (sección «Responsabilidades propuestas para confirmar»: Gerencia de Proyecto, Logística y Equipo, Mantenimiento, Operador, Control de Costos, Soporte de integración, Responsable receptor) exportada a `output/matrices/raci-propuesta.csv`. Implementada como roles de sesión en `apps/api/app/core/auth.py` (`admin`, `logistica`, `gerencia_proyecto`, `mantenimiento`, `control_costos`, `lectura`; permisos `read`, `manage_transfers`, `declare_reception`, `manage_users`; `docs/adr/0005-session-auth-and-roles.md`) y actor registrado en `operation_events.actor_*` y en la recepción `declared_by_*` (migración `0004_guards`, `apps/api/migrations/versions/0004_movement_guards_actors_and_indexes.py`). | `/administracion` (solo `admin`: alta de usuarios por rol); iniciar sesión con un usuario `lectura` y abrir `/operaciones` (sin acciones de gestión); `/operaciones/{id}` (actor de cada transición); `output/matrices/raci-propuesta.csv`; dossier PDF, páginas 2 a 4. | cumple | La RACI es una propuesta pendiente de validación por las tres gerencias; el rol de sesión aplica permisos y registra quién actuó, no acredita esa aprobación. Acción: validar con ECON y fijar la denominación («Logística y Equipo» frente a «Maquinaria y Equipo» del organigrama). |
| RF-04 | El prototipo debe permitir consultar el estado y la ubicación de al menos un equipo de forma unificada, combinando datos de ambas plataformas. | `/maquinaria/{id}` en `apps/api/app/dashboard/views.py` (`equipment_detail`) con `evidence_views.py` (`source_comparison`, `location_facts`, `maintenance_facts`): estado administrativo y mantenimiento de Prisma, tarea y visita de Startrack conservadas en el registro, recepción declarada y ubicación fechada o «no verificable». `GET /api/v1/hub` (`equipment[].transfers`, `location`, `provenance`) y `GET /api/v1/graph` (`gaps.machine_location`, `coverage`). Pruebas: `apps/api/tests/test_evidence_views.py`, `test_graph.py`, `test_hub_evidence_concordance.py`. | `/maquinaria/{id}?mode=fixture` (por ejemplo CF-03, `nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03`); la portada `/?mode=fixture` (asunto «Revisar la asignación» de esa unidad); `GET /api/v1/graph?mode=fixture`. | parcial | La vista combina ambas fuentes, pero ningún registro suministrado tiene evidencia de las dos: la muestra no trae tareas, visitas GPS ni recepciones y el acceso API de Startrack de la cuenta no está validado (403). El jurado ve hechos de Prisma y faltantes explícitos, no una ubicación observada. Acción: cadena live verificada (PROY-006) con tarea y visita reales, conservando IDs; no inventar registros. |
| RF-05 | El prototipo debe reflejar visualmente al menos un caso donde el estado del equipo difiere entre Prisma y Startrack, y cómo se resuelve. | Regla «OCUPADA en Prisma y tarea completada en Startrack coexisten» en `apps/api/app/dashboard/evidence_views.py` (`interpretation_section`) con pruebas en `apps/api/tests/test_evidence_views.py`; tensión `obsolete_with_approved_request` en `apps/api/app/services/graph.py`; estados por objeto en `docs/equivalencias-prisma-startrack.md` (sección «Fechas, unidades y estados separados», `output/matrices/estados-separados.csv`); diagrama 6 `docs/assets/entregables/diagrama-estados.svg`. | `/maquinaria/{id}?mode=fixture` de CF-03 (OBSOLETA en Prisma con solicitud APROBADA: se muestra como tensión, no se «corrige»); `GET /api/v1/graph?mode=fixture` (`tensions`); `docs/entregables-visuales.md`, diagrama 6. | parcial | Con la muestra el caso compara solo hechos de Prisma; la regla Ocupada y Completada se ejercita con casos aislados de prueba, no con datos servidos. Acción: el mismo caso live de RF-04; en la demo decirlo así y no introducir una tarea inventada. |
| RF-06 | Documentar al menos un indicador operativo que la integración haría visible por primera vez, por ejemplo tiempo de equipo fuera de geocerca sin justificación. | Definición única de «tiempo fuera de geocerca sin justificación» en `docs/entregables-visuales.md` (sección RF-06: unidad, cálculo, datos necesarios, decisión, resultado no evaluable). Ocho indicadores calculables por fila en `apps/api/app/services/indicators.py` (`approval_time`, `open_request_age`, `approved_with_unit_without_sent_task`, `occupied_without_project`, `assignment_ended`, `completed_task_without_receipt`, `active_failure_registered`, `evidence_age`) con fichas y SLA propuestos S1–S6 en `docs/indicadores-calculables.md`; pruebas en `apps/api/tests/test_indicators.py`. | `/indicadores?mode=fixture`: el «Tablero de indicadores» (trece cifras agrupadas por Logística, Proyectos, Mantenimiento e Información, cada una con su población y su cobertura, o con el motivo publicado cuando no hay población contable) y, debajo, una pestaña por pregunta con las filas y su estado (evaluable, parcial o no evaluable con motivo) más la pestaña «SLA propuestos» con los umbrales «a validar con ECON»; `GET /api/v1/indicators?mode=fixture`; dossier PDF, ficha RF-06 (páginas 14 a 16). | cumple | RF-06 no es calculable con la muestra (resultado no evaluable, no cero); los indicadores publicados describen filas de la lectura acotada, no la flota, y los umbrales de SLA están «a validar con ECON». Acción: no presentar promedios ni porcentajes. |
| RNF-01 | Toda exploración y prueba exclusivamente sobre el entorno sandbox y los datasets sintéticos provistos por Grupo ECON. | Muestras con hash del documento en `apps/api/app/integrations/data/sandbox_samples.json`; `ALLOW_LIVE_READS`, `ALLOW_LIVE_WRITES` y `AUTO_QUEUE_TRANSFERS` en `false` por defecto (`apps/api/app/core/config.py`); conectores con origen fijo `https://econ-key.maic.ai` y `https://staging.gps.gt/api` (`apps/api/app/integrations/nexus.py`, `startrack.py`, `http.py`); `evidence_kind` `provided_sample`, `live_read` o `test_case` en `apps/api/app/models/hub.py`; pruebas `apps/api/tests/test_security.py`, `test_nexus.py`, `test_startrack.py`. | `/fuentes?mode=fixture` (procedencia, alcance y estado de cada fuente); cada ficha lleva «Datos sintéticos». | cumple | Ninguna. Mantener la distinción fixture, live y caso de prueba en cada captura, cifra y demostración. |
| RNF-02 | La matriz de mapeo y la de responsabilidades en formato legible y reutilizable (hoja de cálculo o tabla estructurada), no solo texto libre. | `scripts/docs/exportar_matrices.py` copia las tablas Markdown de `docs/equivalencias-prisma-startrack.md` y de esta matriz a `output/matrices/*.csv` (17 CSV UTF-8 con cabecera) y `output/matrices/matrices-econ.xlsx` (openpyxl 3.1.5, una hoja por tabla), con `manifest.json` y `MANIFEST.md` (SHA-256 del origen y de cada archivo); `--check` en `scripts/check.sh` y en CI. | `output/matrices/MANIFEST.md`; abrir `matrices-econ.xlsx`; guía en `README.md` («Cómo revisar las matrices»). | cumple | El PDF `output/pdf/ECON-diccionario-mapeo-y-manual-integracion.pdf` (34 páginas, 12/09/2026) no tiene generador y no se regenera; el formato reutilizable vigente es Markdown más CSV/XLSX. Acción: regenerar tras cada edición (CI lo exige). |
| RNF-03 | Prototipo como dashboard, aplicación web o modelo de datos con interfaz mínima; navegable por el jurado. | Aplicación Dash y FastAPI en un proceso (`apps/api/app/main.py`); páginas en la tabla `PAGES` de `apps/api/app/dashboard/views.py`; accesibilidad por teclado en `docs/frontend-architecture.md` (sección «Accesibilidad»); capturas a 1280 y 390 px en `docs/screenshots/2026-09-13-*.png`; pruebas de callbacks y navegación en `apps/api/tests/test_dashboard.py`, `test_workflow_ui.py` y `test_auth_ui.py`. | `http://127.0.0.1:8050/` tras `/login`; guion de diez pasos en `README.md` («Guion de demo para el jurado»). | cumple | Navegabilidad y completitud de datos son dimensiones distintas: los faltantes de RF-04 y RF-05 siguen visibles. Acción: ensayar el guion sobre la entrega final. |
| RNF-04 | Repositorio o carpeta de entrega con README que explique cómo revisar el prototipo y las matrices. | `README.md` (Inicio, Recorrido, Guion de demo para el jurado, Cómo revisar las matrices, Sesión y roles, Verificar y desplegar), `docs/README.md` (índice) y `apps/api/README.md`; enlaces relativos comprobados. | `README.md`. | cumple | Mantener los enlaces y los encabezados cuando cambien los documentos. |
| §9 Matriz de mapeo de campos | Hoja de cálculo o tabla estructurada, incluidos los casos sin equivalente directo; medio: reporte en PDF. | Markdown y CSV/XLSX de RF-02 y RNF-02; el dossier `output/pdf/ECON-entregables-visuales.pdf` (16 páginas, 13/09/2026, `output/pdf/MANIFEST.md`) incluye RACI y diagramas, no la matriz completa; el PDF de 34 páginas del 12/09/2026 contiene una versión anterior sin generador. | `output/matrices/MANIFEST.md`; `output/pdf/MANIFEST.md`. | parcial | No existe un PDF vigente de la matriz completa. Acción: añadir a `scripts/docs/generar_dossier.py` un PDF de la matriz desde el Markdown, o entregar XLSX más Markdown declarándolo en la presentación. |
| §9 Matriz de responsabilidades | Tabla de roles frente a la plataforma integrada, al menos las tres gerencias involucradas; medio: PDF. | RACI de RF-03: `output/matrices/raci-propuesta.csv`, páginas 2 a 4 del dossier PDF (RACI leída del Markdown por `scripts/docs/generar_dossier.py`), roles de sesión implementados. | Dossier PDF, páginas 2 a 4; `raci-propuesta.csv`; `/administracion`. | cumple | Rótulo de propuesta hasta la validación empresarial; las tres gerencias deben seguir visibles al resumirla. |
| §9 Prototipo o mockup navegable | Al menos una consulta unificada; enlace o repositorio con instrucciones; el jurado elige un equipo o partida del sandbox y observa estado, ubicación y discrepancias. | Aplicación de RNF-03; `scripts/dev.sh`, `docs/desarrollo.md`; guion en `README.md`; en `live` (solo si el servidor lo habilita con credenciales) cualquier unidad o solicitud leída de Prisma se consulta por su ID. | `/maquinaria?mode=fixture` (el jurado elige entre CF-01, CF-02, CF-03, EXC-01 y EXC-02) y su detalle; `/solicitudes?mode=fixture`. | parcial | La consulta unificada con ambas plataformas depende de RF-04: con la muestra el jurado ve Prisma y faltantes explícitos; con `live` la lectura de Startrack sigue sin validar. Acción: cadena live verificada o declararlo en la demo. |
| §9 Diagrama de arquitectura | Componentes, flujo de datos entre Prisma, Startrack y el prototipo, y dónde vive cada estado; medio: PDF. | Diagrama 3 (`docs/assets/entregables/diagrama-actual.svg` y `.png`) y diagrama 6 «dónde vive cada estado» (`diagrama-estados.svg` y `.png`), generados por `scripts/docs/generar_dossier.py` y registrados en `docs/assets/entregables/manifest.json`; texto y mermaid en `docs/entregables-visuales.md` y `docs/solucion-integracion.md` (sección «Arquitectura implementada»). | `docs/entregables-visuales.md` (diagramas 3 y 6); dossier PDF, páginas 8 a 13. | cumple | Los diagramas 4 y 5 son propuestas (sincronización y escala) y así se rotulan. Acción: mantener la separación implementado y propuesto en la presentación. |
| §9 Documento de decisiones técnicas | Máximo dos páginas: qué se mapeó, qué se dejó fuera de alcance y por qué; medio: PDF. | `docs/decisiones-tecnicas.md` y `output/pdf/ECON-decisiones-tecnicas.pdf` (2 páginas, 13/09/2026, SHA-256 en `output/pdf/MANIFEST.md`); `scripts/docs/generar_dossier.py` falla si supera dos páginas. | `output/pdf/ECON-decisiones-tecnicas.pdf`; `docs/decisiones-tecnicas.md`. | cumple | Regenerar el PDF cuando cambie el Markdown y registrar el hash. |
| §9 Presentación final | Máximo diez diapositivas: problema, solución, arquitectura, matrices y valor para Grupo ECON, con bloque de reflexión de aprendizaje; presentación en vivo. | No existe en el repositorio. Insumos disponibles: dossier PDF (páginas 1 a 4: requisitos y RACI; 8 a 13: diagramas; 14 a 16: casos, RF-06 y recorrido) y guion de demo del `README.md`. | — | pendiente | Acción: producir el archivo, contar diapositivas, incluir la reflexión real del equipo y mantener separadas capacidades implementadas y propuestas. |
| §6 Arquitectura de integración vía API (obligatorio) | Propuesta de arquitectura de integración entre ambas plataformas, más allá del mockup, con manejo de errores y sincronización de estados. | Estados de envío `draft`, `blocked`, `queued`, `sending`, `sent`, `unknown` y `failed` con conciliación sin reenviar y cierre explícito (`POST /api/v1/operations/{id}/resolve`) en `apps/api/app/services/workflow.py` y `ledger.py`; cola transaccional, exclusividad en vuelo por máquina, `job_id` único y `operation_events` append-only (migración `0004_guards`; pruebas PostgreSQL `apps/api/tests/test_postgres_*.py` ejecutadas en CI); `docs/solucion-integracion.md` (secciones «Estados de envío y evidencia independiente» y «Tiempos del traslado»), `docs/adr/0004-persistent-transfer-workflow.md`, `docs/adr/0006-postgresql-unica-infraestructura-de-estado.md`; propuesta de sincronización y discrepancias en `docs/sincronizacion-y-discrepancias.md`. | `/operaciones/{id}?mode=fixture` (estados, eventos y actor); `/integracion?mode=fixture` (payload preparado y respuesta esperada); Swagger `/docs` (`POST /api/v1/operations/{id}/resolve`, `GET /api/v1/status`). | cumple | La creación autenticada de tareas en la cuenta Startrack sigue sin validar y la detección de cambios de Prisma posteriores al envío es una señal del grafo (`movement_source_changed`), no una incidencia durable. Acción: validar credenciales y contrato; mantener la sincronización propuesta rotulada como tal. |
| §6 Panel de indicadores (deseable) | Panel que aborde al menos un síntoma identificado por ECON: tiempos muertos, baja trazabilidad o ausencia de indicadores unificados. | Página `/indicadores` (`apps/api/app/dashboard/indicator_views.py` con `kpi_views.py`) sobre `GET /api/v1/indicators` (`apps/api/app/api/indicators.py`, `apps/api/app/services/indicators.py`): tablero de trece cifras agrupadas por el área que decide —Logística, Proyectos, Mantenimiento e Información—, cada una con su población, su cobertura y el enlace a las filas que la sustentan, y debajo una pestaña por pregunta (lectura en lenguaje llano, filas y cobertura) más la pestaña «SLA propuestos»; reglas del tablero en `docs/kpis-tablero.md`. Página `/decisiones` (`views.py::decisions`, la misma que la portada `/`) con «Qué pasa · Agenda de uso y asignación» sobre el período de uso solicitado y «Qué hago · Acciones por solicitud» con un asunto por solicitud, su hecho observado y su siguiente paso (`decision_priorities.py`, `decision_analytics.py`); el conteo por estado de solicitud queda como tabla en el desplegable «Datos de la agenda». Fichas y SLA en `docs/indicadores-calculables.md`; pruebas `apps/api/tests/test_indicator_views.py` y `test_decision_priorities.py`. | `/indicadores?mode=fixture`; `/decisiones?mode=fixture`; `GET /api/v1/indicators?mode=fixture`. | cumple | Con la muestra la mayoría de las cifras y fichas queda «no evaluable» con motivo (sin corte, sin tareas) y ninguna publica promedios: el panel muestra cobertura, no desempeño. Corrección del 13/09/2026: esta celda citaba «las tres lecturas más accionables de los indicadores» y una «distribución por estado» en `/decisiones`; ninguna de las dos existe hoy —`indicator_insights` dejó de montarse en esa página y el gráfico de estados se retiró de la portada—, y la capacidad que sostiene el veredicto es ahora el tablero de `/indicadores`. Pendiente: `indicator_insights` y `top_insights` siguen en `indicator_views.py` sin uso en ninguna página. Acción: en `live` completar el registro antes de leerlo como serie. |
| §6 Escalabilidad y portal futuro (deseable) | Propuesta de cómo el mismo modelo podría extenderse a mayor escala, como un portal con visibilidad de tiempos de logística y disponibilidad de equipo. | Propuesta en `docs/sincronizacion-y-discrepancias.md` (sección «Escala a miles de vehículos (propuesta)»), diagrama 5 `docs/assets/entregables/diagrama-escala.svg`, extrapolación de retención y volumen en `docs/database.md`, y límites en `docs/adr/0006-postgresql-unica-infraestructura-de-estado.md`. | `docs/entregables-visuales.md` (diagrama 5); dossier PDF, páginas 8 a 13. | cumple | Es una propuesta sin capacidad demostrada: faltan mediciones de carga, latencia y recuperación. Acción: presentarla como propuesta, no como despliegue. |

Recuento: **13 cumple, 5 parcial, 1 pendiente**. Las cinco filas parciales
comparten dos causas: la muestra no contiene ninguna cadena con evidencia de
las dos plataformas (RF-04, RF-05, prototipo) y el cotejo o el formato final de
la matriz de mapeo (RF-02, PDF de §9). Cerrarlas exige una lectura autenticada
de Startrack y trabajo documental, no inventar registros.

## Lecturas del brief que condicionan la matriz

Los comentarios editoriales **16 y 27** sugieren tratar diagrama de arquitectura
y decisiones técnicas como deseables. El cuerpo de la sección 9 los conserva
en la tabla de entregables; esta contradicción se registra y no se resuelve
borrando las filas. Producirlos cubre ambas lecturas. La FAQ de la sección 19
aclara que una conexión API en vivo **no es obligatoria**; un mockup navegable
sobre datos sandbox puede satisfacer la modalidad de prototipo. Esto no elimina
el contenido de RF-04 y RF-05 ni autoriza a inventar registros.

El panel de indicadores y la extensión a mayor escala figuran como **deseables**
en la sección 6. La documentación de al menos un indicador sigue siendo RF-06.
AS-IS y TO-BE son insumos de proceso: una versión explicativa ayuda al jurado,
pero no reemplaza el diagrama técnico de arquitectura. La sección 9 fija
**domingo 10:00** para todos los entregables y el medio PDF para matrices,
diagrama y decisiones; el prototipo se entrega como demo en vivo con scripts y
documentación.

La rúbrica de la sección 13 evalúa directamente: matriz completa y honesta
(2.1), fuente de verdad y conflictos de estado (2.2), consulta en vivo y
discrepancia resuelta con una regla (3.1 y 3.2), RACI utilizable (3.4) y
reflexión de aprendizaje (4.2). Las filas RF-04, RF-05 y §9 Presentación son
las que hoy limitan esos puntajes.

## Lectura de los procesos y casos para los diagramas

| Fuente | Hecho o intención que debe verse | Límite que debe conservarse |
| --- | --- | --- |
| AS-IS | Solicitud del proyecto, coordinación de Logística, revisión de disponibilidad, asignación, ejecución, bitácora y mantenimiento. Coordinación manual y secuencial. | El ramal «NO» de disponibilidad es gráficamente ambiguo. No resolverlo como regla ejecutable sin confirmación. El dibujo no nombra endpoints ni expande PDA/C.C. |
| TO-BE, planificación | Una **solicitud aprobada** viaja como tarea; Logística asigna equipo, operador y tarifa, y consulta ubicación/disponibilidad. | La flecha automática expresa una meta. No parte de la mera creación del proyecto y no demuestra que exista webhook o creación validada en esa cuenta. |
| TO-BE, ejecución/control | Bitácoras, alertas de paro, mantenimiento, restablecimiento de disponibilidad y retroalimentación de costos. | La creación de mantenimiento por API y la sincronización de estados son intenciones; faltan contratos y reglas. El flujo vigente de ECON no escribe esas actualizaciones en Prisma. |
| Caso 01 | Relacionar solicitud aprobada, maquinaria y tarea de traslado pendiente por identidad; conservar el proyecto. | CF-03/MOT-014/PROY-014 pertenecen al walkthrough. Sus fechas 12–20/09 no reemplazan las fechas 11–14/09 del ejemplo OpenAPI; son fuentes distintas. |
| Caso 02 | Maquinaria **Ocupada** y tarea **Completada** describen objetos diferentes y pueden coexistir. | Resolver significa interpretar los hechos; no cambiar uno para igualarlo al otro. La tarea completada no acredita recepción. |
| Caso 03 | Mantenimiento correctivo y traslado pendiente, vinculados al mismo recurso, justifican revisar la viabilidad del traslado. | El texto del caso usa «Obsoleta (mantenimiento correctivo)»; el ejemplo actual trae OBSOLETA y no demuestra esa falla. No convertir etiquetas distintas en una avería confirmada. |
| Contexto vigente | Proyecto → solicitud → asignación concreta → movimiento/tarea → presencia observada → recepción explícita. | Solicitud, máquina, mantenimiento, envío, tarea, presencia y recepción conservan estados independientes. La geocerca puede observar al transportador o teléfono, no necesariamente a la máquina. |

La asignación confirmada del kit es **RE-03 / MOT-006 / PROY-006**. No se mezcla
con CF-03/MOT-014/PROY-014, con MOT-015 del ejemplo de detalle del contrato ni con
los IDs de pruebas. La captura posterior de PROY-006 no muestra UUID: no permite
completar una unión técnica por nombre.

## Roles documentados y responsabilidades propuestas

**Confirmado en los documentos** significa que el actor aparece en la fuente;
no que una persona de ECON haya aprobado la RACI del prototipo. Los organigramas
transcriben jerarquías. Los roles de sesión de la aplicación
([ADR 0005](adr/0005-session-auth-and-roles.md)) aplican permisos derivados de
esta propuesta; no sustituyen su validación empresarial.

| Actor o rol | Presencia documentada | Alcance confirmado por la fuente | Qué permanece propuesto |
| --- | --- | --- | --- |
| Gerencia Técnica de Proyectos / Gerencia de Proyecto | Brief, AS-IS, TO-BE y organigrama de Gerencia Técnica. | Planificación, programación y solicitud de recursos; Prisma identifica al solicitante como Gerente de Proyecto. | Aprobación de reglas del indicador y de evidencia de recepción; delegación a un receptor concreto. No se equiparan todos los niveles del organigrama. Rol de sesión `gerencia_proyecto` (lee y declara recepción). |
| Gerencia de Logística y Equipo(s) | Brief, AS-IS y TO-BE. | Seguimiento de solicitudes, asignación y coordinación operativa; el TO-BE añade equipo, operador y tarifa. | R/A por correspondencias técnicas, programación, envío y atención de discrepancias. El organigrama usa también «Gerencia de Maquinaria y Equipo»; validar la denominación organizativa. Rol de sesión `logistica` (guarda planes, encola, sincroniza y declara recepción). |
| Gerencia de Mantenimiento | Brief, AS-IS, TO-BE y organigrama específico. | Revisar condición, atender mantenimiento/reparación y confirmar disponibilidad; el TO-BE evalúa el paro. | Aprobación del catálogo canónico, vigencia de restricciones y política de liberación dentro de la integración. Rol de sesión `mantenimiento` (solo lectura). |
| Operadores de Equipos / motorista | AS-IS, TO-BE y casos de uso. | Bitácoras, alertas y ejecución asociada al recurso del caso. | Equivalencia entre ID de operador Prisma, conductor del vehículo y usuario Startrack asignable. Sin rol de sesión propio. |
| Licitaciones | AS-IS, TO-BE y organigrama técnico. | Preparación de requerimientos/oferta y entrega al proyecto. | Participación en la RACI de integración si el alcance se extiende a preconstrucción. |
| Control de Costos | AS-IS, TO-BE y organigrama técnico. | Recibir bitácoras; el TO-BE especifica validación e imputación de costos a partidas. | Política de indicador económico y responsabilidades sobre nuevos datos del hub. Rol de sesión `control_costos` (solo lectura). |
| Soporte de integración / administrador técnico | La propuesta técnica actual necesita estas funciones. | No es una aprobación de ECON de un cargo o persona asignados al hub. | Operar conectores, gestionar credenciales, resolver incidencias técnicas y conservar evidencia. Rol de sesión `admin` (todos los permisos, administra usuarios). |
| Responsable receptor del proyecto | Introducido en el flujo vigente como función de recepción. | La aplicación almacena una declaración con receptor, instante y referencia. | Quién está autorizado a recibir, cómo se acredita y quién aprueba su constancia. Declarar exige el permiso `declare_reception` y el usuario autenticado queda vinculado a la declaración (`declared_by_*`, migración `0004_guards`); ese vínculo registra quién la escribió, no acredita su autoridad empresarial para recibir. |

La [RACI de las equivalencias](equivalencias-prisma-startrack.md#responsabilidades-propuestas-para-confirmar)
es el documento de trabajo actual. Las tres gerencias exigidas deben seguir
visibles incluso al resumirla para el PDF o la presentación.

## Cobertura del diccionario y brechas de mapeo

El diccionario contiene **12 definiciones Prisma y 39 Startrack**: 51 filas,
incluido un nombre repetido. No son 51 columnas API ni un modelo relacional
aprobado. El glosario define módulo, campo, descripción, tipo, ejemplo y valores
posibles; las instrucciones limitan el libro a los campos priorizados del reto.

| Plataforma / módulo | Filas originales y cantidad | Cómo se usa en las matrices y visuales | Brecha que requiere anotación |
| --- | --- | --- | --- |
| Prisma / Maquinaria | [4–8; 5 campos](onedrive/06-diccionario-de-datos/02-prisma.md#fila-4) | Empresa, activo, nombre, clase y estado administrativo. | Empresa no acredita entidad legal ni ID global; activo/nombre no validan identidad Startrack. Estado no se iguala al estado de tarea. |
| Prisma / Solicitudes | [10–15; 6 campos](onedrive/06-diccionario-de-datos/02-prisma.md#fila-10) | Proyecto, tipo, solicitante, período, estado y unidad asignada sostienen la consulta y el calendario. | El libro no aporta un ID inequívoco de solicitud; el contrato suministrado añade UUID. Período es uso, no plazo de entrega; solicitante no es receptor ni motorista. |
| Prisma / Mantenimiento | [17; 1 campo](onedrive/06-diccionario-de-datos/02-prisma.md#fila-17) | Mantener el valor original y explicar su objeto. | «Estado  » tiene espacios y ejemplo compuesto «CF-03 - Obsoleto». Falta validar catálogo y relación con falla/paro. |
| Startrack / Vehículos | [4–14; 11 campos](onedrive/06-diccionario-de-datos/03-startrack.md#fila-4) | Identidad del activo, atributos descriptivos y conductor; separados de solicitud/tarea. | Descripción e ID remoto no son el ID interno acreditado; Normal carece de catálogo exhaustivo. Grupo/etiqueta no equivalen automáticamente a Empresa. |
| Startrack / Geocercas | [16–21; 6 campos](onedrive/06-diccionario-de-datos/03-startrack.md#fila-16) | Destino y geometría conceptual con correspondencia de proyecto explícita. | GEO-014 es ID del ejercicio. Los enteros de coordenadas no tienen escala documentada; no dibujar puntos inferidos. El nombre compartido no prueba una relación 1:1. |
| Startrack / Tareas | [23–33; 11 campos](onedrive/06-diccionario-de-datos/03-startrack.md#fila-23) | ID, título, contenido, tipo, estado, programación, origen/destino y asignados. | «TAR-014» aparece como tipo de Título; conservar anomalía. Fecha programada no equivale al período Prisma. Origen y otras opciones de pantalla no tienen soporte acreditado en el borrador actual. |
| Startrack / Mantenimiento | [35–45; 11 filas](onedrive/06-diccionario-de-datos/03-startrack.md#fila-35) | Vehículo, servicio, fecha/hora, odómetro, horómetro, motivo, proveedor, mecánico y tipo de servicio. | No hay integración de mantenimiento demostrada. Horas y kilómetros son magnitudes distintas; faltan escala y zona temporal. Filas 44/45 repiten «Anadir tipo de servicio» y deben conservar referencias separadas. |

Las tablas de equivalencias deben mostrar los campos sin destino o sin soporte
con el mismo rigor que las correspondencias. Nombres idénticos no establecen
identidad; un ejemplo no define nulabilidad, catálogo completo ni contrato API.

## Indicadores

La fuente única de los indicadores es
[indicadores calculables](indicadores-calculables.md): fichas I1 a I8 de
`GET /api/v1/indicators` (pregunta, grano, población, fórmula con los campos
exactos, exclusiones, fechas, unidad y estado), SLA propuestos S1 a S6 con
umbrales «a validar con ECON», qué impide agregar y qué lecturas no
implementadas habilitarían más. La definición de RF-06 vive en
[entregables visuales](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado)
y los requisitos previos a cualquier medición nueva, en
[contexto vigente](contexto-vigente.md#límites-de-los-datos). Esta matriz no
repite fórmulas: una ausencia se publica como «no evaluable» o «sin casos
evaluables», nunca como cero, y no se adoptan umbrales ni metas atribuidas a ISO.

## Coherencia documental al cerrar la entrega

El [contexto vigente](contexto-vigente.md), la
[guía de analítica](analitica-decisiones.md) y el
[diccionario vigente](diccionario-modelo-econ.md) describen la documentación
actualizada. El inventario anterior de modelo operativo queda sustituido por el
diccionario generado. No recuperar sus tres equipos/tres solicitudes inventados,
sus pantallas anteriores ni sus afirmaciones de falta de persistencia como
descripción del producto actual.

El paquete final debe identificar qué visuales describen el AS-IS del kit, cuáles
explican el TO-BE y cuáles representan código implementado. La exportación PDF
(16 y 2 páginas, [manifiesto](../output/pdf/MANIFEST.md)), las matrices CSV/XLSX
([manifiesto](../output/matrices/MANIFEST.md), incluida esta trazabilidad) y el
diccionario se verifican con `scripts/check.sh` y en CI; las diez diapositivas
de presentación siguen pendientes y se contarán sobre el archivo final. El guion
de la prueba en vivo está en el [README](../README.md#guion-de-demo-para-el-jurado).
Esta matriz no modifica las fuentes de `docs/onedrive`.
