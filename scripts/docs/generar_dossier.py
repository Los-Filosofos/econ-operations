"""Generate ECON diagrams and two reviewed documentary PDFs, without provider calls.

uv run --no-project --with matplotlib --with reportlab --with pypdf \
    --with markdown-it-py python scripts/docs/generar_dossier.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from itertools import pairwise
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from markdown_it import MarkdownIt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/assets/entregables"
OUT = ROOT / "output/pdf"
QA = ROOT / "tmp/pdfs/entregables"
BLUE = "#164f7c"
INK = "#243746"
MUTED = "#556674"
PALE = "#eef4f7"
LINE = "#cedae3"
MD = MarkdownIt("commonmark").enable("table")
matplotlib.use("Agg")


def diagram_canvas():
    fig, ax = plt.subplots(figsize=(13.4, 6.2), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0, 100), ylim=(0, 60))
    ax.axis("off")
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.025, top=0.98)
    return fig, ax


def box(ax, x, y, w, h, title, body="", *, proposed=False):
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=PALE,
            edgecolor=BLUE,
            linewidth=1.2,
            linestyle="--" if proposed else "-",
        )
    )
    ax.text(
        x + w / 2,
        y + h * (0.70 if body else 0.5),
        title,
        ha="center",
        va="center",
        color=BLUE,
        fontsize=13,
        weight="bold",
        linespacing=1.3,
    )
    if body:
        ax.text(
            x + w / 2,
            y + h * 0.29,
            body,
            ha="center",
            va="center",
            color=INK,
            fontsize=11.5,
            linespacing=1.3,
        )


def arrow(ax, start, end, *, via=None, dashed=False):
    points = [start, *(via or []), end]
    for a, b in pairwise(points[:-1]):
        ax.plot(
            [a[0], b[0]],
            [a[1], b[1]],
            color=MUTED,
            linewidth=1.25,
            linestyle="--" if dashed else "-",
            zorder=0,
        )
    ax.add_patch(
        FancyArrowPatch(
            points[-2],
            points[-1],
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.25,
            color=MUTED,
            linestyle="--" if dashed else "-",
            zorder=0,
        )
    )


def label(ax, x, y, text):
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=11.5,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 2.5},
    )


def save_diagram(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(ASSETS / f"diagrama-{name}.{ext}", dpi=220, facecolor="white")
    plt.close(fig)


def diagrams():
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig, ax = diagram_canvas()
    xs = [1, 18, 35, 52, 69, 86]
    titles = ["Proyecto", "Solicitud", "Asignación", "Movimiento", "Tarea", "Recepción"]
    bodies = [
        "Necesidad\ny período",
        "Tipo de\nmaquinaria",
        "Aprobación\ny unidad",
        "Plan y envío\ncontrolado",
        "Traslado en\nStartrack",
        "Persona\ny constancia",
    ]
    for x, title, body in zip(xs, titles, bodies):
        box(ax, x, 29, 13, 16, title, body)
    for x in xs[:-1]:
        arrow(ax, (x + 13, 37), (x + 17, 37))
    label(ax, 24, 52, "PRISMA / NEXUS")
    label(ax, 58.5, 52, "ECON")
    label(ax, 75.5, 52, "STARTRACK")
    label(ax, 92.5, 52, "PROYECTO")
    box(ax, 27, 4, 29, 13, "Mantenimiento", "Restricción y liberación")
    arrow(ax, (41.5, 17), (41.5, 29), dashed=True)
    box(
        ax,
        68,
        4,
        31,
        13,
        "Evidencia GPS",
        "Activo y fecha válidos\nNo acredita recepción",
    )
    arrow(ax, (92.5, 17), (92.5, 29), dashed=True)
    label(ax, 14, 10, "Síntesis del proceso\nNo transcripción exhaustiva")
    save_diagram(fig, "proceso")

    fig, ax = diagram_canvas()
    label(ax, 15, 56, "PRISMA: ID ORIGINAL")
    label(ax, 50, 56, "ECON: CORRESPONDENCIA")
    label(ax, 85, 56, "STARTRACK: ID ORIGINAL")
    rows = [
        (
            40,
            "Proyecto",
            "UUID de proyecto",
            "Destino revisado",
            "No deducir por ciudad",
            "Geocerca",
            "poi_id",
        ),
        (
            27,
            "Solicitud",
            "UUID de solicitud",
            "Uno o varios movimientos",
            "Referencia por movimiento",
            "Tarea confirmada",
            "job_id",
        ),
        (
            14,
            "Maquinaria",
            "UUID de unidad",
            "Activo observado",
            "Máquina o transportador",
            "Vehículo GPS",
            "vehicle_id",
        ),
        (
            1,
            "Operador",
            "UUID de operador",
            "Persona revisada",
            "Roles e IDs distintos",
            "Usuarios asignables",
            "assigned_user_ids",
        ),
    ]
    for y, a, ab, b, bb, c, cb in rows:
        box(ax, 1, y, 28, 11, a, ab)
        box(ax, 36, y, 28, 11, b, bb)
        box(ax, 71, y, 28, 11, c, cb)
        arrow(ax, (29, y + 5.5), (36, y + 5.5))
        arrow(ax, (64, y + 5.5), (71, y + 5.5))
    save_diagram(fig, "identidad")

    fig, ax = diagram_canvas()
    box(ax, 1, 44, 19, 11, "Dash", "Interfaz y gráficos")
    box(ax, 1, 26, 19, 11, "FastAPI", "Contrato HTTP")
    box(ax, 1, 8, 19, 11, "CLI", "Ciclos explícitos")
    box(
        ax,
        29,
        23,
        23,
        17,
        "Servicios Python",
        "Consulta y operación\nReglas compartidas",
    )
    for y in (49.5, 31.5, 13.5):
        arrow(ax, (20, y), (29, 31.5), via=[(24, y), (24, 31.5)])
    box(ax, 61, 44, 18, 11, "SDK Prisma", "Lecturas")
    box(ax, 83, 44, 16, 11, "Prisma", "Sandbox")
    box(ax, 61, 26, 18, 11, "SDK Startrack", "Tareas / visitas")
    box(ax, 83, 26, 16, 11, "Startrack", "Sandbox")
    box(ax, 61, 8, 18, 11, "Ledger", "Eventos y cola")
    box(ax, 83, 8, 16, 11, "PostgreSQL", "Persistencia")
    for y in (49.5, 31.5, 13.5):
        arrow(ax, (52, 31.5), (61, y), via=[(56, 31.5), (56, y)])
        arrow(ax, (79, y), (83, y))
    label(
        ax,
        50,
        2.5,
        "Conectores implementados; validación autenticada de creación Startrack pendiente",
    )
    save_diagram(fig, "actual")

    fig, ax = diagram_canvas()
    box(
        ax,
        1,
        43,
        25,
        12,
        "Prisma",
        "Cambios por consulta\nWebhook por confirmar",
        proposed=True,
    )
    box(
        ax,
        1,
        22,
        25,
        12,
        "Startrack",
        "Consultas + eventos\nsegún contrato habilitado",
        proposed=True,
    )
    box(
        ax,
        36,
        32,
        27,
        17,
        "Registro de eventos",
        "Validar ID, entorno y fecha\nControlar duplicados",
        proposed=True,
    )
    arrow(ax, (26, 49), (36, 40.5), via=[(31, 49), (31, 40.5)])
    arrow(ax, (26, 28), (36, 40.5), via=[(31, 28), (31, 40.5)])
    box(
        ax,
        73,
        32,
        26,
        17,
        "Comparación",
        "Plan guardado + cambios\nReglas por entidad",
        proposed=True,
    )
    arrow(ax, (63, 40.5), (73, 40.5))
    box(
        ax,
        73,
        3,
        26,
        16,
        "Seguimiento",
        "Actualizar evidencia\no abrir incidencia",
        proposed=True,
    )
    arrow(ax, (86, 32), (86, 19))
    box(
        ax,
        36,
        3,
        27,
        16,
        "Decisión humana",
        "Responsable, constancia\ny resolución",
        proposed=True,
    )
    arrow(ax, (73, 11), (63, 11))
    label(ax, 13.5, 9, "PROPUESTA\nSincronización + conciliación")
    save_diagram(fig, "sincronizacion")

    fig, ax = diagram_canvas()
    box(ax, 1, 38, 18, 15, "Proveedores", "Prisma / Startrack", proposed=True)
    box(ax, 26, 38, 20, 15, "Ingreso de eventos", "FastAPI con réplicas", proposed=True)
    box(ax, 53, 38, 20, 15, "Kafka", "Eventos duraderos", proposed=True)
    box(ax, 80, 38, 19, 15, "Trabajadores", "Paralelos por entidad", proposed=True)
    for start, end in ((19, 26), (46, 53), (73, 80)):
        arrow(ax, (start, 45.5), (end, 45.5))
    box(
        ax,
        1,
        4,
        26,
        17,
        "Histórico y archivo",
        "ClickHouse + objetos\nConsumidores separados",
        proposed=True,
    )
    box(
        ax,
        38,
        4,
        25,
        17,
        "Dash + API de lectura",
        "Estado actual\ny agregados",
        proposed=True,
    )
    box(
        ax,
        74,
        4,
        25,
        17,
        "PostgreSQL",
        "Operación, incidencias\ny estado actual",
        proposed=True,
    )
    arrow(ax, (89.5, 38), (86.5, 21), via=[(89.5, 28), (86.5, 28)])
    arrow(ax, (63, 38), (14, 21), via=[(63, 29), (14, 29)])
    arrow(ax, (27, 12.5), (38, 12.5))
    arrow(ax, (74, 12.5), (63, 12.5))
    label(ax, 50, 57.5, "ARQUITECTURA OBJETIVO - NO DESPLEGADA NI VALIDADA EN CARGA")
    save_diagram(fig, "escala")

    fig, ax = diagram_canvas()
    label(ax, 15.5, 57.5, "PRISMA / NEXUS: administración")
    label(ax, 50, 57.5, "ECON: envío, evidencia y recepción declarada")
    label(ax, 84.5, 57.5, "STARTRACK: tarea y ubicación observada")
    columns = {
        "prisma": (
            ("Solicitud", "status: PENDIENTE, APROBADA,\nRECHAZADA · approved_at"),
            ("Asignación", "maquinaria_id de la solicitud;\nproject_id y vigencia del equipo"),
            (
                "Maquinaria y mantenimiento",
                "estado: DISPONIBLE, OCUPADA, OBSOLETA\nactive_failure_status / is_paro",
            ),
        ),
        "econ": (
            ("Envío del movimiento", "state: draft, blocked, queued,\nsending, sent, unknown, failed"),
            (
                "Evidencia y actor",
                "task_state y arrival con event_time,\nobserved_at, recorded_at; actor_*",
            ),
            ("Recepción declarada", "receiver, received_at, reference\ndeclared_by_* (sesión); nunca por GPS"),
        ),
        "startrack": (
            ("Tarea", "status (ID) + workflow_role\n0 pendiente, 1 completada, 2 cancelada"),
            ("Ubicación observada", "visita a POI del vehículo rastreado:\nvehicle_id, start_date, end_date"),
            ("Vehículo rastreado", "puede ser el transportador;\nno es la máquina"),
        ),
    }
    xs = {"prisma": 1, "econ": 36, "startrack": 71}
    for key, rows in columns.items():
        for y, (title, body) in zip((41, 27, 13), rows):
            box(ax, xs[key], y, 28, 11, title, body)
    # Prisma is only read: the request feeds the movement; assignment and
    # administrative state are evidence.
    arrow(ax, (29, 46.5), (36, 46.5))
    label(ax, 32.5, 49.5, "GET")
    arrow(ax, (29, 32.5), (36, 32.5))
    label(ax, 32.5, 35.5, "GET")
    arrow(ax, (29, 18.5), (36, 29.5), via=[(32.5, 18.5), (32.5, 29.5)])
    label(ax, 32.5, 23.5, "GET")
    # Startrack receives one POST and is read back as evidence; nothing feeds
    # the declared receipt.
    arrow(ax, (64, 46.5), (71, 46.5))
    label(ax, 67.5, 50, "único\nPOST")
    arrow(ax, (71, 43), (64, 35.5), via=[(67.5, 43), (67.5, 35.5)])
    label(ax, 67.5, 39.5, "GET")
    arrow(ax, (71, 30.5), (64, 30.5))
    label(ax, 67.5, 28, "GET")
    label(
        ax,
        50,
        4,
        "ECON no escribe en Prisma. Ningún estado se traduce a otro: ubicación observada"
        " no es recepción; tarea completada no es máquina disponible.",
    )
    save_diagram(fig, "estados")


def register_fonts():
    for name, weight in (("Econ", "normal"), ("Econ-Bold", "bold")):
        path = font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight=weight)
        )
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily(
        "Econ", normal="Econ", bold="Econ-Bold", italic="Econ", boldItalic="Econ-Bold"
    )


STYLES = {}


def init_styles():
    for name, size, leading, font, color in (
        ("title", 24, 29, "Econ-Bold", BLUE),
        ("body", 10.2, 14.5, "Econ", INK),
        ("small", 8.6, 12, "Econ", MUTED),
        ("cell", 9.2, 12.5, "Econ", INK),
        ("head", 9.2, 12.5, "Econ-Bold", BLUE),
    ):
        STYLES[name] = ParagraphStyle(
            name,
            fontName=font,
            fontSize=size,
            leading=leading,
            textColor=colors.HexColor(color),
            spaceAfter=8 if name in {"body", "small"} else 14 if name == "title" else 0,
        )


def markup(text):
    text = html.escape(
        text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")
    )
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    return text


def para(text, style="body"):
    return Paragraph(markup(text), STYLES[style])


def tab(rows, widths, *, padding=7):
    data = [
        [para(str(v), "head" if i == 0 else "cell") for v in row]
        for i, row in enumerate(rows)
    ]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PALE)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(BLUE)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor(LINE)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ]
        )
    )
    return result


def foot(canvas, doc):
    w, _h = doc.pagesize
    canvas.setStrokeColor(colors.HexColor(LINE))
    canvas.line(38, 31, w - 38, 31)
    canvas.setFont("Econ", 7.5)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(
        38, 18, "ECON | Prisma + Startrack | Datos sintéticos | 13/09/2026"
    )
    canvas.drawRightString(w - 38, 18, str(doc.page))


def doc(path, pagesize):
    return SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        rightMargin=38,
        leftMargin=38,
        topMargin=34,
        bottomMargin=42,
        title=path.stem.replace("-", " "),
        author="Equipo ECON - Los Filósofos",
    )


def img(name, max_height=340):
    from PIL import Image as PILImage

    path = ASSETS / name
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min((landscape(A4)[0] - 76) / w, max_height / h)
    return Image(str(path), width=w * scale, height=h * scale, hAlign="CENTER")


def visual_page(story, title, subtitle, filename, takeaway, source, *, height=330):
    if story:
        story.append(PageBreak())
    story.extend(
        [
            para(title, "title"),
            para(subtitle),
            img(filename, height),
            Spacer(1, 8),
            para(takeaway),
            para(source, "small"),
        ]
    )


def build_dossier():
    width = landscape(A4)[0] - 76
    story = [
        para("ECON: gráficos, procesos y arquitectura", "title"),
        para(
            "Entrega visual del reto | Prisma / Nexus + Startrack | 13 de septiembre de 2026"
        ),
        Spacer(1, 12),
        para(
            "**La decisión:** relacionar solicitud, máquina, traslado y recepción con evidencia trazable. La portada de Gerencia debe mostrar qué requiere atención y qué acción permite cada dato."
        ),
        para(
            "**Tres niveles de evidencia:** los gráficos describen las muestras del archivo; los diagramas operativos sintetizan el kit; las arquitecturas distinguen código existente de ampliaciones propuestas."
        ),
        tab(
            [
                ["Contenido", "Dónde revisarlo"],
                [
                    "Requisitos y responsabilidades",
                    "Páginas 2-4: RF/RNF, alcance y RACI propuesta",
                ],
                [
                    "Gráficos de los datos suministrados",
                    "Páginas 5-7: uso solicitado, estados y cobertura",
                ],
                [
                    "Procesos y diagramas técnicos",
                    "Páginas 8-13: flujo, identidad, implementación, dónde vive cada estado, sincronización y escala",
                ],
                [
                    "Estados, indicador y pendientes",
                    "Páginas 14-16: interpretación de casos, ficha RF-06 y recorrido de revisión",
                ],
            ],
            [width * 0.40, width * 0.60],
        ),
        Spacer(1, 14),
        para(
            "No hay tareas, GPS ni recepciones en la muestra operativa del archivo. Los diagramas no rellenan esa ausencia. RF-04 y RF-05 conservan su brecha de demostración combinada.",
            "small",
        ),
    ]

    story += [
        PageBreak(),
        para("Qué pide el reto: requisitos funcionales", "title"),
        para(
            "Síntesis del brief, sección 7. La matriz Markdown conserva la redacción original y la evidencia por requisito."
        ),
        tab(
            [
                ["Código", "Entregable", "Evidencia y límite"],
                [
                    "RF-01",
                    "Inventario de campos nuevos",
                    "Inventario reproducible de campos públicos e internos, con tipos, ejemplos y procedencia; generado desde los modelos y verificado en CI (generar_diccionario.py --check). El código fija el tipo; la interpretación se documenta.",
                ],
                [
                    "RF-02",
                    "Matriz de correspondencias",
                    "Matriz completa del formulario de tarea y campos relevantes: directos, transformados, manuales y sin equivalente.",
                ],
                [
                    "RF-03",
                    "Responsabilidades",
                    "RACI propuesta para las tres gerencias; no está aprobada como política empresarial.",
                ],
                [
                    "RF-04",
                    "Consulta unificada de estado y ubicación",
                    "Interfaz y conectores implementados. Falta acreditar una tarea/GPS vinculados al caso con datos disponibles.",
                ],
                [
                    "RF-05",
                    "Diferencia de estados y su resolución",
                    "Caso documental Ocupada/Completada explicado. No se presenta como observación integrada de la muestra.",
                ],
                [
                    "RF-06",
                    "Indicador operativo documentado",
                    "Ficha de tiempo fuera de geocerca sin justificación. Definición disponible; valor no evaluable con la muestra.",
                ],
            ],
            [62, 212, width - 274],
        ),
        Spacer(1, 10),
        para(
            "Fuente: docs/onedrive/02-brief-del-reto.md, sección 7. Trazabilidad completa: docs/matriz-requisitos-entregables.md.",
            "small",
        ),
    ]

    story += [
        PageBreak(),
        para("Condiciones y formato de entrega", "title"),
        tab(
            [
                ["Código", "Condición", "Aplicación"],
                [
                    "RNF-01",
                    "Solo sandbox / datos suministrados",
                    "Se conservan las muestras; no hay lecturas ni escrituras a proveedores durante la generación.",
                ],
                [
                    "RNF-02",
                    "Matrices legibles y reutilizables",
                    "Tablas Markdown exportadas a CSV y XLSX (output/matrices, con manifiesto y verificación en CI) y PDFs. Figuras PNG para consulta y SVG editables para reutilización.",
                ],
                [
                    "RNF-03",
                    "Prototipo navegable",
                    "Dash con solicitudes, operaciones y fuentes; verificar el recorrido y los límites de evidencia.",
                ],
                [
                    "RNF-04",
                    "README de entrega",
                    "Índice de documentos vigentes y guía de ejecución en el repositorio.",
                ],
            ],
            [62, 235, width - 297],
        ),
        Spacer(1, 18),
        para(
            "**Sección 9:** matrices de mapeo y responsabilidades, diagrama de arquitectura y decisiones técnicas en PDF. Las decisiones técnicas tienen máximo dos páginas; se entregan también como archivo independiente."
        ),
        para(
            "La presentación final tiene máximo diez diapositivas e incluye reflexión de aprendizaje. Este dossier es documentación visual, no una presentación terminada."
        ),
        para(
            "El brief contiene comentarios editoriales que matizan algunos entregables; la matriz registra esa ambigüedad sin tratar los comentarios como reemplazo automático del cuerpo.",
            "small",
        ),
    ]

    raci_source = (ROOT / "docs/equivalencias-prisma-startrack.md").read_text(
        encoding="utf-8"
    )
    section = raci_source.split("## Responsabilidades propuestas para confirmar", 1)[
        1
    ].split("## Lagunas", 1)[0]
    rows = [
        [v.strip() for v in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+$", line)
    ]
    story += [
        PageBreak(),
        para("Quién actúa y quién responde", "title"),
        para(
            "RACI propuesta, derivada del TO-BE y el manual. R realiza; A aprueba o responde; C se consulta; I se informa. Debe validarse con ECON."
        ),
        tab(rows, [width * v for v in [0.34, 0.17, 0.17, 0.17, 0.15]], padding=4),
        Spacer(1, 4),
        para(
            "Técnica de Proyectos figura como funciones de proyecto. Roles y permisos de sesión implementados (ADR 0005); el actor autenticado queda vinculado a planes, cola y recepción desde la migración 0004; la RACI empresarial sigue pendiente de validación. Fuente: matriz de equivalencias, sección de responsabilidades.",
            "small",
        ),
    ]

    visual_page(
        story,
        "Cuándo se requiere maquinaria",
        "Planificación de las dos solicitudes suministradas de PROY-014.",
        "grafico-periodos-uso.png",
        "La solicitud aprobada tiene CF-03 asignada; la pendiente todavía requiere resolver la asignación. El intervalo representa uso solicitado, no compromiso de entrega.",
        "Fuente: ejemplos del OpenAPI Prisma; manifiesto con IDs y huellas en docs/assets/entregables/manifest.json.",
        height=340,
    )
    visual_page(
        story,
        "Qué estados administrativos aparecen",
        "Distribución de los cinco equipos incluidos en el archivo.",
        "grafico-estados-administrativos.png",
        "CF-03 figura OBSOLETA y requiere revisar su asignación. La etiqueta no permite deducir una avería; DISPONIBLE tampoco certifica capacidad física para cualquier trabajo.",
        "Fuente: campo estado del listado proporcionado. Son 5 registros de un total declarado de 15.",
        height=340,
    )
    visual_page(
        story,
        "Qué cobertura sostiene la consulta",
        "El archivo de muestras conserva cantidades y ausencias por fuente.",
        "grafico-cobertura.png",
        "Las dos solicitudes están incluidas respecto del total del ejemplo. Esa cobertura no completa la integración: faltan muestras operativas de tareas y GPS Startrack.",
        "La fecha documental no equivale a un corte conjunto ni a una lectura actual del sandbox.",
        height=340,
    )

    visual_page(
        story,
        "Del proyecto a la recepción",
        "Síntesis propia del proceso documentado; alcance centrado en maquinaria.",
        "diagrama-proceso.png",
        "El TO-BE propone que una solicitud aprobada viaje como tarea. ECON exige correspondencias y programación antes del envío. El proyecto declara la recepción con constancia.",
        "Fuentes: docs/onedrive/03-as-is.md, 03-to-be.md y 04-casos-de-uso.md. Los originales mantienen fases y actores fuera de esta síntesis.",
    )
    visual_page(
        story,
        "Cómo se relacionan los registros",
        "Modelo conceptual de correspondencias; no es un esquema físico de base de datos.",
        "diagrama-identidad.png",
        "No se unen nombres. Una solicitud puede requerir varios movimientos; cada movimiento conserva su referencia y un ID de tarea confirmado cuando existe. El GPS puede pertenecer al transportador.",
        "Fuente: docs/equivalencias-prisma-startrack.md. Un maestro de correspondencias con vigencia histórica sigue propuesto.",
    )
    visual_page(
        story,
        "Qué está implementado hoy",
        "Dash y FastAPI comparten reglas; CLI ejecuta sincronización explícita.",
        "diagrama-actual.png",
        "El registro conserva movimientos, eventos, cortes y recepción en PostgreSQL, única infraestructura de estado (ADR 0006): cola, bloqueos e historial append-only. Las habilitaciones live permanecen separadas. La aceptación autenticada de creación Startrack todavía debe validarse.",
        "Fuentes: apps/api/README.md, docs/solucion-integracion.md, ADR 0004 y ADR 0006. Código implementado no equivale a validación productiva.",
    )
    visual_page(
        story,
        "Dónde vive cada estado",
        "Cada estado pertenece a una plataforma; ECON conserva los suyos y no traduce ni iguala los ajenos.",
        "diagrama-estados.png",
        "Prisma guarda solicitud, asignación (maquinaria_id, project_id y vigencia), maquinaria y mantenimiento; ECON guarda el envío del movimiento, la recepción declarada y el actor de cada transición; Startrack guarda la tarea (ID de estado más workflow_role) y la ubicación observada del vehículo rastreado. ECON solo lee Prisma y emite un único POST a Startrack; la recepción existe únicamente como declaración en ECON.",
        "Fuentes: docs/equivalencias-prisma-startrack.md (estados separados), ADR 0004, ADR 0006 y migración 0004. Sin webhooks ni escrituras en Prisma.",
    )
    visual_page(
        story,
        "Cómo detectar cambios y discrepancias",
        "Ampliación propuesta: webhooks habilitados y consultas de conciliación.",
        "diagrama-sincronizacion.png",
        "Comparar también cambios Prisma posteriores al envío. Conservar versiones y evidencia; un evento duplicado no debe repetir la acción. El responsable resuelve las diferencias que requieren decisión.",
        "Fuente: docs/sincronizacion-y-discrepancias.md. No hay un webhook de aprobaciones Prisma o cambios de tarea Startrack confirmado.",
    )
    visual_page(
        story,
        "Cómo crecer a miles de vehículos",
        "Arquitectura objetivo: separar recepción, operación e histórico analítico.",
        "diagrama-escala.png",
        "Hipótesis de prueba: 10.000 vehículos, un evento cada 10 s, producen 1.000 eventos/s medios. Hay que probar ráfagas, recuperación y límites del proveedor; no es capacidad demostrada.",
        "Fuente: docs/sincronizacion-y-discrepancias.md, sección de escala. Kafka y ClickHouse están propuestos; no instalados ni desplegados por esta entrega.",
    )

    story += [
        PageBreak(),
        para("Interpretar diferencias sin borrar significado", "title"),
        tab(
            [
                ["Caso", "Hechos", "Interpretación y decisión"],
                [
                    "Caso documental del brief",
                    "Prisma: maquinaria Ocupada. Startrack: tarea Completada.",
                    "Pueden ser compatibles: terminó el traslado y la maquinaria sigue asignada al proyecto. Conservar ambos estados y comprobar la recepción por separado.",
                ],
                [
                    "Muestra proporcionada CF-03",
                    "Solicitud APROBADA y maquinaria OBSOLETA. Sin tarea ni GPS vinculados en el archivo.",
                    "Revisar la asignación con Logística y Mantenimiento. No fabricar una tarea ni convertir OBSOLETA en avería o paro confirmado.",
                ],
                [
                    "Regla futura de cambio",
                    "Prisma modifica la unidad después de que se envió el movimiento.",
                    "Comparar la versión enviada y la actual; abrir incidencia para conciliar el traslado. No crear otra tarea automáticamente.",
                ],
            ],
            [145, 260, width - 405],
        ),
        Spacer(1, 17),
        para(
            "**RF-05:** esta explicación documenta la interpretación y resolución semántica. Sigue faltando la demostración combinada del caso con IDs y observaciones de ambas fuentes."
        ),
        para(
            "Los casos documentales no se convierten en filas operativas de la muestra. Fuente: brief, casos de uso y matriz de equivalencias.",
            "small",
        ),
    ]

    story += [
        PageBreak(),
        para("RF-06: tiempo fuera de geocerca sin justificación", "title"),
        para(
            "Indicador propuesto por equipo y período. Unidad: horas. Estado actual: no evaluable con la muestra proporcionada."
        ),
        tab(
            [
                ["Elemento", "Definición"],
                [
                    "Cálculo",
                    "Duración de la unión de intervalos válidos fuera de la geocerca asignada, dentro del horario exigible, excluyendo salidas autorizadas o justificadas.",
                ],
                [
                    "Identidad",
                    "Equipo, dispositivo, proyecto y geocerca con correspondencia vigente. No atribuir el recorrido del transportador a la actividad de la máquina.",
                ],
                [
                    "Evidencia",
                    "Eventos fechados y válidos, horario acordado, justificaciones con intervalos y regla de interpolación/corte aprobada.",
                ],
                [
                    "Cobertura",
                    "Mostrar horas evaluables y sin evidencia. Los huecos no cuentan como presencia, ausencia ni tiempo muerto. Evitar doble conteo de intervalos.",
                ],
                [
                    "Decisión",
                    "Logística y Técnica de Proyectos revisan ubicación y autorización. Mantenimiento participa ante una restricción.",
                ],
                [
                    "Gráfico futuro",
                    "Intervalos por equipo con categorías fuera justificado, fuera sin justificación y sin evidencia. No se dibuja una serie numérica antes de obtener esos intervalos.",
                ],
            ],
            [145, width - 145],
        ),
        Spacer(1, 12),
        para(
            "Estar fuera de geocerca no demuestra improductividad ni pérdida económica. Velocidad cero tampoco significa tiempo muerto para una máquina que trabaja estacionaria.",
            "small",
        ),
    ]

    story += [
        PageBreak(),
        para("Recorrido de revisión y pendientes", "title"),
        para(
            "1. Abrir la matriz de requisitos y seleccionar un caso del dataset suministrado. Separar las filas del archivo de las capturas históricas y del caso asignado al equipo."
        ),
        para(
            "2. Revisar el gráfico de planificación y entrar a la solicitud. Verificar aprobación, unidad, estado administrativo y datos que faltan para el movimiento."
        ),
        para(
            "3. Mostrar la matriz de equivalencias: qué viaja, qué se transforma y qué debe completar Logística. Abrir el plan y su historial; no presentar un borrador como tarea enviada."
        ),
        para(
            "4. Explicar los estados de Prisma y Startrack como hechos separados. Cuando falte evidencia de la segunda fuente, dejarla visible. El indicador propuesto necesita datos adicionales."
        ),
        para(
            "5. Distinguir arquitectura implementada y arquitectura de escala propuesta. El documento de decisiones técnicas adjunto ocupa dos páginas."
        ),
        Spacer(1, 12),
        tab(
            [
                ["Pendiente", "Quién debe resolverlo"],
                [
                    "Caso con tarea, GPS y correspondencias verificadas",
                    "Equipo de integración con MAIC / administrador Startrack",
                ],
                [
                    "RACI, estados, recepción y justificaciones",
                    "Mantenimiento, Logística y Técnica de Proyectos",
                ],
                [
                    "Contrato de cambios, cuotas e historial",
                    "Proveedores y equipo técnico",
                ],
                [
                    "Presentación de hasta 10 diapositivas con reflexión",
                    "Equipo participante; este dossier no la sustituye",
                ],
            ],
            [width * 0.48, width * 0.52],
        ),
        Spacer(1, 10),
        para(
            "Fuentes y archivos editables: docs/entregables-visuales.md. Matriz completa: docs/equivalencias-prisma-startrack.md y output/matrices (CSV/XLSX); diccionario: docs/diccionario-modelo-econ.md. No se modificaron datos de proveedores para producir estas figuras.",
            "small",
        ),
    ]

    path = OUT / "ECON-entregables-visuales.pdf"
    doc(path, landscape(A4)).build(story, onFirstPage=foot, onLaterPages=foot)
    return path


def md_flow(text, width):
    tokens = MD.parse(text)
    result, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "paragraph_open":
            result.append(para(tokens[i + 1].content))
            i += 3
        elif t.type == "table_open":
            rows, row = [], []
            i += 1
            while tokens[i].type != "table_close":
                t = tokens[i]
                if t.type == "tr_open":
                    row = []
                elif t.type in {"th_open", "td_open"}:
                    row.append(tokens[i + 1].content)
                elif t.type == "tr_close":
                    rows.append(row)
                i += 1
            result.extend([tab(rows, [width * 0.30, width * 0.70]), Spacer(1, 10)])
            i += 1
        else:
            i += 1
    return result


def build_decisions():
    text = (ROOT / "docs/decisiones-tecnicas.md").read_text(encoding="utf-8")
    sections = re.split(r"^## Página \d+: (.*)$", text, flags=re.MULTILINE)
    story = []
    width = A4[0] - 76
    for number in (1, 3):
        if story:
            story.append(PageBreak())
        story.append(para("Decisiones técnicas: " + sections[number], "title"))
        story.extend(md_flow(sections[number + 1], width))
    path = OUT / "ECON-decisiones-tecnicas.pdf"
    doc(path, A4).build(story, onFirstPage=foot, onLaterPages=foot)
    return path


def main():
    for folder in (ASSETS, OUT, QA):
        folder.mkdir(parents=True, exist_ok=True)
    register_fonts()
    init_styles()
    diagrams()
    paths = [build_dossier(), build_decisions()]
    report = []
    for path in paths:
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        (QA / (path.stem + ".txt")).write_text(text, encoding="utf-8")
        report.append(
            {
                "file": path.name,
                "pages": len(reader.pages),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (QA / "qa.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    assert report[0]["pages"] == 16, (
        "Review overflow in visual dossier and update contents only after QA"
    )
    assert report[1]["pages"] == 2, "Technical decisions must occupy at most two pages"


if __name__ == "__main__":
    main()
