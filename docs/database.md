# Persistencia de operaciones en PostgreSQL

ECON usa SQLModel y Alembic sobre PostgreSQL para guardar movimientos y su
evidencia. Dash, HTTP y CLI comparten `WorkflowService` y el registro transaccional
de `app/services/ledger.py`. La decisión implementada está en
[ADR 0004](adr/0004-persistent-transfer-workflow.md).

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

| Tabla | Contenido y límites |
| --- | --- |
| `users` | Email único, nombre, rol, hash argon2 de la contraseña, `is_active` y fecha de alta; nunca se devuelve el hash |
| `operation_movements` | Plan, correspondencias, IDs de solicitud/maquinaria/proyecto, fuentes y huellas, payload, estado de envío, tarea confirmada y recepción declarada |
| `operation_events` | Eventos de cada movimiento con ID de origen, evidencia, procedencia y fechas de evento, observación y registro separadas |
| `operation_snapshots` | Cortes del hub con modo, contenido, huella, fecha de construcción, fecha de registro y corte de origen cuando existe |

La referencia de movimiento es única dentro de `mode` y `environment`; una
solicitud puede tener varios movimientos. Los eventos referencian el movimiento
por clave foránea y restringen duplicados por movimiento y huella de evidencia.
No se asigna unicidad global a nombres, códigos visibles o `remote_id` de Startrack.

La cola de envío forma parte de `operation_movements`. Su reclamación se confirma
en una transacción antes de llamar al proveedor. Si el resultado queda incierto,
se registra `unknown` y se concilia por lectura; la recuperación no lo devuelve
automáticamente a la cola para repetir el POST.

El esquema usa columnas `JSON` para correspondencias, fuentes, payload y
evidencia. No implementa una capa analítica JSONB ni un archivo de documentos
originales. Conservar un dato en JSON no sustituye conservar su fuente e identidad.
La recepción manual permanece separada de estado de tarea y presencia GPS.

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
Las pruebas usan SQLite aislado; el desarrollo normal conserva PostgreSQL.

`fixture` y `live` mantienen registros separados y ambos corresponden a datos
sintéticos del caso. Las muestras suministradas no se insertan en Prisma.
Guardar planes requiere una sesión con permiso `manage_transfers`; lecturas
y escrituras remotas están deshabilitadas por defecto. Los controles y el worker
se explican en [la guía operativa](solucion-integracion.md).

## Escala y operación pendientes

Esta persistencia no acredita un historial completo de las fuentes ni capacidad
para miles de vehículos. La [propuesta de escala](sincronizacion-y-discrepancias.md#escala-a-miles-de-vehículos-propuesta)
plantea separar operación e histórico, medir carga y evaluar procesamiento
paralelo; esas ampliaciones no están implementadas.

Antes de dimensionar un despliegue, medir volumen y ritmo de eventos, retención,
concurrencia, latencia, conexiones y consultas. Respaldos, restauración,
recuperación y disponibilidad deben verificarse para el entorno elegido.
El Compose local no configura por sí solo esas capacidades.
