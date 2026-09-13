# API ECON: explorar y probar con Swagger

Revisión del **12 de septiembre de 2026**. Describe el backend implementado,
sus respuestas y un ensayo local reproducible. No acredita acceso nuevo a
Startrack ni completa las correspondencias del caso RE-03/MOT-006/PROY-006.

## Abrir el contrato

Con el servidor local en ejecución:

| Dirección | Uso |
| --- | --- |
| [Swagger UI](http://127.0.0.1:8050/docs) | Expandir una operación, pulsar **Try it out**, completar parámetros y **Execute** |
| [OpenAPI JSON](http://127.0.0.1:8050/openapi.json) | Contrato generado desde las rutas y modelos Pydantic |
| [ReDoc](http://127.0.0.1:8050/redoc) | Lectura de esquemas y operaciones |

Swagger muestra propósito, restricciones, ejemplos de cuerpo, esquemas de
respuesta y errores. El bloque **Response body** después de ejecutar contiene
la respuesta observada; **Example Value** es una ilustración del esquema.
Abrir la documentación no crea registros. Pulsar Execute en un POST sí puede
modificar el registro local; `/sync` en live también puede enviar tareas cuando
el servidor está habilitado para ello.

Dash, Swagger y HTTP usan el mismo servidor. Este OpenAPI describe la **API del
hub**, no reproduce el contrato completo de Prisma ni el de Startrack. El hub
no publica creación/aprobación de solicitudes, creación de proyectos ni webhooks
de aprobación. El flujo actual prepara movimientos desde registros existentes.

## Primer recorrido: solo lectura

Desde la raíz, con el entorno local preparado según [desarrollo](desarrollo.md):

```powershell
./scripts/dev.sh   # o .\scripts\dev.ps1 en PowerShell
```

En otra terminal:

```powershell
$econApi = 'http://127.0.0.1:8050'
Invoke-RestMethod "$econApi/health/live"
Invoke-RestMethod "$econApi/health/ready"
# Iniciar sesión una vez y reutilizar la cookie ($econSession, ver «Autenticarse en Swagger»).
$econHub = Invoke-RestMethod "$econApi/api/v1/hub?mode=fixture" -WebSession $econSession
$econHub.scope
$econHub.sources
$econHub.equipment | Select-Object asset_number, machinery_status, maintenance_is_stopped
$econHub.requests | Select-Object status, project_name, starts_on, ends_on
Invoke-RestMethod "$econApi/api/v1/hub?mode=fixture&search=CF-03" -WebSession $econSession
Invoke-RestMethod "$econApi/api/v1/operations?mode=fixture" -WebSession $econSession
```

Los endpoints de salud son públicos; el resto responde `401` sin sesión.

La muestra sin filtro contiene cinco equipos de quince informados en el archivo
y dos solicitudes de PROY-014. No contiene una operación documentada del equipo
RE-03/MOT-006/PROY-006. Buscar RE-03 no debe fabricar esa operación.

`fixture` lee ejemplos proporcionados y evidencia local de ese mismo modo,
sin consultas a proveedores. `live` lee el sandbox sintético; está deshabilitado
por defecto y nunca usa fixtures como sustituto. Ningún parámetro del navegador
habilita proveedores. Las credenciales de proveedores permanecen en la
configuración del servidor y no se introducen en Swagger.

### Autenticarse en Swagger

Todo `/api/v1/*` exige sesión (401 sin ella). La sesión es la cookie HttpOnly
`econ_session`, declarada en OpenAPI como esquema `APIKeyCookie`; Swagger no
puede escribirla desde **Authorize** porque el navegador la gestiona. La forma
práctica es iniciar sesión en la misma pestaña y dejar que el navegador la
envíe:

1. Abrir `POST /api/v1/auth/login`, Try it out, cuerpo
   `{"email": "admin@example.com", "password": "…"}` y Execute. La respuesta
   `200` devuelve el usuario y sus `permissions`; la cookie queda en el
   navegador.
2. Comprobar con `GET /api/v1/auth/me`. Desde entonces Swagger envía la cookie
   en cada Execute del mismo origen.
3. `POST /api/v1/auth/logout` responde `204` y elimina la cookie.

Desde PowerShell, conservar la cookie con una sesión web:

```powershell
$econLogin = @{ email = 'admin@example.com'; password = (Read-Host -AsSecureString 'Contraseña' | ConvertFrom-SecureString -AsPlainText) } | ConvertTo-Json
Invoke-RestMethod "$econApi/api/v1/auth/login" -Method Post -ContentType 'application/json' -Body $econLogin -SessionVariable econSession
Invoke-RestMethod "$econApi/api/v1/auth/me" -WebSession $econSession
Invoke-RestMethod "$econApi/api/v1/hub?mode=fixture" -WebSession $econSession
```

Diez fallos de login desde una IP en quince minutos devuelven `429`. Con
sesión pero sin el permiso de la operación, la respuesta es `403`. Con
`AUTH_REQUIRED=false` (solo desarrollo) no hay login y la gestión depende de
`ALLOW_LOCAL_MANAGEMENT` desde loopback. Roles y permisos:
[ADR 0005](adr/0005-session-auth-and-roles.md).

## Operaciones disponibles

| Método y ruta | Qué hace y qué revisar |
| --- | --- |
| `GET /health/live` | Responde `{"status":"ok"}` si el proceso atiende. No consulta SQL ni proveedores. |
| `GET /health/ready` | Ejecuta `SELECT 1`. Un 200 no acredita tablas migradas ni acceso a proveedores. |
| `POST /api/v1/auth/login` | Crea la cookie de sesión. `401` con credenciales inválidas o usuario inactivo, sin revelar si el email existe; `429` tras diez fallos por IP en quince minutos. |
| `POST /api/v1/auth/logout` | Elimina la cookie; `204` aunque no hubiera sesión. |
| `GET /api/v1/auth/me` | Usuario activo de la cookie y sus permisos efectivos. |
| `GET /api/v1/users` | Lista usuarios sin hashes. Exige `manage_users` (solo `admin`). |
| `POST /api/v1/users` | Crea un usuario activo con rol y contraseña de al menos 12 caracteres; `409` si el email existe. |
| `PATCH /api/v1/users/{user_id}` | Cambia nombre, rol, estado o contraseña. `409` al desactivar la propia cuenta o dejar el sistema sin `admin` activo; una contraseña nueva cierra las sesiones previas. |
| `GET /api/v1/hub` | Consulta maquinaria, solicitudes y evidencia relacionada. Revisar `sources`, `scope`, `operation_evidence` y procedencia. |
| `GET /api/v1/operations` | Lee una página de planes e historial locales, 100 movimientos por defecto. Revisar `available`, `complete`, `coverage` y `message`. |
| `GET /api/v1/operations/catalogs` | Consulta catálogos acotados de Startrack. Siempre es live; no declara selector de modo. Añadir `mode=fixture` no cambia el origen. |
| `POST /api/v1/operations/plans` | Guarda correspondencias y preparación local (`manage_transfers`). Un 201 puede ser un plan `blocked`; revisar `preparation`. |
| `POST /api/v1/operations/{movement_id}/queue` | Revalida un plan live y lo encola (`manage_transfers`). No envía el POST a Startrack en esa petición. |
| `POST /api/v1/operations/sync` | Guarda un corte (`manage_transfers`); en live puede encolar, enviar hasta diez tareas y consultar seguimiento. |
| `POST /api/v1/operations/{movement_id}/receipt` | Guarda una declaración manual para un movimiento live `sent` con `job_id` (`declare_reception`). |

### Filtros y ámbito

- `mode` admite `fixture` y `live`; en GET con selector el valor predeterminado
  es `fixture`. Los cuerpos POST que lo requieren deben proporcionarlo.
- `hub.search` admite hasta 100 caracteres, sin distinguir mayúsculas. Busca
  IDs, código, número de activo, nombre, empresa y proyecto de equipos; ID y
  proyecto de solicitudes. Conserva sus relaciones mediante `maquinaria_id`
  exacto. Se aplica después de la lectura acotada, no sobre toda la flota.
- `operations.request_source_id` admite hasta 255 caracteres y filtra por ID
  original exacto de solicitud. No usar el prefijo normalizado `nexus:request:`.
- El contrato HTTP del hub no implementa filtros por fecha o estado ni
  paginación solicitada por el cliente. Los filtros adicionales de Dash son
  de presentación. El registro de operaciones admite `page` (desde 1) y
  `page_size` (1–500; por defecto 100). `complete` y `coverage.is_complete`
  coinciden: solo son verdaderos si la primera página contiene toda la población
  del modo y filtro. La última página de una población mayor sigue siendo parcial,
  aunque `coverage.has_more=false`. `coverage` informa total, filas y páginas.

### Cómo interpretar una respuesta

| Campo | Significado |
| --- | --- |
| `sources[].status` | `fixture`, `connected`, `partial`, `disabled`, `not_configured`, `not_queried` o `error`; no confundir configuración con consulta verificada. |
| `scope.*_total` | Totales de la fuente antes de búsqueda local; `null` si se desconocen. |
| `scope.*_returned`, `summary` | Población devuelta después del filtro. Los conteos describen esa muestra, no KPIs globales. |
| `scope.complete` | Cobertura integrada; completar páginas de Prisma no acredita integrar todo Startrack. |
| `generated_at` | Momento de construcción de la respuesta; no renueva la evidencia. |
| `data_as_of` | Fin de lectura live o `null` en muestras sin corte común. |
| `provenance` | Fuente, ID original, entorno, carácter sintético, clase de evidencia y fechas conocidas. |
| `operation_evidence` | Disponibilidad y alcance del registro local utilizado para relacionar tareas y observaciones. |
| `WorkflowOverview.complete` | Todos los movimientos del modo/filtro caben en la lectura; no significa que todas las operaciones de los proveedores estén integradas. |
| `last_sync_at` | Último corte local guardado del modo; no la fecha de cada tarea ni de la última recepción. |

El hub devuelve HTTP 200 incluso cuando comunica una fuente deshabilitada o
fallida. Con live deshabilitado, `equipment` y `requests` están vacíos y los
conteos de `summary` son `null`: no significa que haya cero equipos. Del mismo
modo, `available=false` en operaciones no equivale a un registro vacío verificado.
La evidencia histórica de Startrack puede conservarse localmente sin una consulta
actual al proveedor.

## Ensayo de escritura local aislado

Este ensayo crea una base SQLite nueva en el directorio temporal y un plan
didáctico en ella. No modifica PostgreSQL, `.env` ni datos de proveedores.
Ejecutar en **una terminal nueva**, desde la raíz:

```powershell
uv sync --project apps/api --locked
$econDemoDb = Join-Path ([System.IO.Path]::GetTempPath()) ('econ-swagger-' + [guid]::NewGuid() + '.db')
$env:DATABASE_URL = 'sqlite:///' + $econDemoDb.Replace('\', '/')
$env:AUTH_REQUIRED = 'false'          # ensayo local sin usuarios; nunca en un despliegue
$env:ALLOW_LOCAL_MANAGEMENT = 'true'
$env:ALLOW_LIVE_READS = 'false'
$env:ALLOW_LIVE_WRITES = 'false'
$env:AUTO_QUEUE_TRANSFERS = 'false'
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8052
```

Con `AUTH_REQUIRED=false` la gestión se concede a la petición loopback del
propio navegador. Para ensayar con login, omitir esa variable, definir
`SESSION_SECRET`, crear un `admin` con `app.cli.create_user` y autenticarse
como se explica arriba.

Abrir `http://127.0.0.1:8052/docs`. En `POST /operations/plans`, seleccionar
**Ensayo local con la muestra proporcionada de PROY-014**, pulsar Try it out y
Execute. El cuerpo usa estos datos:

```json
{
  "mode": "fixture",
  "mapping": {
    "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
    "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
    "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
    "poi_id": "demo-poi",
    "assigned_user_ids": ["demo-user"],
    "movement_reference": "demo-swagger-fixture-001",
    "scheduled_date": "2026-09-14",
    "scheduled_time": "08:00:00"
  },
  "tracked_vehicle_id": null
}
```

Los UUID Prisma proceden de la muestra; `demo-poi` y `demo-user` son
identificadores didácticos, sin correspondencia validada. La programación es
parte del ensayo, no una entrega derivada de las fechas de uso. No corresponde
al caso asignado a nuestro equipo. Los ejemplos solo existen en documentación
hasta que se ejecuta explícitamente el POST.

Con el código actual se obtiene `201`, `mode=fixture`, `state=draft`, un UUID
local en `id`, `job_id=null` y `receipt=null`. `draft` acredita preparación
formal, no disponibilidad física de CF-03 ni validación de catálogos remotos.
Leer también las notas en `preparation` y el estado administrativo `OBSOLETA`.

Repetir el mismo cuerpo devuelve el mismo `id`; cambiar su identidad conservando
la referencia genera conflicto. Consultar `GET /operations?mode=fixture` permite
ver el movimiento persistido. `POST /operations/sync` con `{"mode":"fixture"}`
guarda un corte y actualiza `last_sync_at`. Encolar ese movimiento devuelve 409:
fixture no puede enviarse. Tampoco puede declararse recepción en este modo.

Para terminar, detener Uvicorn con Ctrl+C y cerrar esa terminal. La base temporal
permanece disponible para inspección; no se elimina automáticamente. El proceso
principal en 8050 conserva su configuración y PostgreSQL.

## Errores y efectos de negocio

| HTTP | Ejemplo o interpretación |
| --- | --- |
| `200` | Consulta o ciclo atendido; revisar cobertura, disponibilidad y advertencias en el cuerpo. |
| `201` | Plan o usuario guardado (plan: recuperado por identidad; revisar si quedó `draft` o `blocked`). |
| `401` | Sin sesión válida: iniciar sesión en `POST /api/v1/auth/login`. |
| `403` | La sesión no tiene el permiso de la operación (`manage_transfers`, `declare_reception` o `manage_users`). |
| `409` | Rechazo del flujo: gestión/live deshabilitados, dependencia no disponible, identidad/estado incompatible, registro no encontrado, evidencia inválida, email repetido o cambio que dejaría sin administrador. El contrato actual usa 409 también para estas causas. |
| `422` | Validación estructural: modo inválido, campo requerido ausente, longitud excesiva, fecha mal formada o campos adicionales en cuerpos estrictos. |
| `429` | Demasiados intentos de login desde la misma IP; esperar quince minutos. |
| `503` | `/health/ready` no pudo consultar SQL. No devuelve detalles de conexión. |

Ejemplo real de rechazo con configuración predeterminada:

```json
{"detail":"Las lecturas en vivo están deshabilitadas en este servidor."}
```

Una recepción exige `mode=live`, `sent` y un ID de tarea. `received_at` debe
incluir zona, como `2026-09-14T14:00:00-06:00`; una fecha sin zona llega al
servicio y se rechaza con 409. `receiver` y `reference` no pueden quedar vacíos.
La referencia de constancia es texto: el endpoint no sube archivos ni verifica
firmas. Repetir una declaración idéntica conserva la original; una modificación
posterior genera conflicto. Ni GPS ni cierre de tarea producen recepción.

`queue` exige lecturas/escrituras live, permiso `manage_transfers` y
credenciales de ambos proveedores. `sync` no debe tratarse como un GET: con habilitaciones puede
procesar la cola. Un envío `unknown` se concilia por lectura y correspondencia
exacta; no repetir la creación para resolver una respuesta incierta.

Las habilitaciones no se modificaron con esta revisión. La validación autenticada
de Startrack, los IDs del caso propio y el formato de arrays aceptado por esa
cuenta siguen pendientes. Revisar [contexto vigente](contexto-vigente.md),
[guía de integración](solucion-integracion.md) y
[equivalencias](equivalencias-prisma-startrack.md) antes de probar proveedores.

## Mantenimiento y verificación

El esquema se genera desde `app/main.py`, `app/api` y los modelos compartidos;
no hay una copia OpenAPI manual que mantener. La prueba `tests/test_openapi.py`
lee el ejemplo publicado en el propio esquema, guarda y consulta el plan en
SQLite aislado, verifica idempotencia, sincronización fixture y rechazo de envío,
y comprueba que no se llama a Prisma ni al creador de tareas de Startrack.

Las descripciones usan las capacidades oficiales de FastAPI para
[metadatos y etiquetas](https://fastapi.tiangolo.com/tutorial/metadata/),
[configuración de Swagger UI](https://fastapi.tiangolo.com/how-to/configure-swagger-ui/)
y [respuestas adicionales](https://fastapi.tiangolo.com/advanced/additional-responses/).
La sesión se declara con `fastapi.security.APIKeyCookie`; `tests/test_auth.py`
y `tests/test_users.py` cubren login y logout, secreto obligatorio, límite de
intentos, 401/redirección, permisos por rol, cierre de sesión al desactivar o
cambiar la contraseña, protección del último `admin`, la CLI y la migración.
