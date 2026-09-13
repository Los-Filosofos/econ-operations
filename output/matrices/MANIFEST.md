# Matrices exportadas de ECON

Generado el 2026-09-13 por `scripts/docs/exportar_matrices.py` desde:

- [`docs/equivalencias-prisma-startrack.md`](../../docs/equivalencias-prisma-startrack.md) (SHA-256 `028001dcdf54b4951172a8297617c95433065315710b18bb4af8a1cff533d306`; revisión del origen: 12 de septiembre de 2026; el glosario de sinónimos y las inconsistencias internas se añadieron el 13 de septiembre de 2026).
- [`docs/matriz-requisitos-entregables.md`](../../docs/matriz-requisitos-entregables.md) (SHA-256 `a84e518a2947907ed100db7a7484f867334847dbf998087e0c92214e9cf64345`; revisión del origen: 13 de septiembre de 2026).

Las tablas Markdown siguen siendo el origen editable; estos archivos son copias
derivadas para reutilizar en hojas de cálculo (RNF-02). No añaden filas, IDs ni
valores. Reproducir y verificar (`uv run --project apps/api python …` también
sirve: openpyxl 3.1.5 está en el grupo `dev` del proyecto):

```sh
uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_matrices.py
uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_matrices.py --check
```

Libro: [`matrices-econ.xlsx`](matrices-econ.xlsx) (SHA-256 `140fc80ad6351fa2f56b9ef1ea6e69d67a8603c3da7d4301a58ae052d0d2aa8d`,
openpyxl 3.1.5, una hoja por tabla, sin formato decorativo).

| Tabla | Documento y sección de origen | Requisito | Filas | Columnas | SHA-256 del CSV |
| --- | --- | --- | --- | --- | --- |
| [`clasificaciones.csv`](clasificaciones.csv) | `equivalencias-prisma-startrack.md` › Cómo leer las matrices | RF-02: leyenda de las clasificaciones usadas en el mapeo | 5 | 2 | `4a4090891b7f6a26c7bb52b3868b02ed306679f1932f25dde725e82a10340024` |
| [`identidad-cardinalidad.csv`](identidad-cardinalidad.csv) | `equivalencias-prisma-startrack.md` › Identidad y cardinalidad | RF-02: relaciones entre objetos y cardinalidad explícita | 6 | 3 | `a3bb7ebd9631c358beecc1a8d620f804ddc27919edb047b243615d80b38eb026` |
| [`glosario-sinonimos.csv`](glosario-sinonimos.csv) | `equivalencias-prisma-startrack.md` › Glosario de sinónimos entre plataformas | RF-01/RF-02: nombre exacto de cada concepto en Prisma, Startrack y ECON | 36 | 5 | `a676753673d55220c329e7c2b2f857215153f9a66b70f6f62933f4cc2bfdc9cb` |
| [`inconsistencias-internas.csv`](inconsistencias-internas.csv) | `equivalencias-prisma-startrack.md` › Inconsistencias internas que ya conoce el kit | RF-02: anomalías de cada plataforma que obligan a comparar por ID | 9 | 3 | `2f4e05b3c6a1775f6dc123f16dfbc3c6af6c935536067d03fc89eebc2d830b61` |
| [`formulario-identificacion.csv`](formulario-identificacion.csv) | `equivalencias-prisma-startrack.md` › Identificación, contenido y estado | RF-02: formulario de tarea, identificación, contenido y estado | 8 | 5 | `cbbc7273f911b798b25d7f999ef1181f7bef72d9d5799a1a8225585c5fae51d4` |
| [`formulario-programacion.csv`](formulario-programacion.csv) | `equivalencias-prisma-startrack.md` › Programación y ubicación | RF-02: formulario de tarea, programación y ubicación | 13 | 5 | `0c042cc01c9948654a8e84e3410b5c751e1ed8b2978c9b8d90b39db27b20db10` |
| [`formulario-asignacion.csv`](formulario-asignacion.csv) | `equivalencias-prisma-startrack.md` › Asignación y formularios | RF-02: formulario de tarea, asignación y formularios | 2 | 5 | `9a1945197361f3e6b05e3a8fd3a528e2e202280fe5fd54fc0726f475d02dd831` |
| [`formulario-articulos.csv`](formulario-articulos.csv) | `equivalencias-prisma-startrack.md` › Artículos y valores económicos | RF-02: formulario de tarea, artículos y valores económicos | 8 | 5 | `c85e46bb321baf9169f0c3a0f9ef5f4cbc2d7c15a7560242bb058163d626a743` |
| [`formulario-contacto.csv`](formulario-contacto.csv) | `equivalencias-prisma-startrack.md` › Contacto y notificaciones | RF-02: formulario de tarea, contacto y notificaciones | 6 | 5 | `dcc3b6441047e464db313d580b417cf93ef306841d4f4540a2292f7f9db6cd57` |
| [`formulario-tarea-completo.csv`](formulario-tarea-completo.csv) | `equivalencias-prisma-startrack.md` › Matriz completa del formulario de tarea suministrado | RF-02: las cinco secciones del formulario de tarea en una sola matriz | 37 | 6 | `8e47d23722183e341f5a043355661a74db457d44b17f7fa3e1cfe4d1319355b1` |
| [`otros-campos-api-tarea.csv`](otros-campos-api-tarea.csv) | `equivalencias-prisma-startrack.md` › Otros campos API de tarea que no deben perder su significado | RF-02: campos del Job sin control editable en el formulario | 11 | 3 | `51fad8d4b27bb3dad8ce48eca04215ae7489724afa0f879e5c0b0261bf61cc42` |
| [`inventario-prisma.csv`](inventario-prisma.csv) | `equivalencias-prisma-startrack.md` › Inventario Prisma que se conserva y que no viaja a la tarea | RF-01/RF-02: campos Prisma conservados y su relación real con Startrack | 28 | 3 | `be98a2864594a136bd07e768dffa3a50b93e225fbd1bd6425747780a2e04589c` |
| [`fechas-y-unidades.csv`](fechas-y-unidades.csv) | `equivalencias-prisma-startrack.md` › Fechas, unidades y estados separados | RF-02: tratamiento de fechas, unidades y coordenadas | 8 | 2 | `77337c057acc78c376bf8c02bd198acb8f15b5057fcb6c7460e4438a07af57e8` |
| [`estados-separados.csv`](estados-separados.csv) | `equivalencias-prisma-startrack.md` › Fechas, unidades y estados separados | RF-05: estados por objeto y regla de interpretación | 7 | 3 | `942bba61d2cbffaf2b58c91ae164d83779e695b4c67d8231699e0ac6b72582d9` |
| [`evidencia-retorno.csv`](evidencia-retorno.csv) | `equivalencias-prisma-startrack.md` › Evidencia de retorno y cobertura | RF-04: qué evidencia de Startrack está implementada y su límite | 5 | 3 | `20bff46c626d93b7ed4d54c3257a223a6252ec793c282dd86fc2816357edede5` |
| [`raci-propuesta.csv`](raci-propuesta.csv) | `equivalencias-prisma-startrack.md` › Responsabilidades propuestas para confirmar | RF-03: matriz RACI propuesta, pendiente de validación empresarial | 9 | 5 | `0408151d367807eec86c5f32d065c4a463b27c251bf8140991048d55b2fedc65` |
| [`trazabilidad-requisitos.csv`](trazabilidad-requisitos.csv) | `matriz-requisitos-entregables.md` › Matriz de trazabilidad | RNF-04: RF-01 a RF-06, RNF-01 a RNF-04 y entregables de §6/§9 con evidencia, dónde lo ve el jurado, estado y brecha | 19 | 6 | `d3b7e0bee286ee1a80e3f29013e9dc2d4f52b78a3cbd9e376c716ae00d1d00dd` |

- Solo se exportan tablas ya escritas en los documentos; no se inventan filas ni IDs.
- La RACI es una propuesta pendiente de validación empresarial (RF-03).
- Una correspondencia documentada no acredita identidad de registros entre plataformas.
- El estado de la trazabilidad (cumple, parcial, pendiente) describe evidencia en el repositorio, no una calificación del jurado.
