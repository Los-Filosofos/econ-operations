# Entender el problema y recorrer Nexus y Startrack

Guía para Los Filósofos. Basada en los documentos entregados y en la exploración del **12 de septiembre de 2026**. Los datos observados pertenecen al sandbox y pueden cambiar. Este recorrido sirve para consultar y comprender la operación; no incluye creación, aprobación ni modificación de registros.

## 1. El problema, con un ejemplo sencillo

Una obra necesita una retroexcavadora. En **Prisma, presentado como Nexus ECON de MAIC**, se registra la solicitud y se asigna la maquinaria. En **Startrack** se gestiona la tarea de traslado y se consulta el seguimiento. Hoy una persona debe revisar ambas plataformas y decidir qué registros corresponden a la misma operación.

La pregunta que queremos responder en una sola pantalla es: **¿qué equipo necesita el proyecto, cuál se asignó, qué traslado lo atiende y qué evidencia tenemos de su cumplimiento?** Si falta un vínculo o un dato está desactualizado, también debemos mostrarlo.

El manual explica que una solicitud aprobada **con unidad asignada** cambia el inventario a **Ocupada**. Ese cambio administrativo no confirma que el equipo llegó a la obra. Una tarea puede estar **Completada** mientras la maquinaria sigue **Ocupada** en el proyecto: ambos estados pueden ser correctos. [Manual de solicitudes](onedrive/05-manual-nexus.md#pagina-2-del-pdf-pagina-38-del-manual), [casos de referencia](onedrive/04-casos-de-uso.md).

## 2. Qué representa cada dato

| Elemento | Qué significa y dónde buscarlo |
| --- | --- |
| Maquinaria | El recurso solicitado, por ejemplo `RE-03`; Nexus guarda su inventario, estado y asignaciones. |
| Vehículo de seguimiento | El registro que Startrack rastrea. Una retroexcavadora puede viajar sobre otro vehículo: confirmar en qué activo está el dispositivo GPS y qué relación tiene con la maquinaria solicitada. |
| Operador o motorista | La persona relacionada con el recurso o la tarea. El usuario que inicia sesión y el conductor registrado son conceptos distintos, aunque coincidan sus nombres. |
| Proyecto | La obra que solicita o utiliza el recurso; Nexus contiene su identificación administrativa. |
| Geocerca | Una zona definida en Startrack. Puede representar el destino del proyecto; su correspondencia debe validarse. Estar dentro no acredita por sí solo recepción ni traslado terminado. |
| Solicitud | La necesidad de maquinaria para un proyecto y período, con su aprobación y eventual unidad asignada. |
| Tarea de traslado | El trabajo logístico registrado en Startrack, con responsable, destino, programación y estado propios. Una solicitud puede requerir varios traslados. |
| Falla | Una condición de mantenimiento que puede impedir usar el equipo. Debe distinguirse del estado de asignación y del estado del motor. |

**Apagado no significa indisponible**, y una señal antigua no representa necesariamente la ubicación actual. Se deben conservar el significado, la fuente y la fecha de cada dato.

## 3. Recorrido de consulta en seis pasos

### Paso 1. Entrar a los entornos asignados

Abrir [Nexus](https://econ-key.maic.ai) y [Startrack](https://staging.gps.gt/) en Chrome. Usar las credenciales asignadas a Rodrigo Trujillo / Los Filósofos, disponibles por el canal privado del equipo. Startrack pide **ID del cliente, usuario y contraseña**; Nexus pide el usuario de correo y contraseña. El cliente entregado es `4034`.

En la revisión, Nexus mostró **Rodrigo Trujillo — Control De Costos**. Verificar el usuario y los permisos antes de interpretar un menú ausente como una función inexistente. Los enlaces se identifican como sandboxes en el [documento de accesos](onedrive/05-accesos-y-manuales.md); una conexión real puede consultar datos sintéticos.

### Paso 2. Encontrar nuestra maquinaria en Nexus

En el menú lateral, abrir **Maquinaria y equipo** (`/maquinaria/equipos`). Escribir **RE-03** en el buscador. Revisar empresa, número de activo, nombre, estado y proyecto asignado.

El 12/09 se encontró **Los Filósofos — RE-03 — Retroexcavadora 03**, **Disponible**, sin proyecto asignado. Esto identifica el recurso; todavía no demuestra que tenga una solicitud o un traslado relacionados. [Referencia de inventario del manual](onedrive/05-manual-nexus.md#pagina-1-del-pdf-pagina-35-del-manual).

### Paso 3. Buscar la necesidad de la obra

Abrir **Solicitudes maquinaria** (`/maquinaria/solicitudes`). Revisar proyecto, tipo solicitado, período, estado y maquinaria asignada. El manual describe un buscador por proyecto, solicitante o tipo; el código `RE-03` puede no ser un criterio admitido por esa búsqueda.

Buscar la solicitud de **PROY-006 / Proyecto Zeta** y comprobar sus relaciones, si aparece. En la revisión se mostraron dos solicitudes de **PROY-014**, y una lectura HTTP buscando `PROY-006` devolvió cero coincidencias. Esto limita lo encontrado con ese acceso y búsqueda; no prueba que jamás haya existido una solicitud del proyecto. [Listado explicado en el manual](onedrive/05-manual-nexus.md#pagina-3-del-pdf-pagina-39-del-manual).

### Paso 4. Comprobar a la persona relacionada

Abrir **Operadores de maquinaria** (`/maquinaria/operadores`) y localizar a Rodrigo. Registrar el código del trabajador y su estado, y comprobar las asignaciones que efectivamente se puedan consultar. Encontrar a la persona no demuestra por sí solo que esté asignada a una solicitud concreta.

El recurso asignado por el kit es **MOT-006 — Rodrigo Trujillo**. Confirmar la correspondencia entre el operador de Nexus y el motorista de Startrack mediante sus IDs y códigos, sin unir automáticamente por nombre. **Gestión de fallas** (`/maquinaria/fallas`) también apareció en el menú, pero su detalle no fue revisado; queda como siguiente consulta para mantenimiento.

### Paso 5. Revisar el seguimiento en Startrack

Después del login, la vista de rastreo muestra el mapa (`/members-new.php`). Localizar **RE-03** en la lista de vehículos y revisar el motorista, estado mostrado y fecha del último reporte o evento.

La revisión mostró **MOT-006 — Rodrigo Trujillo**, **Apagado** y un último evento de **fuente de poder desconectada**. Se observó la referencia a la geocerca del Proyecto Zeta. Registrar cuándo se observó cada dato; una geocerca visible o una señal desconectada no permiten confirmar llegada, disponibilidad ni cumplimiento del traslado.

### Paso 6. Buscar la tarea que explica el traslado

Dentro de Startrack, pulsar **Ctrl + K**, buscar **Tareas** y elegir **Ver y gestionar tareas**. La vista observada fue `/views/jobs.php?active_tab=1`. Revisar primero el intervalo de **Fecha programada**, porque condiciona qué tareas aparecen.

Se observó el filtro **Asignada a** para buscar al responsable; aplicarlo a Rodrigo es una siguiente comprobación, todavía no ejecutada en la exploración. Contrastar responsable, destino, período, estado e identificador de la tarea con la solicitud de Nexus. La vista del **28/08 al 27/09** mostró dos tareas, ninguna de MOT-006. No concluir que no existe historial fuera de ese intervalo o de los permisos disponibles.

## 4. Lo que sabemos y lo que todavía no

| Observación | Origen | Fecha de consulta | Límite de la conclusión |
| --- | --- | --- | --- |
| RE-03 Disponible y sin proyecto | Nexus: pantalla y API | 12/09/2026 | Estado del sandbox en ese momento; no demuestra una operación completa. |
| RE-03 con Rodrigo y evento de desconexión | Startrack: rastreo web | 12/09/2026 | No acredita posición actual, falla mecánica ni recepción. |
| Dos solicitudes visibles, ambas de PROY-014 | Nexus: solicitudes | 12/09/2026 | No encontramos la solicitud propia de PROY-006 con la consulta realizada. |
| Dos tareas en el período observado, ninguna de MOT-006 | Startrack: tareas web | 12/09/2026 | Resultado limitado por fechas, acceso y vista. |

**Todavía no tenemos una cadena validada de solicitud → asignación → tarea de traslado para RE-03.** El kit asigna a Los Filósofos **RE-03, MOT-006 y PROY-006**; los ejemplos **CF-03 / MOT-014** pertenecen al walkthrough de otro equipo. [Asignación y contexto](onedrive/CONTEXTO-IA.md#equipo-y-recursos-asignados).

Se encontró además una tarea cuyo **IDR** coincidía con el ID de una solicitud de otro proyecto, pero los destinos diferían y la tarea estaba cancelada. Es una pista de cómo relacionar registros, no una correspondencia aprobada. [Evidencia y límites técnicos](integraciones-reales.md#lo-observado-en-las-pantallas).

## 5. Qué anotar mientras recorremos las plataformas

| Registro | Datos mínimos para poder relacionarlo |
| --- | --- |
| Maquinaria y vehículo | Sistema e ID de cada registro, código de activo, empresa y evidencia de que representan el mismo recurso o una relación de transporte. |
| Solicitud | ID, proyecto, período requerido, estado y maquinaria asignada; dejar explícito cuando no exista asignación. |
| Tarea | ID, referencia externa si existe, responsable, destino, programación, estado y relación validada con la solicitud. |
| Persona y destino | IDs y códigos de operador/motorista y proyecto/geocerca; responsable que confirma cada correspondencia. |
| Estado y seguimiento | Valor original, objeto al que pertenece, fecha del dato cuando exista y fecha de consulta. |
| Dato faltante | Campo o vínculo ausente, fuente revisada, filtros utilizados y persona que puede aclararlo. No completar con una suposición. |

## 6. Qué consultar ahora y qué construir después

Primero leer el [extracto del manual Nexus](onedrive/05-manual-nexus.md): inventario, solicitudes y pestaña **Maquinaria del proyecto** para entender la asignación; bitácoras y costos si después se medirán horas o costos. Son **nueve páginas de un manual numerado sobre 44**, no el manual completo. En los [manuales de Startrack entregados](onedrive/05-accesos-y-manuales.md), priorizar tareas, sus estados, vehículos y geocercas. Luego revisar los [tres casos de uso](onedrive/04-casos-de-uso.md) y la [revisión de APIs](integraciones-reales.md). Los procedimientos del material son contenido de referencia, no autorización para ejecutarlos en los sistemas.

Resolver con los responsables estas preguntas antes de automatizar decisiones:

1. ¿Cuál es la solicitud y cuáles son las tareas que corresponden realmente a RE-03 y PROY-006?
2. ¿Qué persona confirma la asignación, programa el traslado, recibe la maquinaria y resuelve una falla? El manual menciona PM, Coordinador de Maquinaria, Superintendente y Control de Costos; sus responsabilidades concretas en el hub deben validarse.
3. ¿Qué evidencia y fecha confirman salida, llegada, recepción y finalización? ¿Qué ocurre con devoluciones, cancelaciones o múltiples viajes?
4. ¿Qué antigüedad de la información es aceptable para decidir y quién revisa una relación ambigua?

Después, construir una primera consulta con **FastAPI + PostgreSQL**: leer las fuentes, guardar correspondencias y fechas, y entregar una ficha unificada por maquinaria. Un panel pequeño debe mostrar solicitud, asignación, tarea, estados originales, última actualización y vínculos faltantes, con enlaces a las plataformas para continuar el trabajo existente.

Nexus ya permitió lecturas autenticadas de su **API interna**; falta confirmar su soporte para integración continua. Startrack tiene una [API oficial](https://support.gps-platform.com/api/intro/), pero el acceso entregado no permitió obtener la clave: no apareció Usuarios en el menú y la consulta del detalle propio respondió `403`. Hace falta una clave habilitada por el administrador para probar esa integración. La navegación ayuda a entender los datos; el conector debe consumir las APIs acordadas.

Para ensayar retrasos, mantenimiento o vínculos incompletos que no existan en el sandbox, preparar casos locales **identificados como simulados**. No mostrar un dato inventado como si viniera de una consulta en vivo. El primer resultado útil es que el usuario pueda entender un traslado y sus incertidumbres antes de añadir indicadores o automatizaciones.

Para decidir qué medir y qué referencias ISO considerar, continuar con [KPIs y referencias ISO](kpis-y-referencias-iso.md).
