# PDFs entregables

Regenerados el **13 de septiembre de 2026** con `scripts/docs/generar_dossier.py`
(comando en [entregables-visuales.md](../../docs/entregables-visuales.md#reproducción-y-revisión)).
El generador comprueba al terminar que el dossier tenga 16 páginas y las
decisiones técnicas 2. Los PDF llevan su fecha de creación en los metadatos, por
lo que cada ejecución produce bytes distintos: los SHA-256 siguientes
corresponden a los archivos versionados junto con este manifiesto.

| Archivo | Generado | Páginas | Bytes | SHA-256 | Origen y generador |
| --- | --- | --- | --- | --- | --- |
| [`ECON-entregables-visuales.pdf`](ECON-entregables-visuales.pdf) | 2026-09-13 | 16 | 1915138 | `118149fc6622c06d3a6b616c9cde0d84f04f9076cfd37ccbee811ab479686e2e` | `build_dossier()`: figuras de `docs/assets/entregables/` (incluido `diagrama-estados.png`: solicitud, asignación, maquinaria y mantenimiento en Prisma; envío, recepción declarada y actor en ECON; tarea y ubicación observada en Startrack), RACI leída de `docs/equivalencias-prisma-startrack.md` y textos del generador |
| [`ECON-decisiones-tecnicas.pdf`](ECON-decisiones-tecnicas.pdf) | 2026-09-13 | 2 | 48654 | `97c46d67ea37a4165ca14da91604f92ebfe98b4b320141a6edd144c43b696a1f` | `build_decisions()`: `docs/decisiones-tecnicas.md` (páginas 1 y 2) |
| [`ECON-diccionario-mapeo-y-manual-integracion.pdf`](ECON-diccionario-mapeo-y-manual-integracion.pdf) | 2026-09-12 | 34 | 227928 | `45ab32f4cfdda1f0013de5c4fb9f18afe61e8cde0f232290cfa1e696ba9302df` | **Sin generador en el repositorio**: no se regenera y se conserva tal como se entregó el 12/09/2026. Para la matriz completa queda reemplazado por [`docs/equivalencias-prisma-startrack.md`](../../docs/equivalencias-prisma-startrack.md), sus copias CSV/XLSX en [`output/matrices`](../matrices/MANIFEST.md) y el [diccionario generado](../../docs/diccionario-modelo-econ.md); su texto puede no reflejar los cambios posteriores (actor de sesión, `tracked_vehicle_kind`, grafo, indicadores, sugerencias). |

Verificación desde la raíz:

```sh
sha256sum output/pdf/*.pdf
```

Ninguna generación consulta ni modifica Prisma o Startrack; los gráficos usan
solo la muestra proporcionada y las figuras PNG/SVG se conservan en
`docs/assets/entregables/`.
