# ADR 0006 — PostgreSQL como única infraestructura de estado

Fecha: **13 de septiembre de 2026**. Estado: **aceptada e implementada**.
Complementa [ADR 0004](0004-persistent-transfer-workflow.md) (cola y conciliación
en una transacción) y la migración `0004_guards` (índices parciales, actor,
trigger append-only).

## Contexto

Un solo proceso Python sirve Dash y FastAPI; un worker explícito
(`app.cli.sync_operations`) ejecuta ciclos acotados contra Prisma y Startrack.
El límite publicado de Startrack (240 peticiones por IP cada dos minutos) obliga
a **un solo worker por IP**, de modo que la capacidad de la cola nunca es el
cuello de botella: lo es el presupuesto del proveedor.

La auditoría de escalabilidad planteó si convenía añadir Redis (cola, bloqueos,
caché) o una segunda infraestructura de estado. También detectó escrituras sin
cambio: cada ciclo insertaba un corte del hub aunque el origen no hubiera
cambiado, cada relectura de un plan emitía un evento `revalidated` con una copia
íntegra del origen, y el listado cargaba los eventos con una consulta por
movimiento (N+1).

## Decisión

**PostgreSQL es la única infraestructura de estado**: cola *outbox*, bloqueos,
modelo de lectura e historial viven en las tablas de `app/models/operations.py`
y se manipulan solo desde `app/services/ledger.py`. Evidencia en el código:

| Garantía | Dónde |
| --- | --- |
| Reclamación confirmada antes del POST | `ledger.py` `claim()` (líneas 728-760): `UPDATE … RETURNING` sobre una subconsulta `FOR UPDATE SKIP LOCKED`; la transacción se confirma antes de que el ciclo llame a Startrack. Un fallo posterior deja `sending`, que la recuperación convierte en `unknown`, nunca en un segundo POST |
| Bloqueo por fila | `_row(..., for_update=True)` (línea 380) en `record_observation` (línea 1012); `_finish` y `resolve_unknown` con `UPDATE … RETURNING` guardado por estado |
| Idempotencia | `create()` (líneas 562-611): identidad `(mode, environment, movement_reference)` + `identity_hash`, `IntegrityError` → relectura; `record_observation` con `evidence_hash` único por movimiento; `record_receipt` devuelve la declaración idéntica en vez de 409 |
| Invariantes en la base, no en Python | Migración `0004_guards`: `uq_operation_movements_inflight_machine` (un movimiento en vuelo por máquina) y `uq_operation_movements_job_identity` (una tarea por movimiento y entorno); el pre‑chequeo en Python solo mejora el mensaje |
| Exclusión entre procesos | `app/core/database.py` `cycle_lock()` (línea 42): `pg_try_advisory_lock(hashtext(clave))` sin espera, liberado con la sesión; usado por `workflow.sync` (líneas 664-681) junto con el `Lock` de proceso |
| Modelo de lectura | `operation_snapshots` (`record_snapshot`, `last_snapshot`) con `ix_operation_snapshots_mode_recorded` (0004) |
| Historial | `operation_events`, append-only por trigger en PostgreSQL |

**Higiene de almacenamiento** (esta decisión, `ledger.py`):

- `stable_snapshot_hash` (línea 173) calcula la huella del corte excluyendo
  `generated_at`, `data_as_of`, `operation_evidence.checked_at`,
  `sources[].observed_at/observed_on/last_evidence_at` y `provenance.observed_at/observed_on`
  de cada registro. `content_hash` pasa a ser esa huella estable. Si coincide
  con el último corte del modo, `record_snapshot` no inserta: actualiza
  `operation_snapshots.last_confirmed_at`. `WorkflowOverview.last_sync_at`
  refleja la última **lectura**: `max(recorded_at, last_confirmed_at)`
  (`last_read_at`, línea 199).
- `revalidate` (línea 613) no ejecuta `UPDATE` ni emite evento cuando
  `source_request_hash` y `source_equipment_hash` (huella estable de WP‑1) no
  cambian. Cuando cambian, el evento `revalidated` guarda
  `{previous: {request_hash, equipment_hash}, current: {…}, request, equipment}`.
  El avance de `next_review_at` sigue en `workflow._review`.
- `_events` (línea 406) carga los eventos de un listado en **una** consulta
  (`movement_id IN (…) ORDER BY movement_id, recorded_at, id`) agrupada en
  Python; `_record` conserva su firma para los caminos de una fila.
- `prune_snapshots` (línea 1167) borra solo cortes del modo cuya última lectura
  (`coalesce(last_confirmed_at, recorded_at)`) sea anterior a `keep_days`,
  conservando siempre los `keep_latest` más recientes. Solo se invoca desde
  `python -m app.cli.prune_snapshots`; **nunca** toca `operation_events` ni
  `operation_movements` y la aplicación no poda por sí sola.

## Por qué no Redis

- **Doble escritura sin transacción común.** La reclamación (`state=sending`) y
  la entrada de cola vivirían en dos sistemas. Un fallo entre ambas escrituras es
  una forma nueva de perder o duplicar un POST, justo lo que ADR 0004 elimina
  confirmando la reclamación en una sola transacción SQL.
- **Bloqueos con caducidad.** Un `SET NX` con TTL expira con independencia de la
  transacción; dos workers pueden creerse dueños del ciclo. El *advisory lock*
  muere con la sesión de PostgreSQL y no necesita reloj compartido.
- **Caché innecesaria.** El modelo de lectura ya es una tabla indexada y las
  lecturas están acotadas (100 movimientos por defecto, 500 máximo) en dos
  sentencias. Un ciclo cada 120 s con un worker por IP no produce la presión de
  lectura que justificaría una capa intermedia.
- **Coste operativo.** Otro servicio que desplegar, asegurar, respaldar y
  observar, con credenciales propias; contradice el criterio de mínima
  infraestructura de [ADR 0003](0003-python-dash-hub.md) y de
  [decisiones técnicas](../decisiones-tecnicas.md).

## Criterios de revisión

Reconsiderar esta decisión solo con medición, no por anticipación:

1. **Más de un worker por IP** con un presupuesto del proveedor que no pueda
   resolverse en SQL (por ejemplo, un cupo compartido por tabla con bloqueo de
   fila). Primero agotar la opción SQL; después evaluar alternativas.
2. **Ingesta de telemetría continua** (miles de vehículos, eventos por segundo).
   Ese escenario está descrito en
   [escala a miles de vehículos](../sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta)
   y se resuelve con Kafka y ClickHouse, no con Redis.
3. **Contención observada** en `pg_locks`/`pg_stat_activity` o latencias de
   `claim`/listado medidas bajo carga sintética, con cifras, antes de cambiar la
   arquitectura.

## Integridad sin firmas

- Los hashes SHA‑256 del registro (`content_hash`, `source_request_hash`,
  `source_equipment_hash`, `identity_hash`, `evidence_hash`) detectan **cambio
  accidental y duplicados**: quien puede escribir la fila puede recalcularlos.
  No son firmas ni acreditan autoría. No hay HMAC, claves, sellado externo ni
  cadena de bloques, y no se prevén.
- El trigger `operation_events_append_only` (migración 0004, solo PostgreSQL)
  rechaza `UPDATE` y `DELETE` sobre `operation_events` con
  `integrity_constraint_violation`. Protege frente al **rol de aplicación** y a
  errores de código; un propietario del esquema puede retirarlo. `TRUNCATE`
  sigue permitido (lo usan las pruebas aisladas). SQLite no acredita esta
  protección.
- La autoría de cada transición se registra como dato (`actor_user_id`,
  `actor_role`, `actor_kind`; `declared_by_*` en la recepción), nunca se
  fabrica, y su verificación es la sesión firmada de [ADR 0005](0005-session-auth-and-roles.md).

## Consecuencias

- Una relectura sin cambios no hace crecer la base: cero cortes y cero eventos
  nuevos; solo se mueve `last_confirmed_at`. Las filas anteriores a esta versión
  conservan su `content_hash` completo y provocan como máximo un corte nuevo
  antes de deduplicar.
- La fila del movimiento conserva la fecha de lectura de su **último cambio
  real**; la última lectura del origen se consulta en el corte
  (`last_sync_at`).
- La retención es una decisión explícita del operador (CLI). Las cifras de
  volumen de [database.md](../database.md#retención-y-volumen-extrapolación-desde-el-fixture)
  son **extrapolaciones desde el fixture sintético**, no mediciones de un
  despliegue.
- Pruebas: `tests/test_storage_hygiene.py` (SQLite: deduplicación, evento solo
  ante cambio, listado acotado en sentencias, poda y CLI) y
  `tests/test_postgres_storage.py` (PostgreSQL: columnas JSON/`timestamptz`,
  poda, sin escrituras en relectura, dos sesiones reclaman filas distintas con
  `SKIP LOCKED`). SQLite no acredita comportamiento concurrente de PostgreSQL.
