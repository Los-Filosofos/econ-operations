"""Small Mantine building blocks. Every control carries a visible label and a real effect."""

import re
from pathlib import Path
from urllib.parse import urlsplit

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import dcc, html

from app.dashboard.analytics import day, instant
from app.dashboard.theme import BRAND, GRID_THEME, INK, MUTED, state_color, state_family
from app.models.hub import Provenance

NATURE = {
    "provided_sample": "Muestra del contrato proporcionado",
    "test_case": "Caso interno de prueba",
    "live_read": "Lectura del sandbox",
}
GRID_LOCALE = {
    "page": "Página",
    "to": "a",
    "of": "de",
    "more": "más",
    "pageSizeSelectorLabel": "Filas",
    "ariaPageSizeSelectorLabel": "Tamaño de página",
    "firstPage": "Primera página",
    "previousPage": "Página anterior",
    "nextPage": "Página siguiente",
    "lastPage": "Última página",
    "noRowsToShow": "Sin registros",
    "filterOoo": "Filtrar…",
    "equals": "Igual a",
    "notEqual": "Distinto de",
    "contains": "Contiene",
    "notContains": "No contiene",
    "startsWith": "Empieza con",
    "endsWith": "Termina con",
    "blank": "Vacío",
    "notBlank": "No vacío",
    "andCondition": "Y",
    "orCondition": "O",
    "applyFilter": "Aplicar",
    "resetFilter": "Limpiar",
}


ICONS = Path(__file__).parent / "assets" / "icons"


def icon(name: str, size: int = 18):
    """Tabler outline icon served from assets/icons; the mask keeps it in the text color."""
    if not (ICONS / f"{name}.svg").is_file():
        raise ValueError(f"Icono Tabler no vendorizado: {name}")
    return html.Span(
        className="ui-icon",
        style={"--icon": f"url(/assets/icons/{name}.svg)", "width": size, "height": size},
        **{"aria-hidden": "true"},
    )


def heading(title: str, description: str | None = None):
    return html.Header(
        [
            dmc.Title(title, order=1, size="h2"),
            html.P(description, className="lede") if description else None,
        ],
        className="page-heading",
    )


def flatten(children):
    for child in children:
        if isinstance(child, list | tuple):
            yield from flatten(child)
        elif child is not None:
            yield child


def section(title: str, *children, **props):
    return html.Section(
        [
            dmc.Title(title, order=2, size="h4", mb="sm", className="section-title"),
            *flatten(children),
        ],
        className=props.pop("className", "page-section"),
        **props,
    )


def hint(text: str, *, role: str | None = None, **props):
    note = dmc.Text(text, size="xs", c="dimmed", maw="90ch", my="xs", **props)
    return html.Div(note, role=role) if role else note


def link(label, href: str, **props):
    route = urlsplit(href)
    internal = (
        not route.scheme
        and not route.netloc
        and (
            route.path
            in {"/", "/resumen", "/decisiones", "/indicadores", "/integracion", "/fuentes"}
            or any(
                route.path == prefix or route.path.startswith(prefix + "/")
                for prefix in ("/solicitudes", "/maquinaria", "/operaciones")
            )
        )
    )
    # Keep APIs, downloads, external platforms and advanced Anchor props as real navigation.
    if internal and set(props) <= {"size", "fw", "mt", "mb", "display", "className", "style"}:
        size = props.get("size", "sm")
        style = {"color": BRAND, "fontSize": f"var(--mantine-font-size-{size})"}
        for prop, css in (("mt", "marginTop"), ("mb", "marginBottom")):
            if prop in props:
                value = props[prop]
                style[css] = (
                    value if isinstance(value, int | float) else f"var(--mantine-spacing-{value})"
                )
        if "fw" in props:
            style["fontWeight"] = props["fw"]
        if "display" in props:
            style["display"] = props["display"]
        style.update(props.get("style", {}))
        return dcc.Link(
            label,
            href=href,
            refresh=False,
            className=f"econ-link {props.get('className', '')}".strip(),
            style=style,
        )
    return dmc.Anchor(label, href=href, size=props.pop("size", "sm"), **props)


def breadcrumbs(parent: str, href: str, current: str):
    return html.Nav(
        html.Ol(
            [
                html.Li(link(parent, href)),
                html.Li(
                    [
                        html.Span("/", className="breadcrumb-separator", **{"aria-hidden": "true"}),
                        html.Span(current, **{"aria-current": "page"}),
                    ]
                ),
            ]
        ),
        className="page-breadcrumbs",
        **{"aria-label": "Ruta de navegación"},
    )


def empty(title="Sin registros en esta consulta", description="Prueba con otra búsqueda."):
    return html.Section(
        [
            dmc.Text(title, fw=600, size="sm", c=INK),
            dmc.Text(description, c=MUTED, size="sm", mt=4),
        ],
        className="empty-state",
        role="status",
    )


def notice(title: str, description, *, error=False, children=None):
    return html.Div(
        dmc.Alert(
            [dmc.Text(description, size="sm"), *(children or [])],
            title=title,
            color="red" if error else "econ",
            variant="light",
            icon=icon("alert-circle") if error else None,
        ),
        className="notice",
    )


def loading(rows: int = 4):
    return html.Div(
        [dmc.Skeleton(height=28, width="40%", mb="md")]
        + [dmc.Skeleton(height=14, mb="sm") for _ in range(rows)],
        role="status",
        **{"aria-label": "Consultando la operación…"},
    )


def state_text(value: str | None, key: str | None = None):
    """Plain labels; reserve the warning icon for an actionable issue."""
    family = state_family(key or value)
    label = dmc.Text(value or "Sin estado", size="sm", fw=500, c=INK, span=True)
    if family != "issue":
        return label
    return dmc.Group(
        [
            html.Span(icon("alert-triangle", 15), style={"color": state_color(key or value)}),
            label,
        ],
        gap=6,
        wrap="nowrap",
    )


def facts(values, cols=3):
    """Label/value pairs from a dict or a list of tuples."""
    return dmc.SimpleGrid(
        [
            html.Div(
                [
                    html.Span(label, className="fact-label"),
                    html.Div(value, className="fact-value"),
                ]
            )
            for label, value in dict(values).items()
        ],
        cols={"base": 1, "xs": 2, "md": cols},
        spacing="md",
        mb="md",
        className="facts",
    )


def eyebrow(text: str):
    """Small uppercase label above a title, figure or column. Never the only cue."""
    return html.Div(text, className="eyebrow")


def measure(*children):
    """Constrain children to a comfortable reading measure (72ch)."""
    return html.Div(list(flatten(children)), className="measure")


def data_strip(items):
    """Band of figures from (label, value, qualifier | None) tuples.

    Rules and white space instead of boxes: one hairline above and below the band, a
    vertical hairline between cells. The qualifier carries coverage, unit or cut-off.
    """
    cells = []
    for label, value, *rest in items:
        qualifier = rest[0] if rest else None
        cells.append(
            html.Div(
                [
                    html.Dt(label, className="eyebrow"),
                    html.Dd(
                        [
                            html.Span(value),
                            html.Span(qualifier, className="data-note") if qualifier else None,
                        ]
                    ),
                ]
            )
        )
    return html.Dl(cells, className="data-strip")


def definition_list(pairs):
    """Term/description pairs from a dict or tuples; two columns that collapse when narrow."""
    rows = []
    for term, value in dict(pairs).items():
        rows.extend([html.Dt(term), html.Dd(value)])
    return html.Dl(rows, className="definition-list")


def rows_table(rows, caption: str | None = None):
    """Two-column definition table for small records such as provenance."""
    rows = dict(rows).items()
    return dmc.Table(
        [
            dmc.TableCaption(caption, className="sr-only") if caption else None,
            dmc.TableTbody(
                [
                    dmc.TableTr(
                        [
                            dmc.TableTh(label, w=170, c="dimmed", fw=400),
                            dmc.TableTd(value),
                        ]
                    )
                    for label, value in rows
                ]
            ),
        ],
        fz="xs",
        verticalSpacing=6,
        withRowBorders=False,
        className="rows-table",
    )


def simple_table(headers: list[str], rows: list[list], *, caption: str):
    return dmc.TableScrollContainer(
        dmc.Table(
            [
                dmc.TableCaption(caption, className="sr-only"),
                dmc.TableThead(dmc.TableTr([dmc.TableTh(label) for label in headers])),
                dmc.TableTbody([dmc.TableTr([dmc.TableTd(cell) for cell in row]) for row in rows]),
            ],
            highlightOnHover=True,
        ),
        minWidth=560,
        type="native",
        **{"aria-label": caption},
    )


def disclosure(title: str, *children, value: str | None = None):
    return dmc.AccordionItem(
        [dmc.AccordionControl(title), dmc.AccordionPanel(list(flatten(children)))],
        value=value or title,
    )


def accordion(*items, **props):
    """Closed by default: technical detail never competes with the decision."""
    return dmc.Accordion(
        list(flatten(items)),
        chevronPosition="left",
        variant="default",
        className="disclosures",
        **props,
    )


def provenance(record: Provenance):
    return rows_table(
        [
            ("Fuente", "Prisma / Nexus" if record.source == "nexus" else "Startrack"),
            ("ID original", dmc.Code(record.source_id) if record.source_id else "No proporcionado"),
            ("Entorno", "Local" if record.environment == "local" else "Sandbox"),
            (
                "Lectura",
                instant(record.observed_at) if record.observed_at else "Sin lectura fechada",
            ),
            ("Naturaleza", NATURE[record.evidence_kind]),
            ("Datos", "Sintéticos del sandbox" if record.is_synthetic else "De la fuente"),
            ("Referencia", record.source_reference or "Sin referencia adicional"),
            ("Fecha documental", day(record.observed_on)),
        ],
        caption="Procedencia del registro",
    )


def markdown_link(label: str, href: str) -> str:
    escaped = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", label)
    return f"[{escaped}]({href})"


def grid(
    identifier: str,
    rows: list[dict],
    columns: list[tuple[str, str]],
    *,
    state_field=None,
    column_overrides: dict[str, dict] | None = None,
    markdown_fields: set[str] | None = None,
    no_rows_message: str = "Sin registros",
):
    """Compact columns; small tables fit their data and larger ones scroll virtually."""
    markdown_fields = (
        {columns[0][0]} if markdown_fields is None and columns else (markdown_fields or set())
    )
    overrides = column_overrides or {}
    definitions = []
    for index, (key, title) in enumerate(columns):
        definition = {
            "field": key,
            "headerName": title,
            "width": 200 if index == 0 else 120 if key == state_field else 160,
            "minWidth": 80,
        }
        if key in markdown_fields:
            definition["cellRenderer"] = "markdown"
        else:
            definition["tooltipField"] = key
        definition.update(overrides.get(key, {}))
        definitions.append(definition)
    if state_field:
        states = {row[state_field] for row in rows}
        next(column for column in definitions if column["field"] == state_field)["cellStyle"] = {
            "styleConditions": [
                {
                    "condition": f"params.value == {state!r}",
                    "style": {"borderLeft": f"3px solid {state_color(state)}"},
                }
                for state in sorted(states)
            ]
        }
    compact = len(rows) <= 15
    return dag.AgGrid(
        id=identifier,
        rowData=rows,
        columnDefs=definitions,
        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
            "wrapText": False,
            "autoHeight": False,
            "cellStyle": {"textOverflow": "ellipsis", "overflow": "hidden"},
        },
        dashGridOptions={
            "theme": {"function": GRID_THEME},
            "animateRows": False,
            "domLayout": "autoHeight" if compact else "normal",
            "rowHeight": 42,
            "pagination": not compact,
            "paginationPageSize": 15,
            "paginationPageSizeSelector": [15, 30, 50],
            "localeText": {**GRID_LOCALE, "noRowsToShow": no_rows_message},
        },
        # autoHeight must not inherit AG Grid's default 400px wrapper height.
        style={"height": None if compact else 500, "width": "100%"},
        className="econ-grid",
    )
