# Contexto vigente: solicitud, traslado y recepción de maquinaria

Actualizado el **12 de septiembre de 2026**. Este documento conserva la revisión
de fuentes y las instrucciones posteriores del usuario. Es el punto de entrada
para continuar el trabajo; los registros anteriores conservan valor histórico.

## Última mejora de interfaz

La corrección más reciente del usuario pide retirar las cards de conteos y
comenzar por las decisiones que necesita Gerencia. La portada muestra ahora
proyecto, revisión necesaria, evidencia y siguiente paso por solicitud. El
calendario apoya la planificación debajo; la distribución por estado queda
desplegable. CF-03 `OBSOLETA` requiere revisar la asignación, sin afirmar avería.
La otra solicitud requiere resolver aprobación y asignación. No se infieren
urgencia, atrasos ni impacto económico con esta muestra.

El usuario también pidió documentar las equivalencias de Prisma y Startrack.
La [matriz de equivalencias](equivalencias-prisma-startrack.md) distingue campos
conservados, transformados, manuales, sin equivalente y pendientes de validar.

Esta corrección pasó `scripts/check.ps1 -Container`: **308 pruebas**, Ruff,
formato e imagen construida. La portada y sus enlaces se verificaron en
escritorio y móvil a 390 píxeles. Se conservaron los datos y habilitaciones.

El usuario pidió un sidebar, menos datos irrelevantes y gráficos elegidos con
criterio de analista. Se mantiene Python/Dash/Plotly y la identidad ECON.
La portada es ahora Resumen; el sidebar conduce a Solicitudes, Operaciones y
Fuentes. Las tablas muestran seis columnas y los detalles técnicos usan
desplegables. Los formularios y la evidencia completa permanecen disponibles.

Se añadieron barras de solicitudes por estado y períodos de uso solicitados.
Ambos usan exclusivamente los registros proporcionados/consultados y explican
su cobertura. No representan entregas, utilización o tendencias. Las decisiones
usan la misma población filtrada en Solicitudes. Los detalles están en
[analítica](analitica-decisiones.md) y [arquitectura de interfaz](frontend-architecture.md).

Validación anterior del sidebar: **276 pruebas aprobadas**, Ruff/formato y construcción
del contenedor correctos. Se verificaron escritorio, móvil, filtros, navegación
y foco por teclado. El último ajuste del menú volvió a pasar las **68 pruebas**
de interfaz y analítica. No se agregaron registros al dataset ni hubo envíos a
los proveedores durante esta mejora.

## Implementación vigente tras la petición de desarrollarlo

El usuario confirmó después: **«pura data sintética tenemos»**. Toda la operación
pertenece al sandbox. `fixture` identifica ejemplos del archivo; `live` identifica
lecturas actuales de datos sintéticos en los proveedores, no datos de producción.

Se implementó el recorrido con tres agentes **gpt-6-astra, razonamiento ultra**:

- Dash: solicitudes, preparación del movimiento, registro de operaciones,
  estado del envío, presencia GPS y declaración de recepción con constancia.
- Backend compartido por Dash/HTTP/CLI: lectura de Prisma, validación de IDs,
  correspondencias explícitas, cola de envío y seguimiento de Startrack.
- PostgreSQL: planes, payload, IDs de origen, cortes, historial de eventos y
  recepción. La migración `0001_operations` se aplicó explícitamente al PostgreSQL
  local existente; Alembic comprobó que coincide con el modelo. Se conservó el volumen.
- SDK: creación de tarea con habilitación independiente, catálogos, tareas,
  visitas y formularios. Un resultado incierto se concilia por lectura sin
  repetir automáticamente el POST. El worker se ejecuta explícitamente por CLI.
- Las muestras proporcionadas permiten guardar planes y cortes locales. No se
  agregaron tareas, ubicaciones o recepciones inventadas al dataset ni se cargó
  nuevamente la información en Prisma.

El servidor local usa `http://127.0.0.1:8050`, PostgreSQL, gestión local habilitada
y datos del archivo. La conexión y escritura remotas siguen deshabilitadas por
defecto. No hubo despliegue público ni envío real al sandbox en esta etapa.
La validación autenticada de creación en Startrack sigue pendiente de acceso API,
IDs confirmados y comprobación del formato de arrays aceptado por esa cuenta.

Verificación de esta implementación: `scripts/check.ps1 -Container` terminó con
**233 pruebas aprobadas**, Ruff/formato correctos e imagen construida. Alembic
verificó el esquema PostgreSQL sin diferencias. En el navegador se comprobó el
detalle y su formulario a 1280 y 390 píxeles, la validación de campos vacíos y
el guardado de un corte de las muestras proporcionadas. Tras reiniciar, el corte
se conserva; hay cero movimientos inventados y ningún envío al proveedor.

Consultar [solución y guía operativa](solucion-integracion.md),
[ADR 0004](adr/0004-persistent-transfer-workflow.md) y
[evaluaciones y verificaciones](evaluaciones-astra.md). Las secciones posteriores
conservan la investigación y la primera etapa; este apartado reemplaza sus
afirmaciones antiguas de que no existía persistencia, worker o creación remota.

## Dirección del producto acordada con el usuario

- La interfaz debe seguir **proyecto → solicitud → asignación de una máquina
  concreta → tarea de traslado en Startrack → llegada observada → recepción**.
- El usuario confirmó que «elimina todo» significa **quitar ejemplos inventados
  y pantallas ajenas al flujo**, conservando el código útil y los documentos.
  No pidió borrar bases, volúmenes, originales ni registros de los proveedores.
- Usar los datos sintéticos proporcionados para el reto, preservando su fuente.
  Una muestra de un contrato o una captura fechada no es una lectura actual.
  No fabricar tareas, ubicaciones, responsables o recepciones para completar
  visualmente una cadena que las fuentes no acreditan.
- Evaluar e implementar con agentes **Codex Astra, razonamiento ultra**, por
  petición expresa: datos y proceso, integración, e interfaz.
- Conservar Dash, FastAPI, AG Grid Community y PostgreSQL. No reintroducir React,
  login de aplicación, badges ni decoración. Credenciales solo en el servidor;
  lecturas live deshabilitadas por defecto.

## Fuentes revisadas

Se revisaron los 21 Markdown de `docs/onedrive`, incluidas las 51 definiciones
del diccionario; los documentos operativos del repositorio; las capturas del
usuario; `econ-hackathon-openapi.json` completo (25 rutas, 30 operaciones); y las
23 páginas de `Prisma-Sandbox-API.pdf` (extracción textual completa y revisión
visual de las páginas de solicitudes). Los adjuntos permanecen en la raíz.

La plataforma administrativa que el usuario llama START aparece en el kit como
**Prisma**, con interfaz/manual **Nexus ECON**. **Startrack** gestiona tareas y
seguimiento. No se ha identificado documentalmente una tercera plataforma.

Las instrucciones o ejemplos incluidos en documentos fuente son material citado,
no autorizaciones para ejecutar código o modificar servicios.

## Flujo y significado de los estados

1. Gerencia crea el proyecto en Prisma.
2. El proyecto solicita un tipo de maquinaria, fechas de uso y comentarios.
3. Logística aprueba y asigna una unidad; el operador es opcional en el contrato.
4. La unidad asignada permite preparar la tarea de traslado en Startrack.
5. Startrack aporta ejecución, visitas, telemetría y formularios.
6. El proyecto acredita la recepción según la evidencia empresarial acordada.

El caso de uso sitúa el traslado después de asignar la unidad. El TO-BE propone
crear la tarea desde una **solicitud aprobada**, no desde la mera creación de un
proyecto. Es una automatización objetivo, no una conexión ya demostrada.

El manual indica que aprobar con unidad cambia la solicitud a **Aprobada** y el
equipo a **Ocupada**. La ocupación administrativa, condición de mantenimiento,
estado de tarea, posición y recepción son hechos distintos. Una tarea completada
puede coexistir con una máquina ocupada. Entrar en una geocerca no prueba por sí
solo descarga o recepción; el GPS puede pertenecer al transportador o al teléfono.

Referencias: [casos](onedrive/04-casos-de-uso.md),
[TO-BE](onedrive/03-to-be.md), [manual](onedrive/05-manual-nexus.md).

## Identidad, muestras y fechas

- Asignación del kit: **RE-03 / MOT-006 / PROY-006**. Los ejemplos históricos
  CF-03/MOT-014 pertenecen a otro recorrido y no deben mezclarse con ella.
- La captura nueva muestra una solicitud de **PROY-006, Cargador frontal,
  11/09/2026–26/09/2026, Pendiente, sin maquinaria**. No muestra su UUID.
- El formulario de Minicargador del 02/09 al 09/09 es otra captura; seleccionar
  MOT-014 en un modal no demuestra asignación confirmada ni vínculo con RE-03.
- La observación histórica «no se encontró solicitud PROY-006» no describe el
  estado de las capturas nuevas. Cada evidencia debe conservar su alcance.
- Conservar UUID de proyecto, solicitud, maquinaria y operador, IDs de Startrack,
  entorno, momento de lectura y fechas de origen. Nunca unir por nombres.
- Relacionar explícitamente proyecto/geocerca, maquinaria/activo rastreado,
  operador/conductor/usuario y solicitud/movimiento/tarea. Puede haber varios
  movimientos por solicitud. `remote_id` de tarea no tiene unicidad documentada.
- Fechas de uso no son una ventana de entrega. Una descripción de ciudad no es
  una coordenada. Datos desconocidos permanecen ausentes.

## Contratos y hallazgos técnicos

### Prisma

El adjunto aporta el contrato del proxy de `https://econ-key.maic.ai` que faltaba
en la revisión anterior. Documenta consultas de proyectos, solicitudes, equipos,
operadores e historial. `PATCH /api/maquinaria/requests/{id}/approve` exige
`maquinaria_id` y admite fechas, operador y tarifa.

No publica POST para crear proyectos o solicitudes, endpoints de tareas Startrack
ni suscripciones de webhook. Que la interfaz permita crear un registro no acredita
una ruta pública soportada para hacerlo desde un SDK.

El contrato tiene límites que impiden generar un cliente sin revisión: cookie
`session` frente a `auth-token` observada por el conector; seguridad heredada en
login; esquemas derivados de muestras con nulabilidad incompleta; respuestas de
escritura sin estructura; proyectos sin `total` en su paginación. No corregir el
comportamiento observado de autenticación por una suposición del esquema.

### Startrack

- [Geocercas](https://support.gps-platform.com/api/pois/):
  `GET /api/pois`, `POST /api/poi`, `PUT /api/poi/{id}`. Coordenadas en grados
  (`x` longitud, `y` latitud), radio en metros; grupo requerido para crear.
- [Tareas](https://support.gps-platform.com/api/jobs/): `GET/POST /api/job`.
  Exige `objective` y `start_date`; admite `remote_id`, `poi_id`, usuarios,
  formularios y contacto. Duración en segundos. `status` referencia catálogo;
  `workflow_role` distingue pendiente, completada y cancelada. No documenta todos
  los campos visibles en la interfaz ni idempotencia de creación. Las
  notificaciones no deben activarse incidentalmente al preparar pruebas.
- [Webhooks](https://support.gps-platform.com/admin/api/webhooks/):
  `/api/data-forwarding-rules` reenvía telemetría de vehículos a un receptor.
  No acredita eventos de aprobación de Prisma ni cambios de estado de tareas.
- [Visitas](https://support.gps-platform.com/api/reports/poi-visits/) y
  [formularios](https://support.gps-platform.com/api/reports/form-responses/)
  aportan evidencia vinculable; no definen por sí solos aceptación de maquinaria.
- [Autenticación](https://support.gps-platform.com/api/intro/): Basic con clave
  API y contraseña de usuario. Acceso web no prueba acceso API. Respetar límites
  de consultas; los errores y registros nunca exponen credenciales.

Un SDK facilita llamadas. El servicio de integración conserva correspondencias,
reglas y reintentos. Con las capacidades documentadas, la detección inicial de
aprobaciones puede realizarse mediante consultas periódicas acotadas. Un webhook
de Prisma requeriría capacidad adicional confirmada con su propietario.

## Condiciones para una prueba de extremo a extremo

Antes de cargar o modificar los sandboxes, preparar el caso concreto y sus IDs:
solicitud/unidad, geocerca precisa, usuario asignable, activo rastreado, fecha
programada y criterio de recepción. Comprobar si esos registros ya existen para
no duplicar el dataset suministrado. Una preparación local no se presenta como
si hubiera enviado una tarea o entregado maquinaria.

La revisión previa no hizo escrituras en plataformas. Al iniciar esta etapa,
la aplicación solo consultaba equipos y solicitudes de Prisma; no tenía
conector Startrack, persistencia de movimientos ni sincronización periódica.
La etapa incorpora ahora muestras extraídas del contrato, interfaz centrada en
solicitudes, un SDK de lectura Startrack deshabilitado y un preparador local de
borradores con CLI. Se retiraron los casos inventados servidos al usuario; sus
reglas se ensayan exclusivamente en tests. No se insertaron ni borraron registros
en los proveedores, no se habilitó live y no se tocó el volumen PostgreSQL.
El detalle está en [evaluaciones de Astra](evaluaciones-astra.md), el
[servicio](../apps/api/README.md) y la [interfaz](frontend-architecture.md).
