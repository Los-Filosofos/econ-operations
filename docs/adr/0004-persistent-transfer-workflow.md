# ADR 0004: Persistencia y ejecución del traslado

Fecha: 2026-09-12. Estado: implementado; validación autenticada de Startrack pendiente.

## Contexto

El usuario pidió implementar el flujo proyecto, solicitud, asignación, tarea de
Startrack y recepción. Confirmó que todo el caso contiene datos sintéticos.
Prisma conserva el proceso administrativo existente. Los contratos revisados
no documentan crear proyectos/solicitudes ni recibir webhooks de aprobación.

## Decisión

Conservar Dash/FastAPI y añadir un servicio compartido de operaciones con
SQLModel, PostgreSQL y una migración explícita. Guardar IDs por origen y entorno,
payload revisable, cortes de datos y eventos. Las muestras del archivo permiten
planes locales; una escritura al sandbox exige volver a consultar la solicitud
y validar sus correspondencias actuales.

La cola reclama cada envío en una transacción antes de llamar a Startrack. Un
resultado incierto se concilia mediante lectura; no genera un segundo POST.
Un worker explícito consulta periódicamente los proveedores. El SDK resuelve el
transporte HTTP; el servicio conserva las reglas y la coordinación persistente.

La presencia de un vehículo GPS en una geocerca y la recepción de maquinaria
son eventos distintos. La recepción requiere responsable, fecha con zona y
referencia de constancia. El estado completado de una tarea no la sustituye.

## Consecuencias

Una sola aplicación sirve frontend y backend. Se conserva el Compose y su
volumen. No hay login de aplicación; la gestión se limita al equipo local y
requiere habilitación del servidor. Los defaults mantienen lecturas/escrituras
remotas deshabilitadas. No se insertan ejemplos inventados ni se duplica el
dataset en Prisma.

Las pruebas controladas cubren el flujo, concurrencia y resultados inciertos.
El acceso API y el formato efectivo de creación de esta cuenta de Startrack
deben verificarse con una conexión autorizada al sandbox.

Detalles y comandos: [solución y guía operativa](../solucion-integracion.md).
