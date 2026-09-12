# Base central: PostgreSQL en Docker

Recomendación inicial: PostgreSQL 18 para los datos compartidos, SQLModel para
acceder a ellos desde FastAPI y Alembic para evolucionar el esquema. Docker
Compose ejecuta PostgreSQL localmente; Docker no es una base de datos.

## Por qué encaja

El escenario sugiere entidades relacionadas, conciliación entre fuentes y
consultas para indicadores. PostgreSQL permite claves foráneas y restricciones
de unicidad: ayudan a mantener relaciones válidas y a evitar duplicados cuando
ya se han definido correctamente sus identificadores.
[Documentación de restricciones](https://www.postgresql.org/docs/current/ddl-constraints.html).

También permite combinar tablas estructuradas con campos JSONB e índices sobre
ellos. Propongo normalizar los campos acordados y usar JSONB, cuando corresponda,
para conservar el contenido recibido y campos aún no mapeados. JSONB no conserva
el texto original byte por byte ni claves duplicadas; si se necesita un original
exacto para auditoría, habrá que conservar el archivo o texto por separado.
[Documentación de JSON](https://www.postgresql.org/docs/current/datatype-json.html).

Esto evita escoger otra base únicamente porque las fuentes tengan campos
distintos. Las reglas para identificar el mismo registro, resolver conflictos
y validar datos siguen siendo responsabilidad de la integración.

## Cuándo reconsiderar

| Si el reto resulta ser… | Evaluación |
| --- | --- |
| Una API operativa con datos relacionados e indicadores | Mantener PostgreSQL como punto de partida |
| Una demostración local sin usuarios concurrentes | SQLite puede ser suficiente |
| Una organización con otra base estándar y equipo que la opera | Evaluar esa base antes de introducir infraestructura nueva |
| Análisis masivo sobre un historial muy grande | Medir consultas y volumen; podría requerir una plataforma analítica adicional |
| Solo consulta en vivo de dos APIs sin almacenamiento propio | Confirmar si hace falta una base central |

Estas son recomendaciones de arquitectura, no resultados de una comparación
de rendimiento. Aún no se conocen las cargas reales.

## Información necesaria

Contexto confirmado: se ofrecerá un sandbox y se espera un volumen alto en una
empresa de logística. Todavía no hay acceso al sandbox ni cifras de carga.
La instalación local es una base de desarrollo, no una validación de capacidad.

1. **Acceso a las fuentes:** API, webhooks, exportaciones o acceso autorizado a
   bases; autenticación, límites y posibilidad de extraer cambios y eliminaciones.
2. **Tamaño y uso:** registros actuales, cambios diarios, años de historial,
   archivos adjuntos, usuarios concurrentes y consultas esperadas.
3. **Actualización:** si el panel puede llevar minutos de retraso o requiere
   segundos; cómo trabajarían los operadores sin conexión.
4. **Identidad y autoridad:** claves para cruzar registros, campos faltantes,
   cuál fuente manda por campo y quién resuelve discrepancias.
5. **Operación:** infraestructura disponible, presupuesto, permisos, respaldos,
   tiempo máximo de caída aceptable y pérdida de datos tolerable.

## Validación cuando llegue el sandbox

Registrar filas y tamaño por entidad, cambios por segundo en horas pico,
retención, consultas concurrentes y latencia objetivo. El sandbox podría tener
menos datos o recursos que producción; confirmar si es representativo.

Probar primero una importación acotada por lotes, con paginación, puntos de
reanudación y procesamiento idempotente. Medir duración, errores, uso de memoria,
conexiones y retraso de sincronización antes de aumentar la carga.

Crear índices según las consultas reales y comprobar sus planes de ejecución.
El particionado y una plataforma analítica separada se evaluarán si las mediciones
los justifican; no se activan solo por describir el volumen como alto.
[Estadísticas de PostgreSQL](https://www.postgresql.org/docs/current/monitoring-stats.html)
y [particionado](https://www.postgresql.org/docs/current/ddl-partitioning.html).

## Configuración entregada

- Imagen oficial `postgres:18`, versión mayor estable soportada. El tag recibe
  parches; se descarga con `docker compose pull db`. Para despliegues reproducibles
  se debe fijar la imagen probada por digest y planificar las actualizaciones.
- Puerto `127.0.0.1:54329`, base `econ`, usuario `econ`.
- Volumen persistente `econ-backend_postgres18_data` y comprobación de salud.
- Reinicio automático salvo parada explícita.
- Conexión de FastAPI mediante `DATABASE_URL` en `.env`, sin fallback silencioso.
- Credenciales exclusivamente de desarrollo; no se ha configurado producción.

PostgreSQL 18 está soportado hasta noviembre de 2030 según la
[política oficial](https://www.postgresql.org/support/versioning/). El montaje
del volumen sigue el cambio introducido en la
[imagen oficial de PostgreSQL 18](https://hub.docker.com/_/postgres).

Para producción, mi preferencia inicial sería PostgreSQL administrado si encaja
en presupuesto: evaluar respaldos automáticos, recuperación a un momento dado,
acceso privado y monitoreo. Docker local sirve para desarrollar y demostrar el
prototipo; por sí solo no configura esas capacidades.
