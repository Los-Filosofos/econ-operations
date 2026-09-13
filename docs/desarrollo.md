# Desarrollo del hub Python

Dash, Plotly, Dash AG Grid y FastAPI se ejecutan juntos en `apps/api`.
Se usa Python 3.13 y uv; `apps/api/uv.lock` fija las dependencias.

## Preparar y ejecutar

```sh
uv sync --project apps/api --locked
[ -f apps/api/.env ] || cp apps/api/.env.example apps/api/.env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # pegar como SESSION_SECRET en apps/api/.env
docker compose up -d --wait db
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m app.cli.create_user --email admin@example.com --role admin --name "Administración"
./scripts/dev.sh
```

En PowerShell, `Copy-Item apps/api/.env.example apps/api/.env` si falta el
`.env` y `.\scripts\dev.ps1` para arrancar. `SESSION_SECRET` es obligatorio:
sin él la aplicación no arranca. `create_user` pide la contraseña (mínimo 12
caracteres) o la lee con `--password-stdin`. Iniciar sesión en `/login`; los
demás usuarios se crean en `/administracion`
([ADR 0005](adr/0005-session-auth-and-roles.md)).

La copia conserva los `.env` existentes. Compose conserva `econ-backend`, el
volumen `econ-backend_postgres18_data` y PostgreSQL en `127.0.0.1:54329`.
Las migraciones se ejecutan explícitamente, no al arrancar.

En `DATABASE_URL`, usar `127.0.0.1` para ese PostgreSQL local, como indica
`.env.example`. En Windows, `localhost` puede intentar primero IPv6 (`::1`),
pero Compose escucha solo en IPv4: cada conexión nueva puede esperar el timeout
antes de conectarse. Si un `.env` existente usa `localhost:54329`, sustituir
solo ese host, conservando credenciales, base, puerto y demás opciones. No
aplicar este ajuste a bases remotas ni cambiar el volumen de Compose.

Usar `scripts/dev.sh 8051` o `scripts/dev.ps1 -Port 8051` para otro puerto.
Sin scripts:

```sh
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

| Dirección | Uso |
| --- | --- |
| `http://127.0.0.1:8050` | Panel Dash (redirige a `/login` sin sesión) |
| `/administracion` | Usuarios y roles (solo `admin`) |
| `/docs` | API y contrato OpenAPI |
| `/api/v1/hub?mode=fixture` | Proyección operativa común |
| `/operaciones?mode=fixture` | Planes guardados e historial |
| `/api/v1/operations?mode=fixture` | Registro persistido por origen |
| `/health/live` | Proceso disponible |
| `/health/ready` | Conexión con la base |

Para una demo temporal sin Docker, en una terminal separada:

```sh
DATABASE_URL='sqlite://' ALLOW_LIVE_READS='false' AUTH_REQUIRED='false' ./scripts/dev.sh
```

En PowerShell: `$env:DATABASE_URL = 'sqlite://'; $env:ALLOW_LIVE_READS = 'false'; $env:AUTH_REQUIRED = 'false'; .\scripts\dev.ps1`.

Esto no modifica el `.env` ni PostgreSQL. `AUTH_REQUIRED=false` quita el login
**solo para desarrollo**: no hay tabla de usuarios en SQLite en memoria. Las
muestras no requieren almacenamiento; SQLite en memoria permite el control de
salud. Para probar el registro persistente y el login sin Docker, usar
`DATABASE_URL=sqlite:///./econ.db`, ejecutar `alembic upgrade head` y crear el
`admin` con `create_user` antes de iniciar. La aplicación no crea tablas
automáticamente.

Con login, guardar planes exige un usuario `admin` o `logistica`. Sin login
(`AUTH_REQUIRED=false`), definir `ALLOW_LOCAL_MANAGEMENT=true` para gestionar
desde localhost. Todo el caso es sintético: `fixture` conserva los ejemplos del
archivo y `live` consulta el sandbox. Los flags y la ejecución del worker se
explican en la [guía de integración](solucion-integracion.md).

## Estructura

| Ruta en `app/` | Responsabilidad |
| --- | --- |
| `services/hub.py` | Consulta, normalización, relaciones, alertas y cobertura |
| `api/hub.py` | Adaptador HTTP de la consulta |
| `core/auth.py`, `api/auth.py`, `api/users.py`, `cli/create_user.py` | Roles, permisos, sesión, login y administración de usuarios |
| `dashboard/application.py` | AppShell Mantine, callbacks y lectura compartida |
| `dashboard/theme.py`, `dashboard/components.py` | Paleta semántica, tema y bloques reutilizables |
| `dashboard/views.py` | `PAGES`, vistas, tablas, ficha y evidencia |
| `dashboard/analytics.py` | Proyección de cada solicitud y utilidades analíticas |
| `dashboard/context.py` | Validación de modo, búsqueda, filtros y enlaces |
| `dashboard/assets` | CSS mínimo, logos y tipografía locales |
| `integrations`, `models` | Conectores con `BoundedClient`, fixtures y contrato Pydantic |

## Recorrido de revisión

0. Iniciar sesión con el `admin` creado; abrir Administración y dar de alta un
   usuario `lectura` para comprobar que no ve acciones de gestión.
1. Abrir Solicitudes con «Muestras proporcionadas»: dos solicitudes de PROY-014,
   cinco máquinas de un total documental de quince y cobertura parcial.
2. Abrir la solicitud aprobada: la relación por UUID lleva a CF-03, cuyo estado
   de origen es `OBSOLETA`; traslado, llegada y recepción siguen sin evidencia.
3. Abrir la pendiente: tipo y período están disponibles, pero no tiene unidad.
4. Buscar CF-03, aplicar, navegar, volver y recargar: origen y búsqueda siguen
   en la URL. Buscar RE-03 no fabrica una operación ausente de las muestras.
5. Revisar Fuentes y cobertura y expandir procedencia de la solicitud. La fecha
   documental no se muestra como una lectura actual ni como corte conjunto.
6. Cambiar a Sandbox en vivo y aplicar: si está deshabilitado, los conteos son
   desconocidos y no reaparecen fixtures. Actualizar permite reintentar.
7. Revisar móvil y teclado. Las tablas anchas tienen desplazamiento horizontal
   y paginación; no se ocultan columnas de negocio.

Navegar (también desde enlaces de las tablas) o filtrar la presentación reutiliza
el corte del navegador. Cambiar origen/búsqueda, completar una acción o usar
«Volver a leer ahora» consulta otra vez. El sondeo cada 15 segundos lee solo
la versión del registro; recarga datos únicamente si cambió. No hay DataFrames
globales modificables. El navegador no autoriza los conectores.

## Verificaciones

```sh
./scripts/check.sh --container   # PowerShell: .\scripts\check.ps1 -Container
```

Comandos equivalentes:

```sh
uv run --directory apps/api ruff check .
uv run --directory apps/api ruff format --check .
uv run --directory apps/api pytest
docker build -t econ-hub:check apps/api
```

Sin `.env`, exportar `DATABASE_URL=sqlite://` antes de pytest. Las pruebas
aíslan bases y proveedores, fijan `AUTH_REQUIRED=false` salvo las de
autenticación, tratan `DeprecationWarning` como error y comprueban rutas,
callbacks HTTP, assets, sesión, roles y API.
La imagen contiene los assets; construirla no hace un despliegue remoto.

`ALLOW_LIVE_READS=false` sigue siendo el valor predeterminado. Credenciales
solo en el servidor, nunca en `dcc.Store`, URLs o assets. La API key de
Startrack sigue pendiente; ver [integraciones](integraciones-reales.md).
