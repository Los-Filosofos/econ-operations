# Contexto vigente

Punto de entrada para quien continúa el trabajo. Reúne las decisiones del
usuario, los límites de los datos y las reglas de dominio que siguen vigentes.
No narra etapas anteriores: el historial Git conserva esas versiones. Los
comandos están en [desarrollo](desarrollo.md) y la operación en la
[guía operativa](solucion-integracion.md).

## Producto y flujo

ECON sigue **proyecto → solicitud → asignación de una máquina concreta → tarea
de traslado en Startrack → llegada observada → recepción**. Gerencia necesita
saber qué revisar y con qué evidencia; Logística, correspondencias y planificación;
Mantenimiento, conservar sus hechos sin confundirlos con el estado administrativo.

1. Gerencia crea el proyecto en Prisma (presentada como Nexus ECON; el usuario la
   llama START). No hay una tercera plataforma documentada.
2. El proyecto solicita un tipo de maquinaria, fechas de uso y comentarios.
3. Logística aprueba y asigna una unidad; el operador es opcional en el contrato.
4. La unidad asignada permite preparar la tarea de traslado en Startrack. El
   TO-BE crea la tarea desde una **solicitud aprobada**, no desde el proyecto.
5. Startrack aporta ejecución, visitas, telemetría y formularios.
6. El proyecto acredita la recepción con la evidencia empresarial acordada.

Aprobar con unidad cambia la solicitud a **Aprobada** y el equipo a **Ocupada**.
Ocupación administrativa, condición de mantenimiento, estado de tarea, posición
y recepción son hechos distintos: una tarea completada coexiste con una máquina
ocupada; entrar en una geocerca no prueba descarga ni recepción; el GPS puede
pertenecer al transportador o al teléfono. Fuentes: [casos](onedrive/04-casos-de-uso.md),
[TO-BE](onedrive/03-to-be.md), [manual](onedrive/05-manual-nexus.md).

## Decisiones del usuario

- Un solo proceso Python: Dash, Plotly, AG Grid Community y FastAPI, con
  SQLModel/Alembic sobre PostgreSQL. React y la salida estática fueron retirados
  y no se recrean ([ADR 0003](adr/0003-python-dash-hub.md)).
- Todo el caso usa **datos sintéticos**. `fixture` son ejemplos del archivo;
  `live` es una lectura actual del sandbox. Nunca se sustituyen entre sí.
- La portada empieza por decisiones (proyecto, revisión necesaria, evidencia y
  siguiente paso), sin cards de conteos, badges ni prioridad inventada. Sidebar
  con Resumen, Solicitudes, Maquinaria, Operaciones y Fuentes (y Administración
  para `admin`); tablas de seis columnas con detalles desplegables. Gráficos
  elegidos con criterio de analista ([analítica](analitica-decisiones.md)).
- Interfaz con dash-mantine-components, iconos Tabler locales y AG Grid
  Community. El color codifica información, no decoración: el azul ECON es
  marca y acción; los estados usan una paleta cualitativa propia; magnitudes,
  escala secuencial; desviaciones frente a meta, escala divergente
  ([arquitectura](frontend-architecture.md)).
- Credenciales solo en el servidor; lecturas y escrituras remotas deshabilitadas
  por defecto; no publicar acceso live sin protección.
- La autenticación y los roles se administran en la aplicación
  ([ADR 0005](adr/0005-session-auth-and-roles.md)): sesión por cookie firmada,
  `AUTH_REQUIRED=true` por defecto y primer `admin` creado por CLI. `admin`
  tiene todos los permisos; `logistica` gestiona traslados y declara recepción;
  `gerencia_proyecto` declara recepción; `mantenimiento`, `control_costos` y
  `lectura` solo leen. La autoridad de gestión viene del rol; las
  habilitaciones `ALLOW_LIVE_READS`, `ALLOW_LIVE_WRITES` y
  `AUTO_QUEUE_TRANSFERS` siguen siendo del servidor y ningún rol las enciende.
  `ALLOW_LOCAL_MANAGEMENT` solo cuenta en desarrollo con `AUTH_REQUIRED=false`.
- UI y textos en español; código, commits y PR en inglés.

## Identidad y muestras

- Asignación del kit: **RE-03 / MOT-006 / PROY-006**. Los ejemplos CF-03 /
  MOT-014 / PROY-014 pertenecen a otro recorrido y no se mezclan con ella.
- Runtime `fixture`: cinco equipos de un total documental de quince y dos
  solicitudes de PROY-014 (ambas cargador frontal; una APROBADA con CF-03 en
  estado administrativo `OBSOLETA`, otra PENDIENTE sin unidad; períodos 11–14 y
  16–18 de septiembre de 2026). Sin tareas, GPS ni recepciones suministradas.
  Fuente reproducible: `apps/api/app/integrations/data/sandbox_samples.json`.
- Fecha documental 12/09/2026 sin instante común de observación: no se
  clasifican atrasos con el reloj actual. `OBSOLETA` pide revisar la asignación;
  no afirma avería ni paro.
- Una captura muestra una solicitud pendiente de PROY-006 (cargador frontal,
  11–26/09/2026, sin unidad ni UUID visible); no prueba una asignación guardada.
- Conservar UUID de proyecto, solicitud, maquinaria y operador, IDs de Startrack,
  entorno, momento de lectura y fechas de origen. Nunca unir por nombres.
  Puede haber varios movimientos por solicitud; `remote_id` no tiene unicidad
  documentada. Fechas de uso no son ventana de entrega; una ciudad no es una
  coordenada; lo desconocido permanece ausente.

## Límites de los datos

| Se puede afirmar | No se puede afirmar |
| --- | --- |
| La muestra de maquinaria es parcial (5 de 15) | Que los 10 restantes existan, estén disponibles o se comporten igual |
| Cuatro equipos `DISPONIBLE` y CF-03 `OBSOLETA` son estados administrativos | Disponibilidad física, productividad o falla activa |
| Dos solicitudes con sus períodos e intervalos | Utilización, duración del traslado, promesa de entrega o desempeño |
| Ausencia de tareas, GPS y recepciones en el archivo | Cero tareas o recepciones en la operación real |

Antes de publicar una nueva medición deben quedar definidos: pregunta y
decisión que habilita; grano de la fila; IDs, plataforma, entorno y vigencia del
vínculo; población, numerador, denominador, exclusiones y desconocidos; fórmula y
política de cancelaciones/reprogramaciones; fechas de evento, observación y
registro con zona; estado evaluable/parcial/no evaluable (ausencia no es cero);
enlace a los registros de soporte. El diccionario fuente tiene tipos y ejemplos
inconsistentes y coordenadas sin escala documentada: no convertirlos en
restricciones ([observaciones](onedrive/06-diccionario-de-datos/README.md)).

## Contratos de proveedores

**Prisma** (`https://econ-key.maic.ai`): consultas de proyectos, solicitudes,
equipos, operadores e historial; `PATCH /api/maquinaria/requests/{id}/approve`
exige `maquinaria_id`. No publica POST de proyectos/solicitudes ni webhooks.
La autenticación observada usa cookie `auth-token` (el esquema dice `session`):
no corregir el comportamiento observado por una suposición del esquema.
`clave` puede ser `null` mientras `no_activo` tiene texto; se conservan separados.

**Startrack** (`https://staging.gps.gt/api`): Basic con API key y contraseña;
límite de 240 peticiones por IP cada dos minutos (`529`). Tareas `GET/POST /api/job`
(`objective` y `start_date` obligatorios; `status` es catálogo con `workflow_role`
0 pendiente, 1 completada, 2 cancelada; `closed_date` cubre completar o cancelar).
Geocercas `/api/pois` en grados, radio en metros. Los webhooks documentados
reenvían telemetría; no acreditan eventos de aprobación ni cambios de tarea.
El acceso web no prueba acceso API: la clave de esta cuenta sigue pendiente
(respondió `403`). Detalle observado en [integraciones](integraciones-reales.md)
y mapeo en [equivalencias](equivalencias-prisma-startrack.md).

## Implementado y pendiente

Implementado: lectura acotada de Prisma; SDK Startrack de lectura y creación con
habilitación independiente; planes, cortes, eventos, cola transaccional y
recepción declarada en PostgreSQL ([ADR 0004](adr/0004-persistent-transfer-workflow.md));
worker explícito por CLI con avance durable de revisión; cobertura visible del
registro (`WorkflowOverview.complete`); proyección de evidencia persistida en el
hub; inicio de sesión, roles y administración de usuarios (`/login`,
`/administracion`, `/api/v1/auth`, `/api/v1/users`).

Pendiente: validación autenticada de Startrack (clave, catálogos y codificación
de listas en creación); cotejo individual de las 51 definiciones para RF-02;
demostración RF-04/RF-05 con evidencia vinculada de ambas plataformas;
presentación final de hasta diez diapositivas; reproducción del PDF del manual;
detección de cambios Prisma posteriores al envío, orden determinista de
observaciones, cobertura por fuente y bandeja durable de eventos; vincular el
usuario autenticado a la declaración de recepción. El backlog con
criterios está en [output/auditoria-2026-09-12](../output/auditoria-2026-09-12/README.md).
Las propuestas de [sincronización y escala](sincronizacion-y-discrepancias.md)
no están implementadas.

Antes de escribir en los sandboxes: fijar solicitud/unidad, geocerca, usuario
asignable, activo rastreado, fecha programada y criterio de recepción, y comprobar
que los registros no existan ya.
