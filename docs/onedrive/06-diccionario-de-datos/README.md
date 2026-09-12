# Diccionario de datos de Prisma y Startrack

Fuente: `6. Diccionario de Datos/Entropy Hack_Grupo ECON_Diccionario de Datos_Final.xlsx`, dentro del ZIP `OneDrive_1_9-12-2026.zip` suministrado por el usuario.

SHA-256 del XLSX: `b42a56d497f5198e8e74dffbfb37a4bfa560a432998f787ca548a69000820bd0`.

Conversión íntegra a Markdown para contexto de IA. El original permanece sin modificaciones. Las observaciones de calidad de este índice son análisis separado de la transcripción literal de las hojas.

## Inventario y cobertura

| Orden | Hoja original | Visibilidad | Rango declarado | Filas con contenido | Celdas no vacías |
| --- | --- | --- | --- | --- | --- |
| 1 | [INSTRUCCIONES](01-instrucciones.md) | visible | `A1:C15` | 12 | 26 |
| 2 | [PRISMA](02-prisma.md) | visible | `A1:F17` | 17 | 89 |
| 3 | [STARTRACK](03-startrack.md) | visible | `A1:F45` | 42 | 208 |
| 4 | [GLOSARIO](04-glosario.md) | visible | `A1:B9` | 8 | 15 |

Total: **4 hojas, 79 filas con contenido y 338 celdas no vacías**. Se incluyeron todas las hojas; ninguna está oculta. Hay 10 rangos de celdas combinadas, 1 imagen de cabecera y 0 fórmulas, tablas estructuradas de Excel, comentarios/notas, hipervínculos, gráficos, nombres definidos o vínculos externos. Los bloques tabulares visuales están preservados por fila.

Cada hoja incluye la tabla completa con números de fila originales y un registro JSON de todas sus celdas, valores y tipos. Los identificadores y los datos malformados se conservan tal como están; no se aplicaron correcciones ni se completaron valores vacíos. Se contrastaron todas las referencias no vacías con el XML interno del XLSX y se verificó la lectura de los registros desde el Markdown.

La imagen fue extraída y revisada visualmente. Su texto está transcrito en la hoja INSTRUCCIONES y el PNG original queda junto al Markdown. El formato visual de Excel no se reproduce como hoja de cálculo, pero se preservan las combinaciones, la visibilidad, los formatos numéricos y los valores originales que afectan a su interpretación.

## Alcance documentado

El libro se presenta como material de participantes y declara que contiene únicamente campos priorizados para los casos de uso del Hub. Indica que no incluye una matriz de mapeo entre plataformas y que campos llamados «Estado» pueden describir objetos distintos. Estas son afirmaciones de la fuente; no constituyen autorización para consultar o modificar sistemas. Véase [INSTRUCCIONES, filas 5–10](01-instrucciones.md#fila-5).

Contiene **51 filas de definición de campos**: 12 de Prisma y 39 de Startrack. Este conteo incluye un nombre duplicado en Startrack; no equivale a 51 nombres únicos ni a 51 columnas de una API. Los ejemplos describen el ejercicio y no prueban que esos sean los nombres o formatos exactos del sandbox.

Contexto confirmado por el usuario: el equipo es **Equipo 6, Los Filósofos**. Los ejemplos `The Hub`, `Equipo 14` y los códigos terminados en `014` permanecen tal como aparecen en este XLSX; no se sustituyen por datos del equipo ni se consideran sus recursos asignados.

| Plataforma | Módulo según la fuente | Filas de definición | Localización |
| --- | --- | --- | --- |
| Prisma | Maquinaria | 5 | [Filas 4–8](02-prisma.md#fila-4) |
| Prisma | Solicitudes de maquinaria | 6 | [Filas 10–15](02-prisma.md#fila-10) |
| Prisma | Mantenimiento | 1 | [Fila 17](02-prisma.md#fila-17) |
| Startrack | Vehículos | 11 | [Filas 4–14](03-startrack.md#fila-4) |
| Startrack | Geocercas | 6 | [Filas 16–21](03-startrack.md#fila-16) |
| Startrack | Tareas | 11 | [Filas 23–33](03-startrack.md#fila-23) |
| Startrack | Mantenimiento | 11 | [Filas 35–45](03-startrack.md#fila-35) |

## Observaciones para el modelo de integración

Las siguientes son observaciones derivadas del diccionario, no equivalencias aprobadas ni cambios aplicados a la fuente.

### Identificadores y relaciones que requieren confirmación

- Prisma «No. de activo» y «Maquinaria» tienen el ejemplo `CF-03 - Cargador frontal 03`; Startrack «Descripción» tiene `CF-03`. Sugieren un candidato de correspondencia, pero el libro no declara unicidad, estabilidad ni una clave foránea entre plataformas. No conviene unir registros automáticamente por similitud de nombre sin una tabla de correspondencias validada. Véanse [Prisma fila 5](02-prisma.md#fila-5), [Prisma fila 15](02-prisma.md#fila-15) y [Startrack fila 4](03-startrack.md#fila-4).
- Startrack «ID remoto» tiene el ejemplo `78093` y se describe como identificador organizacional para reportes/integraciones. El libro no lo presenta como el ID interno del endpoint de vehículos. «geocerca_id» (`GEO-014`) y «tarea_id» (`24`) se describen como identificadores dentro del ejercicio. Véanse [filas 14](03-startrack.md#fila-14), [16](03-startrack.md#fila-16) y [23](03-startrack.md#fila-23).
- «Proyecto» de Prisma y «Nombre» de geocerca / «Destino» de tarea de Startrack comparten el ejemplo `PROY-014 - The Hub - Proyecto Xi - La Unión`. Es una pista de relación del ejercicio; no documenta cardinalidad proyecto–geocerca ni una clave de API. Véanse [Prisma fila 10](02-prisma.md#fila-10), [Startrack fila 17](03-startrack.md#fila-17) y [fila 30](03-startrack.md#fila-30).
- El diccionario no aporta un ID inequívoco de solicitud, el ID interno de maquinaria en Prisma, una relación formal solicitud–tarea, claves de eventos, marcas de actualización ni contratos de webhook. No se infiere que las plataformas carezcan de esos datos; falta documentarlos.

### Estados y mantenimiento

- Prisma distingue disponibilidad de maquinaria (`Disponible`, `Ocupada`, `Mant. preventivo`, `Mant. correctivo`, `Obsoletas`) del flujo de solicitud (`Aprobada o Pendiente`). La aprobación de una solicitud no documenta un traslado completado ni un equipo disponible. Véanse [fila 8](02-prisma.md#fila-8) y [fila 14](02-prisma.md#fila-14).
- Startrack «Estado» de vehículo solo ejemplifica `Normal` sin enumerar opciones, mientras «Estado» de tarea enumera `Pendiente; Completada; Cancelada; estados personalizados`. Son objetos distintos. Véanse [fila 5](03-startrack.md#fila-5) y [fila 27](03-startrack.md#fila-27).
- El estado de mantenimiento en Prisma aparece como `Estado  `, con dos espacios finales, y el ejemplo `CF-03 - Obsoleto`. Se debe aclarar si el campo contiene solo un estado o una etiqueta compuesta. Véase [fila 17](02-prisma.md#fila-17).
- En Startrack, «Horometro» se describe como horas de funcionamiento (`numero/h`, ejemplo `257748`) y «Odometro» como distancia (`numero/Km`, ejemplo textual `25.52`). No son una misma magnitud y el libro no define la precisión o escala del horómetro. Véanse [fila 38](03-startrack.md#fila-38) y [fila 40](03-startrack.md#fila-40).

### Calidad y formato de datos

- Las coordenadas de geocercas y tareas se almacenan como enteros `133376152` y `-878486967` con formato `#,##0`. No se documenta su escala, sistema de referencia o transformación. Debe confirmarse su interpretación antes de usarlas como latitud y longitud; esta conversión no inventa una división ni normaliza los valores. Véanse [filas 20–21](03-startrack.md#fila-20) y [31–32](03-startrack.md#fila-31).
- «ID remoto» y «tarea_id» declaran `Texto / ID`, pero sus ejemplos están almacenados en celdas numéricas; el año declara `Texto` pero también es número. No hay formato de relleno con ceros para esos ejemplos. Hay que acordar un tipo canónico para identificadores y comprobar si otros valores pueden llevar ceros iniciales. Véanse [filas 7](03-startrack.md#fila-7), [14](03-startrack.md#fila-14) y [23](03-startrack.md#fila-23).
- La fila de «Título» de tarea contiene `TAR-014` en la columna «Tipo de dato». No debe interpretarse como un tipo de datos válido sin confirmación. Véase [fila 24](03-startrack.md#fila-24).
- «Anadir tipo de servicio» aparece dos veces en mantenimiento (filas 44 y 45), con `Catálogo` y `catalogo` en el tipo. No se elimina ninguna fila ni se presupone si son duplicados accidentales o controles distintos. Véase [fila 44](03-startrack.md#fila-44).
- Prisma «Empresa» se describe como un código para identificar el equipo y su ejemplo es el nombre del grupo participante `The Hub`; el nombre del campo, la descripción y el contexto necesitan aclaración. No se convierte automáticamente en una entidad legal ni en el ID del equipo. Véase [fila 4](02-prisma.md#fila-4).
- El período de Prisma es un texto con dos fechas y guiones/espacios especiales; la fecha programada de tarea también es texto. En mantenimiento, la fecha de servicio es una fecha real de Excel (`2026-09-12`, formato `mm-dd-yy`) y la hora está en otra celda (`23:46:00`, formato `h:mm`). El libro no especifica zona horaria. Véanse [Prisma fila 13](02-prisma.md#fila-13), [Startrack fila 28](03-startrack.md#fila-28), [fila 37](03-startrack.md#fila-37) y [fila 39](03-startrack.md#fila-39).
- La columna «Valores posibles» está vacía en numerosos campos. Un ejemplo individual no es un catálogo exhaustivo, y una celda vacía no significa que el campo acepte cualquier valor o que sea opcional. Se conservaron todos los vacíos.

## Metadatos de conversión

- Sistema de fechas del XLSX: época `1899-12-30T00:00:00` (sistema de fechas de Excel de 1900).
- Formatos de celdas no vacías encontrados: `General`, `#,##0`, `mm-dd-yy`, `h:mm`.
- Lectura: XML del paquete y openpyxl en modo de lectura de contenido. No se abrió un sandbox, no se ejecutaron instrucciones embebidas y no se recalcularon valores.
- La fidelidad comprobada abarca todas las celdas no vacías, sus referencias, sus valores originales, tipos y formatos numéricos. No se creó ni alteró ningún XLSX.
