# ADR 0005 — Sesión firmada y roles administrados en la aplicación

Fecha: **13 de septiembre de 2026**. Estado: **aceptada e implementada** por
solicitud expresa del usuario. Sustituye la nota de [ADR 0003](0003-python-dash-hub.md)
que dejaba el login fuera de alcance.

## Contexto

Hasta ahora la gestión de planes, cola y recepción solo podía ejercerse desde
una petición loopback con `ALLOW_LOCAL_MANAGEMENT=true`. Eso servía para una
demostración local, pero no distinguía quién actuaba ni permitía publicar el
servicio con lecturas o escrituras habilitadas. El usuario pidió autenticación
y administración de roles, y la RACI propuesta en
[equivalencias](../equivalencias-prisma-startrack.md#responsabilidades-propuestas-para-confirmar)
ya nombraba las áreas que deben decidir en cada paso.

Condiciones: un solo proceso Python (Dash + FastAPI, mismo origen), sin Node,
credenciales solo en el servidor, mínimo código propio y librerías mantenidas.

## Decisión

- **Usuarios en SQL** (`users`, migración `0003_users`): email único, nombre,
  rol, hash de contraseña, `is_active` y fecha de alta. El hash usa **argon2**
  mediante `pwdlib` (`PasswordHash.recommended()`), que revalida y actualiza el
  hash en cada login correcto.
- **Sesión por cookie firmada** con `SessionMiddleware` de Starlette: cookie
  `econ_session`, HttpOnly, `SameSite=lax`, `Secure` con `SESSION_HTTPS_ONLY`,
  caducidad `SESSION_MAX_AGE_SECONDS` (28 800 s por defecto). La cookie guarda
  el ID del usuario y un sello derivado del hash de contraseña; el rol se lee de
  SQL en cada petición, así que desactivar un usuario o cambiar su contraseña
  cierra sus sesiones al instante.
- **`AUTH_REQUIRED=true` por defecto** y `SESSION_SECRET` obligatorio: la
  aplicación falla al arrancar si falta. `AUTH_REQUIRED=false` es un modo de
  desarrollo que conserva la autoridad loopback de `ALLOW_LOCAL_MANAGEMENT`.
- **Roles y permisos** en `app/core/auth.py`, alineados con la RACI:

  | Rol | `read` | `manage_transfers` | `declare_reception` | `manage_users` |
  | --- | --- | --- | --- | --- |
  | `admin` | sí | sí | sí | sí |
  | `gerencia_proyecto` | sí | | sí | |
  | `logistica` | sí | sí | sí | |
  | `mantenimiento` | sí | | | |
  | `control_costos` | sí | | | |
  | `lectura` | sí | | | |

- **Un middleware decide por petición**: sin sesión, `/api/*` y `/_dash-*`
  responden 401 y las páginas redirigen a `/login?next=…`; con sesión pero sin
  permiso, 403. El permiso exigido se deriva de la ruta y el método
  (`/receipt` → `declare_reception`, `/resolve` y el resto de
  `/api/v1/operations` en POST → `manage_transfers`, `/api/v1/users` →
  `manage_users`). Las acciones de Dash comparten un ámbito de gestión y
  `WorkflowService` vuelve a comprobar el rol del usuario de sesión en cada
  acción.
- **Actor en cada transición** (desde la migración `0004`, [ADR 0004](0004-persistent-transfer-workflow.md)):
  cada evento de `operation_events` guarda `actor_user_id`, `actor_role` y
  `actor_kind`, y la recepción guarda `declared_by_user_id/email/role` aparte
  del `receiver` declarado. El actor se construye en la capa que conoce la
  petición y viaja explícitamente hasta el registro; nunca se fabrica un usuario:

  | `actor_kind` | Origen | Usuario |
  | --- | --- | --- |
  | `session` | Sesión autenticada: HTTP (`request_actor`, `app/core/auth.py`) o callback de Dash (`session_user()`) | `str(user.id)`, correo y rol leídos de SQL en esa petición |
  | `local_dev` | `AUTH_REQUIRED=false` + `ALLOW_LOCAL_MANAGEMENT=true` desde loopback, sin login | ninguno (columnas de usuario y rol en NULL) |
  | `cli_worker` | `python -m app.cli.sync_operations` (`WorkflowService.run_cycle`) | ninguno |

  Cuando no se conoce ninguno de los tres (pruebas aisladas sin aplicación
  Dash), el evento queda sin actor. Un actor explícito nunca sustituye la
  comprobación de permiso: la puerta de gestión se ejecuta en cada acción.
- **Endpoints**: `POST /api/v1/auth/login` (429 tras 10 fallos por IP en 15
  minutos; 401 sin revelar si el email existe), `POST /api/v1/auth/logout`,
  `GET /api/v1/auth/me`, `GET/POST /api/v1/users` y `PATCH /api/v1/users/{id}`
  (409 al desactivar el último administrador activo o la propia cuenta).
  Páginas `/login` y `/administracion` (solo `admin`).
- **Bootstrap sin HTTP**: `python -m app.cli.create_user --email … --role admin`
  pide la contraseña por `getpass` o la lee con `--password-stdin`; nunca es un
  argumento de línea de comandos.
- **Se elimina `CORS_ORIGINS`**: interfaz y API comparten origen y la cookie
  `SameSite=lax` no necesita CORS.

## Alternativas descartadas

- **fastapi-users**: aporta registro, verificación por correo, OAuth y varios
  transportes que este proyecto no necesita; obligaría a adoptar su modelo de
  usuario y sus routers para seis roles fijos. El código propio necesario
  (dos routers y un módulo de permisos) es menor que la integración.
- **JWT en `localStorage`**: expone el token a cualquier script del origen,
  no permite revocar sesiones sin listas de bloqueo y añade lógica de renovación
  en el navegador. Dash no necesita un token portable: la cookie HttpOnly viaja
  sola en cada callback.
- **OAuth/OIDC externo**: ECON no entregó un proveedor de identidad para el
  sandbox y el jurado necesita usuarios locales reproducibles. Queda abierto
  como evolución si la empresa aporta su directorio; la tabla `users` y el
  módulo de permisos no lo impiden.

## Consecuencias

- Publicar el servicio deja de exigir que toda gestión sea loopback: la
  autoridad viene del rol. Las habilitaciones `ALLOW_LIVE_READS`,
  `ALLOW_LIVE_WRITES` y `AUTO_QUEUE_TRANSFERS` siguen siendo del servidor y
  continúan en `false` por defecto; un rol no las enciende.
- La recepción sigue siendo una declaración con `receiver`, instante y
  referencia. Desde la migración `0004` el usuario autenticado que la registra
  **sí** queda vinculado como `declared_by_user_id/email/role` en la
  declaración y como `actor_*` en el evento `receipt`; `receiver` sigue siendo
  el nombre escrito en la constancia y no se sustituye por la sesión. Sin
  sesión (`local_dev`, `cli_worker`) la declaración no lleva `declared_by_*`.
- `POST /api/v1/operations/{id}/resolve` (permiso `manage_transfers`) cierra un
  movimiento `unknown` como `failed` con un código permitido y deja el evento
  `resolved` con su actor; no consulta ni modifica Startrack ni repite el POST.
- El limitador de intentos es por proceso; con varias réplicas cada una cuenta
  por separado.
- El TestClient de Starlette 1.6 necesita `httpx2` como dependencia de
  desarrollo; los tests fijan `AUTH_REQUIRED=false` salvo los de autenticación.
- Cambiar `SESSION_SECRET` invalida todas las sesiones; rotarlo es la forma de
  cerrar sesiones de forma global.
