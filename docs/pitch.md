# Pitch y demo · ECON · Hub de operaciones

Equipo 6 — Los Filósofos. Reto **Hub de Operaciones** de Grupo ECON en Entropy
Hack. Formato del bloque final: **5 minutos de pitch + 5 minutos de demo en
vivo + 3 minutos de preguntas**, con al menos dos integrantes hablando.

Este guion solo afirma lo que se puede abrir en pantalla o en un documento de
este repositorio. Las preguntas previsibles del jurado, con su respuesta y su
evidencia, están en [pitch-preguntas.md](pitch-preguntas.md).

Recursos asignados al equipo en el kit: **RE-03 · MOT-006 · PROY-006 (Proyecto
Zeta, San Salvador)**. Las muestras del contrato que usa el modo `fixture`
corresponden a **PROY-014 / CF-03**: son fuentes distintas y no se mezclan
([identidad y muestras](contexto-vigente.md#identidad-y-muestras)).

---

## 1. Resumen en 30 segundos

> Grupo ECON coordina la misma maquinaria desde dos plataformas que no se
> hablan: Prisma sabe qué se solicitó, quién aprobó y qué unidad se asignó;
> Startrack sabe qué traslado se programó y dónde está el activo. Hoy el puente
> entre ambas son llamadas y correos entre tres gerencias. Construimos un hub
> que lee las dos, conserva los identificadores de origen, aplica reglas
> explícitas y muestra en una sola pantalla el estado, la ubicación observada
> cuando existe y lo que falta para cerrar cada traslado —incluido lo que
> ninguna de las dos plataformas sabe—. Para Logística, Mantenimiento y
> Proyectos es una consulta en lugar de una llamada.

Frase de reserva si hay que acortar: «Una sola pantalla que responde, por
unidad y por solicitud, qué dice Prisma, qué dice Startrack y qué evidencia
falta, sin inventar la parte que no existe».

---

## 2. Guion minutado del pitch (5 minutos, dos voces)

**Voz 1** (negocio y proceso) · **Voz 2** (datos y arquitectura). Los tiempos
son acumulados; cada bloque incluye lo que se dice y de dónde sale.

### 0:00 – 0:40 · Voz 1 · El problema real (AS-IS)

- Grupo ECON gestiona maquinaria pesada con dos plataformas construidas por
  separado. **Prisma** organiza proyectos, partidas, solicitudes, asignación y
  costos. **Startrack** rastrea la flota, define geocercas y gestiona las tareas
  de traslado.
- Tres gerencias persiguen el mismo objetivo desde plataformas distintas:
  **Logística y Equipo**, **Mantenimiento** y **Técnica de Proyectos**. Cada una
  con sus estados y su vocabulario.
- Consecuencia documentada en el AS-IS del reto: información dispersa, sin
  fuente única, trabajo duplicado para mantener ambas plataformas y una
  coordinación diaria que depende de comunicación manual.
- Frase de cierre del bloque: «El problema no es que falte un dato. Es que
  ningún sistema tiene los dos lados de la misma operación».

### 0:40 – 1:30 · Voz 1 · Qué falla hoy exactamente entre Prisma y Startrack

Tres hechos concretos, no adjetivos. Los tres están en la matriz de mapeo
([glosario de sinónimos](equivalencias-prisma-startrack.md#glosario-de-sinónimos-entre-plataformas)):

1. **No existe la llave que une las dos plataformas.** Prisma no tiene
   geocercas; el objeto de tarea de Startrack no tiene campo de proyecto. El
   vínculo proyecto ↔ geocerca es una decisión humana que **ninguno de los dos
   contratos consultados guarda**.
2. **«Estado» significa cuatro cosas distintas.** Estado de la solicitud
   (Prisma), estado de la maquinaria (Prisma), estado de la tarea (Startrack) y
   estado del envío (el hub). Compararlos por su nombre fabrica conflictos que
   no existen: una máquina «Ocupada» y una tarea «Completada» pueden ser
   correctas a la vez.
3. **La misma palabra nombra objetos distintos.** «Tipo» es la clase de equipo
   en Prisma y el tipo de tarea en Startrack; «Traslado» también es un paso del
   flujo de fallas de Prisma (`TRASLADO_STD`). Un mapeo por nombre parece
   funcionar y falla en producción.

### 1:30 – 2:15 · Voz 2 · La propuesta

- Un **hub de operaciones**: no reemplaza Prisma ni Startrack, los reconcilia.
- Lee de Prisma la solicitud, la aprobación y la unidad asignada; **conserva los
  UUID de origen**, el entorno y el momento de lectura.
- Guarda la correspondencia que ninguna plataforma tiene —proyecto ↔ geocerca,
  operador ↔ usuario de Startrack, activo rastreado— **por identificador, nunca
  por nombre**, y la deja asociada al movimiento.
- Prepara el cuerpo de la tarea de Startrack con reglas visibles y **muestra los
  campos que faltan** en lugar de rellenarlos.
- Publica lo mismo en pantalla y en JSON: `/integracion` y
  `GET /api/v1/integration/{request_id}` usan el mismo servicio.
- Y, cuando un dato no existe, lo dice: **no verificable** es un resultado
  válido; cero es una afirmación y no la hacemos sin evidencia.

### 2:15 – 2:45 · Voz 2 · La arquitectura en una frase

> Un solo servicio Python —Dash y FastAPI en el mismo proceso— que lee Prisma,
> prepara la tarea de Startrack, registra cada movimiento y su evidencia en
> PostgreSQL con eventos que no se reescriben, y publica la misma proyección en
> la pantalla y en la API.

Complemento en una línea si hay tiempo: «cada estado vive donde nació —solicitud
y maquinaria en Prisma, tarea y posición en Startrack, envío y recepción en
ECON— y el hub los muestra juntos sin fusionarlos»
([diagrama «dónde vive cada estado»](entregables-visuales.md#diagrama-6-dónde-vive-cada-estado)).

### 2:45 – 3:45 · Voz 1 · Impacto para las tres gerencias

Una decisión concreta por gerencia; ninguna requiere una cifra inventada:

| Gerencia | Pregunta que hoy exige una llamada | Dónde la responde el hub |
| --- | --- | --- |
| Logística y Equipo | ¿Qué unidades cumplen las reglas para esta solicitud pendiente y por qué las demás no? | Detalle de la solicitud: candidatas con su regla (clase, estado, paro, período) y las excluidas con su motivo |
| Mantenimiento | ¿Hay un traslado programado sobre una unidad que yo tengo restringida? | Ficha de la unidad: estado administrativo y condición de mantenimiento separados, con el traslado al lado |
| Técnica de Proyectos | ¿Qué falta para dar por recibida esta máquina en mi proyecto? | Un asunto por solicitud con su evidencia y el siguiente paso; la recepción es una declaración con responsable y constancia |

Tres efectos que sí podemos sostener:

- **Trazabilidad**: la correspondencia entre plataformas queda guardada por ID,
  con quién la registró y cuándo. Ninguno de los dos contratos consultados tiene
  dónde guardarla.
- **Menos trabajo duplicado**: el mismo dato se captura una vez y se reutiliza
  en la preparación de la tarea, en el seguimiento y en la evidencia.
- **Indicadores que hoy nadie puede calcular**: la integración habilita por
  primera vez «tiempo de equipo fuera de geocerca sin justificación», con su
  fórmula ya definida y su resultado declarado **no evaluable** mientras falten
  los datos ([RF-06](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado)).

### 3:45 – 4:20 · Voz 2 · Qué no afirmamos

- Todo el caso usa **datos sintéticos**: `fixture` son muestras del contrato
  entregado; `live` consulta el sandbox. **Sin fallback entre ambos**: si la
  lectura en vivo falla, no se sustituye por la muestra.
- Una flecha del recorrido describe el **contrato** de interacción; no prueba
  que una petición ocurrió. Un cuerpo preparado no acredita envío. El GPS no
  acredita recepción.
- Lecturas y escrituras remotas están **deshabilitadas por defecto**; las
  credenciales viven solo en el servidor.
- «Lo que no sabemos lo decimos. En un mapeo forzado el error aparece en
  producción; en un campo marcado sin equivalente, aparece en la reunión.»

### 4:20 – 4:50 · Voz 1 y Voz 2 · Reflexión de aprendizaje

Bloque exigido por la rúbrica (4.2). Cada voz dice una frase **propia**; estas
tres son las que el trabajo respalda y sirven de guion:

- «Llegamos pensando que dos estados distintos entre plataformas eran un error
  de sincronización. Aprendimos que describen objetos distintos: una máquina
  ocupada y una tarea completada pueden ser correctas a la vez, y corregir una
  para igualarla a la otra destruye información.»
- «Creíamos que el mapeo era un problema de nombres de campo. La parte difícil
  fue la identidad: qué es la misma cosa en los dos sistemas y quién decide que
  lo es. El GPS puede ir en el transportador, no en la máquina.»
- «Descubrimos que el dato más útil para la operación es el que falta. Por eso
  la pantalla distingue “no informado” de “cero”.»

### 4:50 – 5:00 · Voz 1 · Cierre y traspaso a la demo

«El jurado elige la unidad o la solicitud. Vamos a la aplicación.»

---

## 3. Guion de la demo (5 minutos)

Base: el [guion de diez pasos del README](../README.md#guion-de-demo-para-el-jurado),
recortado a cinco minutos. Modo `fixture`, sin proveedores. Cada paso dice **qué
URL abrir** y **qué señalar**.

### Antes de empezar (fuera del reloj)

1. Aplicación levantada en `http://127.0.0.1:8050`, sesión iniciada con un
   usuario `admin` o `logistica`; segunda pestaña en `/docs` ya autenticada.
2. **Plan de traslado guardado de antemano** para la solicitud APROBADA, con una
   geocerca, un usuario de Startrack, una referencia y una fecha programada. Sin
   ese plan `/integracion` no muestra cuerpo preparado: muestra los cuatro datos
   que faltan. Ambas situaciones sirven; hay que saber cuál se está enseñando y
   decirlo.
3. Pestañas abiertas en este orden: portada (`/?mode=fixture`), `/maquinaria`,
   `/solicitudes`, `/integracion`, `/indicadores`, `/fuentes`, y `/operaciones`
   como reserva.

IDs de la muestra (los de la demo; se leen del archivo, no se inventan):

| Objeto | ID | Dato visible |
| --- | --- | --- |
| Unidad CF-03 | `nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03` | `OBSOLETA`, PROY-014, asignación 11–14/09/2026 |
| Solicitud APROBADA | `nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135` | Cargador frontal, 11–14/09/2026, CF-03 |
| Solicitud PENDIENTE | `nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888` | Cargador frontal, 16–18/09/2026, sin unidad |

Los detalles se abren con el ID codificado en la URL, por ejemplo
`/maquinaria/nexus%3Aequipment%3A66faacde-728c-4378-8b46-dbfb38254e03?mode=fixture`.
En la demo se llega a ellos haciendo clic en la tabla, que es más rápido.

### 0:00 – 0:15 · La portada: qué requiere atención

- **URL**: `/?mode=fixture`.
- **Señalar**: la página abre en **«Operación · Qué requiere atención»**, con dos
  bloques: **«Qué pasa»** (agenda de uso y asignación, una franja por solicitud
  entre el inicio y el fin pedidos) y **«Qué hago»** (un asunto por solicitud con
  el hecho observado que lo sustenta). Con la muestra, los dos asuntos son
  «Resolver aprobación y asignación» y «Revisar la asignación».
- **Decir**: «Esto no es un tablero de conteos: es la cola de trabajo de la
  operación, con el hecho que justifica cada asunto y sin orden inferido del
  reloj».

### 0:15 – 0:40 · El jurado elige

- **URL**: `/maquinaria?mode=fixture`.
- **Señalar**: cinco unidades (CF-01, CF-02, CF-03, EXC-01, EXC-02) con su
  estado administrativo, proyecto y procedencia; el buscador filtra por código,
  activo, nombre, proyecto o empresa.
- **Decir**: «Esta lectura trae 5 de 15 unidades informadas por Prisma. Elija la
  que quiera; seguimos con la que elija». Si elige una de las cinco, continuar
  con ella; si pide otra, ir al **plan B de cobertura** del apartado 6.

### 0:40 – 1:25 · Consulta unificada de la unidad (RF-04)

- **URL**: detalle de la unidad elegida, p. ej.
  `/maquinaria/{id}?mode=fixture`.
- **Señalar**, de arriba abajo:
  - la interpretación de la unidad. Con CF-03: **«Revisar el estado
    administrativo antes de continuar»**, porque Prisma informa `OBSOLETA` y ese
    estado administrativo no demuestra una avería;
  - desplegar **«Comparar fuentes y evidencia»**: a la izquierda lo de Prisma
    (estado, mantenimiento, período de asignación 11–14/09, procedencia); a la
    derecha lo de Startrack, con su propia fecha de observación;
  - dentro de esa comparación, las filas **«Estado de tarea → No determinado»**
    y **«Ubicación observada → Sin observación disponible / Sin lectura
    fechada»**, cada una con su nota: una visita de geocerca puede corresponder
    al transportador y no acredita recepción. Es la respuesta literal a «dónde
    está»: no hay observación, y no la inventamos;
  - las solicitudes que asignan esa unidad **por su `maquinaria_id` exacto**,
    nunca por nombre.
- **Decir**: «Con la muestra, el lado de Startrack aparece sin determinar porque
  el archivo entregado no contiene tareas, visitas ni recepciones. Eso no
  significa que no existan en la operación: significa que no las hemos leído».

### 1:25 – 2:05 · Estados que difieren y cómo se resuelven (RF-05)

- **URL**: `/solicitudes/{id APROBADA}?mode=fixture`.
- **Señalar**: la solicitud está **APROBADA** con su `approved_at` sobre una
  unidad **OBSOLETA**. En pantalla, el asunto de la solicitud se titula
  **«Revisar la asignación»** y su evidencia es literal: «Unidad CF-03; estado
  administrativo OBSOLETA. Sin falla activa ni paro registrados». En la ficha de
  la unidad, la interpretación dice **«Revisar el estado administrativo antes de
  continuar»** y nombra a quién corresponde: Logística confirma si mantiene la
  asignación y consulta a Mantenimiento cuando falta evidencia de la condición.
  Ninguno de los dos hechos se modifica para que coincidan.
- **Por API**: `GET /api/v1/graph?mode=fixture` devuelve el mismo caso en
  `tensions`, como `obsolete_with_approved_request`, con los dos IDs y su
  evidencia (`machinery_status=OBSOLETA`, `request.status=APROBADA`). La
  proyección del grafo es la vía por API; en la interfaz el caso se lee en el
  asunto y en la interpretación.
- **Decir la regla**: «Cada estado describe un objeto distinto y se conserva en
  su fuente. La regla del caso 02 —Ocupada en Prisma y Completada en Startrack
  coexisten— está implementada y documentada; con esta muestra no se puede
  ejercitar porque no hay tareas, y preferimos decirlo a fabricar una».
- **Si hay tiempo**, abrir `/solicitudes/{id PENDIENTE}?mode=fixture`: el bloque
  de unidades candidatas lista **CF-01 y CF-02 elegibles**, **CF-03 excluida**
  («OBSOLETA: revisar con Mantenimiento; el estado no afirma avería ni paro») y
  **EXC-01 y EXC-02 excluidas** por clase distinta. Cerrar con: «recomendar no
  es asignar: la asignación se registra en Prisma».

### 2:05 – 3:00 · La integración, campo por campo

- **URL**: `/integracion?mode=fixture`, selector **«Solicitud a seguir»**.
- **Pestaña «Recorrido»**: las cuatro etapas —consultar solicitud y unidad en
  Prisma, normalizar y validar en ECON, preparar la tarea para Startrack,
  consultar la evidencia de retorno— cada una con su estado propio. Decir:
  «estas flechas son el contrato de integración, no una captura de tráfico».
- **Pestaña «Mapa de campos»**: 26 filas con el concepto y su nombre exacto en
  Prisma, en ECON y en Startrack, y el tratamiento de cada una —**Conservado**,
  **Transformado**, **Manual (operador)** o **Sin equivalente**—. **Aquí va el
  caso de mapeo no directo** (apartado siguiente).
- **Pestaña «Respuesta de nuestra API»**: el mismo JSON que devuelve
  `GET /api/v1/integration/{request_id}?mode=fixture`. Decir: «un HTTP 200 de
  nuestra API puede describir evidencia faltante; no certifica que se haya
  enviado nada a Startrack».
- Si el plan está guardado, mostrar **el cuerpo preparado** para `POST /api/job`
  y subrayar: «preparado, no enviado». Si no lo está, mostrar los cuatro datos
  que faltan —correspondencia de proyecto con `poi_id`, usuarios asignables,
  referencia del movimiento y fecha programada— y decir que sin ellos el hub
  **no construye el cuerpo**.

#### El caso donde el mapeo no fue directo (exigido por el brief)

**Campo:** proyecto de destino. **Prisma:** `Solicitud.project_id` /
`project_name`. **Startrack:** `StartrackJob.poi_id`.

- Prisma **no tiene geocercas** y el objeto de tarea de Startrack **no tiene
  campo de proyecto**. No hay clave foránea, ni catálogo común, ni ninguna de
  las dos plataformas conoce a la otra.
- El nombre compartido del ejercicio, `PROY-014 - The Hub - Proyecto Xi - La
  Unión`, es una pista, **no una llave**: unir por nombre habría producido un
  mapeo que se rompe con cualquier cambio de rótulo.
- **Cómo se resolvió**: la fila se clasifica como **Manual** en la matriz. El
  hub obliga a una correspondencia explícita por ID, elegida por Logística, y la
  guarda en el propio movimiento (`project_source_id` y `poi_id`). Sin ella, la
  preparación queda en `missing_information` y la primera línea de datos
  faltantes es «Correspondencia de proyecto con `poi_id` de destino».
- **Qué queda documentado como pendiente**: no existe todavía un maestro
  versionado de equivalencias con vigencias; hoy la correspondencia vive por
  movimiento
  ([lagunas](equivalencias-prisma-startrack.md#lagunas-que-deben-resolverse-antes-de-ampliar-la-equivalencia), punto 5).

Dos casos de reserva, por si el jurado pide otro:

- **Operador ↔ usuario de Startrack**: son cuatro roles distintos (persona en
  Prisma, conductor del activo, usuario que ejecuta la tarea, firmante de la
  visita). Se corresponden **por el código documentado `MOT-xxx`, nunca por
  nombre**; `assigned_user_remote_ids` es la vía documentada y queda pendiente
  de confirmar con el proveedor.
- **Campo sin equivalente que se puede señalar en pantalla**: «Origen
  (geocerca)». El formulario real de Startrack lo pide, pero el objeto público
  de tarea tiene **una sola geocerca** (`poi_id`). No inventamos
  `origin_poi_id`: la fila aparece marcada *sin equivalente* en «Mapa de
  campos», junto con «Completar antes de», la ventana horaria de entrega y los
  artículos.

### 3:00 – 3:45 · Indicadores y SLA

- **URL**: `/indicadores?mode=fixture`.
- **Señalar primero el «Tablero de indicadores»**: trece cifras agrupadas por el
  área que decide —Logística, Proyectos, Mantenimiento e Información—. Leer dos
  en voz alta y dejar que el contraste hable: «Aprobaciones con tiempo medido:
  **1**, tiempo medido **42 s**» y «Aprobadas con unidad sin tarea enviada:
  **No evaluable**, porque las muestras no envían tareas y la ausencia en el
  archivo no es cero». Cada cifra lleva su población («2 de 2 solicitudes
  leídas», «5 de 15») y enlaza con las filas que la sustentan.
- **Señalar después las pestañas**, una por pregunta. Con la muestra,
  **«Aprobación»** es la única con una fila evaluable: la solicitud APROBADA
  tardó **42,2 segundos** entre `created_at` y `approved_at`; la PENDIENTE
  aparece como no evaluable con el motivo «sin `approved_at`». El resto declara
  **por qué** no es evaluable —sin corte de observación, sin tareas en la
  muestra, sin casos entre las cinco filas leídas—. La pestaña
  **«SLA propuestos»** lleva los seis objetivos con umbral «a validar con ECON»
  y **sin cálculo de cumplimiento**.
- **Decir**: «No publicamos promedios, medianas ni porcentajes: con dos
  solicitudes, un promedio es decoración. Publicamos filas con su evidencia, y
  cuando no hay dato publicamos el motivo».

### 3:45 – 4:15 · Fuentes, cobertura y honestidad del dato

- **URL**: `/fuentes?mode=fixture`.
- **Señalar**: el bloque **«Procedencia»**, con cada fuente, su estado, su
  lectura y su situación; y el bloque **«Alcance · Cobertura por colección de
  Prisma»**, cuya línea lo resume: «Solicitudes: 2 de 2 · Maquinaria: 5 de 15 ·
  un total desconocido no es cero». La parte rayada del gráfico son registros
  fuera de esta consulta, no equipos indisponibles.
- **Decir**: «La ausencia de tareas en el corte de Prisma no determina si
  existen tareas en Startrack. Un total desconocido no es cero».
- Opcional, 10 segundos: cambiar a `?mode=live`. Con las lecturas remotas
  deshabilitadas por defecto, la pantalla dice **«deshabilitadas»** y no muestra
  ningún registro. Ese es el comportamiento correcto: no hay fallback a la
  muestra.

### 4:15 – 5:00 · Reserva para lo que pida el jurado

Guardar cuarenta y cinco segundos. Usos previstos, por orden de utilidad:

- **`/operaciones?mode=fixture`**: el movimiento guardado con su estado, sus
  eventos y el usuario de sesión que actuó; la tabla dice cuándo la lectura del
  registro es parcial. Añadir: «con un usuario de rol `lectura` esta pantalla no
  muestra ninguna acción». En `fixture` no hay envío: encolar responde 409.
- **`/docs`** y ejecutar `GET /api/v1/graph?mode=fixture`: 5 máquinas,
  2 solicitudes, 1 proyecto, 4 aristas, 0 conflictos, la tensión
  `obsolete_with_approved_request` y `coverage.complete=false`.
- Repetir la consulta unificada sobre otra unidad que pida el jurado.

### El momento en que el jurado elige (preparación explícita)

El brief obliga: el jurado **elige en vivo** un equipo o una partida no
anunciada y pide estado, ubicación y discrepancias.

**Camino exacto, en tres clics:**

1. `/maquinaria?mode=fixture` → escribir el código en el buscador (por ejemplo
   `CF-02`) → clic en la fila.
2. En el detalle: interpretación de la unidad → «Comparar fuentes y evidencia»
   → «Solicitudes con esta unidad asignada».
3. Desde ahí, clic en la solicitud para ver aprobación, período, plan de
   traslado y siguiente paso; o `/integracion` y elegir esa solicitud en el
   selector.

**Qué se ve según lo que elijan:**

| Elección del jurado | Lo que aparece | Lo que hay que decir |
| --- | --- | --- |
| CF-03 | `OBSOLETA`, PROY-014, asignación 11–14/09, solicitud APROBADA asociada, asunto «Revisar la asignación» | El caso más rico: dos hechos ciertos que obligan a revisar |
| CF-01 o CF-02 | `DISPONIBLE`, sin proyecto ni fechas, elegibles para la solicitud pendiente | Disponible es un estado administrativo; no acredita disponibilidad física |
| EXC-01 o EXC-02 | `DISPONIBLE`, clase Excavadora, excluidas de la solicitud de cargador frontal | La regla de clase se aplica tal cual, sin «parecidos» |
| Una unidad fuera de las cinco (RE-03, por ejemplo) | No está en la lectura | Ver el plan B de cobertura (apartado 6) |
| La solicitud PENDIENTE | Sin unidad, 16–18/09, candidatas con reglas | Recomendar no es asignar |

---

## 4. Mapeo contra la rúbrica

Rúbrica de la sección 13 del brief: 100 puntos en 5 criterios. Esta tabla cruza
cada indicador con la evidencia y dice, sin adornos, cuándo está parcial.

| # | Indicador (pts) | Evidencia en el proyecto | Estado honesto |
| --- | --- | --- | --- |
| 1.1 | Propuesta de valor más allá de lo obligatorio (10) | Panel de indicadores y SLA (`/indicadores`, `GET /api/v1/indicators`); unidades candidatas con reglas explícitas (`/solicitudes/{id}`, `GET /api/v1/requests/{id}/suggestions`); traza de integración (`/integracion`); propuesta de portal y escala en [sincronización y escala](sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta) | Completo como capacidad demostrable; la escala es **propuesta**, sin mediciones de carga |
| 1.1 | Argumento de reducción de tiempos muertos, trazabilidad y decisiones (10) | Correspondencias guardadas por ID con actor y fecha; [RF-06](entregables-visuales.md#rf-06-indicador-definido-sin-valor-inventado); [qué impide agregar hoy](indicadores-calculables.md#qué-impide-agregar-hoy) | Argumento sostenido con la mecánica, **sin cifras de ahorro**: no hay datos para calcularlas |
| 1.2 | Relevancia para las tres gerencias (10) | [RACI de nueve decisiones](equivalencias-prisma-startrack.md#responsabilidades-propuestas-para-confirmar) (`output/matrices/raci-propuesta.csv`); roles de sesión aplicados en la app ([ADR 0005](adr/0005-session-auth-and-roles.md)); indicadores agrupados por área que decide | Cumple; la RACI es **propuesta pendiente de validación** por las gerencias |
| 2.1 | Matriz de mapeo completa y honesta (10) | [equivalencias-prisma-startrack.md](equivalencias-prisma-startrack.md) con cinco clasificaciones; 17 CSV y `matrices-econ.xlsx` con SHA-256 en [MANIFEST](../output/matrices/MANIFEST.md); `exportar_matrices.py --check` en CI | **Parcial**: falta el cotejo fila a fila de las 51 definiciones del diccionario del kit y no hay PDF vigente de la matriz completa |
| 2.2 | Arquitectura defendible en Q&A (10) | [solución de integración](solucion-integracion.md#arquitectura-implementada); estados de envío `draft`…`failed` con conciliación sin reenvío; `operation_events` append-only y unicidad en vuelo (migración `0004`); [ADR 0004](adr/0004-persistent-transfer-workflow.md) y [ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md) | Cumple; la **creación autenticada de tareas en Startrack sigue sin validar** (la cuenta no entregó API key) |
| 3.1 | Funciona en vivo y responde a la consulta que pida el jurado (5) | Aplicación navegable; guion de diez pasos del README; `/maquinaria`, `/solicitudes`, `/integracion` con IDs reales de la muestra | Cumple dentro de la lectura: **5 de 15 unidades y 2 solicitudes**; fuera de eso hace falta `live` habilitado |
| 3.2 | Discrepancia de estados resuelta con una regla clara (5) | En pantalla: interpretación de la unidad y asunto «Revisar la asignación» en `/maquinaria/{id}` y `/solicitudes/{id}` (`apps/api/app/dashboard/evidence_views.py`, `decision_priorities.py`); por API: `tensions` con `obsolete_with_approved_request` en `GET /api/v1/graph`; regla documentada en [estados separados](equivalencias-prisma-startrack.md#fechas-unidades-y-estados-separados) | **Parcial**: la muestra solo permite mostrar la tensión entre dos hechos de Prisma; la regla Ocupada/Completada está implementada pero no se ejercita con estos datos, y las tensiones del grafo no tienen todavía una vista propia en la interfaz |
| 3.3 | Pensado para quien lo usaría de verdad (5) | Un asunto por solicitud con evidencia y siguiente paso; roles que ocultan acciones que el usuario no puede ejecutar; «no verificable» en vez de vacíos; [arquitectura de interfaz](frontend-architecture.md) | Cumple |
| 3.4 | RACI clara y utilizable (5) | Nueve decisiones con R/A/C/I para siete roles; `output/matrices/raci-propuesta.csv`; páginas 2 a 4 del dossier PDF; roles implementados en `/administracion` | Cumple, con el rótulo de propuesta |
| 4.1 | Claridad del pitch y traducción a valor (7.5) | Este guion; [matriz de trazabilidad](matriz-requisitos-entregables.md#matriz-de-trazabilidad) | Depende de la ejecución; ensayar con reloj |
| 4.2 | Bloque de reflexión de aprendizaje (7.5) | Bloque 4:20–4:50 de este guion | Debe decirse con palabras propias del equipo |
| 5.1 | Trabajo en equipo y coordinación de roles (7.5) | Fichas de observación de los checkpoints; reparto de voces de este guion | Lo evalúan los mentores; no depende del repositorio |
| 5.2 | Urgencia, gestión del tiempo y recorte de alcance (7.5) | Recuento de la [matriz de trazabilidad](matriz-requisitos-entregables.md#matriz-de-trazabilidad): 13 cumple, 5 parcial, 1 pendiente, con la brecha y la acción de cada fila | Evidencia de alcance recortado y declarado |

Requisitos del brief, para responder si preguntan por uno: **RF-01, RF-03,
RF-06 y RNF-01 a RNF-04 cumplen**; quedan **parciales RF-02, RF-04, RF-05, el
PDF de la matriz completa y el prototipo navegable**, por dos causas comunes
—ninguna cadena de la muestra tiene evidencia de las dos plataformas y la API
de Startrack no está validada—; la **presentación de diez diapositivas** es el
único entregable pendiente en el repositorio. El recuento completo, fila por
fila y con su brecha, está en la
[matriz de trazabilidad](matriz-requisitos-entregables.md#matriz-de-trazabilidad).

---

## 5. Qué NO afirmamos

Se dice en el pitch (bloque 3:45) y se repite si una pregunta lo roza. Es la
ventaja competitiva, no una disculpa.

1. **Los datos son sintéticos.** `fixture` son ejemplos del OpenAPI entregado;
   `live` es una lectura del sandbox. Ninguno es producción y **no hay fallback
   entre ellos**: un fallo de conexión no se rellena con la muestra.
2. **La ausencia no es cero.** La muestra trae 5 de 15 unidades y ninguna tarea
   de Startrack. Eso no significa que la flota tenga 5 máquinas ni que no
   existan traslados: significa que no los hemos leído.
3. **Un payload preparado no acredita un envío.** El cuerpo para
   `POST /api/job` puede estar completo y la tarea no existir. `sent` confirma
   una tarea asociada, no su ejecución ni la entrega.
4. **Una flecha no es tráfico.** El recorrido de `/integracion` describe el
   contrato de interacción; no prueba que una petición haya ocurrido.
5. **El GPS no acredita recepción.** Entrar en una geocerca no prueba descarga,
   y el dispositivo puede ir en el transportador. La recepción existe solo como
   declaración explícita, con responsable, instante y referencia de constancia.
6. **Estados distintos no son necesariamente un conflicto.** Ocupada y
   Completada describen objetos distintos; resolver es interpretar, no igualar.
7. **Sin promedios ni porcentajes con esta cohorte.** Dos solicitudes y cinco
   unidades no sostienen un promedio, un percentil ni un cumplimiento de SLA.
   Los umbrales propuestos están marcados «a validar con ECON».
8. **Un estado administrativo no es una condición física.** `DISPONIBLE` no
   acredita disponibilidad; `OBSOLETA` no afirma avería ni paro.
9. **Las lecturas y escrituras remotas están deshabilitadas por defecto** y las
   credenciales solo viven en el servidor. No hemos creado ni modificado ningún
   registro en Prisma ni en Startrack: la exploración fue de lectura, y la
   aprobación y la asignación siguen siendo operaciones de Prisma.
10. **La suite completa de pruebas no está verde.** La última corrida completa
    registrada —565 correctas, 49 fallos y 20 omitidas en Windows— dejó fallos
    por expectativas antiguas de callbacks y de estructura visual, un caso de
    codificación y una simulación de fallo de registro. Están anotados como
    pendientes en [CLAUDE.md](../CLAUDE.md) y **no se han borrado pruebas para
    ocultarlo**. La revisión del visor de integración sí pasó Ruff y sus trece
    pruebas de integración y navegación.
11. **La correspondencia documentada no acredita identidad de registros** entre
    plataformas; la RACI es una propuesta y no una asignación firmada.

---

## 6. Riesgos de la demo y plan B

| Riesgo | Señal de que ocurrió | Acción concreta |
| --- | --- | --- |
| **Sandbox de Prisma caído o lento** | `/maquinaria?mode=live` muestra error o tarda | No es un problema: **la demo corre en `fixture`**, que lee un archivo local y no contacta proveedores. Enseñar `/fuentes` y explicar por qué la aplicación no sustituye una fuente por otra |
| **Sin red en la sede** | No carga nada externo | La aplicación es local: un solo proceso en `127.0.0.1:8050`, tipografías e iconos servidos desde el propio repositorio, sin peticiones a terceros. Continuar igual |
| **API de Startrack sin credencial** | Ya ocurrió: la cuenta respondió `403` al pedir la API key | Está previsto y dicho en el pitch: la parte de Startrack se demuestra como **cuerpo preparado y contrato**, no como envío. Mostrar el mapa de campos y el JSON de nuestra API |
| **El jurado pide una unidad o partida fuera de las cinco** (por ejemplo RE-03 / PROY-006) | El buscador no la encuentra en `fixture` | Decirlo de frente: «esta lectura trae 5 de 15; la muestra del contrato solo incluye estas». Abrir `/fuentes` y enseñar la cobertura. **Si el servidor tiene `ALLOW_LIVE_READS=true` y credenciales de Prisma**, cambiar a `?mode=live` y repetir la búsqueda por código; la misma pantalla lista lo que Prisma devuelva, con su cobertura de páginas declarada. Habilitarlo es una decisión previa del equipo, no una improvisación en escena |
| **Falla PostgreSQL o Docker** | `/health/ready` no responde; `/operaciones` vacío | Levantar la demo sin Docker: `DATABASE_URL=sqlite:///./econ.db`, `alembic upgrade head`, crear el `admin` con `app.cli.create_user` y arrancar. Alternativa mínima sin registro persistente: `DATABASE_URL='sqlite://' AUTH_REQUIRED=false ./scripts/dev.sh` (sin login y sin planes guardados) |
| **No se guardó el plan y `/integracion` no muestra cuerpo** | La etapa «Preparar tarea» aparece pendiente | Convertirlo en contenido: enseñar los cuatro datos que faltan y explicar que el hub no rellena una geocerca ni una fecha por conveniencia. Guardarlo en vivo desde «Preparar traslado» si sobra tiempo |
| **La sesión expira o el rol no permite una acción** | Botones ausentes o 403 | Es el comportamiento esperado y da puntos: explicar que las acciones dependen del rol y que el actor queda registrado en cada evento. Reingresar con el usuario `admin` |
| **El proyector recorta la pantalla** | Columnas fuera de vista | La interfaz está verificada a 1280 y 390 px; reducir el zoom del navegador al 80 % antes de empezar, no durante |
| **Se acaba el tiempo** | Pasan 4 minutos y falta `/indicadores` | Orden de sacrificio: primero `/fuentes`, luego `/indicadores`, nunca la consulta unificada ni el mapa de campos: son RF-04, RF-05 y RF-02 |

**Ensayo obligatorio antes del bloque final**: recorrer el guion completo con
reloj sobre la entrega congelada, comprobando que cada URL abre y que los IDs
citados existen. Un guion que no se ensayó sobre la versión entregada no es un
guion.

Dos avisos para ese ensayo, comprobados el 13/09/2026 sobre esta versión:

- La interfaz estaba en edición cuando se escribió este guion. Los **datos, las
  rutas y las reglas** citados están verificados contra el servicio; los
  detalles visuales pueden haber cambiado. Confirmar en el ensayo antes de
  señalar algo en pantalla.
- El guion de diez pasos del README describe en `/decisiones` un bloque «Lo que
  dicen los indicadores». Esa función existe en el código pero **no está
  enlazada a ninguna página**, así que hoy no se ve. No prometerlo en la demo;
  las lecturas de los indicadores se enseñan en `/indicadores`.
