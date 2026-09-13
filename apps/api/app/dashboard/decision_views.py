"""Lead with reviewable decisions; calendar and state distributions provide context."""

from dash import dcc, html

from app.dashboard.analytics import instant, readable
from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import (
    request_states,
    requests_in_scope,
    short_date,
    states_figure,
    usage_figure,
    usage_timeline,
)
from app.dashboard.decision_priorities import decision_items
from app.models.hub import HubResponse
from app.models.workflow import WorkflowOverview

FILTER_LABELS = {
    "unassigned": "sin unidad",
    "unlinked": "sin tarea confirmada",
    "approved_unassigned": "aprobadas sin unidad",
    "active_failures": "con falla registrada",
    "pending_started": "pendientes con inicio alcanzado",
}


def _decisions(hub, context, workflow):
    items = decision_items(hub, context, workflow)
    rows = []
    for item in items:
        request = item.request
        timeline = usage_timeline([request])
        if timeline.periods:
            period = timeline.periods[0]
            dates = f"{short_date(period.starts_on)} – {short_date(period.ends_on, year=True)}"
        else:
            dates = "Período por verificar"
        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            dcc.Link(
                                request.project_name or "Proyecto sin identificar",
                                href=context.request_href(request.id),
                                className="decision-project",
                            ),
                            html.Span(request.machinery_type or "Tipo sin informar"),
                            html.Span(dates),
                        ],
                        className="decision-subject",
                        role="cell",
                    ),
                    html.Td([html.H2(item.title), html.P(item.evidence)], role="cell"),
                    html.Td(
                        dcc.Link(item.action, href=item.href),
                        className="decision-next-step",
                        role="cell",
                    ),
                ],
                role="row",
            )
        )
    if not rows:
        return html.P(
            "No se identificaron asuntos por revisar con la evidencia de esta consulta.",
            className="decision-empty",
        )
    return html.Div(
        html.Table(
            [
                html.Caption("Asuntos para revisión de la operación", className="sr-only"),
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Proyecto y necesidad", scope="col"),
                            html.Th("Qué requiere revisión", scope="col"),
                            html.Th("Siguiente paso", scope="col"),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            className="decision-agenda",
            role="table",
        ),
        className="decision-agenda-wrap",
    )


def _table(headers: list[str], rows: list[list], caption: str):
    return html.Div(
        html.Table(
            [
                html.Caption(caption, className="sr-only"),
                html.Thead(html.Tr([html.Th(header, scope="col") for header in headers])),
                html.Tbody([html.Tr([html.Td(value) for value in row]) for row in rows]),
            ]
        ),
        className="table-scroll",
    )


def _graph(identifier: str, figure):
    return dcc.Graph(
        id=identifier,
        figure=figure,
        responsive=True,
        config={"displayModeBar": False, "responsive": True, "locale": "es"},
        style={"height": f"{figure.layout.height}px"},
    )


def overview(hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None = None):
    available = context.mode == hub.mode and readable(hub)
    requests = requests_in_scope(hub, context, workflow)
    selected_filter = FILTER_LABELS.get(context.filter)
    header = html.Header(
        [
            html.H1("Qué requiere atención"),
            html.P("Decisiones sobre la asignación y el traslado de maquinaria a cada proyecto."),
        ],
        className="decision-heading page-heading",
    )
    content = [header]
    if selected_filter and available:
        content.append(
            html.P(f"Filtro aplicado: {selected_filter}.", className="decision-chart-note")
        )
    if not available or not requests:
        content.append(
            html.Div(
                [
                    html.H2("Sin solicitudes para representar"),
                    html.P(
                        "Revisa las fuentes para obtener una lectura."
                        if not available
                        else "Amplía la búsqueda o cambia el filtro de solicitudes."
                    ),
                    dcc.Link(
                        "Consultar fuentes" if not available else "Ver solicitudes",
                        href=context.href("/fuentes" if not available else "/solicitudes"),
                    ),
                ],
                className="decision-empty",
                role="status",
            )
        )
        return html.Div(content, className="decision-overview")

    content.append(_decisions(hub, context, workflow))
    if workflow is None or not workflow.available:
        content.append(
            html.P(
                "Registro de tareas sin confirmar. Consulta las operaciones antes de concluir "
                "si un traslado está preparado o enviado.",
                className="decision-chart-note",
                role="status",
            )
        )
    elif not workflow.complete:
        content.append(
            html.P(
                "Registro de movimientos parcial. Una tarea sin confirmar en esta vista puede "
                "tener evidencia fuera de la ventana consultada.",
                className="decision-chart-note",
                role="status",
            )
        )
    content.append(
        html.Div(
            [
                html.Span("Revisiones basadas en la evidencia disponible; no indican atraso."),
                dcc.Link("Ver todas las solicitudes", href=context.href("/solicitudes")),
            ],
            className="decision-agenda-footer",
        )
    )
    states = request_states(requests)
    timeline = usage_timeline(requests)
    source = next(source for source in hub.sources if source.id == "nexus")
    origin = "Muestras del archivo" if hub.mode == "fixture" else "Lectura del sandbox"
    cutoff = (
        f"Corte de lectura: {instant(hub.data_as_of)} (El Salvador)."
        if hub.data_as_of is not None
        else f"Fecha documental: {source.observed_on:%d/%m/%Y}; sin instante común de observación."
        if source.observed_on is not None
        else "Sin instante común de observación."
    )
    total = (
        f"Total de solicitudes informado por el origen: {hub.scope.requests_total}, "
        "antes de la búsqueda local."
        if hub.scope.requests_total is not None
        else "El origen no informa un total de solicitudes."
    )
    content.append(
        html.P(
            f"{origin} · Datos sintéticos. Solicitudes en esta vista: {len(requests)}; "
            f"devueltas por la consulta: {len(hub.requests)}. {total} {cutoff} "
            + ("Cobertura integrada parcial." if not hub.scope.complete else ""),
            className="analysis-scope",
        )
    )
    states_section = html.Section(
        [
            html.Div(
                [
                    html.H2("Estado de las solicitudes"),
                    html.P(
                        f"Solicitudes de esta vista por estado administrativo: {len(requests)}.",
                        className="decision-chart-note",
                    ),
                ],
                className="decision-chart-heading",
            ),
            _graph("decision-request-states", states_figure(states)),
            html.Details(
                [
                    html.Summary("Ver datos de estados"),
                    _table(
                        ["Estado original", "Solicitudes"],
                        [[state, count] for state, count in states],
                        "Solicitudes de esta vista por estado administrativo original",
                    ),
                ],
                className="decision-chart-data",
            ),
        ],
        className="decision-chart",
        **{"aria-label": "Estado administrativo de solicitudes"},
    )

    period_note = (
        f"Solicitudes con período representable: {len(timeline.periods)} de {len(requests)}. "
        "Inicio y fin incluidos; no son plazos de entrega."
    )
    if timeline.periods:
        start = min(period.starts_on for period in timeline.periods)
        end = max(period.ends_on for period in timeline.periods)
        period_note = f"{short_date(start)} – {short_date(end, year=True)}. {period_note}"
    usage_children = [
        html.Div(
            [
                html.H2("Período de uso solicitado"),
                html.P(period_note, className="decision-chart-note"),
            ],
            className="decision-chart-heading",
        ),
        _graph("decision-request-usage", usage_figure(timeline))
        if timeline.periods
        else html.P(
            "No hay períodos con inicio y fin válidos para representar.", className="decision-empty"
        ),
    ]
    if timeline.excluded:
        usage_children.append(
            html.P(
                f"{len(timeline.excluded)} solicitud(es) no representadas por fechas incompletas, "
                "ambiguas o invertidas. Consulta el detalle en la tabla.",
                className="decision-chart-note",
                role="status",
            )
        )
    table_content = [
        html.Summary("Ver datos de períodos"),
        _table(
            ["Solicitud", "Proyecto", "Inicio solicitado", "Fin solicitado"],
            [
                [
                    dcc.Link(
                        period.request.provenance.source_id or period.request.id,
                        href=context.request_href(period.request.id),
                    ),
                    period.request.project_name or period.request.project_id or "Sin proyecto",
                    period.request.starts_on,
                    period.request.ends_on,
                ]
                for period in timeline.periods
            ],
            "Períodos originales de uso de las solicitudes representadas",
        ),
    ]
    if timeline.excluded:
        table_content.extend(
            [
                html.H3("Solicitudes no representadas"),
                _table(
                    ["Solicitud", "Inicio original", "Fin original", "Motivo"],
                    [
                        [
                            dcc.Link(
                                item.request.provenance.source_id or item.request.id,
                                href=context.request_href(item.request.id),
                            ),
                            item.request.starts_on or "Sin informar",
                            item.request.ends_on or "Sin informar",
                            item.reason,
                        ]
                        for item in timeline.excluded
                    ],
                    "Solicitudes excluidas del gráfico y motivo de exclusión",
                ),
            ]
        )
    table_content.append(
        html.P(
            "Fechas con hora y zona se representan por su día en El Salvador. "
            "La tabla conserva los valores originales.",
            className="decision-chart-note",
        )
    )
    usage_children.append(html.Details(table_content, className="decision-chart-data"))
    usage_section = html.Section(
        usage_children, className="decision-chart", **{"aria-label": "Períodos de uso solicitados"}
    )
    content.append(usage_section)
    content.append(
        html.Details(
            [html.Summary("Ver distribución por estado de solicitud"), states_section],
            className="decision-secondary",
        )
    )
    return html.Div(content, className="decision-overview")
