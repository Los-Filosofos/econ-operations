"""Small Mantine building blocks. Every control carries a visible label and a real effect."""

import re

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from app.dashboard.analytics import day, instant
from app.dashboard.theme import GRID_THEME, state_color, state_family
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


def icon(name: str, size: int = 18):
    return DashIconify(icon=f"tabler:{name}", width=size, height=size)


def heading(title: str, description: str | None = None):
    return html.Header(
        [
            dmc.Title(title, order=1, size="h2"),
            dmc.Text(description, c="dimmed", size="sm", maw="72ch") if description else None,
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
        [dmc.Title(title, order=2, size="h4", mb="sm"), *flatten(children)],
        className="page-section",
        **props,
    )


def hint(text: str, *, role: str | None = None, **props):
    note = dmc.Text(text, size="xs", c="dimmed", maw="90ch", my="xs", **props)
    return html.Div(note, role=role) if role else note


def link(label, href: str, **props):
    return dmc.Anchor(label, href=href, size=props.pop("size", "sm"), **props)


def back_link(label: str, href: str):
    return link(dmc.Group([icon("arrow-left", 16), label], gap=6, wrap="nowrap"), href, mt="sm")


def empty(title="Sin registros en esta consulta", description="Prueba con otra búsqueda."):
    return html.Div(
        dmc.Paper(
            [dmc.Text(title, fw=600), dmc.Text(description, c="dimmed", size="sm", mt=4)],
            withBorder=True,
            p="lg",
            bg="gray.0",
        ),
        role="status",
    )


def notice(title: str, description, *, error=False, children=None):
    return html.Div(
        dmc.Alert(
            [dmc.Text(description, size="sm"), *(children or [])],
            title=title,
            color="red" if error else "econ",
            variant="light",
            icon=icon("alert-circle" if error else "info-circle"),
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
    """Same state, same color everywhere; the label always carries the meaning."""
    family = state_family(key or value)
    mark = (
        icon("alert-triangle", 15)
        if family == "issue"
        else html.Span(className="state-dot", style={"background": state_color(key or value)})
    )
    return dmc.Group(
        [mark, dmc.Text(value or "Sin estado", size="sm", span=True)], gap=6, wrap="nowrap"
    )


def facts(values, cols=3):
    """Label/value pairs from a dict or a list of tuples."""
    return dmc.SimpleGrid(
        [
            html.Div([dmc.Text(label, size="xs", c="dimmed"), dmc.Text(value, size="sm", fw=500)])
            for label, value in dict(values).items()
        ],
        cols={"base": 1, "xs": 2, "md": cols},
        spacing="md",
        mb="md",
        className="facts",
    )


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


def grid(identifier: str, rows: list[dict], columns: list[tuple[str, str]], *, state_field=None):
    """Community AG Grid keeps sorting, filters and keyboard navigation for large tables."""
    definitions = [{"field": key, "headerName": title} for key, title in columns]
    definitions[0]["cellRenderer"] = "markdown"
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
    return dag.AgGrid(
        id=identifier,
        rowData=rows,
        columnDefs=definitions,
        defaultColDef={
            "flex": 1,
            "minWidth": 150,
            "sortable": True,
            "filter": True,
            "resizable": True,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
            "wrapText": True,
            "autoHeight": True,
        },
        dashGridOptions={
            "theme": {"function": GRID_THEME},
            "animateRows": False,
            "domLayout": "autoHeight",
            "pagination": True,
            "paginationPageSize": 15,
            "paginationPageSizeSelector": [15, 30, 50],
            "localeText": GRID_LOCALE,
        },
        className="econ-grid",
    )
