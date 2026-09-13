"""The data path of one request, stage by stage and field by field.

Everything shown comes from `services.integration_trace`, the same derivation the HTTP
route returns, so the page and `GET /api/v1/integration/{request_id}` cannot diverge.
"""

import dash_mantine_components as dmc
from dash import ALL, html

from app.dashboard.analytics import instant
from app.dashboard.components import (
    accordion,
    disclosure,
    empty,
    facts,
    heading,
    hint,
    icon,
    link,
    provenance,
    rows_table,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.models.hub import HubResponse
from app.services.integration_trace import (
    TREATMENTS,
    IntegrationTrace,
    TraceCell,
    TraceEntry,
    TraceStage,
    build_trace,
    default_request_id,
    traceable_requests,
)

# Pattern ids: the controls only exist on this page, and the callback still registers.
SELECT_ID = {"type": "integration-request", "field": "request"}
PANEL_ID = {"type": "integration-trace", "field": "panel"}
SELECT_PATTERN = {"type": "integration-request", "field": ALL}
PANEL_PATTERN = {"type": "integration-trace", "field": ALL}
# Stage progress reuses the shared state palette: no decorative colors.
STAGE_STATES = {
    "done": ("active", "Completa"),
    "pending": ("pending", "Pendiente"),
    "blocked": ("issue", "Bloqueada"),
}
STAGE_ICONS = {
    "prisma": "database",
    "econ": "arrows-exchange",
    "startrack_request": "send",
    "startrack_response": "clipboard-check",
}
TREATMENT_ICONS = {
    "kept": "check",
    "transformed": "arrows-exchange",
    "manual": "hand-click",
    "absent": "minus",
}
NO_VALUE = "No informado"
NO_FIELD = "Sin campo equivalente"
INTRO = "Prisma → ECON → Startrack. Campos, eventos y tiempos de cada solicitud."


def request_options(hub: HubResponse):
    return [
        {
            "value": request.id,
            "label": " · ".join(
                filter(
                    None,
                    [
                        request.project_name or request.project_id or "Proyecto sin nombre",
                        request.machinery_type,
                        request.machinery_asset_number or "sin unidad asignada",
                    ],
                )
            ),
        }
        for request in traceable_requests(hub)
    ]


def code(value: str | None):
    return dmc.Code(value, fz="xs") if value else dmc.Text(NO_FIELD, size="xs", c="dimmed")


def observed(value: str | None, **props):
    """A missing value is dimmed and named, never blank and never invented."""
    return dmc.Text(value or NO_VALUE, size="sm", **({} if value else {"c": "dimmed"}), **props)


def cell_view(cell: TraceCell):
    if cell.field is None:
        return dmc.Text(TREATMENTS["absent"], size="sm", c="dimmed")
    return html.Div([code(cell.field), observed(cell.value, mt=2)])


def entry_view(entry: TraceEntry):
    return html.Div([observed(entry.value), code(entry.field)])


def treatment_view(treatment: str):
    return dmc.Group(
        [icon(TREATMENT_ICONS[treatment], 15), dmc.Text(TREATMENTS[treatment], size="sm")],
        gap=6,
        wrap="nowrap",
    )


def steps(trace: IntegrationTrace):
    return [
        dmc.StepperStep(
            label=f"{position}. {stage.title}",
            description=STAGE_STATES[stage.state][1],
            icon=icon(STAGE_ICONS[stage.key], 18),
            completedIcon=icon(STAGE_ICONS[stage.key], 18),
        )
        for position, stage in enumerate(trace.stages, start=1)
    ]


def stepper(trace: IntegrationTrace):
    """Horizontal on the desktop, vertical on a phone; the same four stages either way."""
    active = sum(1 for stage in trace.stages if stage.state == "done")
    return html.Div(
        [
            dmc.Stepper(
                steps(trace),
                active=active,
                orientation=orientation,
                iconSize=34,
                size="sm",
                my="md",
                visibleFrom="sm" if orientation == "horizontal" else None,
                hiddenFrom="sm" if orientation == "vertical" else None,
                **{"aria-label": "Etapas del recorrido de los datos"},
            )
            for orientation in ("horizontal", "vertical")
        ]
    )


def stage_section(position: int, stage: TraceStage, context: QueryContext):
    body = [
        hint(stage.summary),
        rows_table({entry.label: entry_view(entry) for entry in stage.entries})
        if stage.entries
        else empty("Sin campos que mostrar en esta etapa", stage.summary),
        dmc.List([dmc.ListItem(rule) for rule in stage.rules], size="sm", mt="xs")
        if stage.rules
        else None,
    ]
    if stage.provenance or stage.equipment_provenance:
        body.append(
            accordion(
                disclosure("Procedencia de la solicitud", provenance(stage.provenance))
                if stage.provenance
                else None,
                disclosure("Procedencia de la unidad", provenance(stage.equipment_provenance))
                if stage.equipment_provenance
                else None,
                mt="sm",
            )
        )
    return section(
        f"Etapa {position} · {stage.title}",
        dmc.Group(
            [state_text(STAGE_STATES[stage.state][1], STAGE_STATES[stage.state][0])],
            mb="xs",
        ),
        *body,
    )


def duration_text(seconds: float) -> str:
    minutes, remainder = divmod(int(abs(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = [
        f"{value} {unit}" for value, unit in [(days, "d"), (hours, "h"), (minutes, "min")] if value
    ] or [f"{remainder} s"]
    return ("−" if seconds < 0 else "") + " ".join(parts)


def times_section(trace: IntegrationTrace):
    timeline = trace.timeline
    expected = timeline.expected_duration_seconds
    return section(
        "Tiempos del traslado",
        simple_table(
            ["Instante", "Momento registrado", "De dónde sale"],
            [
                [
                    moment.label,
                    instant(moment.at) if moment.at else "Sin registro",
                    moment.source,
                ]
                for moment in timeline.instants
            ],
            caption="Instantes registrados por las fuentes para este traslado",
        ),
        simple_table(
            ["Duración", "Valor", "Lectura"],
            [
                *(
                    [
                        duration.label,
                        duration_text(duration.seconds),
                        duration.detail,
                    ]
                    for duration in timeline.durations
                ),
                [
                    "Duración esperada (Startrack)",
                    duration_text(expected)
                    if expected is not None
                    else "Sin duración esperada informada",
                    "Campo duration del Job Data Object, en segundos.",
                ],
            ],
            caption="Duraciones calculadas solo con instantes registrados",
        ),
        hint(timeline.note),
    )


def field_map_section(trace: IntegrationTrace):
    return section(
        "Mapeo campo a campo",
        html.Div(
            simple_table(
                ["Concepto", "Prisma", "ECON", "Startrack", "Tratamiento"],
                [
                    [
                        html.Div(
                            [
                                dmc.Text(row.concept, size="sm", fw=500),
                                dmc.Text(row.note, size="xs", c="dimmed", mt=2)
                                if row.note
                                else None,
                            ]
                        ),
                        cell_view(row.prisma),
                        cell_view(row.econ),
                        cell_view(row.startrack),
                        treatment_view(row.treatment),
                    ]
                    for row in trace.field_map
                ],
                caption="Correspondencia de campos entre Prisma, ECON y Startrack",
            ),
            className="field-map",
        ),
        hint(
            "Conservado: el mismo dato con el mismo significado. Transformado: ECON lo reescribe "
            "para el contrato de destino. Manual (operador): lo decide una persona al preparar "
            "el traslado. Sin equivalente: el dato no viaja."
        ),
    )


def trace_panel(hub: HubResponse, context: QueryContext, workflow, request_id: str | None):
    if request_id is None:
        return empty(
            "Sin solicitudes en esta consulta",
            "Cambia el origen de datos o revisa la cobertura de la lectura.",
        )
    trace = build_trace(hub, request_id, workflow)
    if trace is None:
        return empty(
            "Solicitud fuera de la consulta",
            "Comprueba el origen seleccionado y el identificador de la solicitud.",
        )
    current = next((stage for stage in trace.stages if stage.state != "done"), None)
    return [
        facts(
            [
                ("Solicitud", link(trace.request_label, context.request_href(trace.request_id))),
                ("Unidad asignada", trace.equipment_label or "Sin unidad asignada"),
                (
                    "Movimiento guardado",
                    link(trace.movement_reference, context.movement_href(trace.movement_id))
                    if trace.movement_id
                    else trace.message,
                ),
            ]
        ),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        *[
                            dmc.TabsTab(
                                stage.title,
                                value=stage.key,
                                leftSection=icon(STAGE_ICONS[stage.key], 16),
                            )
                            for stage in trace.stages
                        ],
                        dmc.TabsTab("Tiempos", value="times"),
                        dmc.TabsTab("Mapa de campos", value="fields"),
                    ]
                ),
                *[
                    dmc.TabsPanel(stage_section(position, stage, context), value=stage.key)
                    for position, stage in enumerate(trace.stages, start=1)
                ],
                dmc.TabsPanel(times_section(trace), value="times"),
                dmc.TabsPanel(
                    [
                        field_map_section(trace),
                        link(
                            "Consultar contrato JSON",
                            f"/api/v1/integration/{trace.request_id}?mode={trace.mode}",
                        ),
                    ],
                    value="fields",
                ),
            ],
            id={"type": "integration-stage", "request": trace.request_id},
            value=current.key if current else trace.stages[-1].key,
            persistence=trace.mode,
            persistence_type="session",
            keepMounted=False,
            className="analysis-tabs",
            mt="md",
        ),
    ]


def integration_page(hub: HubResponse, context: QueryContext, workflow=None):
    selected = default_request_id(hub)
    return [
        heading("Integración", INTRO),
        dmc.Select(
            id=SELECT_ID,
            label="Solicitud a seguir",
            value=selected,
            persistence=context.mode,
            persistence_type="session",
            data=request_options(hub),
            allowDeselect=False,
            searchable=True,
            nothingFoundMessage="Sin solicitudes en esta consulta",
            w={"base": "100%", "sm": 520},
            mb="md",
        ),
        html.Div(trace_panel(hub, context, workflow, selected), id=PANEL_ID),
    ]


def integration_controls():
    """Declare the page ids for the validation layout without building a whole trace."""
    return [dmc.Select(id=SELECT_ID, data=[], label="Solicitud a seguir"), html.Div(id=PANEL_ID)]
