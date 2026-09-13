# Persistencia de operaciones en PostgreSQL

ECON usa SQLModel y Alembic sobre PostgreSQL para guardar movimientos y su
evidencia. Dash, HTTP y CLI comparten `WorkflowService` y el registro transaccional
de `app/services/ledger.py`. La decisión implementada está en
[ADR 0004](adr/0004-persistent-transfer-workflow.md); PostgreSQL es la única
infraestructura de estado (cola, bloqueos, modelo de lectura e historial) según
[ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md).

La consulta `GET /api/v1/hub` sigue siendo una proyección de lectura. Guardar un
plan o un corte es una operación explícita; abrir el panel no convierte cada
respuesta en una copia persistida de toda la flota.

## Esquema implementado

La [migración 0001_operations](../apps/api/migrations/versions/0001_operations.py)
crea las tres tablas definidas en
[los modelos de operaciones](../apps/api/app/models/operations.py):

La [migración 0002_review_schedule](../apps/api/migrations/versions/0002_movement_review_schedule.py)
agrega `next_review_at` y el índice de selección por modo, estado y revisión.
Antes de ejecutar esta versión sobre una base existente, aplicar explícitamente
`uv run --directory apps/api alembic upgrade head`. El worker conserva el avance
de revisión entre ciclos y reinicios, con presupuestos independientes de
revalidación y observación (25 por defecto). El arranque no migra la base.

La [migración 0003_users](../apps/api/migrations/versions/0003_users.py) crea
`users` para el inicio de sesión ([ADR 0005](adr/0005-session-auth-and-roles.md)).
Las columnas de fecha usan `UTCDateTime` (`models/operations.py`): se guardan y
devuelven instantes UTC con zona en PostgreSQL y SQLite.

La [migración 0004_guards](../apps/api/migrations/versions/0004_movement_guards_actors_and_indexes.py)
añade columnas y guardas sin reescribir filas. **Detener el worker antes de
migrar**; ante violaciones preexistentes falla con `IntegrityError` y no borra,
fusiona ni reasigna nada (las consultas de prechequeo están en su docstring).

| Columna o guarda | Tabla | Significado |
| --- | --- | --- |
| `tracked_vehicle_kind` | `operation_movements` | `machine_device` o `transporter`: declarado por el operador, no verificado; `CHECK ck_operation_movements_tracked_vehicle_kind` |
| `uq_operation_movements_inflight_machine` | `operation_movements` | Índice único parcial `(mode, environment, machinery_source_id) WHERE state IN ('queued','sending','unknown')`: un movimiento en vuelo por máquina |
| `uq_operation_movements_job_identity` | `operation_movements` | Índice único parcial `(mode, environment, job_id) WHERE job_id IS NOT NULL`: una tarea por movimiento |
| `actor_user_id`, `actor_role`, `actor_kind` | `operation_events` | Quién causó la transición (`session`, `local_dev`, `cli_worker`); nulos cuando no se conoce, nunca inventados |
| `operation_events_append_only` | `operation_events` | Trigger solo en PostgreSQL: rechaza `UPDATE` y `DELETE`; `TRUNCATE` sigue permitido |
| `last_confirmed_at` | `operation_snapshots` | Última lectura que confirmó el corte sin cambios (ver higiene de almacenamiento) |
| `ix_operation_snapshots_mode_recorded` | `operation_snapshots` | `(mode, recorded_at)`: sirve `last_snapshot` y la poda; sustituye a `ix_operation_snapshots_mode` |

| Tabla | Contenido y límites |
| --- | --- |
| `users` | Email único, nombre, rol, hash argon2 de la contraseña, `is_active` y fecha de alta; nunca se devuelve el hash |
| `operation_movements` | Plan, correspondencias, IDs de solicitud/maquinaria/proyecto, fuentes y huellas estables, payload, estado de envío, tarea confirmada, tipo del dispositivo GPS y recepción declarada (con `declared_by_*` cuando hubo sesión) |
| `operation_events` | Eventos de cada movimiento con ID de origen, evidencia, procedencia, actor y fechas de evento, observación y registro separadas; append-only |
| `operation_snapshots` | Cortes del hub con modo, contenido, huella estable, fecha de construcción, fecha de registro, corte de origen cuando existe y última confirmación sin cambios |

La referencia de movimiento es única dentro de `mode` y `environment`; una
solicitud puede tener varios movimientos. Los eventos referencian el movimiento
por clave foránea y restringen duplicados por movimiento y huella de evidencia.
No se asigna unicidad global a nombres, códigos visibles o `remote_id` de Startrack.

La cola de envío forma parte de `operation_movements`. Su reclamación se confirma
en una transacción antes de llamar al proveedor (`FOR UPDATE SKIP LOCKED` en
PostgreSQL; SQLite serializa escritores). Si el resultado queda incierto,
se registra `unknown` y se concilia por lectura; la recuperación no lo devuelve
automáticamente a la cola para repetir el POST. Salir de `unknown` es una
decisión explícita (`POST /api/v1/operations/{id}/resolve` o tarea verificada).
Un ciclo por modo y por base: `cycle_lock` toma un *advisory lock* de sesión en
PostgreSQL (en SQLite es un no‑op documentado).

El esquema usa columnas `JSON` para correspondencias, fuentes, payload y
evidencia. No implementa una capa analítica JSONB ni un archivo de documentos
originales. Conservar un dato en JSON no sustituye conservar su fuente e identidad.
La recepción manual permanece separada de estado de tarea y presencia GPS.

## Higiene de almacenamiento

Una lectura que no cambia nada no escribe nada duradero
([ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md)):

- **Cortes.** `content_hash` es la huella estable del corte
  (`stable_snapshot_hash`): excluye `generated_at`, `data_as_of`,
  `operation_evidence.checked_at`, `sources[].observed_at/observed_on/last_evidence_at`
  y `provenance.observed_at/observed_on` de cada registro; el JSON guardado
  conserva todas esas fechas. Si la huella coincide con el último corte del
  modo, no se inserta una fila: se actualiza `last_confirmed_at`. El corte
  guardado no cambia en nada más.
- **`last_sync_at`** (`GET /api/v1/operations`, Dash) es la última lectura del
  origen: `max(recorded_at, last_confirmed_at)` del último corte del modo. No es
  la fecha de actualización de cada tarea.
- **Relecturas de planes.** `revalidate` compara las huellas estables
  `source_request_hash` y `source_equipment_hash` (sin `provenance.observed_at`).
  Sin cambio: ni `UPDATE` ni evento; la fila conserva la fecha de lectura de su
  último cambio real. Con cambio: evento `revalidated` con
  `previous`/`current` (huellas) y copia íntegra de `request` y `equipment`.
- **Listados.** Los eventos de una página se cargan en una sola consulta
  (`movement_id IN (…)`), no una por movimiento; una página de 50 movimientos
  ejecuta dos sentencias.
- Dos procesos leyendo a la vez podrían insertar dos cortes iguales: la
  deduplicación ahorra espacio, no es un invariante; el `cycle_lock` es lo que
  mantiene un ciclo por modo.

## Integridad del historial

- `operation_events` es **append-only**: el trigger `operation_events_append_only`
  (migración 0004, solo PostgreSQL) rechaza `UPDATE` y `DELETE` con
  `integrity_constraint_violation`. Protege frente al rol de aplicación y a
  errores de código; el propietario del esquema puede retirarlo y `TRUNCATE`
  sigue permitido. SQLite no acredita esta protección; las pruebas de
  `tests/test_postgres_guarantees.py` sí.
- Los hashes SHA‑256 (`content_hash`, `source_request_hash`,
  `source_equipment_hash`, `identity_hash`, `evidence_hash`) son **controles de
  integridad y deduplicación, no firmas**: quien puede escribir la fila puede
  recalcularlos. No acreditan autoría ni orden temporal. No hay HMAC, claves,
  sellado externo ni cadena de bloques.
- La autoría se guarda como dato (`actor_*`, `declared_by_*`) a partir de la
  sesión firmada; cuando no hay sesión queda nulo, nunca se inventa.
- La poda (`prune_snapshots`) borra solo `operation_snapshots`; los eventos y
  movimientos no se podan desde la aplicación.

## Retención y volumen (extrapolación desde el fixture)

Cifras medidas el 13/09/2026 sobre el fixture sintético
(`read_hub(..., "fixture")`, 5 equipos y 2 solicitudes, JSON UTF‑8 sin
compresión ni sobrecarga de PostgreSQL). **Cualquier proyección por ciclo es una
extrapolación desde el fixture, no una medición de producción**; el tamaño
físico (TOAST, índices, WAL, réplicas) se mide en el despliegue.

| Elemento | Bytes medidos | Observación |
| --- | ---: | --- |
| Corte del hub (`operation_snapshots.content`) | ≈ 10.300 | ≈ 1.243 por equipo y ≈ 1.153 por solicitud; el resto es cabecera, fuentes, alcance y alertas |
| Movimiento (`operation_movements`, columnas JSON) | ≈ 6.600 | `source_request` ≈ 1.255, `source_equipment` ≈ 1.385, `preparation` ≈ 2.250, `payload` ≈ 420, `mapping` ≈ 360 |
| Evento `created` o `revalidated` (con cambio) | ≈ 2.950 | `data` ≈ 2.668: copia de solicitud y unidad tal como se vieron |
| Evento `task_state` o `arrival` | no medido | Solo campos tipados de `ObservationData`; nunca cuerpos de error del proveedor |

Fórmula por ciclo, con `E` equipos y `S` solicitudes leídos:

- Corte: `≈ 1.000 + 1.243·E + 1.153·S` bytes **solo si el contenido estable
  cambió**; una relectura idéntica escribe cero bytes nuevos (mueve
  `last_confirmed_at`).
- Revalidación de planes: cero bytes sin cambio; con cambio, un evento de
  ≈ 3 kB más la actualización de la fila.
- Ejemplo extrapolado: 50 equipos y 50 solicitudes por lectura ⇒ un corte
  cambiado ≈ 121 kB. Con un ciclo cada 120 s (720 al día) y **sin**
  deduplicación serían ≈ 87 MB/día de JSON bruto; con deduplicación solo
  cuentan los cortes que cambian. La cifra real se mide, no se deduce.

Qué es redundante con Prisma y qué es propio de ECON:

- **Redundante (recuperable de Prisma):** las copias de solicitud y unidad en
  `source_request`/`source_equipment`, en los eventos `created`/`revalidated`
  y en los cortes. Se conservan como evidencia de lo que se vio al decidir
  (ADR 0004): la relectura puede devolver otra cosa.
- **Propio de ECON (no recuperable de ningún proveedor):** correspondencias,
  payload y preparación, estados de la cola y sus fechas, tarea vinculada,
  observaciones con fecha de evento/lectura/registro separadas, recepción
  declarada y actor de cada transición. Nunca se poda.

Poda explícita de cortes (autoridad de proceso, como `sync_operations`; sin
sesión de usuario, sin llamadas a proveedores):

```powershell
uv run --directory apps/api python -m app.cli.prune_snapshots --mode live --keep-days 30 --dry-run
uv run --directory apps/api python -m app.cli.prune_snapshots --mode live --keep-days 30 --keep-latest 1
```

`--keep-days N` (≥ 1) conserva los cortes leídos o confirmados en los últimos
`N` días; `--keep-latest N` (≥ 1, 1 por defecto) conserva siempre los `N` más
recientes del modo aunque sean antiguos, de modo que `last_sync_at` y el modelo
de lectura sobreviven a cualquier retención; `--dry-run` imprime el conteo sin
borrar. La aplicación nunca poda por sí sola y el comando nunca toca
`operation_events` ni `operation_movements`.

## Entorno local y migraciones

[compose.yaml](../compose.yaml) mantiene:

- Proyecto `econ-backend` y servicio `db`, con imagen `postgres:18`.
- Base y usuario `econ`; acceso local en `127.0.0.1:54329`.
- Volumen `econ-backend_postgres18_data`, montado en `/var/lib/postgresql`.
- Comprobación de salud con `pg_isready` y reinicio `unless-stopped`.

Conservar el nombre del proyecto, el volumen y la configuración existente.
`DATABASE_URL` se carga desde `apps/api/.env`; no se reemplaza un archivo
existente ni se cambia de base ante un fallo. Las credenciales de proveedores
permanecen en el servidor y no forman parte de los payloads persistidos.

Desde la raíz, después de preparar el entorno según [desarrollo](desarrollo.md):

```powershell
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api alembic current
```

Las migraciones se ejecutan explícitamente. Arrancar el servidor no crea ni
elimina tablas; no se requiere recrear el volumen para aplicar el esquema.
`/health/ready` comprueba conexión con la base, no conectividad de los proveedores.
Las pruebas usan SQLite aislado; el desarrollo normal conserva PostgreSQL. Las
garantías que solo PostgreSQL acredita (índices parciales, `SKIP LOCKED`,
*advisory lock*, trigger append-only, deduplicación sobre columnas JSON) se
prueban con `ECON_TEST_POSTGRES_URL` (`tests/test_postgres_*.py`); las pruebas
de upgrade/downgrade usan la base aparte `ECON_TEST_POSTGRES_MIGRATIONS_URL`.

`fixture` y `live` mantienen registros separados y ambos corresponden a datos
sintéticos del caso. Las muestras suministradas no se insertan en Prisma.
Guardar planes requiere una sesión con permiso `manage_transfers`; lecturas
y escrituras remotas están deshabilitadas por defecto. Los controles y el worker
se explican en [la guía operativa](solucion-integracion.md).

## Escala y operación pendientes

Esta persistencia no acredita un historial completo de las fuentes ni capacidad
para miles de vehículos. La [propuesta de escala](sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta)
plantea separar operación e histórico, medir carga y evaluar procesamiento
paralelo; esas ampliaciones no están implementadas. Los criterios para
reconsiderar PostgreSQL como única infraestructura de estado (más de un worker
por IP, telemetría continua, contención medida) están en
[ADR 0006](adr/0006-postgresql-unica-infraestructura-de-estado.md); Redis no
forma parte de ninguno de ellos.

Antes de dimensionar un despliegue, medir volumen y ritmo de eventos, retención,
concurrencia, latencia, conexiones y consultas. Respaldos, restauración,
recuperación y disponibilidad deben verificarse para el entorno elegido.
El Compose local no configura por sí solo esas capacidades.
