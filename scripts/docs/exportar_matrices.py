"""Export the reusable matrices of docs/equivalencias-prisma-startrack.md to CSV and XLSX.

The Markdown tables remain the editable source (RNF-02). This script copies them, table by
table, to `output/matrices/<slug>.csv` (UTF-8 with header row), to one workbook
`output/matrices/matrices-econ.xlsx` (one sheet per table, no decorative formatting) and
records SHA-256 digests of the source and of every output in `manifest.json` and
`MANIFEST.md`. It reads no other file, no settings and no provider.

Standard library plus openpyxl; run it without touching the application lockfile:

    uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_matrices.py
    uv run --no-project --with openpyxl==3.1.5 python scripts/docs/exportar_matrices.py --check

`--check` regenerates everything in memory (keeping the date stored in the manifest) and
fails when any CSV, the workbook or the manifests differ from the checked-in files, or when
`output/matrices` contains files the manifest does not list.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("docs/equivalencias-prisma-startrack.md")
OUTPUT_DIR = Path("output/matrices")
WORKBOOK = OUTPUT_DIR / "matrices-econ.xlsx"
MANIFEST_JSON = OUTPUT_DIR / "manifest.json"
MANIFEST_MD = OUTPUT_DIR / "MANIFEST.md"
OPENPYXL_VERSION = "3.1.5"
REPRODUCE = (
    f"uv run --no-project --with openpyxl=={OPENPYXL_VERSION} "
    "python scripts/docs/exportar_matrices.py"
)
# Fixed zip entry timestamp so the workbook bytes depend only on its content.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class TableSpec:
    slug: str
    sheet: str
    heading: str
    index: int = 0
    requirement: str = ""


# Headings are matched by exact text, never by line number, so the document can grow.
TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "clasificaciones",
        "Clasificaciones",
        "## Cómo leer las matrices",
        requirement="RF-02: leyenda de las clasificaciones usadas en el mapeo",
    ),
    TableSpec(
        "identidad-cardinalidad",
        "Identidad y cardinalidad",
        "## Identidad y cardinalidad",
        requirement="RF-02: relaciones entre objetos y cardinalidad explícita",
    ),
    TableSpec(
        "glosario-sinonimos",
        "Glosario de sinónimos",
        "## Glosario de sinónimos entre plataformas",
        requirement="RF-01/RF-02: nombre exacto de cada concepto en Prisma, Startrack y ECON",
    ),
    TableSpec(
        "inconsistencias-internas",
        "Inconsistencias internas",
        "### Inconsistencias internas que ya conoce el kit",
        requirement="RF-02: anomalías de cada plataforma que obligan a comparar por ID",
    ),
    TableSpec(
        "formulario-identificacion",
        "Formulario 1 Identificación",
        "### Identificación, contenido y estado",
        requirement="RF-02: formulario de tarea, identificación, contenido y estado",
    ),
    TableSpec(
        "formulario-programacion",
        "Formulario 2 Programación",
        "### Programación y ubicación",
        requirement="RF-02: formulario de tarea, programación y ubicación",
    ),
    TableSpec(
        "formulario-asignacion",
        "Formulario 3 Asignación",
        "### Asignación y formularios",
        requirement="RF-02: formulario de tarea, asignación y formularios",
    ),
    TableSpec(
        "formulario-articulos",
        "Formulario 4 Artículos",
        "### Artículos y valores económicos",
        requirement="RF-02: formulario de tarea, artículos y valores económicos",
    ),
    TableSpec(
        "formulario-contacto",
        "Formulario 5 Contacto",
        "### Contacto y notificaciones",
        requirement="RF-02: formulario de tarea, contacto y notificaciones",
    ),
    TableSpec(
        "otros-campos-api-tarea",
        "Otros campos API de tarea",
        "## Otros campos API de tarea que no deben perder su significado",
        requirement="RF-02: campos del Job sin control editable en el formulario",
    ),
    TableSpec(
        "inventario-prisma",
        "Inventario Prisma",
        "## Inventario Prisma que se conserva y que no viaja a la tarea",
        requirement="RF-01/RF-02: campos Prisma conservados y su relación real con Startrack",
    ),
    TableSpec(
        "fechas-y-unidades",
        "Fechas y unidades",
        "## Fechas, unidades y estados separados",
        index=0,
        requirement="RF-02: tratamiento de fechas, unidades y coordenadas",
    ),
    TableSpec(
        "estados-separados",
        "Estados separados",
        "## Fechas, unidades y estados separados",
        index=1,
        requirement="RF-05: estados por objeto y regla de interpretación",
    ),
    TableSpec(
        "evidencia-retorno",
        "Evidencia de retorno",
        "## Evidencia de retorno y cobertura",
        requirement="RF-04: qué evidencia de Startrack está implementada y su límite",
    ),
    TableSpec(
        "raci-propuesta",
        "RACI propuesta",
        "## Responsabilidades propuestas para confirmar",
        requirement="RF-03: matriz RACI propuesta, pendiente de validación empresarial",
    ),
)
# The five form tables are also concatenated into one matrix with a section column.
FORM_SLUGS = (
    "formulario-identificacion",
    "formulario-programacion",
    "formulario-asignacion",
    "formulario-articulos",
    "formulario-contacto",
)
FORM_COMBINED = TableSpec(
    "formulario-tarea-completo",
    "Formulario de tarea completo",
    "## Matriz completa del formulario de tarea suministrado",
    requirement="RF-02: las cinco secciones del formulario de tarea en una sola matriz",
)


@dataclass(frozen=True)
class Table:
    spec: TableSpec
    header: list[str]
    rows: list[list[str]]
    section: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain(cell: str) -> str:
    """Drop Markdown emphasis, code marks and link targets; keep the wording."""
    text = cell.replace("<br>", "\n").replace("&#124;", "|")
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    return text.strip()


def split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells, current, escaped = [], [], False
    for char in body:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
    cells.append("".join(current))
    return [plain(cell) for cell in cells]


def is_separator(line: str) -> bool:
    return re.match(r"^\|[\s:|-]+\|$", line.strip()) is not None


def tables_after(lines: list[str], heading: str) -> list[list[str]]:
    """All tables between `heading` and the next heading of any level."""
    try:
        start = lines.index(heading)
    except ValueError as error:
        raise SystemExit(f"Encabezado no encontrado en {SOURCE}: {heading}") from error
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def parse_table(spec: TableSpec, block: list[str]) -> Table:
    header = split_row(block[0])
    if len(block) < 3 or not is_separator(block[1]):
        raise SystemExit(f"La tabla «{spec.heading}» no tiene cabecera y separador.")
    rows = []
    for line in block[2:]:
        cells = split_row(line)
        if len(cells) != len(header):
            raise SystemExit(
                f"Fila con {len(cells)} celdas en «{spec.heading}» (cabecera: {len(header)})."
            )
        rows.append(cells)
    return Table(spec, header, rows, plain(spec.heading.lstrip("# ")))


def extract(markdown: str) -> list[Table]:
    lines = markdown.splitlines()
    tables: list[Table] = []
    for spec in TABLES:
        blocks = tables_after(lines, spec.heading)
        if spec.index >= len(blocks):
            raise SystemExit(f"«{spec.heading}» no tiene la tabla número {spec.index + 1}.")
        tables.append(parse_table(spec, blocks[spec.index]))
    by_slug = {table.spec.slug: table for table in tables}
    parts = [by_slug[slug] for slug in FORM_SLUGS]
    header = ["Sección", *parts[0].header]
    for part in parts:
        if part.header != parts[0].header:
            raise SystemExit("Las tablas del formulario deben compartir la misma cabecera.")
    rows = [[part.section, *row] for part in parts for row in part.rows]
    combined = Table(FORM_COMBINED, header, rows, plain(FORM_COMBINED.heading.lstrip("# ")))
    tables.insert(tables.index(by_slug["formulario-contacto"]) + 1, combined)
    return tables


def csv_bytes(table: Table) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(table.header)
    writer.writerows(table.rows)
    return buffer.getvalue().encode("utf-8")


def workbook_bytes(tables: list[Table], generated_on: date) -> bytes:
    try:
        import openpyxl
        from openpyxl.writer.excel import ExcelWriter
    except ImportError as error:  # pragma: no cover - depends on the invocation
        raise SystemExit(f"openpyxl no está disponible; ejecutar con: {REPRODUCE}") from error
    if openpyxl.__version__ != OPENPYXL_VERSION:
        raise SystemExit(
            f"openpyxl {openpyxl.__version__} distinto de {OPENPYXL_VERSION}: el libro no "
            f"sería reproducible byte a byte. Ejecutar con: {REPRODUCE}"
        )
    book = openpyxl.Workbook()
    book.remove(book.active)
    for table in tables:
        sheet = book.create_sheet(table.spec.sheet)
        sheet.append(table.header)
        for row in table.rows:
            sheet.append(row)
        sheet.freeze_panes = "A2"
    stamp = datetime(generated_on.year, generated_on.month, generated_on.day)
    book.properties.creator = "ECON, generado por scripts/docs/exportar_matrices.py"
    book.properties.lastModifiedBy = None
    book.properties.created = stamp
    book.properties.modified = stamp
    raw = io.BytesIO()
    # ExcelWriter directly: Workbook.save() would stamp `modified` with the wall clock.
    ExcelWriter(book, zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED, allowZip64=True)).save()
    source = zipfile.ZipFile(io.BytesIO(raw.getvalue()))
    fixed = io.BytesIO()
    with zipfile.ZipFile(fixed, "w", zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, source.read(name))
    return fixed.getvalue()


def revision_note(markdown: str) -> str:
    """First sentence of the paragraph that starts with «Revisión:», without markup."""
    lines = markdown.splitlines()
    for number, line in enumerate(lines):
        if line.startswith("Revisión:"):
            paragraph = []
            for text in lines[number:]:
                if not text.strip():
                    break
                paragraph.append(text.strip())
            match = re.match(r"Revisión:\s*(.*?\.)(\s|$)", plain(" ".join(paragraph)))
            return (match.group(1) if match else plain(" ".join(paragraph))).rstrip(".")
    return ""


def build(markdown: str, generated_on: date) -> dict[str, bytes]:
    """Every output file as bytes, keyed by path relative to the repository root."""
    tables = extract(markdown)
    files: dict[str, bytes] = {}
    entries = []
    for table in tables:
        path = OUTPUT_DIR / f"{table.spec.slug}.csv"
        data = csv_bytes(table)
        files[path.as_posix()] = data
        entries.append(
            {
                "slug": table.spec.slug,
                "heading": table.section,
                "requirement": table.spec.requirement,
                "csv": path.as_posix(),
                "sheet": table.spec.sheet,
                "columns": table.header,
                "rows": len(table.rows),
                "sha256": sha256_bytes(data),
            }
        )
    xlsx = workbook_bytes(tables, generated_on)
    files[WORKBOOK.as_posix()] = xlsx
    manifest = {
        "schema_version": 1,
        "generator": "scripts/docs/exportar_matrices.py",
        "reproduce": REPRODUCE,
        "check": f"{REPRODUCE} --check",
        "generated_on": generated_on.isoformat(),
        "source": {
            "path": SOURCE.as_posix(),
            "sha256": sha256_bytes(markdown.encode("utf-8")),
            "revision": revision_note(markdown),
            "note": (
                "Las tablas Markdown son el origen editable; CSV y XLSX son copias derivadas "
                "sin datos añadidos. Formato quitado: énfasis, código y destinos de enlaces."
            ),
        },
        "tables": entries,
        "workbook": {
            "path": WORKBOOK.as_posix(),
            "sha256": sha256_bytes(xlsx),
            "openpyxl": OPENPYXL_VERSION,
            "sheets": [entry["sheet"] for entry in entries],
        },
        "scope_notes": [
            "Solo se exportan tablas ya escritas en la matriz; no se inventan filas ni IDs.",
            "La RACI es una propuesta pendiente de validación empresarial (RF-03).",
            "Una correspondencia documentada no acredita identidad de registros entre plataformas.",
        ],
    }
    files[MANIFEST_JSON.as_posix()] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    files[MANIFEST_MD.as_posix()] = manifest_markdown(manifest).encode("utf-8")
    return files


def manifest_markdown(manifest: dict) -> str:
    source = manifest["source"]
    workbook = manifest["workbook"]
    workbook_name = Path(workbook["path"]).name
    lines = [
        "# Matrices exportadas de ECON",
        "",
        f"Generado el {manifest['generated_on']} por `{manifest['generator']}` desde",
        f"[`{source['path']}`](../../{source['path']}) (SHA-256 `{source['sha256']}`).",
        f"Revisión del origen: {source['revision'] or 'no indicada'}.",
        "",
        "Las tablas Markdown siguen siendo el origen editable; estos archivos son copias",
        "derivadas para reutilizar en hojas de cálculo (RNF-02). No añaden filas, IDs ni",
        "valores. Reproducir y verificar:",
        "",
        "```sh",
        manifest["reproduce"],
        manifest["check"],
        "```",
        "",
        f"Libro: [`{workbook_name}`]({workbook_name}) (SHA-256 `{workbook['sha256']}`,",
        f"openpyxl {workbook['openpyxl']}, una hoja por tabla, sin formato decorativo).",
        "",
        "| Tabla | Sección de origen | Requisito | Filas | Columnas | SHA-256 del CSV |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in manifest["tables"]:
        name = Path(entry["csv"]).name
        lines.append(
            f"| [`{name}`]({name}) | {entry['heading']} | {entry['requirement']} | "
            f"{entry['rows']} | {len(entry['columns'])} | `{entry['sha256']}` |"
        )
    lines.extend(["", *(f"- {note}" for note in manifest["scope_notes"]), ""])
    return "\n".join(lines)


def stored_generated_on() -> date | None:
    path = ROOT / MANIFEST_JSON
    if not path.exists():
        return None
    try:
        return date.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["generated_on"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def check(files: dict[str, bytes]) -> int:
    problems = []
    for relative, expected in files.items():
        path = ROOT / relative
        if not path.exists():
            problems.append(f"falta {relative}")
        elif path.read_bytes() != expected:
            problems.append(f"desactualizado {relative}")
    listed = set(files)
    for path in sorted((ROOT / OUTPUT_DIR).glob("*")):
        relative = path.relative_to(ROOT).as_posix()
        if path.is_file() and relative not in listed:
            problems.append(f"no listado en el manifiesto: {relative}")
    if problems:
        print("Matrices exportadas no coinciden con la matriz Markdown:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(f"Regenerar con: {REPRODUCE}", file=sys.stderr)
        return 1
    print(f"Matrices vigentes: {len(files) - 3} CSV, libro XLSX y manifiestos coinciden.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="Compare the checked-in exports; write nothing"
    )
    args = parser.parse_args()
    markdown = (ROOT / SOURCE).read_text(encoding="utf-8")
    today = datetime.now(UTC).date()
    generated_on = (stored_generated_on() or today) if args.check else today
    files = build(markdown, generated_on)
    if args.check:
        return check(files)
    (ROOT / OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    for relative, data in files.items():
        (ROOT / relative).write_bytes(data)
    for path in sorted((ROOT / OUTPUT_DIR).glob("*.csv")):
        if path.relative_to(ROOT).as_posix() not in files:
            path.unlink()
    print(f"Generado: {len(files) - 3} CSV, {WORKBOOK.name}, manifest.json y MANIFEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
