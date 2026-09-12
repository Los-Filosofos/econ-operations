# Evaluaciones de Astra

Fecha: **12 de septiembre de 2026**. Registro de revisiones del código y las fuentes ya conservadas; no representa nuevas lecturas ni cambios en los proveedores. El alcance vigente está en [contexto-vigente.md](contexto-vigente.md).

## Datos y flujo operativo

Se revisaron el contrato de lectura, sus mapeos para muestras y conexión en vivo, la procedencia y las reglas de alertas. La interfaz conserva el recorrido **proyecto → solicitud → maquinaria → traslado → recepción**, mostrando los tramos cuya evidencia falta.

| Aspecto | Resultado verificado |
| --- | --- |
| Datos mostrados por defecto | Cinco maquinarias y dos solicitudes del OpenAPI proporcionado. La muestra de maquinaria reporta un total de quince: la cobertura permanece parcial. |
| Identidad | Se preservan los UUID de origen. La relación solicitud–maquinaria usa `maquinaria_id` exacto. `clave`, número de activo y nombre siguen siendo campos separados. |
| Procedencia | Las muestras se identifican como `provided_sample`, entorno `sandbox`, con referencia al elemento del documento. La fecha documentada es 12/09/2026; la hora de observación y el corte conjunto son desconocidos. |
| Tiempo | `created_at`, `updated_at` y `approved_at` mantienen sus valores de fuente. Una lectura en vivo tiene su propia fecha de observación. Las muestras antiguas no se convierten en observaciones actuales al abrir el panel. |
| Solicitudes | Se conservan tipo requerido, inicio y fin del período, ID y nombre del solicitante, comentarios y aprobación. Los valores ausentes continúan siendo nulos. |
| Estados | CF-03 conserva `OBSOLETA`, sin falla activa ni paro documentado en esa muestra. No se transforma ese estado en un diagnóstico de mantenimiento. |
| Traslado y recepción | Las muestras no contienen tareas de Startrack, posiciones ni comprobantes de recepción. No se fabrican registros para completar el recorrido. |

Se retiraron del conjunto servido los escenarios inventados de proyectos Norte, Sur y Este, sus traslados, ubicaciones y fallas. Los datos fabricados necesarios para comprobar reglas permanecen exclusivamente dentro de las pruebas automatizadas, con identificadores `test:`.

La asignación del kit **RE-03 / MOT-006 / PROY-006** y la captura de una solicitud pendiente de cargador frontal para PROY-006 se conservan en la documentación. No se insertan como filas del OpenAPI: esa captura no proporciona un UUID fiable y no demuestra una asignación de RE-03. CF-03 / PROY-014 pertenece a otras muestras suministradas, no al equipo Los Filósofos.

La revisión cruzada corrigió la propagación del ID del solicitante en las muestras y una pérdida de acento en el texto de relación. Las pruebas verifican la fidelidad de los campos extraídos respecto del OpenAPI, la preservación de períodos, IDs y zonas horarias en ambos modos, la ausencia de alertas temporales cuando no existe corte de observación, la separación de estados y el aislamiento de datos entre peticiones. No hacen llamadas a los proveedores.

Permanecen pendientes los IDs y relaciones de la operación propia, un contrato validado de tareas y eventos de Startrack, las correspondencias entre maquinaria y vehículo transportador, y una evidencia explícita de recepción. Completar una tarea o entrar en una geocerca no cubre esas ausencias. El modelo actual tampoco acredita sincronización continua, persistencia de operaciones ni un historial de entregas.

## Integración y preparación de tareas

El agente Astra ultra contrastó la API pública de tareas, geocercas, autenticación
y webhooks. Implementó `integrations/startrack.py`: consultas GET acotadas,
configuración deshabilitada por defecto, origen fijo del sandbox y credenciales
privadas. No hay métodos de escritura ni montaje del cliente en la API pública.
El contrato autenticado de esta cuenta sigue pendiente de comprobación.

El servicio `services/transfers.py` prepara un borrador mediante IDs explícitos.
Comprueba solicitud aprobada, unidad exacta, proyecto y compatibilidad de fuente,
entorno y naturaleza de la evidencia. Exige destino, usuarios, referencia de
movimiento y fecha programada; conserva procedencia en el resultado. Un paro
explícito requiere revisión. Los demás estados permanecen originales, sin afirmar
disponibilidad física. La fecha de uso nunca sustituye a la programación logística.

La revisión cruzada corrigió coerciones de timestamps/épocas a fechas y evitó
aceptar fuentes incompatibles como una operación Prisma. El borrador desactiva
notificaciones de contacto y no acredita permisos, existencia de IDs remotos,
unicidad de `remote_id`, entrega ni recepción.

La CLI `python -m app.cli.prepare_transfer --request-source-id <UUID>` consulta
exclusivamente la muestra local y permite revisar un mapeo JSON mediante
`--mapping`. La solicitud aprobada proporcionada devuelve `missing_information`
con cuatro campos de mapeo faltantes, `draft=null` y `remote_writes=false`.
La pendiente devuelve `review_required`, sin crear una asignación.

## Interfaz

El agente Astra ultra sustituyó la portada general por el seguimiento de
solicitudes. La navegación principal contiene Solicitudes y Fuentes y cobertura.
Los detalles conservan período solicitado, unidad, condición mecánica, tarea,
destino y evidencia faltante. Los UUID completos permanecen en el detalle y la
procedencia, con nombres legibles en la tabla. Se retiraron de la interfaz
gráficos y pantallas generales que apartaban la atención de este recorrido.

Las pruebas comprueban enlaces, estado por navegador, consultas fallidas,
registros fuera de la muestra y ausencia de uniones por nombre. Una tarea
completada nunca genera recepción ni llegada por sí sola. Las utilidades
analíticas conservadas están fuera de la interfaz operativa.

La revisión visual local verificó la tabla y el detalle, incluidos los faltantes
reales de CF-03 y la adaptación a un ancho de 390 píxeles. No se consultaron ni
modificaron proveedores durante esas verificaciones.

## Verificación final de esta etapa

- `scripts/check.ps1 -Container`: Ruff, formato, **123 pruebas aprobadas** y
  construcción de la imagen. Tras el último ajuste de encabezados y pie,
  las 16 pruebas del dashboard volvieron a pasar y la imagen se reconstruyó.
- La CLI ejecutada dentro de `econ-hub:check` con `--network none` encontró
  las muestras empaquetadas y devolvió cuatro datos faltantes, sin borrador
  ni escrituras remotas.
- Revisión visual local de tabla, fuente y solicitud aprobada; comprobación
  de lectura en escritorio y móvil. El servidor de revisión queda en
  `http://127.0.0.1:8051`, con SQLite en memoria y live deshabilitado.
- Originales, datos de proveedores y volumen PostgreSQL conservados. No hubo
  carga a sandboxes ni despliegue público. La creación remota y sincronización
  quedan pendientes de validar permisos, mapeos y el contrato de escritura.

## Segunda etapa: implementación autorizada del flujo completo

El usuario pidió ejecutar la solución con todo el contexto y aclaró que todos
los datos son sintéticos. Tres agentes `gpt-6-astra` con razonamiento `ultra`
trabajaron en paralelo con integración y revisión por el agente principal:

| Área | Resultado |
| --- | --- |
| Persistencia | Planes, cortes, eventos, recibos y cola transaccional; migración explícita; aislamiento por origen |
| Proveedores | Lecturas y detalles Prisma; creación y catálogos Startrack; visitas y formularios; tratamiento de respuestas inciertas |
| Interfaz | Preparación, operaciones, evidencia e historial; tabla y detalle alimentados por registros persistidos |
| Integración principal | Servicio compartido, API tipada, gestión local por petición y worker de sincronización |

La revisión cruzada corrigió la interpretación de respuestas de creación con
campos opcionales ausentes, exigió coincidencias estrictas para conciliar
resultados inciertos y evitó atribuir visitas a un destino que cambió. No se
repite automáticamente un POST incierto. Las observaciones exigen los IDs exactos
de tarea, geocerca y vehículo; ninguna completa automáticamente la recepción.

Validación final del 12/09/2026:

- `scripts/check.ps1 -Container`: **233 pruebas aprobadas**, Ruff y formato correctos.
- Imagen `econ-hub:check` construida; digest de manifiesto
  `sha256:f5c902799917160611944997f666df62486ff4157d468526586f87354f28ecf4`.
- `alembic upgrade head` aplicó `0001_operations` al PostgreSQL local existente;
  `alembic check` no detectó diferencias. Proyecto y volumen Compose conservados.
- Navegador: detalle, validación de campos y formularios a 1280/390 píxeles.
  Se guardó un corte de las muestras y se comprobó su persistencia tras reiniciar.
- Servidor local en `http://127.0.0.1:8050`, gestión local habilitada y conexión
  remota deshabilitada. Registro disponible, cero movimientos de demostración
  inventados y ningún envío realizado a Prisma/Startrack.

Las pruebas controladas ejercitan creación, conciliación, concurrencia,
persistencia, callbacks HTTP, bloqueo de peticiones externas y recepción
independiente de GPS. No sustituyen la comprobación autenticada de la cuenta
Startrack, cuyo acceso API y formato efectivo de creación siguen pendientes.
El significado de `live` es consulta actual del sandbox sintético, no producción.

La arquitectura y los comandos actuales están en
[solución y guía operativa](solucion-integracion.md) y
[ADR 0004](adr/0004-persistent-transfer-workflow.md).

## Tercera etapa: navegación lateral y análisis de solicitudes

El usuario pidió mejorar la interfaz Python, reducir información secundaria y
elegir gráficos útiles para la operación. Tres agentes `gpt-6-astra` con
razonamiento `ultra` revisaron analítica, contenido y reglas de evidencia; el
agente principal integró la navegación y verificó el resultado en el navegador.

- Sidebar con Resumen, Solicitudes, Operaciones y Fuentes. En móvil se convierte
  en un panel con cierre explícito, Escape, recorrido de foco contenido y retorno
  al botón Menú.
- Resumen con tres conteos enlazados: solicitudes en vista, sin unidad asignada
  y sin tarea confirmada en el registro consultado. El último permanece desconocido
  si el registro no está disponible.
- Dos gráficos Plotly: distribución del estado administrativo y períodos de uso
  solicitados. Las fechas son las proporcionadas; el gráfico no representa
  programación logística ni cumplimiento de entregas.
- Tablas de seis columnas y detalles desplegables para referencias técnicas,
  historial y preparación de traslados. La cobertura y los datos faltantes siguen
  visibles. Los filtros usan el mismo alcance que los conteos.

La batería completa pasó con **276 pruebas**, Ruff y formato correctos, junto con
la construcción del contenedor. Se revisaron escritorio a 1440 píxeles y móvil a
390: gráficos legibles, filtro de una solicitud sobre dos y navegación por
teclado. La revisión de foco detectó y corrigió una carrera entre el renderizado
de Dash y la apertura del panel; se verificaron Escape, Tab y Shift+Tab después
del ajuste. El tamaño temporal del navegador se restauró.

La aplicación sigue disponible en `http://127.0.0.1:8050`. Esta etapa no agregó
filas sintéticas ni realizó escrituras a proveedores. La muestra proporcionada
conserva dos solicitudes, una unidad pendiente de asignación y ninguna tarea
confirmada en el registro local.

## Cuarta etapa: decisiones primero y equivalencias documentadas

El usuario corrigió la jerarquía de la portada: los conteos no debían ocupar el
primer plano de Gerencia. Se retiraron las cards. La primera sección presenta
proyecto/necesidad, revisión respaldada por evidencia y enlace al siguiente
paso. El período de uso sirve de contexto inferior; los estados se consultan en
un desplegable. Los envíos inciertos requieren conciliación, y una solicitud
cerrada o un movimiento recibido no genera trabajo pendiente por sí solo.

La revisión por Astra comprobó que `OBSOLETA` es un hecho administrativo de
CF-03, no una falla ni un paro. La otra solicitud está pendiente y sin unidad.
Se preservó una fila por solicitud y no se incorporaron urgencia, atraso ni
impacto económico sin evidencia. El filtro y la agenda ahora comprueban también
el período y la aprobación del corte guardado para evitar que un traslado
anterior oculte una ejecución actual.

La [matriz Prisma → Startrack](equivalencias-prisma-startrack.md) registra todos
los controles del formulario suministrado, sus campos de origen, transformaciones,
correspondencias manuales, ausencias y límites de soporte. Distingue el contrato
público, el SDK y el flujo realmente implementado. Las fechas de uso no equivalen
a programación del traslado; maquinaria, vehículo, operador y usuario mantienen
identidades independientes. No se amplió el contrato de escritura en esta etapa.

Verificación: **308 pruebas aprobadas**, Ruff y formato correctos, imagen
`econ-hub:check` reconstruida. Navegador: portada sin cards, análisis secundario
desplegable, enlace a la solicitud correcta y lectura móvil a 390 píxeles sin
desbordamiento de la agenda. Servidor local en `http://127.0.0.1:8050`; sin carga
de datos ni escrituras remotas.
