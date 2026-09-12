# ECON · Backend de integración

Base de FastAPI para explorar la integración de dos sistemas. El reto todavía no
está definido: no hay tablas de negocio, conectores reales ni sincronización.

## Arrancar por CLI

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/) y Docker Desktop activo.
Desde esta carpeta:

```powershell
uv sync --locked
Copy-Item .env.example .env  # Solo la primera vez; conserva tu .env si ya existe.
docker compose up -d --wait db
uv run alembic upgrade head
uv run --env-file .env fastapi dev
```

- Swagger: http://127.0.0.1:8000/docs
- API activa: http://127.0.0.1:8000/health/live
- Conexión a la base: http://127.0.0.1:8000/health/ready

El arranque local usa PostgreSQL 18 en Docker. `uv.lock` fija las versiones resueltas;
`.venv`, `.env` y las bases locales quedan fuera de Git. No hay revisiones de
negocio todavía: `alembic upgrade head` verifica la conexión e inicializa el
control de versiones, sin crear tablas del dominio.

`--env-file .env` también activa UTF-8 antes de iniciar Python, para que los
mensajes de FastAPI CLI funcionen en PowerShell de Windows.

## Stack

| Herramienta | Para qué sirve |
| --- | --- |
| FastAPI | API HTTP, validación y documentación OpenAPI |
| SQLModel | ORM basado en SQLAlchemy y Pydantic |
| Alembic | Migraciones versionadas del esquema |
| PostgreSQL 18 + Psycopg | Base central de desarrollo, ejecutada en Docker |
| Pydantic Settings | Configuración desde variables de entorno y `.env` |
| HTTPX | Cliente HTTP disponible para futuros conectores |
| uv, Ruff, pytest | Dependencias reproducibles, formato y comprobaciones |

SQLModel permite representar tablas con clases de Python. Para consultas avanzadas
se puede utilizar SQLAlchemy directamente. Los esquemas de entrada/salida deben
separarse de las tablas cuando tengan campos o permisos diferentes.

## Base de datos local

```powershell
docker compose up -d --wait db
```

La conexión ya está configurada en `.env.example` y en el `.env` local:

```dotenv
DATABASE_URL=postgresql+psycopg://econ:econ_local_only@localhost:54329/econ
```

El contenedor usa el puerto local 54329 para reducir conflictos con otras instalaciones. Sus
credenciales son exclusivamente de desarrollo. `docker compose stop db` lo
detiene conservando el volumen `econ-backend_postgres18_data`. En PostgreSQL 18,
el volumen se monta en `/var/lib/postgresql` según la imagen oficial.

Docker ejecuta la base; PostgreSQL almacena y consulta los datos. La API se ejecuta
en Windows y se conecta al puerto publicado. Dentro de otro contenedor de este
Compose, el servidor sería `db:5432`, no `localhost:54329`.

Para abrir la consola SQL:

```powershell
docker compose exec db psql -U econ -d econ
```

Si necesitas ejecutar sin Docker, configura `DATABASE_URL=sqlite:///./econ.db`
en `.env`, aplica Alembic y reinicia la API. Cambiar la URL no transfiere datos
entre bases. Las pruebas automatizadas usan SQLite temporal e independiente.

El volumen de la prueba anterior con PostgreSQL 17 se conserva sin modificar;
el volumen nuevo de PostgreSQL 18 es independiente. No se ha realizado una
migración de datos entre versiones. No uses `docker compose down -v` si quieres
conservar los datos: un volumen persistente tampoco reemplaza un respaldo.

La [decisión de base de datos](docs/database.md) explica los criterios y pendientes.

## Estructura

```text
app/
  main.py             Aplicación, ciclo de vida y CORS
  api/health.py       Comprobaciones de API y conexión
  core/config.py      Variables de entorno
  core/database.py    Motor y sesión por petición
  models/__init__.py  Registro de futuros modelos para Alembic
  integrations/      Espacio para adaptadores cuando se conozcan las APIs
migrations/           Entorno de Alembic y futuras revisiones
tests/                Arranque y fallo de conexión
docs/architecture.md  Evaluación técnica y decisiones pendientes
```

## Cuando se conozcan los datos

1. Crear modelos `SQLModel` con `table=True` en `app/models/` e importarlos en
   `app/models/__init__.py` para que Alembic los descubra.
2. Generar una revisión: `uv run alembic revision --autogenerate -m "initial domain"`.
3. Revisar el archivo generado y aplicar: `uv run alembic upgrade head`.
4. Añadir esquemas de entrada/salida y rutas, usando `SessionDep` para acceder a
   la base. Las escrituras deben confirmar explícitamente con `session.commit()`.

Las tablas no se crean automáticamente al arrancar. Las operaciones actuales de
base de datos son síncronas y las rutas usan `def`, que FastAPI ejecuta en su pool
de hilos. Para conectores HTTP asíncronos, usar `async def` y HTTPX `AsyncClient`
con tiempos de espera. No compartir sesiones entre tareas concurrentes.

## Comprobaciones

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
```

Esta base está destinada al desarrollo local. Autenticación, roles, trabajos de
sincronización y reglas de conciliación se definirán con los requisitos; aún no
están implementados. CORS no sustituye la autenticación.

La evaluación y las fuentes oficiales están en [docs/architecture.md](docs/architecture.md).
