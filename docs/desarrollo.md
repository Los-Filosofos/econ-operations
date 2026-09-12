# Desarrollo local

El monorepo mantiene dos aplicaciones: **`apps/web`**, React/Vite con npm, y **`apps/api`**, FastAPI con uv. El frontend consulta al backend incluso cuando se elige demostración: los fixtures son respuestas explícitas de la API. No hay datos de reemplazo silenciosos en el navegador ni login de la aplicación.

## Preparación desde la raíz

Usar **Node.js 24.19 o posterior dentro de la rama 24**, npm 11, **Python 3.13**, uv y Docker Compose para PostgreSQL. Las dependencias exactas están en `apps/web/package-lock.json` y `apps/api/uv.lock`; no se mezclan ambos entornos.

```powershell
npm run setup:web
npm run setup:api
if (-not (Test-Path -LiteralPath apps/api/.env)) {
    Copy-Item -LiteralPath apps/api/.env.example -Destination apps/api/.env
}
npm run db:up
npm run db:migrate
```

La copia condicional conserva una configuración local existente. La migración usa el entorno de Alembic disponible; no crea modelos de sincronización que aún no se hayan implementado.

Compose conserva el nombre `econ-backend`, el volumen `econ-backend_postgres18_data` y el puerto PostgreSQL `127.0.0.1:54329`. Mover Python a `apps/api` no requiere recrear el volumen. Las credenciales del ejemplo son exclusivamente locales. Los originales de OneDrive y secretos privados de `.context-work/` no forman parte de la instalación.

## Arrancar ambas aplicaciones

En una terminal, desde la raíz:

```powershell
npm run dev:api
```

En otra terminal:

```powershell
npm run dev:web
```

| Dirección habitual | Uso |
| --- | --- |
| `http://localhost:5173` | Panel de operaciones |
| `http://127.0.0.1:8000/docs` | Swagger/OpenAPI de FastAPI |
| `http://127.0.0.1:8000/health/live` | Proceso de API disponible |
| `http://127.0.0.1:8000/health/ready` | Conexión a la base disponible |
| `http://127.0.0.1:8000/api/v1/hub?mode=fixture` | Contrato del panel con casos sintéticos locales |

Vite remite `/api/v1` a FastAPI mediante su proxy de desarrollo. `API_PROXY_TARGET` permite cambiar el destino local; el valor predeterminado es `http://127.0.0.1:8000`. El cliente utiliza `VITE_API_BASE_URL` cuando se configura un origen explícito. Esa variable llega al navegador: contiene una URL pública, nunca una contraseña, cookie o clave API.

Si el puerto 8000 ya pertenece a otro proceso, iniciar la API con un puerto libre y ajustar el proxy en `apps/web/.env.local`:

```powershell
uv run --directory apps/api --env-file .env fastapi dev --port 8001
```

```dotenv
API_PROXY_TARGET=http://127.0.0.1:8001
```

Reiniciar Vite después de cambiar sus variables. En Windows, `npm run dev:api` carga `PYTHONUTF8=1` mediante `uv --env-file` antes de arrancar Python.

## Recorrido de revisión

Abrir el panel en modo demostración y seleccionar distintas maquinarias. Comprobar solicitud y asignación, estado administrativo, mantenimiento, traslado y ubicación fechada. Los ejemplos con relación confirmada pertenecen exclusivamente a los fixtures. `RE-03` debe poder mostrar que falta un vínculo; no se presenta una relación inventada como lectura del sandbox.

Usar búsqueda, filtros y enlaces de navegación; recargar una ruta interna. Revisar tanto las fuentes como la fecha de los datos y los casos que explican cada alerta. Los conteos describen el conjunto devuelto y su filtro, no KPIs globales ni rendimiento histórico de ECON.

Cambiar a modo en vivo permite comprobar la respuesta de configuración. Con `ALLOW_LIVE_READS=false` se informa que el servidor no habilita esas lecturas. Una API detenida debe producir un estado de error recuperable, sin volver a demostración por su cuenta.

## Lecturas reales del sandbox

El backend utiliza `ALLOW_LIVE_READS=false` por defecto. Para una ejecución privada autorizada se configuran `NEXUS_EMAIL` y `NEXUS_PASSWORD` en `apps/api/.env`, se habilita la lectura y se reinicia FastAPI. La configuración de ejemplo documenta además límites de páginas y tiempos de espera. Esos datos nunca se copian a variables `VITE_*`, fixtures, capturas o logs compartidos.

La opción habilita acceso a quienes puedan consultar esa API; no es autenticación de usuarios. Mantener el servidor en loopback o en un perímetro privado efectivo. Startrack permanece sin API key y se muestra como no configurado; su sesión web no sustituye esa credencial. Ver [estado de acceso](revision-contexto.md#estado-de-acceso-con-fecha).

El conector actual consulta páginas acotadas de Nexus bajo demanda. Todavía no constituye un trabajador de sincronización, almacenamiento histórico del hub ni una exportación completa. Los estados `partial`, `error`, `disabled` y `not_configured` forman parte del contrato.

## Verificaciones antes de compartir cambios

Desde la raíz:

```powershell
npm run lint:web
npm run test:web
npm run lint:api
npm run format:api:check
npm run test:api
npm run deploy:web:check
```

`deploy:web:check` construye los activos, comprueba TypeScript y ejecuta Wrangler en modo `--dry-run`; no publica el sitio. Para revisar solamente tipos puede usarse `npm --prefix apps/web run typecheck`; para compilar sin Wrangler, `npm run build`. No es necesario repetirlos cuando ya se ejecuta la comprobación completa. Las pruebas de conectores usan transportes controlados, sin depender de credenciales de los proveedores. La configuración de base y las pruebas específicas se explican en [apps/api/README.md](../apps/api/README.md).

Los comandos de instalación y scaffolding ya se ejecutaron al crear la aplicación. Para reproducir la elección visual, la receta utilizada fue:

```powershell
npx shadcn@latest init --preset b0 --template vite --name web --cwd apps --base base --no-monorepo --yes
```

No ejecutarla sobre la aplicación existente. El preset `b0` genera el estilo `base-nova`, base neutral y sus componentes; `vite` es la plantilla elegida por la [decisión de arquitectura](adr/0001-web-platform.md). El tema se personalizó después por solicitud del usuario; consultar [arquitectura del frontend](frontend-architecture.md) antes de regenerar componentes para preservar esas decisiones.

Los commits y pull requests se redactan en inglés. Mantener cambios revisables, explicar el comportamiento y registrar validaciones y límites según [CONTRIBUTING.md](../CONTRIBUTING.md). Las decisiones funcionales del kit y la implementación actual están separadas en [revisión de contexto](revision-contexto.md).
