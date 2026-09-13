# Auditoría de requisitos y entregables ECON

**12 de septiembre de 2026.** La documentación local cubre el inventario de
campos, la RACI propuesta, indicadores definidos y diagramas. Siguen pendientes
la demostración integrada de RF-04/RF-05, el cotejo exhaustivo de RF-02, la
presentación final y la reproducción de uno de los tres PDFs.

Esta auditoría distingue una obligación del brief, una propuesta de evolución y
una capacidad demostrada. No modifica las fuentes, configura proveedores ni
autoriza escrituras remotas. Los issues consolidados se conservan en
[el registro de creación](../output/auditoria-2026-09-12/issues-creados.json) y
[el índice de seguimiento](../output/auditoria-2026-09-12/README.md).
La revisión técnica complementaria está en
[arquitectura y eventos](auditoria-arquitectura-eventos-2026-09-12.md).

## Alcance y procedencia

El universo documental incluye los 21 Markdown de `docs/onedrive`: introducción,
confidencialidad, brief, guía de diagramas, AS-IS, TO-BE, organigramas, casos,
accesos/manuales, extracto Nexus, cuatro hojas y el índice del diccionario,
propuesta original, análisis, contexto de conversación, contexto para IA,
inventario e índice general. Se contrastaron requisitos y tablas prioritarias
con los documentos actuales, modelos de lectura, scripts documentales y tres
PDFs de `output/pdf`.

No se repitió la conversión ni la comparación binaria de los originales. Los
conteos históricos de 11 archivos del ZIP, 338 celdas y nueve páginas del manual
Nexus proceden del [inventario de conversión](onedrive/INVENTARIO.md) y del
[índice del diccionario](onedrive/06-diccionario-de-datos/README.md). El análisis
de acceso conserva los límites históricos del kit y no reproduce credenciales.

| Fuente | Criterio aplicado |
| --- | --- |
| [Introducción](onedrive/00-introduccion-equipo.md) | RE-03/MOT-006/PROY-006 es la asignación del equipo; los casos del walkthrough permanecen separados. Los diagramas no imponen una arquitectura técnica. |
| [Brief](onedrive/02-brief-del-reto.md), secciones 6, 7, 9 y 19 | Seis RF, cuatro RNF, entregables y modalidad de demostración. La API live no es obligatoria. |
| [AS-IS](onedrive/03-as-is.md), [TO-BE](onedrive/03-to-be.md), [guía](onedrive/03-diagramas-de-procesos.md) | Proceso actual y objetivo; las flechas de integración no acreditan endpoints o webhooks disponibles. |
| [Casos](onedrive/04-casos-de-uso.md) | Solicitud/traslado, estados de objetos diferentes y restricción de mantenimiento. Son referencias; no órdenes para recrear esos escenarios en proveedores. |
| [Organigramas](onedrive/03-organigramas.md) y [manual Nexus](onedrive/05-manual-nexus.md) | Actores y pasos administrativos; no equivalen a una RACI aprobada ni a contratos técnicos. |
| [Diccionario](onedrive/06-diccionario-de-datos/README.md) | 51 definiciones priorizadas: 12 Prisma y 39 Startrack, incluido un duplicado. No son 51 columnas API. |
| [Propuesta original](onedrive/07-propuesta-original.md), [análisis](onedrive/08-analisis-propuesta.md), [contexto histórico](onedrive/09-contexto-conversacion.md) | Hipótesis y etapas anteriores, subordinadas al contexto vigente para describir la implementación actual. |
| [Contexto vigente](contexto-vigente.md), [revisión](revision-contexto.md), [equivalencias](equivalencias-prisma-startrack.md), [servicio](../apps/api/README.md) | Python/Dash/FastAPI, persistencia, worker explícito, estados separados y límites del sandbox. |

## Baseline compartido y entrega local

Durante la inspección, la rama fue `feat/operations-hub-foundation`. El código
existente y la matriz de equivalencias pertenecían al material versionado. En
cambio, `git status --short` y `git ls-files` mostraron como **no versionados**
`output/`, `scripts/docs/`, la matriz de requisitos, el diccionario generado,
el manual, las decisiones, el índice visual y las propuestas de sincronización
y escala. Los README y diversos documentos de contexto tenían modificaciones
locales previas. Esos cambios se conservaron.

Por tanto, «cubierto localmente» no significa «disponible en un clon del baseline».
Tampoco corresponde abrir un issue por ausencia de una RACI, indicador o diagrama
que ya existe en la entrega local. El cierre de la entrega requiere incluir sus
fuentes y artefactos en el canal compartido acordado; esta auditoría no hace
commit ni altera el trabajo previo.

## Matriz completa RF/RNF

Las ubicaciones de línea siguientes corresponden al árbol inspeccionado; pueden
cambiar con ediciones posteriores. El texto literal permanece en el brief.

| Requisito y fuente | Evidencia concreta | Estado y condición de cierre |
| --- | --- | --- |
| RF-01, brief:214. Inventario de términos/campos nuevos con tipo y ejemplo. | [Diccionario ECON](diccionario-modelo-econ.md): 25 modelos y 242 campos declarados, más derivaciones de presentación; [generador](../scripts/docs/generar_diccionario.py) con `--check`. | **Cubierto localmente en el alcance declarado.** El check pasó; ejemplos técnicos distinguidos de muestras. No implica cubrir cada propiedad visual ni DTO externo. |
| RF-02, brief:215. Mapeo relevante con ausencias explícitas. | [Equivalencias](equivalencias-prisma-startrack.md), formulario/API, cardinalidades y clasificación; 51 definiciones transcritas en el manual PDF. | **Parcial.** Falta cotejo explícito por cada fila priorizada del libro; transcribir no equivale a mapear. La [matriz vigente](matriz-requisitos-entregables.md):49 reconoce la brecha. |
| RF-03, brief:216. Responsabilidades de al menos tres roles. | RACI de [equivalencias](equivalencias-prisma-startrack.md):350-371; dossier PDF, página 4. | **Cubierto como propuesta documental.** Incluye Proyecto/Técnica, Logística y Mantenimiento. Validación empresarial pendiente; el brief no exige una firma. |
| RF-04, brief:217. Estado y ubicación de al menos un equipo combinando plataformas. | Dash consulta solicitudes/unidades y registra operaciones; [fixtures.py](../apps/api/app/integrations/fixtures.py):16-88 devuelve equipos/solicitudes; matriz vigente:51. | **No demostrado con evidencia combinada.** La muestra no incluye tarea ni ubicación. Hace falta cadena vinculada suministrada o verificada del sandbox. |
| RF-05, brief:218. Diferencia visual de estados e interpretación/resolución. | Modelos preservan hechos separados; caso 02 y dossier página 13 explican Ocupada/Completada; matriz vigente:52. | **Parcial, falta demostración UI.** APROBADA/OBSOLETA de Prisma no constituye comparación entre plataformas. No se fabrican registros para cerrar la brecha. |
| RF-06, brief:219. Documentar al menos un indicador nuevo habilitado por integración. | [Ficha del paquete visual](entregables-visuales.md), tiempo fuera de geocerca sin justificación, fórmula, población, cobertura, exclusiones y responsables; dossier página 14. | **Cubierto documentalmente.** El requisito no exige calcularlo sin datos ni demostrar ahorro económico. |
| RNF-01, brief:225. Sandbox/datasets sintéticos provistos. | Procedencia, separación fixture/live, destinos sandbox, permisos remotos desactivados por defecto y faltantes visibles. | **Alineado con la evidencia revisada.** No se consultaron proveedores en esta auditoría. Los tests aislados no sustituyen el dataset suministrado en la demo. |
| RNF-02, brief:226. Matrices legibles y reutilizables. | Tablas Markdown y matrices en PDFs de 15 y 34 páginas. | **Cubierto en formato.** RACI p. 4 y tabla de diccionario p. 33 inspeccionadas visualmente. La completitud semántica de RF-02 sigue pendiente. |
| RNF-03, brief:227. Prototipo navegable por jurado. | Dash/FastAPI, rutas e instrucciones de ejecución y evidencias previas de escritorio/móvil/teclado. | **Implementado; ensayo final pendiente.** Esta auditoría no repitió un E2E de navegador. La navegación no subsana RF-04/RF-05. |
| RNF-04, brief:228. README para revisar prototipo y matrices. | [README raíz](../README.md), [índice documental](README.md), [README del servicio](../apps/api/README.md) y [paquete visual](entregables-visuales.md). | **Cubierto localmente.** Verificar enlaces y disponibilidad desde la entrega compartida final. |

## Entregables de la sección 9

| Entregable y referencia | Artefacto local | Resultado |
| --- | --- | --- |
| Matriz de campos, brief:256 | Equivalencias Markdown y manual PDF de 34 páginas. | Existe; cierre exhaustivo RF-02 pendiente. |
| Matriz de responsabilidades, brief:257 | Equivalencias Markdown y dossier página 4. | Existe y es legible; propuesta, no política aprobada. |
| Prototipo o mockup, brief:258 | Aplicación Python y scripts de ejecución. | Navegable según verificaciones previas; consulta integrada acreditada pendiente. |
| Diagrama de arquitectura, brief:260 | Dossier páginas 8-12; arquitectura implementada y ampliaciones diferenciadas. | Existe. No equivale a despliegue de Kafka ni a capacidad masiva medida. |
| Decisiones técnicas, brief:261 | `output/pdf/ECON-decisiones-tecnicas.pdf`. | **2 páginas**, cumple el máximo. |
| Presentación final, brief:262 | No se encontró PPTX/ODP ni artefacto de presentación final. | **Pendiente:** máximo diez diapositivas con reflexión de aprendizaje. El dossier de 15 páginas no lo sustituye. |

La demo de la sección 9 permite al jurado elegir un equipo o partida no anunciado
(brief:272). El alcance accesible debe declararse y el recorrido no debe depender
de una única fila fija. La FAQ, brief:457-459, permite un mockup navegable sobre
datos sandbox: obtener una exportación autorizada es una vía válida para aportar
evidencia sin exigir una conexión live durante la presentación.

## Brechas verificadas y criterios de aceptación

| Prioridad | Trabajo | Criterio de aceptación |
| --- | --- | --- |
| P1 | Demostración RF-04/RF-05 con evidencia Prisma/Startrack. | IDs, entorno y tiempos conservados; correspondencias revisadas; selección de registros del alcance; estado de máquina, tarea y ubicación fechada visibles; interpretación de estados distintos sin cierre por geocerca; faltantes explícitos. No inventar tareas, GPS o recepciones. |
| P1 | Cotejo de las 51 definiciones para RF-02. | Cada fila original tiene destino o ausencia, transformación/cardinalidad, motivo, fuente y validación; se preservan las filas Startrack 44/45. Revisión automática de cobertura y tabla PDF legible. |
| P1 | Presentación final. | Máximo diez diapositivas editables/presentables: problema, solución, arquitectura, matrices, valor y reflexión real del equipo; límites de evidencia y guion de demo; enlace desde la entrega. |
| P2 | Reproducción de los tres PDFs. | Builder versionable del manual completo, dependencias/comando documentados, generación desde Markdown sin proveedores y checks de contenido, páginas y enlaces, con revisión visual. |

RF-02 tiene ausencias concretas en el cotejo: mantenimiento Startrack
«Proveedor», «Mecanico» y ambas filas «Anadir tipo de servicio» aparecen en el
diccionario, pero no tienen resolución individual en las equivalencias.
«Color» del vehículo es otro ejemplo. La tabla de
`docs/equivalencias-prisma-startrack.md:216-222` agrupa límites de vehículos y
mantenimiento; no resuelve cada definición. Un campo puede quedar fuera del
flujo, pero debe marcarse y justificarse expresamente.

La brecha de reproducción se observa en
`scripts/docs/generar_dossier.py:890-916`: solo genera el dossier y las decisiones,
y comprueba 15 y 2 páginas. Los comandos publicados en
`docs/entregables-visuales.md:155-161` no reconstruyen
`ECON-diccionario-mapeo-y-manual-integracion.pdf`, aunque el índice y el propio
dossier lo anuncian. `scripts/check.ps1:6-8` limita Ruff al proyecto `apps/api`;
los scripts documentales requieren su propia comprobación de entrega.

## Seguimiento previo y repositorios

La consolidación conserva los issues históricos de `econ-protocol` como
antecedentes. Los nuevos issues focalizados se registran en `econ-operations`,
repositorio de seguimiento activo indicado por la revisión principal. La tabla
no afirma que esos issues históricos estén cerrados o que su cuerpo siga
describiendo el producto vigente.

| Antecedente en econ-protocol | Tratamiento recomendado |
| --- | --- |
| [#1: mapeo/RACI](https://github.com/Los-Filosofos/econ-protocol/issues/1) | Ya rastrea el tema general. Vincular el cierre específico de 51 filas; no volver a declarar ausente toda la RACI. |
| [#2: acceso](https://github.com/Los-Filosofos/econ-protocol/issues/2) | Antecedente de validación de acceso; distinguir login web, API autenticada y permisos de la cuenta. |
| [#8: proyección unificada](https://github.com/Los-Filosofos/econ-protocol/issues/8) | Vincular con RF-04/RF-05 y con la proyección de operaciones; evitar duplicado general. |
| [#10: SDK/ubicación](https://github.com/Los-Filosofos/econ-protocol/issues/10) | SDK implementado no acredita observación integrada demostrada; conservar dependencia. |
| [#14: validación](https://github.com/Los-Filosofos/econ-protocol/issues/14) | Relacionar comprobaciones actuales y ensayo de demo pendiente. |
| [#4: login](https://github.com/Los-Filosofos/econ-protocol/issues/4), [#11: React](https://github.com/Los-Filosofos/econ-protocol/issues/11), [#13: cards](https://github.com/Los-Filosofos/econ-protocol/issues/13) | **Recomendar triage solamente.** Reemplazados por instrucciones actuales: sin login de aplicación, React retirado y sin cards de conteos. No se editaron estos issues. |

## Ambigüedades y límites que se preservan

- Los comentarios editoriales 16/27 sugieren carácter deseable para diagrama y
  decisiones; la tabla principal conserva ambos entregables. Producirlos cubre
  las dos lecturas sin reescribir el brief.
- El manual asocia aprobación con unidad a Ocupada; la muestra aporta una
  solicitud aprobada y CF-03 OBSOLETA. Se conservan ambas evidencias. OBSOLETA no
  identifica por sí sola una avería ni un intervalo de reparación.
- Las fechas del walkthrough y del OpenAPI pertenecen a muestras diferentes.
  RE-03/MOT-006/PROY-006 no se sustituye por CF-03/MOT-014/PROY-014.
- La fuente no acredita escala de las coordenadas enteras del diccionario ni
  catálogo exhaustivo de estado de vehículo. No se normalizan por suposición.
- Organigramas usan denominaciones distintas para Logística/Maquinaria y Equipo;
  una relación jerárquica no constituye aprobación de la RACI del hub.
- La propuesta original de eventos no es contrato del proveedor. La ausencia de
  un webhook Prisma confirmado no impide proponer consultas periódicas; tampoco
  autoriza inventar un endpoint de eventos de aprobación.
- Los indicadores documentados no prueban rendimiento productivo, ahorro,
  cumplimiento ISO ni capacidad de miles de vehículos.

Se conserva el principio visual ECON: colores de imágenes o gráficos deben
servir a la lectura, evidencia o identidad ya definida. Esta auditoría no
introduce una paleta nueva ni recomienda recolorear fuentes sin justificación.
Mantener tokens semánticos, estados en texto, componentes consistentes y la
interfaz sobria solicitada; no restaurar badges decorativos o cards de conteos.

## Verificación efectuada

| Comprobación | Resultado y límite |
| --- | --- |
| `scripts/check.ps1 -Container` | Revisión principal: Ruff y formato correctos, **308 pruebas aprobadas**, imagen Docker construida. No acredita conectividad API ni ensayo visual nuevo. |
| `uv run --project apps/api python scripts/docs/generar_diccionario.py --check` | **Aprobado** en esta auditoría. Coinciden modelos, campos y anotaciones generadas con el documento local. |
| `verified_data()` de `scripts/docs/generar_graficos.py` | **Aprobado** por importación y llamada en lectura: SHA-256 del OpenAPI, referencias JSON, IDs, campos y metadatos de paginación cotejados. Cinco equipos y dos solicitudes. No regeneró ni modificó las muestras. |
| PDF decisiones | pypdf confirmó **2 páginas**; inspección visual de la página 2. |
| PDF dossier visual | pypdf confirmó **15 páginas**; inspección visual de la página 4, RACI. |
| PDF diccionario/manual | pypdf confirmó **34 páginas**; extracción de contenido y recorrido de encabezados; inspección visual de la página 33, mantenimiento y duplicado conservado. |
| Presentación | No se encontró artefacto de presentación final por extensión/nombres; el índice visual declara que el dossier no es una presentación terminada. |
| Git | Diferenciados cambios previos y archivos no versionados. Ningún original ni archivo existente se modificó en este subtrabajo. |

La inspección visual de tres páginas no constituye revisión visual de las 51
páginas de los tres PDFs. No se realizó un nuevo E2E de navegador, escritura en
proveedores, medición de carga ni validación autenticada Startrack. Los renders
de inspección fueron intermediarios temporales y no son entregables.
