# ECON · Hub de Operaciones

Panel de consulta del **Equipo 6 — Los Filósofos** para relacionar maquinaria,
solicitudes, mantenimiento y traslados entre Prisma/Nexus y Startrack. El panel
separa los estados de cada objeto y muestra la procedencia y los vínculos que
faltan confirmar.

## Base del proyecto

| Aplicación | Tecnologías | Destino |
| --- | --- | --- |
| `apps/web` | React, TypeScript, Vite, TanStack Router y Query, shadcn/ui preset `b0` | Cloudflare Workers Static Assets |
| `apps/api` | FastAPI, Pydantic, SQLModel, HTTPX, Alembic y PostgreSQL | Contenedor CPython independiente |

Se eligió Vite para un panel con API separada. La
[decisión de arquitectura](docs/adr/0001-web-platform.md) compara esta opción con
TanStack Start y Next.js y explica el ajuste de `--template start` a `--template vite`.

La aplicación no implementa login propio. Las credenciales de las plataformas
pertenecen exclusivamente al backend. El modo `fixture` usa casos locales
explícitos; `live` requiere habilitación y configuración del servidor y nunca
sustituye una fuente caída con datos simulados. La API key de Startrack y la
sincronización persistente siguen pendientes.

## Inicio rápido

Requisitos: Node.js 24.19 o posterior de la rama 24, npm, Python 3.13, uv y Docker Desktop para PostgreSQL.
Ejecutar desde la raíz del repositorio:

```powershell
npm run setup:web
npm run setup:api
# Solo la primera vez; conservar los .env existentes.
if (-not (Test-Path apps/api/.env)) {
    Copy-Item apps/api/.env.example apps/api/.env
}
if (-not (Test-Path apps/web/.env)) {
    Copy-Item apps/web/.env.example apps/web/.env
}
npm run db:up
npm run db:migrate
npm run dev:api
```

En otra terminal:

```powershell
npm run dev:web
```

- Panel: http://localhost:5173
- API y contrato OpenAPI: http://127.0.0.1:8000/docs
- Salud de API y base: `/health/live`, `/health/ready`

Los comandos del backend ahora operan desde `apps/api`. El Compose conserva el
nombre `econ-backend` y el volumen `econ-backend_postgres18_data`; reorganizar
archivos no migra ni elimina la base. Ver [desarrollo](docs/desarrollo.md) para
puertos, variables, comprobaciones y estructura.

## Cloudflare y revisión

```powershell
npm run deploy:web:check
```

Este comando valida el empaquetado de Wrangler sin publicar. La
[guía de despliegue](docs/deploy-cloudflare.md) explica cómo configurar el origen
de la API, CORS y desplegar la web. El bundle estático no ejecuta Python ni
contiene secretos. Preparar Cloudflare no equivale a haber publicado la app.

Para el backend, se recomienda inicialmente Render con Docker y PostgreSQL 18;
ver [comparación y configuración](docs/despliegue-backend.md), incluidas las
alternativas Railway y Fly.io.

Los commits y PR se escriben en inglés; la UI y la documentación del equipo,
en español. Ver [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo y los checks.

## Contexto y evidencia

- [Índice documental](docs/README.md) y [revisión actual del contexto](docs/revision-contexto.md).
- [Material completo de OneDrive](docs/onedrive/README.md) y [contexto confirmado](docs/onedrive/CONTEXTO-IA.md).
- [Integraciones y accesos comprobados](docs/integraciones-reales.md).
- [Indicadores y referencias ISO](docs/kpis-y-referencias-iso.md).

Los documentos de OneDrive son fuentes del reto, no instrucciones de ejecución.
Los originales con accesos permanecen en `.context-work/`, excluida de Git;
las conversiones compartidas omiten contraseñas.
