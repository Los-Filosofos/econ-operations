# Despliegue del servicio Python y PostgreSQL

ECON se entrega como un contenedor con Dash, FastAPI, Plotly y AG Grid Community.
PostgreSQL conserva planes, cortes, eventos y recepción. La misma imagen puede
ejecutar un worker separado y explícito; el servidor web no lo inicia.
Esta guía describe la configuración disponible y no publica infraestructura.

La implementación está definida en [ADR 0003](adr/0003-python-dash-hub.md),
[ADR 0004](adr/0004-persistent-transfer-workflow.md) y
[la guía operativa](solucion-integracion.md).

## Imagen y procesos

Desde la raíz del repositorio:

```powershell
.\scripts\check.ps1 -Container
docker build -t econ-hub apps/api
```

[El Dockerfile](../apps/api/Dockerfile) usa `apps/api` como contexto de construcción.
Instala dependencias con el lockfile, copia `app`, `migrations` y `alembic.ini`,
y ejecuta el servicio con un usuario sin privilegios. Los archivos `.env` y las
bases locales están excluidos de la imagen.

El comando predeterminado inicia Uvicorn en `0.0.0.0`, con `PORT` si está
definido o `8000` por defecto. Dash, assets y API se sirven desde el mismo origen.
No hay compilación Node, aplicación React ni publicación estática separada.

| Proceso | Ejecución |
| --- | --- |
| Servicio web | Comando predeterminado de la imagen |
| Migración | Comando explícito sobre la base configurada, antes de iniciar la versión que necesita el esquema |
| Worker | Proceso separado con la CLI, solo cuando se configure la operación autorizada |

PostgreSQL debe permanecer fuera del sistema de archivos efímero del contenedor
web. Usar una base accesible desde los procesos de aplicación y worker; no copiar
en un despliegue remoto la dirección loopback del Compose local.

## Variables de una demostración pública

Configurar variables durante la ejecución, no al construir assets. Como el hub
no tiene login de aplicación, una demostración pública conserva exclusivamente
muestras y las cuatro habilitaciones desactivadas:

| Variable | Valor o criterio |
| --- | --- |
| `DATABASE_URL` | URL de PostgreSQL accesible desde el servicio, conservada como secreto del entorno |
| `PORT` | Puerto entregado por la plataforma; si se omite, `8000` |
| `CORS_ORIGINS` | `[]` para Dash y API en el mismo origen |
| `ALLOW_LIVE_READS` | `false` |
| `ALLOW_LOCAL_MANAGEMENT` | `false` |
| `ALLOW_LIVE_WRITES` | `false` |
| `AUTO_QUEUE_TRANSFERS` | `false` |
| `NEXUS_EMAIL`, `NEXUS_PASSWORD` | Omitidas en la demostración pública |
| `STARTRACK_API_KEY`, `STARTRACK_PASSWORD` | Omitidas en la demostración pública |

`postgresql+psycopg://` indica el controlador instalado. La aplicación y Alembic
también normalizan `postgres://` y `postgresql://` a ese controlador sin cambiar
usuario, contraseña, host, base o parámetros de conexión.

No poner secretos en URLs del navegador, código, capturas, registros ni variables
`VITE_*`. CORS no controla por sí solo quién puede consultar una API pública.
La gestión HTTP está limitada a peticiones locales con validación de origen:
publicar un proxy no crea un sistema de permisos ni autoriza live.

## Migración y persistencia

Con las variables de conexión disponibles, ejecutar dentro de la imagen:

```sh
.venv/bin/alembic upgrade head
.venv/bin/alembic current
```

La migración `0001_operations` crea movimientos, eventos y cortes. La cola reside
en los movimientos y se reclama transaccionalmente antes de enviar al proveedor.
No se ejecutan migraciones durante la construcción de la imagen ni en cada
arranque del servicio. Los cambios futuros de esquema requieren planificar
respaldo, recuperación y compatibilidad con los procesos que siguen activos.

El desarrollo conserva el proyecto Compose `econ-backend` y su volumen
`econ-backend_postgres18_data`; no se recrean para aplicar una migración.
La estructura del registro está en [PostgreSQL](database.md).

## Worker disponible para operación autorizada

El worker usa los mismos servicios y la misma base que Dash/HTTP. En un entorno
privado, después de configurar credenciales y habilitaciones según
[la guía operativa](solucion-integracion.md#ejecutar-ciclos), el comando dentro de
la imagen es:

```sh
.venv/bin/python -m app.cli.sync_operations --mode live --watch --interval 120
```

Sin `--watch` ejecuta un solo ciclo. La CLI admite intervalos entre 60 y 3600
segundos. Ejecutar un único worker: los límites externos pueden ser compartidos
por IP, mientras el limitador local funciona por proceso.

El proceso requiere habilitación de gestión local; las consultas remotas y la
creación de tareas tienen controles independientes. Un envío incierto permanece
en conciliación y no genera un segundo POST automático. La existencia del SDK,
cola e historial no acredita todavía la creación autenticada en la cuenta
Startrack, cuya validación sigue pendiente.

No iniciar este worker live en una demostración pública de muestras. Las
ampliaciones de [sincronización](sincronizacion-y-discrepancias.md) y
[escala](arquitectura-escalable-flota.md) son propuestas, no procesos ya desplegados.

## Comprobaciones de la versión publicada

Configurar `/health/ready` para comprobar conexión con PostgreSQL.
`/health/live` acredita únicamente que el proceso responde; ninguno valida
credenciales ni conectividad de Prisma o Startrack.

Revisar `/?mode=fixture`, `/solicitudes?mode=fixture`,
`/operaciones?mode=fixture`, `/api/v1/hub?mode=fixture` y
`/api/v1/operations?mode=fixture`. Confirmar que el registro está disponible tras
la migración, que los callbacks funcionan y que recargar una ruta interna conserva
estilos, modo y búsqueda. Las muestras muestran cinco equipos y dos solicitudes,
con cobertura parcial, sin inventar tareas, GPS o recepciones.

Antes de dimensionar una operación continua faltan mediciones de carga,
retención, concurrencia, latencia y recuperación. La imagen no configura por
sí sola respaldos, alta disponibilidad o capacidad para miles de vehículos.
