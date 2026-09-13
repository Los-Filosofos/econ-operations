"""Generate publication charts from the supplied, synthetic Prisma examples.

Run from any directory (no application or dependency-lock changes):
    uv run --no-project --with matplotlib python scripts/docs/generar_graficos.py

The extracted sample is checked against its original OpenAPI document before
rendering. The manifest preserves source identifiers, timestamps, JSON pointers,
counts and hashes. Startrack evidence is unavailable in this collection; it is
never encoded as a measured zero.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "apps/api/app/integrations/data/sandbox_samples.json"
OUTPUT = ROOT / "docs/assets/entregables"
BLUE = "#145DA0"
BLUE_LIGHT = "#7593AD"
TEXT = "#182D40"
MUTED = "#526578"
GRID = "#DFE5EA"
PALE = "#F0F4F7"
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
SHORT_MONTHS = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointer_value(document: dict, pointer: str) -> dict:
    result = document
    if not pointer.startswith("#/"):
        raise ValueError(f"Unsupported source pointer: {pointer}")
    for token in pointer[2:].split("/"):
        result = result[token.replace("~1", "/").replace("~0", "~")]
    return result


def verified_data() -> tuple[dict, dict]:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    original_path = ROOT / data["source_document"]
    actual_hash = sha256(original_path)
    if actual_hash != data["source_sha256"]:
        raise ValueError("The supplied OpenAPI document does not match the sample hash")
    original = json.loads(original_path.read_text(encoding="utf-8"))
    for collection in ("equipment", "requests", "projects"):
        sample = data[collection]
        example = pointer_value(original, sample["source_reference"])
        originals = {item["id"]: item for item in example["items"]}
        if len(originals) != len(example["items"]):
            raise ValueError(f"Duplicate source IDs in {collection}")
        if len({item["id"] for item in sample["items"]}) != len(sample["items"]):
            raise ValueError(f"Duplicate sample IDs in {collection}")
        if set(originals) != {item["id"] for item in sample["items"]}:
            raise ValueError(
                f"The extracted IDs differ from the example in {collection}"
            )
        for item in sample["items"]:
            for key, value in item.items():
                if (
                    key not in originals[item["id"]]
                    or originals[item["id"]][key] != value
                ):
                    raise ValueError(
                        f"Field differs from source: {collection}/{item['id']}/{key}"
                    )
        for sample_key, source_key in (
            ("reported_total", "total"),
            ("page", "page"),
            ("limit", "limit"),
        ):
            if sample[sample_key] != example.get(source_key):
                raise ValueError(
                    f"Pagination differs from source in {collection}: {sample_key}"
                )
        if (
            sample["reported_total"] is not None
            and len(sample["items"]) > sample["reported_total"]
        ):
            raise ValueError(f"Sample count exceeds its reported total: {collection}")
    if any("startrack" in path.lower() for path in original["paths"]):
        raise ValueError(
            "Review the coverage visual: the source now includes Startrack paths"
        )
    if any(
        key in data for key in ("startrack", "tasks", "locations", "receipts", "visits")
    ):
        raise ValueError(
            "Review the coverage visual: operational samples may now be supplied"
        )
    if data["observed_at"] is not None:
        raise ValueError(
            "Review the time disclaimer: the sample now has an observation instant"
        )
    return data, {
        "sample_file": SAMPLE.relative_to(ROOT).as_posix(),
        "sample_sha256": sha256(SAMPLE),
        "source_document": original_path.relative_to(ROOT).as_posix(),
        "source_sha256": actual_hash,
        "evidence_kind": data["evidence_kind"],
        "environment": "sandbox",
        "synthetic": True,
        "documented_on": data["documented_on"],
        "observed_at": data["observed_at"],
        "verified_against_original": True,
    }


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 13,
            "text.color": TEXT,
            "axes.labelcolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": TEXT,
            "axes.edgecolor": GRID,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
            "svg.hashsalt": "econ-provided-sample-charts-v1",
        }
    )


def frame(title: str, subtitle: str):
    fig = plt.figure(figsize=(11.69, 7.65))
    fig.text(
        0.06, 0.942, "ECON · DATOS SINTÉTICOS PROPORCIONADOS", fontsize=10, color=MUTED
    )
    fig.text(0.06, 0.875, title, fontsize=23, fontweight="bold")
    fig.text(0.06, 0.82, subtitle, fontsize=13, color=MUTED)
    return fig


def footer(fig, data: dict, notes: list[str]) -> None:
    documented = date.fromisoformat(data["documented_on"]).strftime("%d/%m/%Y")
    fig.add_artist(plt.Line2D([0.06, 0.94], [0.226, 0.226], color=GRID, linewidth=0.8))
    for index, note in enumerate(notes):
        fig.text(0.06, 0.19 - index * 0.035, note, fontsize=11, color=MUTED)
    fig.text(
        0.06,
        0.069,
        f"Fuente: {data['source_document']} · Ejemplos de respuesta de Prisma.",
        fontsize=10,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.035,
        f"Fecha documental: {documented} · Sin corte de observación conjunto · IDs y hashes en manifest.json.",
        fontsize=10,
        color=MUTED,
    )


def save(fig, stem: str) -> list[dict]:
    result = []
    for extension in ("png", "svg"):
        path = OUTPUT / f"{stem}.{extension}"
        options = {"dpi": 300} if extension == "png" else {"metadata": {"Date": None}}
        fig.savefig(path, **options)
        result.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
                "format": extension,
                "dpi": 300 if extension == "png" else None,
            }
        )
    plt.close(fig)
    return result


def period_label(start: date, end: date) -> str:
    days = (end - start).days + 1
    if start.year == end.year and start.month == end.month:
        return f"{start.day}–{end.day} {SHORT_MONTHS[start.month - 1]} · {days} días"
    return f"{start:%d/%m}–{end:%d/%m} · {days} días"


def periods(data: dict) -> dict:
    items = sorted(
        data["requests"]["items"], key=lambda item: (item["fecha_inicio"], item["id"])
    )
    project_ids = {item["project_id"] for item in items}
    project_by_id = {item["id"]: item for item in data["projects"]["items"]}
    if len(project_ids) != 1 or not project_ids <= project_by_id.keys():
        raise ValueError("Review the project subtitle for the supplied requests")
    project = project_by_id[next(iter(project_ids))]
    fig = frame("Períodos de uso solicitados", project["name"].replace(" - ", " · "))
    ax = fig.add_axes((0.30, 0.37, 0.64, 0.37))
    rows = []
    labels = []
    for index, item in enumerate(items):
        start = date.fromisoformat(item["fecha_inicio"])
        end = date.fromisoformat(item["fecha_fin"])
        if end < start:
            raise ValueError(f"Invalid usage interval: {item['id']}")
        inclusive_days = (end - start).days + 1
        assigned = (
            item["maquinaria_no_activo"]
            if item["maquinaria_id"]
            else "Sin unidad asignada"
        )
        if item["maquinaria_id"]:
            equipment = next(
                e
                for e in data["equipment"]["items"]
                if e["id"] == item["maquinaria_id"]
            )
            if equipment["no_activo"] != assigned:
                raise ValueError(
                    "Assigned equipment identity does not match its exact source ID"
                )
        labels.append(f"{item['status']}\n{assigned}\n{item['tipo']}")
        color = BLUE if item["status"] == "APROBADA" else BLUE_LIGHT
        ax.barh(
            index, inclusive_days, left=mdates.date2num(start), height=0.47, color=color
        )
        ax.text(
            mdates.date2num(start) + inclusive_days / 2,
            index,
            period_label(start, end),
            va="center",
            ha="center",
            color="white",
            fontweight="bold",
            fontsize=13,
        )
        rows.append(
            {
                "source_id": item["id"],
                "project_id": item["project_id"],
                "status": item["status"],
                "equipment_source_id": item["maquinaria_id"],
                "asset_number": item["maquinaria_no_activo"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "inclusive_days": inclusive_days,
                "source_timestamps": {
                    key: value for key, value in item.items() if key.endswith("_at")
                },
            }
        )
    first = min(date.fromisoformat(item["fecha_inicio"]) for item in items)
    last = max(date.fromisoformat(item["fecha_fin"]) for item in items)
    ticks = [
        first + timedelta(days=offset) for offset in range((last - first).days + 1)
    ]
    ax.set_xticks(
        [mdates.date2num(day) + 0.5 for day in ticks], [str(day.day) for day in ticks]
    )
    ax.set_xlim(mdates.date2num(first), mdates.date2num(last + timedelta(days=1)))
    ax.set_yticks(range(len(items)), labels)
    ax.set_ylim(len(items) - 0.45, -0.55)
    ax.set_xlabel(
        f"{MONTHS[first.month - 1].capitalize()} de {first.year}", labelpad=14
    )
    ax.tick_params(axis="both", length=0, pad=12)
    for side in ("top", "left", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    footer(
        fig,
        data,
        [
            f"{len(items)} solicitudes incluidas de {data['requests']['reported_total']} reportadas en el ejemplo.",
            "Intervalos de uso con días inclusivos. No representan compromiso de entrega, traslado ni recepción.",
            "Los estados son los del documento; no se infieren atrasos a partir de la fecha actual.",
        ],
    )
    return {
        "id": "periodos-uso",
        "visual": "horizontal_usage_intervals",
        "source_reference": data["requests"]["source_reference"],
        "rows": rows,
        "definition": "End date is drawn through the end of that calendar day; inclusive duration is end minus start plus one.",
        "files": save(fig, "grafico-periodos-uso"),
    }


def administrative_states(data: dict) -> dict:
    items = data["equipment"]["items"]
    counts = Counter(item["estado"] for item in items)
    states = sorted(counts, key=lambda value: (-counts[value], value))
    total = data["equipment"]["reported_total"]
    fig = frame(
        "Estado administrativo de los equipos",
        f"{len(items)} registros incluidos de {total} equipos reportados en el ejemplo de Prisma.",
    )
    ax = fig.add_axes((0.24, 0.37, 0.68, 0.37))
    values = [counts[state] for state in states]
    ax.barh(states, values, color=BLUE, height=0.45)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) + 0.55)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Equipos incluidos en la muestra", labelpad=14)
    ax.tick_params(axis="both", length=0, pad=12)
    for index, count in enumerate(values):
        ax.text(
            count + 0.12,
            index,
            str(count),
            va="center",
            fontsize=20,
            fontweight="bold",
            color=BLUE,
        )
    for side in ("top", "left", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    footer(
        fig,
        data,
        [
            "Cobertura parcial: la distribución describe únicamente los registros incluidos, no toda la flota.",
            "DISPONIBLE es un estado administrativo; no acredita disponibilidad física ni aptitud técnica.",
            "OBSOLETA no equivale a avería. Los estados de mantenimiento deben leerse por separado.",
        ],
    )
    return {
        "id": "estados-administrativos",
        "visual": "horizontal_count_bars_zero_baseline",
        "source_reference": data["equipment"]["source_reference"],
        "included_count": len(items),
        "reported_total": total,
        "counts": {state: counts[state] for state in states},
        "rows": [
            {
                "source_id": item["id"],
                "asset_number": item["no_activo"],
                "administrative_state": item["estado"],
                "project_id": item["project_id"],
                "active_failure_id": item["active_failure_id"],
                "active_failure_status": item["active_failure_status"],
                "active_failure_is_paro": item["active_failure_is_paro"],
                "source_timestamps": {
                    key: value for key, value in item.items() if key.endswith("_at")
                },
            }
            for item in items
        ],
        "files": save(fig, "grafico-estados-administrativos"),
    }


def coverage(data: dict) -> dict:
    equipment_count = len(data["equipment"]["items"])
    equipment_total = data["equipment"]["reported_total"]
    request_count = len(data["requests"]["items"])
    request_total = data["requests"]["reported_total"]
    fig = frame(
        "Cobertura de la evidencia proporcionada",
        "El alcance corresponde al archivo de ejemplos; no a una lectura actual de los proveedores.",
    )
    ax = fig.add_axes((0.06, 0.32, 0.88, 0.44))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    widths = [0.02, 0.28, 0.49, 0.70]
    headings = ["Fuente / conjunto", "Incluidos / total", "Lectura", "Límite"]
    ax.add_patch(plt.Rectangle((0, 0.82), 1, 0.18, facecolor=PALE, edgecolor="none"))
    for x, text in zip(widths, headings):
        ax.text(x, 0.91, text, fontsize=12, fontweight="bold", va="center")
    rows = [
        [
            "Prisma\nEquipos",
            f"{equipment_count} / {equipment_total}",
            "Cobertura parcial",
            f"{equipment_total - equipment_count} registros no\nincluidos en el ejemplo",
        ],
        [
            "Prisma\nSolicitudes",
            f"{request_count} / {request_total}",
            "Total reportado\nen el ejemplo",
            "No acredita el\nuniverso operativo",
        ],
        [
            "Startrack\nEvidencia operativa",
            "Sin muestras",
            "No evaluable",
            "Sin tareas, posiciones\nni recepciones\nen este conjunto",
        ],
    ]
    for index, row in enumerate(rows):
        center = 0.69 - index * 0.275
        for x, text in zip(widths, row):
            ax.text(
                x,
                center,
                text,
                fontsize=12.5,
                va="center",
                color=BLUE if x == widths[1] else TEXT,
                fontweight="bold" if x == widths[1] else "normal",
                linespacing=1.45,
            )
        ax.axhline(center - 0.137, color=GRID, linewidth=0.8)
    footer(
        fig,
        data,
        [
            "Ausencia de muestra operativa significa falta de evidencia; no equivale a cero operaciones.",
            "Los totales son los declarados por los ejemplos de respuesta, sin extrapolación a toda ECON.",
            "Con este conjunto no se calculan puntualidad, utilización, productividad ni recepción efectiva.",
        ],
    )
    return {
        "id": "cobertura",
        "visual": "coverage_table",
        "selection_reason": "A table separates available counts from missing operational evidence without implying that missing Startrack data is a measured zero.",
        "rows": [
            {
                "provider": "Prisma",
                "collection": name,
                "included_count": len(data[name]["items"]),
                "reported_total": data[name]["reported_total"],
                "page": data[name]["page"],
                "limit": data[name]["limit"],
                "source_reference": data[name]["source_reference"],
                "scope": "provided_document_example",
            }
            for name in ("equipment", "requests")
        ]
        + [
            {
                "provider": "Startrack",
                "collection": "operational_evidence",
                "included_count": None,
                "reported_total": None,
                "availability": "not_supplied_in_this_dataset",
                "measurement": None,
            }
        ],
        "files": save(fig, "grafico-cobertura"),
    }


def main() -> None:
    data, provenance = verified_data()
    configure()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    charts = [periods(data), administrative_states(data), coverage(data)]
    manifest = {
        "schema_version": 1,
        "generator": Path(__file__).relative_to(ROOT).as_posix(),
        "generator_sha256": sha256(Path(__file__)),
        "reproduce": "uv run --no-project --with matplotlib python scripts/docs/generar_graficos.py",
        "rendering": {
            "matplotlib": matplotlib.__version__,
            "figure_inches": [11.69, 7.65],
            "png_dpi": 300,
            "svg_text": True,
        },
        "provenance": provenance,
        "scope_notes": [
            "Only supplied synthetic Prisma examples are counted; no new operational records are generated.",
            "PROY-014 and CF-03 remain the source identities; they are not mapped to the kit assignment RE-03/MOT-006/PROY-006.",
            "Equipment administrative state, maintenance, transfer state, location and receipt are separate facts.",
            "The documentation date is not a shared observation instant, so no lateness metric is derived.",
        ],
        "charts": charts,
    }
    destination = OUTPUT / "manifest.json"
    destination.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Verified OpenAPI SHA-256: {provenance['source_sha256']}")
    for chart in charts:
        for artifact in chart["files"]:
            print(artifact["path"])
    print(destination.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
