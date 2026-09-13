# Revisión de consultas y navegación

Revisión local del 13/09/2026, Windows, PostgreSQL de Compose y modo `fixture`.
La espera principal identificada estaba en abrir conexiones a la base, no en
procesar las cinco máquinas y dos solicitudes de la muestra.

## Mediciones

Tiempos con `perf_counter`, sin imprimir cadenas de conexión ni credenciales:

| Operación | Tiempo observado |
| --- | --- |
| Leer y transformar las muestras sin SQL | 0,5–0,9 ms |
| Abrir conexión nueva y ejecutar `SELECT 1` usando `localhost` | 5.121–5.131 ms |
| La misma operación usando `127.0.0.1`, después del ajuste local | 17–40 ms |
| Consultar versión del registro con conexión reutilizada | 5 ms |
| Leer muestras y evidencia persistida con conexión reutilizada | 4–7 ms |
| Leer el registro de operaciones con conexión reutilizada | 10–13 ms |

`localhost` resuelve tanto a `::1` como a `127.0.0.1`, mientras Compose publica
PostgreSQL solo en IPv4. La espera se reprodujo en tres conexiones nuevas y
desapareció al usar la dirección publicada. Los callbacks concurrentes pueden
abrir más conexiones del pool aunque el conjunto de datos sea pequeño.
Estos tiempos miden operaciones del servidor, no el tiempo total de dibujar
una página en cualquier navegador o equipo.

## Correcciones

- Se corrigió únicamente el host de PostgreSQL local en el `.env` existente
  y en `.env.example`; permanecen base, puerto, credenciales, permisos y volumen.
  El motor sigue respetando las URLs configuradas, incluidas las remotas.
- Los enlaces Markdown de las tablas AG Grid a solicitudes, maquinaria y
  operaciones navegan dentro de Dash. Abrir un detalle conserva el documento,
  el shell y los stores del navegador. Descargas, otros destinos y clics con
  modificadores conservan su comportamiento nativo.
- Tres callbacks de presentación (menú móvil, `aria-expanded` y visibilidad
  del estado de lectura) se ejecutan en el navegador. Evitan llamadas HTTP y
  consultas de sesión para esas interacciones; los datos y acciones siguen
  autenticándose en el servidor.

El menú lateral ya navegaba dentro de Dash. Los callbacks de datos ya
reutilizaban el store para la misma consulta: se verificó esa propiedad en
portada, alias, todas las secciones y sus detalles. Cambiar modo o búsqueda,
completar una acción, un cambio de versión o el refresco explícito siguen
teniendo sus reglas de relectura. No se introdujo una caché global ni se
consultaron proveedores durante esta revisión.

## Validación y límites

- `tests/test_navigation_reads.py`: tres pruebas nuevas; cubren 13 rutas y
  variantes sin reconsultar datos al navegar, cambios de modo/búsqueda,
  actualización forzada y callbacks de presentación locales.
- 21 pruebas dirigidas de navegación, conexión y autenticación de interfaz
  aprobadas; 17 casos de navegación JavaScript comprobados con Node, incluidos
  modificadores, descargas, enlaces externos y API.
- Navegador con sesión admin: las ocho secciones principales, un detalle desde
  tabla y escritorio a 1280 px; menú móvil a 390 px, foco atrapado y Escape.
- Ruff y formato aprobados. Diccionario generado vigente.
- Suite completa antes: **550 aprobadas, 54 fallidas, 20 omitidas**. Después:
  **553 aprobadas, las mismas 54 fallidas, 20 omitidas**. Los fallos previos
  incluyen expectativas y firmas antiguas de callbacks/vistas, una lectura de
  assets con codificación incorrecta y un mock de registro desactualizado.
  No se presenta la suite general como aprobada. PostgreSQL de pruebas aisladas
  no estaba disponible; no se usó la base de desarrollo para esas pruebas.
- La comprobación separada de matrices detecta exportaciones desactualizadas;
  sus fuentes y artefactos no forman parte de esta corrección de rendimiento.

Para repetir las pruebas dirigidas en PowerShell desde la raíz:

```powershell
$env:DATABASE_URL = 'sqlite://'
$env:ALLOW_LIVE_READS = 'false'
uv run --directory apps/api pytest tests/test_navigation_reads.py tests/test_database.py tests/test_auth_ui.py -q
```

La comprobación completa sigue siendo `scripts/check.ps1` o `scripts/check.sh`.
