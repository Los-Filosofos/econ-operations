# Preguntas del jurado · preparación

Complemento de [pitch.md](pitch.md) para los **3 minutos de preguntas**.
Veintiuna preguntas probables, agrupadas por tema, con una respuesta corta y
defendible y el lugar exacto del repositorio donde está la evidencia.

Reglas de la ronda:

- Responder en **dos o tres frases** y ofrecer la pantalla: «se lo enseño».
- Si no lo sabemos, decirlo y decir qué haría falta para saberlo. En este reto,
  un límite declarado suma; un mapeo inventado resta.
- Nunca improvisar una cifra. Si no está en el repositorio o en el brief, no
  existe.

---

## A · Arquitectura e integración

### A1. ¿Cuál es su fuente de verdad?

Cada hecho conserva la suya. **Prisma** es autoridad de la solicitud, la
aprobación, la asignación y el estado administrativo de la maquinaria;
**Startrack**, de la tarea, su ejecución y la posición del activo; **ECON** solo
de lo que él mismo crea: las correspondencias, el movimiento, el estado de envío
y la recepción declarada. No aplicamos «el último que responde sobreescribe».

> Evidencia: [solucion-integracion.md § Responsabilidad de cada aplicación](solucion-integracion.md#responsabilidad-de-cada-aplicación) ·
> [equivalencias § Fechas, unidades y estados separados](equivalencias-prisma-startrack.md#fechas-unidades-y-estados-separados)

### A2. En producción, dos plataformas dicen cosas distintas. ¿Qué hace su sistema?

No sobrescribe ninguna. Conserva los dos hechos con sus identificadores de
origen, los presenta juntos y nombra a quién le toca decidir; la corrección se
hace en la plataforma dueña del dato. En la demo lo ve con la unidad `OBSOLETA`
que tiene una solicitud `APROBADA`: en pantalla, el asunto «Revisar la
asignación» y la interpretación de la unidad; por API, la misma situación sale
en `tensions`.

> Evidencia: `/solicitudes/{id}` y `/maquinaria/{id}` (`apps/api/app/dashboard/evidence_views.py`,
> `decision_priorities.py`); `GET /api/v1/graph?mode=fixture` → `tensions`
> (`obsolete_with_approved_request`), `apps/api/app/services/graph.py`;
> [reglas prioritarias](sincronizacion-y-discrepancias.md#reglas-prioritarias)

### A3. ¿Por qué consultan en vez de recibir eventos por webhook?

Porque los contratos consultados no los ofrecen para este caso: Prisma no
publica un webhook de aprobación y los webhooks documentados de Startrack
reenvían telemetría, no acreditan un cambio de tarea ni una aprobación. Por eso
hoy hacemos lecturas acotadas con presupuesto por proveedor, y la bandeja
durable de eventos queda como propuesta rotulada.

> Evidencia: [contexto vigente § Contratos de proveedores](contexto-vigente.md#contratos-de-proveedores) ·
> [equivalencias § Evidencia de retorno y cobertura](equivalencias-prisma-startrack.md#evidencia-de-retorno-y-cobertura)

### A4. ¿Qué pasa si crean una tarea y Startrack no responde? ¿Duplican?

No. El movimiento queda en estado `unknown` y **no se repite el POST**
automáticamente: se concilia por lectura, y solo se acepta la coincidencia si la
búsqueda agotada devuelve un único resultado con la misma referencia, destino,
título, fecha y asignados. Si no se puede cerrar, existe
`POST /api/v1/operations/{id}/resolve` para cerrarlo de forma explícita y con
motivo. Además, la base impide dos movimientos en vuelo por máquina y dos
movimientos con el mismo `job_id` por modo y entorno.

> Evidencia: [ADR 0004](adr/0004-persistent-transfer-workflow.md) ·
> [ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md) ·
> migración `0004_movement_guards_actors_and_indexes.py`

### A5. ¿Esto aguanta miles de vehículos?

Lo implementado está pensado para ser correcto antes que grande: un ciclo por
proceso y por base con candado de PostgreSQL, cola transaccional con reclamación
atómica, lecturas paginadas y el límite publicado de Startrack de 240 peticiones
por IP cada dos minutos. La escala a miles de vehículos está **documentada como
propuesta**, sin mediciones de carga ni de recuperación: no afirmamos una
capacidad que no medimos.

> Evidencia: [sincronización § Escala a miles de vehículos (propuesta)](sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta) ·
> [database.md](database.md)

---

## B · Calidad y gobierno del dato

### B1. ¿Cómo evitan unir dos registros que no son el mismo?

Todo se une por **identificador de origen**, nunca por nombre: UUID de proyecto,
solicitud, maquinaria y operador, e IDs de Startrack. Cada registro conserva su
procedencia —fuente, entorno, clase de evidencia y momento de lectura— y los IDs
del hub llevan prefijo (`nexus:request:…`) para no confundirse con los del
proveedor. Que un nombre coincida en las dos pantallas no acredita identidad.

> Evidencia: [equivalencias § Identidad y cardinalidad](equivalencias-prisma-startrack.md#identidad-y-cardinalidad) ·
> `apps/api/app/models/hub.py`

### B2. ¿Qué hicieron con los campos que no tienen equivalente?

Se marcan **sin equivalente** y no se envían. En la pantalla de integración se
ven cuatro que el formulario real de Startrack pide y su objeto público no
expone: «Origen», «Completar antes de», la ventana horaria de entrega y los
artículos. Y al revés: la tarifa por hora y el período de uso de Prisma no
viajan a la tarea porque describen otra cosa. Un mapeo forzado es una deuda
oculta; una fila marcada es una decisión.

> Evidencia: `/integracion?mode=fixture` → pestaña «Mapa de campos» ·
> `output/matrices/formulario-tarea-completo.csv` ·
> `apps/api/app/services/integration_trace.py` (`STARTRACK_ONLY`)

### B3. El propio diccionario del kit tiene errores. ¿Los corrigieron?

No los corregimos en origen: los documentamos y comparamos por ID. Hay nueve
inconsistencias internas registradas, entre ellas `Retroexcavadora` y
`Retroexcavadoras` como dos clases distintas, tres grafías de `OBSOLETA`, el
rótulo «Titulo» sin tilde cuando la clave de la API es `objective`, y varios
formatos de fecha conviviendo —incluido un modal que muestra `MM/DD/AAAA`
mientras el resto de la interfaz usa `DD/MM/AAAA`—. Por eso solo transcribimos
fechas desde la API y agrupamos por ID, no por etiqueta.

> Evidencia: [equivalencias § Inconsistencias internas que ya conoce el kit](equivalencias-prisma-startrack.md#inconsistencias-internas-que-ya-conoce-el-kit) ·
> `output/matrices/inconsistencias-internas.csv`

### B4. ¿Cómo sé que la hoja de cálculo que me entregan dice lo mismo que su documento?

Porque no se escribe a mano. El Markdown es el original y un script copia sus
tablas a 17 CSV y a un XLSX, con el SHA-256 del origen y de cada archivo en el
manifiesto; `exportar_matrices.py --check` falla en CI si una copia se queda
atrás. Lo mismo con el diccionario de RF-01, que se genera desde los modelos.

> Evidencia: [output/matrices/MANIFEST.md](../output/matrices/MANIFEST.md) ·
> `scripts/docs/exportar_matrices.py --check` · `.github/workflows/ci.yml`

---

## C · Seguridad y credenciales

### C1. ¿Dónde viven las credenciales de los sandboxes?

Solo en el servidor, en un `.env` que no se versiona. El navegador nunca recibe
ni habilita credenciales de proveedor, y los mensajes de error públicos no
incluyen respuestas crudas, cookies ni secretos. La sesión de la aplicación es
una cookie firmada `HttpOnly` y `Secure` por defecto.

> Evidencia: `apps/api/app/core/config.py` · `.gitignore` ·
> [ADR 0005](adr/0005-session-auth-and-roles.md) · `apps/api/tests/test_security.py`

### C2. ¿Han escrito algo en Prisma o en Startrack?

No. Todo el trabajo es sobre sandbox y datos sintéticos. Las tres habilitaciones
del servidor —lecturas remotas, escrituras remotas y encolado automático— están
en `false` por defecto y **ningún rol de la aplicación puede encenderlas**:
requieren configuración del servidor. Además, ECON no ejecuta el `PATCH` de
aprobación de Prisma: aprobar y asignar sigue siendo una operación de Prisma.

> Evidencia: `apps/api/app/core/config.py` (`allow_live_reads`,
> `allow_live_writes`, `auto_queue_transfers`) ·
> [equivalencias § De la aprobación a la tarea](equivalencias-prisma-startrack.md#de-la-aprobación-a-la-tarea-contrato-frente-a-implementación)

### C3. ¿Quién puede hacer qué, y queda registrado?

Seis roles con permisos explícitos: `logistica` guarda planes, encola y declara
recepción; `gerencia_proyecto` declara recepción; `mantenimiento`,
`control_costos` y `lectura` solo consultan; `admin` administra usuarios. El
usuario autenticado queda vinculado a cada transición (`actor_*`) y a la
recepción (`declared_by_*`), y en PostgreSQL la tabla de eventos es
**append-only** por trigger: un evento no se reescribe.

> Evidencia: `/administracion`; `/operaciones/{id}` (actor de cada evento) ·
> [ADR 0005](adr/0005-session-auth-and-roles.md) · migración `0004`

### C4. ¿Por qué no tienen la API de Startrack funcionando?

Porque la cuenta entregada da acceso web, no acceso de integración. Seguimos el
procedimiento documentado para obtener la API key y la consulta al detalle de
usuario respondió **403**; detuvimos esa vía y no probamos claves de otros
usuarios. Es una dependencia del administrador del cliente, no una decisión
técnica nuestra, y por eso la parte de Startrack se demuestra como contrato y
cuerpo preparado.

> Evidencia: [integraciones-reales.md § Startrack: API oficial y sesión web](integraciones-reales.md#startrack-api-oficial-y-sesión-web)

---

## D · Indicadores y SLA

### D1. ¿Por qué casi todos sus indicadores dicen «no evaluable»?

Porque la muestra no permite calcularlos y preferimos decirlo a publicar un
cero. Faltan dos cosas: un **corte de observación** común —el documento tiene
día, no instante— y **tareas de Startrack**, que el archivo entregado no
contiene. La lectura cubre 5 de 15 unidades y 2 solicitudes. Cada ficha declara
su motivo, y con `live` y el registro completo las mismas fichas se calculan sin
cambiar la fórmula.

> Evidencia: `/indicadores?mode=fixture`; `GET /api/v1/indicators?mode=fixture` ·
> [indicadores calculables](indicadores-calculables.md#qué-impide-agregar-hoy) · `/fuentes`

### D2. ¿Qué indicador hace visible la integración que hoy no existe?

**Tiempo de equipo fuera de geocerca sin justificación**, en horas por equipo y
período: se calcula como la unión de los intervalos válidos fuera de la geocerca
asignada, dentro del horario exigible, excluyendo salidas justificadas. Necesita
identidad y vigencia del dispositivo, geocerca y asignación, eventos fechados y
un criterio de justificación acordado. Hoy su resultado es **no evaluable**, y
lo publicamos así: estar fuera de la geocerca no equivale por sí solo a tiempo
muerto ni a uso indebido.

> Evidencia: [RF-06, definición única](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado)

### D3. ¿Me pueden dar un porcentaje de cumplimiento de SLA o un promedio?

No con estos datos, y no lo vamos a inventar. Con dos solicitudes y cinco
unidades, un promedio o un percentil no describe la operación. Los seis SLA que
proponemos —aprobación, asignación, envío de tarea, recepción, atención de falla
con paro y frescura de la evidencia— llevan fórmula y unidad, pero su umbral
está marcado **«a validar con ECON»** y la pantalla no calcula cumplimiento.
Publicamos filas con su evidencia, no indicadores agregados.

> Evidencia: `/indicadores` → pestaña «SLA propuestos» ·
> [fichas de SLA](indicadores-calculables.md#fichas-de-sla-propuestas-no-implementadas)

### D4. Entonces, ¿pueden medir tiempos muertos o utilización de la flota?

Todavía no, y decir que sí sería el error más caro. El horómetro mide una
magnitud cuya definición hay que validar y no equivale a horas productivas; en
una excavadora, estar quieta puede ser trabajo normal, así que velocidad cero
con motor encendido no define ralentí improductivo. Hace falta jornada
planificada, bitácoras aprobadas, causas de espera y señales de actividad. La
clasificación por intervalo —trabajo, traslado, espera con causa, mantenimiento,
pausa planificada y tiempo sin evidencia— está propuesta, con la categoría «sin
clasificar» siempre visible.

> Evidencia: [sincronización § Cómo medir utilización y tiempos muertos](sincronizacion-y-discrepancias.md#cómo-medir-utilización-y-tiempos-muertos) ·
> [kpis-y-referencias-iso.md](kpis-y-referencias-iso.md)

---

## E · Viabilidad de producción y siguientes pasos

### E1. ¿Qué falta para que esto entre en producción?

Cinco cosas, en este orden: **(1)** la API key de Startrack y una validación
autenticada —catálogos, permisos, zona horaria, formato de arrays y respuesta
real de creación—; **(2)** acordar y versionar las correspondencias proyecto ↔
geocerca, máquina ↔ vehículo rastreado y operador ↔ usuario, con vigencias;
**(3)** validar la RACI con las tres gerencias; **(4)** fijar el criterio
empresarial de recepción; **(5)** la bandeja durable de eventos y la cobertura
por fuente. No damos una fecha sin alcance acordado.

> Evidencia: [contexto vigente § Implementado y pendiente](contexto-vigente.md#implementado-y-pendiente) ·
> [equivalencias § Lagunas](equivalencias-prisma-startrack.md#lagunas-que-deben-resolverse-antes-de-ampliar-la-equivalencia)

### E2. Si en Prisma cambian la asignación después de enviar la tarea, ¿qué pasa?

Hoy el hub conserva la copia de Prisma con la que preparó el envío y el grafo
señala `movement_source_changed` cuando el origen difiere de esa copia. La
**incidencia durable** con historial de revisión es propuesta, no está
implementada, y así lo decimos. La regla propuesta es revisar el traslado
existente y acordar su modificación o cancelación: nunca crear otra tarea
automáticamente.

> Evidencia: `apps/api/app/services/graph.py` ·
> [reglas prioritarias](sincronizacion-y-discrepancias.md#reglas-prioritarias) ·
> [arquitectura por eventos (propuesta)](arquitectura-integracion-eventos.md)

### E3. ¿Cómo llegan de aquí a un portal con visibilidad para el cliente?

La proyección ya existe: cada solicitud se publica en JSON con su evidencia y su
cobertura, y la misma respuesta alimenta la pantalla. Para un portal faltan dos
decisiones, no una reescritura: control de acceso por proyecto y acuerdo sobre
qué evidencia es publicable hacia fuera. Lo presentamos como propuesta, con su
diagrama, no como algo desplegado.

> Evidencia: `GET /api/v1/integration/{request_id}` · `GET /api/v1/hub` ·
> [sincronización § Escala](sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta)

### E4. Su equipo tenía asignados RE-03, MOT-006 y PROY-006. ¿Por qué la demo usa CF-03?

Porque el modo de la demo lee las **muestras del contrato entregado**, y esas
muestras contienen PROY-014 y CF-03, no RE-03. En el sandbox sí encontramos
RE-03 buscando por su código, y vimos en pantalla una solicitud de PROY-006 sin
unidad; pero la búsqueda de solicitudes por `PROY-006` devolvió cero resultados
y una captura no acredita un UUID. Mezclar los IDs de los dos casos para
completar el relato habría sido exactamente el atajo que este reto castiga. Con
las lecturas en vivo habilitadas en el servidor, RE-03 se consulta por su código
en la misma pantalla.

> Evidencia: [contexto vigente § Identidad y muestras](contexto-vigente.md#identidad-y-muestras) ·
> `apps/api/app/integrations/data/sandbox_samples.json` ·
> [integraciones-reales.md](integraciones-reales.md) (búsqueda `RE-03` en Prisma: una coincidencia)

---

## Frases que no decimos

Si alguna se escapa, corregirla en el momento; el jurado evalúa exactamente esto.

| No decir | Decir |
| --- | --- |
| «Está integrado con Startrack» | «Está preparado el cuerpo de la tarea según el contrato; el envío autenticado está pendiente de la API key» |
| «No hay tareas» | «La muestra no trae tareas; no sabemos cuántas hay en la operación» |
| «El equipo está en el proyecto» | «Prisma informa esa asignación administrativa; no tenemos posición observada» |
| «La máquina llegó» | «Hay una visita a la geocerca; la recepción es una declaración con responsable y constancia» |
| «Reducimos los tiempos muertos un X %» | «Habilitamos el indicador que hoy nadie puede calcular, con su fórmula y sus datos requeridos» |
| «Las pruebas están en verde» | «La revisión del visor de integración pasó Ruff y sus pruebas; la suite completa tiene fallos registrados que no ocultamos» |
