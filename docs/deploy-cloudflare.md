# Preparar el despliegue web en Cloudflare

El destino preparado es **Cloudflare Workers Static Assets** para `apps/web`. La API FastAPI se ejecuta como un servicio CPython con PostgreSQL y una URL HTTPS propia. Esta guía prepara la publicación; la implementación de esta etapa no publica recursos en Cloudflare.

La recomendación de proveedor para la API dockerizada y PostgreSQL está en [despliegue del backend](despliegue-backend.md). El backend permanece separado de Cloudflare, según confirmó el usuario.

## Qué se despliega

| Pieza | Destino | Configuración |
| --- | --- | --- |
| React, CSS, fuentes y recursos compilados | Workers Static Assets | `apps/web/wrangler.jsonc`, directorio `dist` |
| FastAPI y conectores | Servicio/contenedor de Python | `apps/api/Dockerfile`, variables de servidor y origen HTTPS |
| PostgreSQL | Servicio accesible por FastAPI | `DATABASE_URL`, migraciones, respaldo y conectividad privada |

La configuración `assets.not_found_handling = "single-page-application"` permite abrir rutas internas de la SPA. Cloudflare sirve `index.html` para navegaciones sin un recurso coincidente. Esto resuelve la navegación del frontend; no crea endpoints de FastAPI. [Enrutamiento SPA de Cloudflare](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/).

**El sitio necesita una API accesible incluso en modo demostración.** Los fixtures se sirven desde FastAPI; no están empaquetados como respaldo dentro de React. El proxy `API_PROXY_TARGET` es de desarrollo y no se despliega con los archivos estáticos.

## Preparar el backend

El Dockerfile de `apps/api` utiliza el runtime convencional. Se puede construir desde la raíz:

```powershell
docker build -t econ-api:local apps/api
```

Configurar en el proveedor del servicio `DATABASE_URL`, `CORS_ORIGINS` y las demás variables descritas en [apps/api/.env.example](../apps/api/.env.example). Usar el origen real del frontend, por ejemplo:

```dotenv
CORS_ORIGINS=["https://hub.example.com"]
ALLOW_LIVE_READS=false
```

`example.com` es un marcador para sustituir. Ejecutar las migraciones de Alembic con el entorno del despliegue y verificar `/health/live` y `/health/ready`. El puerto loopback y las credenciales del Compose local no constituyen configuración de producción. La elección y configuración de un proveedor para FastAPI/PostgreSQL sigue siendo una decisión del despliegue.

Cloudflare también admite [FastAPI en Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/). No se empaqueta este backend como Python Worker: la compatibilidad del conjunto SQLModel/psycopg y su forma de conexión no está validada en ese runtime. Es una decisión de compatibilidad, no ausencia de Python en Cloudflare. [Restricciones de paquetes](https://developers.cloudflare.com/workers/languages/python/packages/).

## Construir y verificar sin publicar

Desde la raíz, instalar el lockfile del frontend y configurar la URL del backend **antes de compilar**:

```powershell
npm run setup:web
$env:VITE_API_BASE_URL = 'https://api.example.com'
npm run deploy:web:check
```

El valor se integra al JavaScript del navegador. No lleva `/api/v1/hub` ni credenciales: es el origen/base de la API, como `https://api.example.com`. Al cambiarlo hay que compilar nuevamente. Para una construcción remota, declararlo en las variables de compilación de Cloudflare.

El comando realiza una compilación y `wrangler deploy --dry-run`. Valida la preparación del despliegue, pero no demuestra DNS, permisos de la cuenta, disponibilidad del backend, CORS del dominio final ni conectividad con proveedores.

Revisar el nombre del Worker en [wrangler.jsonc](../apps/web/wrangler.jsonc), elegir el dominio y conservar una versión identificable del código y sus archivos de dependencias bloqueadas. Los comandos se ejecutan con Wrangler instalado en el proyecto.

## Publicar cuando el usuario lo decida

Con una terminal en `apps/web`, autenticar la CLI de Cloudflare y publicar:

```powershell
npm exec -- wrangler login
npm run deploy
```

La variable `VITE_API_BASE_URL` debe seguir definida en esa terminal o en la configuración de compilación. `npm run deploy` vuelve a construir y luego publica. Con una CLI ya autenticada, también puede ejecutarse `npm run deploy:web` desde la raíz.

Para Workers Builds, usar `apps/web` como directorio del proyecto, instalar con `npm ci` y ejecutar el script `npm run deploy`, que ya incluye el build. El secreto de despliegue de Cloudflare pertenece al entorno de publicación; ninguna credencial de Nexus/Startrack debe configurarse en la compilación web.

Después de publicar, abrir la URL resultante, navegar y recargar una ruta interna; comprobar la consulta `mode=fixture`, el origen HTTPS correcto y la recuperación ante error de API. El indicador de fuentes debe seguir identificando los datos como sintéticos locales. Una página que carga HTML pero no consulta FastAPI no verifica el panel completo.

## Datos en un panel sin login

El despliegue inicial mantiene **`ALLOW_LIVE_READS=false`** y expone solo casos sintéticos del hub. No hay autenticación de usuarios de la aplicación. Habilitar lecturas privadas requiere limitar el acceso efectivo tanto al panel como a su API; proteger únicamente los archivos web deja el origen del backend expuesto. La lista CORS no es un control de acceso para clientes HTTP directos.

El despliegue no incluye webhooks, trabajos de sincronización, API key de Startrack, conciliación operativa validada ni persistencia histórica del hub. Esas capacidades se registran por separado en [revisión de contexto](revision-contexto.md). La selección de Vite, Start y Next.js se explica en [ADR 0001](adr/0001-web-platform.md).
