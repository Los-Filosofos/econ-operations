# Dónde desplegar FastAPI y PostgreSQL

Recomendación consultada el **12 de septiembre de 2026**. El usuario confirmó
que el backend permanece dockerizado y separado de Cloudflare; esta comparación
no crea servicios ni contrata un plan.

## Recomendación para ECON

Empezaría con **Render: un Web Service Docker para FastAPI y Render Postgres 18
en la misma región**. Encaja con el contenedor actual y permite añadir después
un proceso de sincronización independiente. La recomendación es una decisión
para esta base, no un benchmark de rendimiento ni una estimación de capacidad.
Render documenta [servicios Docker](https://render.com/docs/docker),
[PostgreSQL 18 y conexión interna](https://render.com/docs/postgresql-creating-connecting)
y [workers que ejecutan procesos continuos](https://render.com/docs/background-workers).

| Opción | Cuándo la elegiría | Qué revisar antes de contratar |
| --- | --- | --- |
| **Render** | Primera opción para API Docker, base administrada y futuros procesos independientes | Región conjunta, memoria, conexiones de base, respaldo/recuperación y costo total de API + base + worker cuando exista |
| **Railway** | Alternativa cómoda para trabajar con servicios del proyecto y desplegar directamente el Dockerfile | Versión de PostgreSQL, backups, consumo y límites de cada servicio; decidir cuándo habilitar alta disponibilidad |
| **Fly.io Machines** | Si necesitamos controlar más la ejecución y la distribución de contenedores por región | Operación de Machines, configuración de parada/arranque y compatibilidad de la versión elegida de su base administrada |

Railway detecta el Dockerfile del directorio del servicio y ofrece PostgreSQL
con red privada y opciones de respaldo y alta disponibilidad. No asumir que
todas esas opciones se habilitan por crear la base.
[Dockerfiles](https://docs.railway.com/builds/dockerfiles),
[PostgreSQL](https://docs.railway.com/databases/postgresql).

Fly.io puede ejecutar una imagen Docker en Machines y tiene una oferta
administrada de PostgreSQL. Revisar la versión soportada antes de mover nuestra
base PostgreSQL 18. La configuración de autostop debe ser compatible con un
proceso que necesite ejecutarse continuamente.
[Machines](https://fly.io/docs/machines/flyctl/fly-machine-run/),
[Managed Postgres](https://fly.io/docs/mpg/),
[autostop/autostart](https://fly.io/docs/launch/autostop-autostart/).

No fijamos todavía tamaños ni una factura mensual: faltan carga, retención,
presupuesto y frecuencia de sincronización. Comparar el costo total de cómputo,
base, almacenamiento, backups y tráfico al elegir el plan. Para una operación
continua, elegir recursos que permanezcan ejecutándose según la configuración
contratada. [Precios de Render](https://render.com/pricing).

## Configuración inicial recomendada en Render

Crear la API desde este repositorio cuando se decida publicar, con `apps/api`
como directorio raíz y `Dockerfile` relativo a ese directorio. El contexto de
construcción también debe ser `apps/api`: el Dockerfile copia `pyproject.toml`,
`uv.lock`, `README.md`, `app` y `migrations` desde allí. Conservar el `CMD` del
contenedor, que escucha en `0.0.0.0` usando `PORT` si el proveedor lo define,
o el puerto `8000` por defecto.
[Configuración Docker de Render](https://render.com/docs/docker).

Crear PostgreSQL 18 en la misma región y usar su URL interna desde FastAPI.
Configurar las siguientes variables en el servicio, nunca en la compilación
de la web:

| Variable | Valor o criterio |
| --- | --- |
| `DATABASE_URL` | URL interna de PostgreSQL suministrada por el proveedor; conexión mediante Psycopg 3 |
| `CORS_ORIGINS` | Lista JSON con el origen HTTPS real del frontend |
| `ALLOW_LIVE_READS` | `false` en la demostración pública sin login |
| `NEXUS_EMAIL`, `NEXUS_PASSWORD` | Omitidas en la demostración; solo para un entorno privado con lecturas autorizadas |

Usar `postgresql+psycopg://` para indicar explícitamente el controlador de este
proyecto. La API y Alembic también adaptan `postgres://` y `postgresql://` a
ese controlador. Conservar usuario, contraseña, host, base y parámetros de conexión
entregados por el proveedor; no usar la URL local del Compose en la nube.

Configurar `/health/ready` como comprobación de despliegue para verificar la
conexión a la base. `/health/live` solo acredita que el proceso responde.
Antes de publicar una nueva versión, ejecutar desde el contenedor:

```sh
.venv/bin/alembic upgrade head
```

Render permite un comando de predespliegue en servicios de pago; resulta útil
para esa migración. Mantenerla como paso explícito, sin ejecutarla en cada
arranque ni al construir la imagen. Las revisiones de esquema nuevas requieren
respaldo y una estrategia de compatibilidad con la versión que sigue atendiendo
peticiones. [Predespliegue de Render](https://render.com/docs/deploys#pre-deploy-command).

Después, configurar la URL HTTPS de esta API en `VITE_API_BASE_URL` y compilar
la web según [la guía de Cloudflare](deploy-cloudflare.md). Verificar una
consulta `fixture` desde el dominio final y una recarga de ruta interna.

## Evolución de la sincronización

El endpoint actual hace lecturas acotadas bajo demanda. Cuando se implemente
sincronización persistente, ejecutarla en un proceso separado de la API HTTP,
con su propio comando, supervisión y permisos. Reutilizar la imagen Docker
puede ser suficiente; no hace falta convertir el panel en un servidor nuevo.
La cola, el planificador, la idempotencia y el historial todavía no existen y
no se deben anunciar como desplegados.

Conservar los límites y reintentos del proveedor aunque el contenedor pueda
correr continuamente. Separar API y trabajador facilita controlar su consumo;
elegir un contenedor no elimina límites de CPU, memoria, conexiones o red.

El perímetro de datos sigue siendo una decisión independiente del hosting:
sin login propio, la demostración pública usa únicamente fixtures. Para
habilitar información privada, proteger también el acceso al origen de la API.
La guía actual no modifica DNS, cuentas, secretos remotos ni planes contratados.
