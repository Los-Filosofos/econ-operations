# Matriz de requisitos, entregables y evidencia

Revisión documental: **12 de septiembre de 2026**. Esta matriz conecta el
material de Grupo ECON con los documentos, gráficos y diagramas del proyecto.
Describe evidencia disponible y brechas; no otorga una calificación ni declara
completa la integración.

Todo dato operativo del caso es **sintético**. `fixture` distingue muestras
proporcionadas en archivos; `live`, lecturas actuales del sandbox. Ninguno
significa producción. La muestra que sirve la aplicación contiene cinco equipos
de quince declarados y dos solicitudes; no incluye tareas, ubicaciones GPS ni
recepciones. El día del documento no constituye un instante de observación común.

## Fuentes y criterio de lectura

Se leyeron íntegros el [brief](onedrive/02-brief-del-reto.md), el
[AS-IS](onedrive/03-as-is.md), el [TO-BE](onedrive/03-to-be.md), los
[tres casos de uso](onedrive/04-casos-de-uso.md) y las cuatro hojas del
[diccionario](onedrive/06-diccionario-de-datos/README.md), incluidos sus registros
de celdas. Los [organigramas](onedrive/03-organigramas.md) permiten distinguir
actores documentados de responsabilidades propuestas. El contraste de estado
actual usa el [contexto vigente](contexto-vigente.md), las
[equivalencias](equivalencias-prisma-startrack.md), el
[README del servicio](../apps/api/README.md) y los modelos de
[lectura](../apps/api/app/models/hub.py) y
[operaciones](../apps/api/app/models/operations.py).

El brief contiene **seis RF y cuatro RNF**, todos en su sección 7. No aparecen
RF-07, RNF-05 ni requisitos ISO. La sección 6 define alcance; la 9 define
entregables; la 13 contiene una rúbrica propuesta, sujeta a validación. Esos
apartados no se renumeran como requisitos nuevos. Los comentarios editoriales
del Word se conservan como comentarios y no se aplican silenciosamente.

En este documento, **implementado** significa que existe código local y
documentación de verificación; **demostrado con datos** exige registros con
procedencia que sostengan el caso; **propuesto** identifica una decisión o
capacidad que todavía requiere validación. Una prueba con transporte HTTP
controlado no acredita una respuesta autenticada de Startrack.

## Trazabilidad de los requisitos funcionales

Los textos de la segunda columna transcriben la sección 7 del brief. La tercera
columna traduce cada requisito a una evidencia revisable; no añade obligaciones
al documento original.

| Código | Requisito del brief | Entregable visual o documental que lo hace revisable | Evidencia actual | Brecha o condición pendiente |
| --- | --- | --- | --- | --- |
| RF-01 | El equipo debe generar un inventario de cualquier campo o término nuevo que genere a partir del diccionario y dataset sandbox provisto de Prisma y Startrack: nombre de campo, tipo de dato y ejemplo de valor. | Tabla de campos derivados, renombrados y de procedencia: nombre, tipo, ejemplo, significado, fuente y regla. | El [diccionario vigente de ECON](diccionario-modelo-econ.md) enumera 25 modelos y 242 campos declarados, incluidos movimientos, recepción, eventos, cortes, preparación y entradas HTTP. Incluye derivaciones de presentación y generador verificable; separa muestras proporcionadas de ejemplos técnicos. | El alcance cubre los modelos propios enumerados y las derivaciones actuales de decisión/calendario; no todas las propiedades visuales ni los DTO de proveedores. Mantenerlo alineado con cada cambio; este inventario no sustituye el cotejo de las 51 definiciones del kit ni valida equivalencias externas. |
| RF-02 | El equipo debe construir una matriz de mapeo de campos que conecte cada campo relevante de una plataforma con su equivalente en la otra, marcando de forma explícita los campos sin equivalente directo. | Matriz reutilizable y versión PDF con objeto de origen/destino, campo, transformación, cardinalidad, ausencia y estado de validación. Diagrama de relaciones para explicar los vínculos no uno a uno. | La matriz de equivalencias distingue directa, transformada, manual, sin equivalente y no soportada; cubre el formulario de tarea, el contrato relevante y relaciones por ID. El diccionario aporta 51 filas de definición. | Asegurar un cotejo explícito de las 51 filas del diccionario contra la matriz, preservando el duplicado. Las correspondencias concretas de proyecto/geocerca, máquina/activo y operador/usuario siguen pendientes; documentar una relación propuesta no la valida. |
| RF-03 | El equipo debe construir una matriz de responsabilidades que defina, para al menos tres roles funcionales, quien es Responsable, quien Aprueba, a quien se Consulta y a quien se Informa sobre el estado de un equipo. Un formato recomendable, es el de las matrices RACI | Tabla R/A/C/I que incluya Mantenimiento, Logística y Equipos, y Técnica de Proyectos; acompañada de actores documentados y decisiones pendientes de aprobación. | Las equivalencias contienen una matriz de responsabilidades propuesta; AS-IS, TO-BE y organigramas documentan las áreas y actividades. La matriz está además **implementada en la aplicación** como roles de sesión con permisos (`admin`, `gerencia_proyecto`, `logistica`, `mantenimiento`, `control_costos`, `lectura`; [ADR 0005](adr/0005-session-auth-and-roles.md)): quién guarda planes, quién declara recepción y quién administra usuarios. | Validar las asignaciones R/A/C/I con las gerencias y acordar quién confirma correspondencias y recepción. No confundir organigrama, rol operativo, usuario del proveedor e identidad autenticada de la aplicación: el rol de sesión aplica permisos, no acredita la aprobación empresarial de la RACI. |
| RF-04 | El prototipo debe permitir consultar el estado y la ubicación de al menos un equipo de forma unificada, combinando datos de ambas plataformas. | Recorrido navegable de solicitud, unidad y traslado, con ubicación fechada y procedencia visible; guion para seleccionar un registro del dataset. | Dash permite consultar solicitudes y unidades y muestra los faltantes. Hay SDK y seguimiento de visitas implementados; las operaciones persisten por separado del contrato de lectura del hub. | La muestra actual no tiene tarea ni ubicación. Falta una cadena suministrada o verificada del sandbox con IDs y evidencia temporal de ambas fuentes. Un diagrama conceptual, el SDK o el campo vacío no demuestran por sí solos la consulta integrada exigida. |
| RF-05 | El prototipo debe reflejar visualmente al menos un caso donde el estado del equipo difiere entre Prisma y Startrack, y como se resuelve. | Comparación visual por objeto: solicitud, maquinaria, mantenimiento, tarea, presencia y recepción. Mostrar la regla aplicada y su evidencia. | Los modelos mantienen estados separados. El caso 02 explica que maquinaria Ocupada y tarea Completada pueden coexistir. La aplicación puede mostrar condiciones y faltantes; las reglas se verifican con casos aislados de prueba. | Falta demostrar en la interfaz un caso de ambas fuentes con vínculo validado. CF-03 con solicitud APROBADA y maquinaria OBSOLETA solo compara hechos de Prisma; no acredita por sí solo este RF. No introducir una tarea inventada para cerrar la brecha. |
| RF-06 | El equipo debe documentar al menos un indicador operativo que la integración haría visible por primera vez, por ejemplo, tiempo de equipo fuera de geocerca sin justificación. | Ficha de indicador con fórmula, unidad, población, corte, cobertura, faltantes, responsable propuesto y decisión; gráfico únicamente cuando haya datos evaluables. | La guía de indicadores documenta cobertura solicitud–traslado y puntualidad de recepción como propuestas. Esta matriz precisa datos y exclusiones. El panel actual representa estados y períodos de uso de dos solicitudes. | Validar población y reglas del indicador integrado; no presentarlo como ya calculado. Los conteos actuales y el calendario describen Prisma y no prueban un resultado nuevo de integración. RF-06 pide documentar un indicador, no fabricar mediciones para poblarlo. |

Referencias de la tabla: [requisitos originales](onedrive/02-brief-del-reto.md#7-requerimientos),
[matriz de equivalencias](equivalencias-prisma-startrack.md),
[analítica vigente](analitica-decisiones.md),
[indicadores propuestos](kpis-y-referencias-iso.md).

## Trazabilidad de los requisitos complementarios

| Código | Requisito del brief | Entregable o control revisable | Evidencia actual | Brecha o condición pendiente |
| --- | --- | --- | --- | --- |
| RNF-01 | Toda exploración y prueba debe realizarse exclusivamente sobre el entorno sandbox y los datasets sintéticos provistos por Grupo ECON. | Procedencia visible, separación archivo/consulta actual, configuración de destinos y registro del alcance de las pruebas. | README y contexto distinguen muestras proporcionadas, consultas del sandbox y casos internos de prueba. Live y escritura remota están deshabilitados por defecto. Esta revisión no accedió a proveedores ni utilizó credenciales. | Mantener esta distinción en cada captura, cifra y demostración. Los escenarios de pruebas aisladas no sustituyen el dataset proporcionado en la presentación operativa. |
| RNF-02 | La matriz de mapeo y la matriz de responsabilidades deben entregarse en un formato legible y reutilizable, como hoja de cálculo o tabla estructurada, no solo como texto libre. | Tablas estructuradas editables y su reproducción legible en PDF, según sección 9. | Las matrices están en tablas Markdown con referencias. Este documento también usa tablas reutilizables. | Comprobar que el PDF final incluya las matrices, con texto y columnas legibles; conservar el origen editable. Un diagrama de cajas no reemplaza las tablas. |
| RNF-03 | El prototipo puede construirse como dashboard, aplicación web o modelo de datos con interfaz mínima. Debe ser navegable por el jurado. | Aplicación ejecutable con selección, consulta, filtros, detalle y ruta de revisión. | Dash/FastAPI conforman un servicio; README explica ejecución y navegación. El contexto registra verificaciones de escritorio, móvil y teclado. | Ensayar el recorrido sobre la entrega final. Navegabilidad y completitud de los datos son dimensiones distintas; los faltantes de RF-04/RF-05 siguen visibles. |
| RNF-04 | Repositorio o carpeta de entrega con README que explique cómo revisar el prototipo y las matrices. | README con inicio, recorrido, matrices y artefactos finales. | Existen README raíz, índice documental y README del servicio con instrucciones de ejecución. | Mantener enlaces a las matrices y al paquete visual/PDF final; retirar de la ruta principal las instrucciones históricas sustituidas. Verificar enlaces después de la depuración. |

## Entregables literales de la sección 9

La tabla original fija **domingo 10:00** para todos los entregables. La siguiente
tabla conserva formato y medio; no afirma que cada artefacto final esté ya
exportado o entregado.

| Entregable del brief | Formato o contenido exigido | Medio original | Evidencia que revisar antes de entregar |
| --- | --- | --- | --- |
| Matriz de mapeo de campos | Hoja de cálculo o tabla estructurada, incluidos casos sin equivalente directo. | Reporte en Documento PDF. | Tabla completa del alcance seleccionado, ausencias explícitas, cardinalidades y referencias a las fuentes; origen editable conservado. |
| Matriz de Responsabilidades | Tabla de roles, al menos las tres gerencias involucradas. | Reporte en Documento PDF. | R/A/C/I legible y rótulo de propuesta cuando no existe validación empresarial. |
| Prototipo o mockup navegable | Al menos una consulta unificada; enlace o repositorio con instrucciones. El jurado elige equipo o partida del sandbox. | Demo en vivo y entrega de scripts y documentación. | Recorrido seleccionable; vínculo y ubicación acreditados o limitación explicada. La prueba guiada no debe depender únicamente de un caso previamente elegido. |
| Diagrama de arquitectura | Componentes, flujo de datos entre Prisma, Startrack y prototipo, y dónde vive cada estado. | Reporte en Documento PDF. | Separar proveedores, adaptadores, servicio, almacenamiento, interfaz y trabajador; señalar conexiones implementadas, validación pendiente y extensiones propuestas. |
| Documento de decisiones técnicas | **Máximo 2 páginas**: qué se mapeó, qué quedó fuera y por qué. | Reporte en Documento PDF. | Documento identificable dentro del paquete, limitado a dos páginas y coherente con la implementación vigente. Un dossier largo no sustituye ese límite. |
| Presentación final | **Máximo 10 diapositivas**: problema, solución, arquitectura, matrices, valor y bloque de reflexión de aprendizaje. | Presentación en vivo. | Contar diapositivas, incluir reflexión real del equipo y mantener separadas las capacidades implementadas y las propuestas. |

Los comentarios editoriales **16 y 27** sugieren tratar diagrama de arquitectura
y decisiones técnicas como deseables. El cuerpo de la sección 9 los conserva
en la tabla de entregables; esta contradicción se registra y no se resuelve
borrando las filas. Producirlos cubre ambas lecturas. La FAQ de la sección 19
aclara que una conexión API en vivo **no es obligatoria**; un mockup navegable
sobre datos sandbox puede satisfacer la modalidad de prototipo. Esto no elimina
el contenido de RF-04/RF-05 ni autoriza a inventar registros.

El panel de indicadores y la extensión a mayor escala figuran como **deseables**
en la sección 6. La documentación de al menos un indicador sigue siendo RF-06.
AS-IS y TO-BE son insumos de proceso: una versión explicativa ayuda al jurado,
pero no reemplaza el diagrama técnico de arquitectura.

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
| Gerencia Técnica de Proyectos / Gerencia de Proyecto | Brief, AS-IS, TO-BE y organigrama de Gerencia Técnica. | Planificación, programación y solicitud de recursos; Prisma identifica al solicitante como Gerente de Proyecto. | Aprobación de reglas del indicador y de evidencia de recepción; delegación a un receptor concreto. No se equiparan todos los niveles del organigrama. |
| Gerencia de Logística y Equipo(s) | Brief, AS-IS y TO-BE. | Seguimiento de solicitudes, asignación y coordinación operativa; el TO-BE añade equipo, operador y tarifa. | R/A por correspondencias técnicas, programación, envío y atención de discrepancias. El organigrama usa también «Gerencia de Maquinaria y Equipo»; validar la denominación organizativa. |
| Gerencia de Mantenimiento | Brief, AS-IS, TO-BE y organigrama específico. | Revisar condición, atender mantenimiento/reparación y confirmar disponibilidad; el TO-BE evalúa el paro. | Aprobación del catálogo canónico, vigencia de restricciones y política de liberación dentro de la integración. |
| Operadores de Equipos / motorista | AS-IS, TO-BE y casos de uso. | Bitácoras, alertas y ejecución asociada al recurso del caso. | Equivalencia entre ID de operador Prisma, conductor del vehículo y usuario Startrack asignable. |
| Licitaciones | AS-IS, TO-BE y organigrama técnico. | Preparación de requerimientos/oferta y entrega al proyecto. | Participación en la RACI de integración si el alcance se extiende a preconstrucción. |
| Control de Costos | AS-IS, TO-BE y organigrama técnico. | Recibir bitácoras; el TO-BE especifica validación e imputación de costos a partidas. | Política de indicador económico y responsabilidades sobre nuevos datos del hub. |
| Soporte de integración / administrador técnico | La propuesta técnica actual necesita estas funciones. | No es una aprobación de ECON de un cargo o persona asignados al hub. | Operar conectores, gestionar credenciales, resolver incidencias técnicas y conservar evidencia. |
| Responsable receptor del proyecto | Introducido en el flujo vigente como función de recepción. | La aplicación almacena una declaración con receptor, instante y referencia. | Quién está autorizado a recibir, cómo se acredita y quién aprueba su constancia. Declarar exige el permiso `declare_reception`, pero el usuario autenticado todavía no queda vinculado a la declaración. |

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

## Indicadores: qué puede verse y qué datos faltan

Para cualquier ficha: declarar población y filtros, numerador/denominador,
unidad, fuente, fecha del evento, fecha de observación, cobertura y exclusiones.
Si no hay casos evaluables, mostrar **sin casos evaluables**; si falta fuente o
evidencia, **sin información suficiente**. Una lista vacía por fallo no es cero
operaciones. No se adoptan umbrales de éxito ni metas atribuidas a ISO.

| Indicador o visual | Definición y población | Datos necesarios | Situación actual y representación defendible |
| --- | --- | --- | --- |
| Solicitudes por estado | Cantidad por `status` dentro de las solicitudes devueltas y filtradas. Unidad: solicitudes. | ID, estado, alcance de consulta y procedencia. | Disponible: una APROBADA y una PENDIENTE en la muestra sin filtros. Barras desde cero y tabla alternativa. Es contexto descriptivo, no desempeño integrado. |
| Períodos de uso solicitado | Una franja por solicitud entre `starts_on` y `ends_on`; días calendario inclusivos. | ID de solicitud/proyecto, fechas válidas y estado; informar exclusiones. | Disponible: 11–14 y 16–18/09/2026. Calendario de uso, sin línea de «hoy» ni atraso inferido. No representa duración del traslado, utilización ni recepción. |
| Cobertura de vinculación solicitud–traslado | `100 × solicitudes que requieren traslado con vínculo validado / solicitudes que requieren traslado`, en ámbito y corte acordados. Cuenta solicitudes distintas, aunque haya varios movimientos. | Política que identifica qué solicitudes requieren traslado; UUID de solicitud/máquina/proyecto, IDs de movimientos/tareas, validación del destino y vigencia, cobertura de consultas. | Propuesto para RF-06: cruza Prisma y Startrack y permite localizar vínculos por revisar. La muestra no permite fijar el denominador operacional ni los vínculos; no publicar 0 % como resultado. Mostrar ficha y faltantes. |
| Tiempo fuera de geocerca sin justificación | Suma de intervalos observados fuera de una geocerca asignada y sin justificación aprobada, dentro del período evaluado; unidad: minutos u horas por activo. Excluir solapamientos. | Activo rastreado y vínculo temporal con maquinaria; geometría validada; telemetría/visitas con instantes; asignación vigente; causas/justificaciones y calendario de operación. | Ejemplo del RF-06, aún no calculable. Faltan datos de seguimiento y política de justificación. Las lagunas GPS se declaran desconocidas; no se cuentan automáticamente como tiempo fuera. |
| Tiempo registrado hasta aprobación | Diferencia `approved_at − created_at` por solicitud aprobada; mediana/p90 únicamente con cohorte suficiente y comparable. | Instantes con zona, significado de aprobación, historia de reaprobaciones/cancelaciones y pendientes al corte. | El contrato aporta campos y una muestra aprobada; no sostiene un benchmark ni una tendencia. El tiempo del archivo no es un corte de observación. |
| Puntualidad de recepción | `100 × traslados evaluables recibidos dentro del compromiso / traslados evaluables cuyo compromiso vence en el período`. Mostrar también desconocidos y cobertura. | Compromiso explícito con zona, constancia de recepción, receptor, vínculo al movimiento, historial de cancelación/reprogramación y seguimiento suficiente. | Propuesto. La persistencia de una declaración no acredita por sí sola autoridad del receptor ni un compromiso contractual. Faltan eventos operativos; no dibujar un porcentaje. |
| Tiempo de paro / reparación | Intervalos de paro y reparación por equipo, con inicio/fin y causa definidos; agregado según calendario acordado. | Eventos de mantenimiento, decisión explícita de paro/liberación, unidades y calendario. | No calculable con un estado actual o un valor de horómetro. OBSOLETA no fija un intervalo de reparación. |

Para cobertura de vinculación, si varias tareas son necesarias para una solicitud,
la política debe definir si «vínculo validado» exige todas o al menos una; esa
decisión modifica el significado del indicador y debe preceder a su publicación.
Una ficha adicional puede medir cobertura por **movimiento requerido** cuando
esa población esté definida. No cambiar de unidad para mejorar el porcentaje.

Los beneficios esperados —menos búsqueda manual, mayor trazabilidad y revisión
oportuna— deben explicarse como hipótesis. Medir ahorro, disponibilidad técnica,
productividad, OEE, impacto económico o desempeño histórico exige evidencia
adicional. Los materiales revisados no acreditan certificación, cumplimiento ni
metas ISO de ECON; esas referencias no son RF/RNF del reto.

## Coherencia documental al cerrar la entrega

El [contexto vigente](contexto-vigente.md), la
[guía de analítica](analitica-decisiones.md) y el
[diccionario vigente](diccionario-modelo-econ.md) describen la documentación
actualizada. El inventario anterior de modelo operativo queda sustituido por el
diccionario generado. No recuperar sus tres equipos/tres solicitudes inventados,
sus pantallas anteriores ni sus afirmaciones de falta de persistencia como
descripción del producto actual.

El paquete final debe identificar qué visuales describen el AS-IS del kit, cuáles
explican el TO-BE y cuáles representan código implementado. La exportación PDF,
el límite de dos páginas de decisiones y las diez diapositivas de presentación
se verifican sobre los archivos finales. Esta matriz deja esas comprobaciones
abiertas hasta que exista el artefacto correspondiente y no modifica las fuentes
de `docs/onedrive`.
