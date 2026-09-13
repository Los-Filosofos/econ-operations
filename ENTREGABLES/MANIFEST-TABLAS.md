# Tablas exportadas de los entregables

Generado el 2026-09-13 por `scripts/docs/exportar_entregables.py` desde:

- [`docs/equivalencias-prisma-startrack.md`](../docs/equivalencias-prisma-startrack.md) (SHA-256 `028001dcdf54b4951172a8297617c95433065315710b18bb4af8a1cff533d306`).
- [`docs/matriz-requisitos-entregables.md`](../docs/matriz-requisitos-entregables.md) (SHA-256 `87c78899199de31ee701729ec77c460addcebd9fd99e8d71e3fb82db8ecffd22`).
- [`ENTREGABLES/1-Matriz-de-Mapeo-de-Campos.md`](1-Matriz-de-Mapeo-de-Campos.md) (SHA-256 `9adc5f7742cdf7a45cac59243367dd1f62a1dee69ce6bb5df80ec84463197f92`).
- [`ENTREGABLES/2-Matriz-de-Responsabilidades-RACI.md`](2-Matriz-de-Responsabilidades-RACI.md) (SHA-256 `cd67575b5d53d1a32576fce0572374dd982bf9193084264c8ce322ee89cbd48b`).

El Markdown de cada entregable sigue siendo el origen editable; estos archivos
son copias derivadas para hojas de cálculo (RNF-02). No añaden filas ni valores.

**Formato CSV**: `utf-8-sig` (UTF-8 con BOM), fin de línea `CRLF`, separador `,`.

BOM y CRLF para que Excel muestre los acentos al abrir el archivo con doble clic. El separador es la coma de RFC 4180: el CSV es para ingesta automatizada y el XLSX es el archivo para abrir en Excel.

**Formato XLSX**: una hoja por tabla, fila de cabecera fija y filtrable, ancho de
columna calculado, ajuste de texto y alineación superior.

Reproducir y verificar:

```sh
uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_entregables.py
uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_entregables.py --check
```

| Archivo | Origen | Contenido | Filas | SHA-256 |
| --- | --- | --- | --- | --- |
| [`1-Matriz-de-Mapeo-de-Campos.csv`](1-Matriz-de-Mapeo-de-Campos.csv) | `1-Matriz-de-Mapeo-de-Campos.md` | 5 columnas: 1. Mapeo Consolidado de Correspondencia | 14 | `bcce3a624ad039d4f9929a7c81142e79e8ad395cbeea384a62935e00a765df2d` |
| [`1-Matriz-de-Mapeo-de-Campos-Detalle-Formulario.csv`](1-Matriz-de-Mapeo-de-Campos-Detalle-Formulario.csv) | `equivalencias-prisma-startrack.md` | 6 columnas: Matriz completa del formulario de tarea suministrado | 37 | `307d9b244d7cb9f2fce27614272c06df2b2775bed88796a656a7382b37e2454c` |
| [`1-Matriz-de-Mapeo-de-Campos.xlsx`](1-Matriz-de-Mapeo-de-Campos.xlsx) | `1-Matriz-de-Mapeo-de-Campos.md` | 18 hojas: Mapeo consolidado … | 231 | `e49387e69a707b8320623553dd2b3ee7a10cfd54b48ea6c5fd1d0258c410d1c1` |
| [`2-Matriz-de-Responsabilidades-RACI.csv`](2-Matriz-de-Responsabilidades-RACI.csv) | `2-Matriz-de-Responsabilidades-RACI.md` | 5 columnas: 1. Tabla Estructurada RACI | 9 | `78bbfcdf7ceddc62714c5f3d25eb403a8f902c7687767e44267591202093c882` |
| [`2-Matriz-de-Responsabilidades-RACI-Detalle.csv`](2-Matriz-de-Responsabilidades-RACI-Detalle.csv) | `equivalencias-prisma-startrack.md` | 5 columnas: Responsabilidades propuestas para confirmar | 9 | `126fa3b3b61290332dbecb04de3cc23d3b52304769599b2b7683614486f9a25f` |
| [`2-Matriz-de-Responsabilidades-RACI.xlsx`](2-Matriz-de-Responsabilidades-RACI.xlsx) | `2-Matriz-de-Responsabilidades-RACI.md` | 2 hojas: RACI por gerencia … | 18 | `626a7afb3cde7b6e025958b12842430a206c7dba897026cf3a53754f7faa77f6` |

- El Markdown de cada entregable es el origen editable; CSV y XLSX son copias.
- Cada archivo contiene la misma matriz que el entregable cuyo nombre lleva.
- Las hojas de detalle proceden de docs/ y coinciden con output/matrices.
- La RACI es una propuesta pendiente de validación empresarial (RF-03).
- Una correspondencia documentada no acredita identidad de registros entre plataformas.
