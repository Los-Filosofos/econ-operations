"""Spanish operational views, built entirely with Dash components."""

from urllib.parse import unquote

import dash_ag_grid as dag
from dash import dcc, html

from app.dashboard.analytics import (
    calendar,
    calendar_figure,
    distribution,
    distribution_figure,
    equipment_label,
    exception_groups,
    instant,
    readable,
    requests_for,
)
from app.dashboard.context import QueryContext
from app.models.hub import EquipmentRecord, HubResponse, Provenance

NAVIGATION = [
    ("/", "Vista general"),
    ("/maquinaria", "Maquinaria"),
    ("/solicitudes", "Solicitudes"),
    ("/traslados", "Traslados"),
    ("/alertas", "Atención"),
    ("/fuentes", "Fuentes"),
]
SOURCE_STATES = {
    "fixture": "Ejemplos locales",
    "connected": "Conectada",
    "partial": "Lectura parcial",
    "not_configured": "Pendiente de conexión",
    "disabled": "Consulta desactivada",
    "error": "Error de lectura",
}
RELATIONS = {
    "confirmed": "Vínculo confirmado",
    "candidate": "Vínculo por revisar",
    "unlinked": "Sin vínculo confirmado",
}
SEVERITIES = {"critical": "Alta", "warning": "Revisar", "info": "Informativa"}


def heading(title: str, description: str):
    return html.Header([html.H1(title), html.P(description)], className="page-heading")


def empty(title="Sin registros en esta consulta", description="Prueba con otra búsqueda."):
    return html.Div([html.H3(title), html.P(description)], className="empty-state", role="status")


def notice(title: str, description: str, *, error=False):
    return html.Div(
        [html.Strong(title), html.P(description)],
        className="notice notice-error" if error else "notice",
        role="alert" if error else "note",
    )


def navigation(path: str, context: QueryContext):
    return [
        dcc.Link(
            label,
            href=context.href(route),
            className="nav-link active"
            if (path == route or (route != "/" and path.startswith(f"{route}/")))
            else "nav-link",
        )
        for route, label in NAVIGATION
    ]


def scope(hub: HubResponse):
    mode = "Ejemplos locales" if hub.mode == "fixture" else "Sandbox en vivo"
    return html.Div(
        [
            html.Span(mode, className="scope-mode"),
            html.Span(f"Corte {instant(hub.data_as_of)} · hora de El Salvador"),
            html.Span(
                f"{hub.scope.equipment_returned} equipos · "
                f"{hub.scope.requests_returned} solicitudes",
                className="scope-count",
            ),
        ],
        className="scope-line",
    )


def coverage(hub: HubResponse, context: QueryContext):
    if hub.mode == "fixture":
        return html.P(
            "Datos sintéticos de demostración. Los conteos describen únicamente esta consulta.",
            className="coverage-note",
        )
    messages = [
        html.Span(f"{source.label}: {SOURCE_STATES[source.status]}. ") for source in hub.sources
    ]
    return html.Div(
        [
            html.Strong("Cobertura incompleta. "),
            *messages,
            dcc.Link("Revisar fuentes", href=context.href("/fuentes")),
        ],
        className="coverage-note",
    )


def simple_table(headers: list[str], rows: list[list], *, caption: str):
    return html.Div(
        html.Table(
            [
                html.Caption(caption, className="sr-only"),
                html.Thead(html.Tr([html.Th(label, scope="col") for label in headers])),
                html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows]),
            ]
        ),
        className="table-scroll",
    )


def grid(identifier: str, rows: list[dict], columns: list[tuple[str, str]], *, links=False):
    definitions = [{"field": key, "headerName": title} for key, title in columns]
    if links:
        definitions.append(
            {
                "field": "detail",
                "headerName": "Ficha",
                "cellRenderer": "markdown",
                "filter": False,
                "sortable": False,
                "minWidth": 100,
                "maxWidth": 120,
            }
        )
    return dag.AgGrid(
        id=identifier,
        rowData=rows,
        columnDefs=definitions,
        defaultColDef={
            "flex": 1,
            "minWidth": 145,
            "sortable": True,
            "filter": True,
            "resizable": True,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
        },
        dashGridOptions={
            "theme": {
                "function": (
                    "themeQuartz.withParams({fontFamily:'Inter, sans-serif',fontSize:12,"
                    "accentColor:'#144f81',foregroundColor:'#202c38',"
                    "headerTextColor:'#626e7a',headerBackgroundColor:'#f8fafb',"
                    "borderColor:'#e2e7eb',wrapperBorderRadius:0,borderRadius:0})"
                )
            },
            "animateRows": False,
            "domLayout": "autoHeight",
            "pagination": True,
            "paginationPageSize": 15,
            "paginationPageSizeSelector": [15, 30, 50],
            "suppressCellFocus": False,
            "rowHeight": 54,
            "localeText": {
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
            },
        },
        className="econ-grid",
        style={"width": "100%"},
    )


def equipment_link(item: EquipmentRecord, context: QueryContext):
    return dcc.Link(equipment_label(item), href=context.equipment_href(item.id))


def _detail_markdown(identifier: str | None, context: QueryContext) -> str:
    return f"[Ver ficha]({context.equipment_href(identifier)})" if identifier else "Sin unidad"


def exceptions(hub: HubResponse, context: QueryContext, *, expanded=False):
    groups = exception_groups(hub)
    if not readable(hub):
        return empty("Sin datos para evaluar", "Revisa la conexión de las fuentes.")
    if not groups:
        return empty(
            "Sin alertas en los registros evaluados",
            "Este resultado se limita a la consulta actual.",
        )
    equipment = {item.id: item for item in hub.equipment}
    rows = []
    for group in groups:
        item = equipment.get(group["equipment_id"])
        subject = equipment_link(item, context) if item else "Solicitud sin unidad"
        reasons = []
        for alert in group["alerts"]:
            reason = [html.Strong(alert.title)]
            if expanded:
                reason += [
                    html.P(alert.description),
                    html.Details(
                        [
                            html.Summary("Ver evidencia"),
                            html.Ul([html.Li(html.Code(value)) for value in alert.evidence]),
                            html.P(
                                f"Referencia: {alert.request_id or alert.equipment_id or alert.id}"
                            ),
                        ]
                    ),
                ]
            reasons.append(html.Div(reason, className="alert-reason"))
        rows.append(
            [
                html.Span(SEVERITIES[group["severity"]], className=f"priority {group['severity']}"),
                subject,
                html.Div(reasons),
                " · ".join(group["owners"]),
            ]
        )
    return simple_table(
        ["Prioridad", "Operación", "Qué revisar", "Responsable"],
        rows,
        caption="Asuntos operativos que requieren atención",
    )


def overview(hub: HubResponse, context: QueryContext):
    available = readable(hub)
    metrics = [
        (
            len(requests_for(hub, "pending_started")),
            "Solicitudes por atender",
            "Pendientes con inicio previsto alcanzado",
            "/solicitudes",
            "pending_started",
        ),
        (
            len(requests_for(hub, "approved_unassigned")),
            "Aprobadas sin unidad",
            "Asignaciones que requieren revisión",
            "/solicitudes",
            "approved_unassigned",
        ),
        (
            hub.summary.active_failures,
            "Equipos con falla activa",
            "Revisar diagnóstico y decisión de paro",
            "/maquinaria",
            "active_failures",
        ),
    ]
    cards = [
        dcc.Link(
            [
                html.Span(label, className="metric-label"),
                html.Strong(
                    str(value) if available and value is not None else "—", className="metric-value"
                ),
                html.Span(description, className="metric-description"),
                html.Span("Revisar →", className="metric-action"),
            ],
            href=context.href(path, filter=filter),
            className="metric",
        )
        for value, label, description, path, filter in metrics
    ]
    states, dates = distribution(hub), calendar(hub)
    state_chart = empty(
        "Sin datos para calcular", "La fuente debe aportar equipos a esta consulta."
    )
    date_chart = empty("Sin datos para calcular", "La fuente debe aportar solicitudes y un corte.")
    if states:
        state_chart = [
            dcc.Graph(
                figure=distribution_figure(states),
                config={"displayModeBar": False, "responsive": True},
            ),
            html.Details(
                [
                    html.Summary("Ver datos"),
                    simple_table(
                        ["Estado administrativo", "Equipos"],
                        [list(row) for row in states],
                        caption="Distribución administrativa de la maquinaria consultada",
                    ),
                ]
            ),
        ]
    if dates and hub.requests:
        date_chart = [
            dcc.Graph(
                figure=calendar_figure(dates), config={"displayModeBar": False, "responsive": True}
            ),
            html.Div(
                [
                    html.Details(
                        [
                            html.Summary("Ver datos"),
                            simple_table(
                                ["Inicio previsto", "Solicitudes"],
                                [
                                    [day.strftime("%d/%m/%Y"), count]
                                    for day, count in dates["days"].items()
                                ],
                                caption="Solicitudes por fecha prevista de inicio",
                            ),
                        ]
                    ),
                    html.Span(
                        f"{dates['undated']} sin fecha válida · "
                        f"{dates['outside']} fuera del período"
                    ),
                ],
                className="chart-foot",
            ),
        ]
    return [
        heading("Vista general", "Lo que necesita atención y el contexto para decidir."),
        html.Div(cards, className="metrics"),
        html.Div(
            [
                html.Section(
                    [
                        html.H2("Maquinaria por estado"),
                        html.P(
                            "Estado administrativo de los equipos consultados",
                            className="section-caption",
                        ),
                        html.Div(state_chart),
                    ],
                    className="chart-section",
                ),
                html.Section(
                    [
                        html.H2("Solicitudes por inicio previsto"),
                        html.P(
                            "Planificación: seis días antes y siete después del corte",
                            className="section-caption",
                        ),
                        html.Div(date_chart),
                    ],
                    className="chart-section",
                ),
            ],
            className="charts",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.H2("Qué necesita atención"),
                        dcc.Link("Ver toda la evidencia →", href=context.href("/alertas")),
                    ],
                    className="section-heading",
                ),
                exceptions(hub, context),
            ],
            className="attention-section",
        ),
    ]


def machinery(hub: HubResponse, context: QueryContext):
    items = hub.equipment
    if context.filter == "active_failures":
        items = [item for item in items if item.maintenance_failure_id]
    elif context.filter == "unlinked":
        items = [item for item in items if item.relation_status != "confirmed"]
    rows = [
        {
            "code": equipment_label(item),
            "name": item.name,
            "project": item.project_name or "Sin proyecto informado",
            "state": item.machinery_status,
            "maintenance": item.maintenance_status or "Sin información",
            "relation": RELATIONS[item.relation_status],
            "detail": _detail_markdown(item.id, context),
        }
        for item in items
    ]
    return [
        heading("Maquinaria", "Consulta el equipo, su asignación y las condiciones de operación."),
        filter_links(
            context,
            "/maquinaria",
            [
                ("all", "Todos los equipos"),
                ("active_failures", "Con falla activa"),
                ("unlinked", "Sin vínculo confirmado"),
            ],
        ),
        grid(
            "equipment-grid",
            rows,
            [
                ("code", "Equipo"),
                ("name", "Descripción"),
                ("project", "Proyecto"),
                ("state", "Estado administrativo"),
                ("maintenance", "Mantenimiento"),
                ("relation", "Relación con traslado"),
            ],
            links=True,
        )
        if rows
        else empty(description="Amplía los filtros o revisa las fuentes."),
        html.P(
            "Ordena por los encabezados o utiliza sus filtros. "
            "Abre la ficha para revisar la evidencia.",
            className="table-hint",
        ),
    ]


def filter_links(context: QueryContext, path: str, filters: list[tuple[str, str]]):
    return html.Nav(
        [
            dcc.Link(
                label,
                href=context.href(path, filter=value),
                className="filter-link selected" if context.filter == value else "filter-link",
            )
            for value, label in filters
        ],
        className="filters",
        **{"aria-label": "Filtros de la consulta"},
    )


def requests(hub: HubResponse, context: QueryContext):
    items = requests_for(hub, context.filter)
    equipment = {item.id: item for item in hub.equipment}
    rows = [
        {
            "id": item.provenance.source_id,
            "project": item.project_name or "Sin proyecto informado",
            "state": item.status,
            "date": item.starts_on or "Sin fecha",
            "equipment": equipment_label(equipment[item.machinery_id])
            if item.machinery_id in equipment
            else item.machinery_id or "Sin unidad vinculada",
            "detail": _detail_markdown(item.machinery_id, context),
        }
        for item in items
    ]
    return [
        heading(
            "Solicitudes", "Revisa las fechas previstas y las asignaciones pendientes de resolver."
        ),
        filter_links(
            context,
            "/solicitudes",
            [
                ("all", "Todas"),
                ("pending_started", "Inicio alcanzado"),
                ("approved_unassigned", "Aprobadas sin unidad"),
            ],
        ),
        grid(
            "requests-grid",
            rows,
            [
                ("id", "Solicitud"),
                ("project", "Proyecto"),
                ("state", "Estado"),
                ("date", "Inicio previsto"),
                ("equipment", "Maquinaria"),
            ],
            links=True,
        )
        if rows
        else empty(description="No hay solicitudes para el origen y los filtros seleccionados."),
        html.P(
            "El inicio previsto orienta la revisión; no acredita un incumplimiento de entrega.",
            className="table-hint",
        ),
    ]


def transfers(hub: HubResponse, context: QueryContext):
    rows = [
        {
            "task": task.code,
            "equipment": equipment_label(item),
            "state": task.status,
            "request": task.request_id or "Sin solicitud vinculada",
            "destination": task.destination_project_name or "Sin destino informado",
            "driver": task.driver or "Sin motorista informado",
            "detail": _detail_markdown(item.id, context),
        }
        for item in hub.equipment
        for task in item.transfers
    ]
    return [
        heading("Traslados", "Tareas relacionadas con la maquinaria de esta consulta."),
        grid(
            "transfers-grid",
            rows,
            [
                ("task", "Tarea"),
                ("equipment", "Equipo"),
                ("state", "Estado del traslado"),
                ("request", "Solicitud vinculada"),
                ("destination", "Destino"),
                ("driver", "Motorista"),
            ],
            links=True,
        )
        if rows
        else empty(
            "Sin traslados disponibles",
            "No hay tareas vinculadas en esta lectura. Revisa las fuentes y las correspondencias.",
        ),
        html.P(
            "Una tarea completada no demuestra recepción física ni disponibilidad del equipo.",
            className="table-hint",
        ),
    ]


def provenance(record: Provenance):
    return html.Dl(
        [
            html.Dt("Fuente"),
            html.Dd("Prisma / Nexus" if record.source == "nexus" else "Startrack"),
            html.Dt("ID original"),
            html.Dd(html.Code(record.source_id)),
            html.Dt("Entorno"),
            html.Dd("Local" if record.environment == "local" else "Sandbox"),
            html.Dt("Lectura"),
            html.Dd(instant(record.observed_at)),
            html.Dt("Naturaleza"),
            html.Dd("Datos sintéticos" if record.is_synthetic else "Datos de la fuente"),
        ],
        className="provenance",
    )


def equipment_detail(hub: HubResponse, context: QueryContext, identifier: str):
    item = next((item for item in hub.equipment if item.id == identifier), None)
    back = dcc.Link(
        "← Volver a maquinaria", href=context.href("/maquinaria"), className="back-link"
    )
    if item is None:
        return [
            back,
            empty(
                "Equipo fuera de la consulta",
                "Comprueba el origen y limpia la búsqueda para ampliar el alcance.",
            ),
        ]
    stopped = (
        "Sí"
        if item.maintenance_is_stopped is True
        else "No"
        if item.maintenance_is_stopped is False
        else "Sin información"
    )
    facts = [
        ("Estado administrativo", item.machinery_status),
        ("Mantenimiento", item.maintenance_status or "Sin información"),
        ("Paro registrado", stopped),
        (
            "Última ubicación",
            item.location.label if item.location else "Sin observación disponible",
        ),
    ]
    related = [request for request in hub.requests if request.id in item.request_ids]
    operations = []
    for request in related:
        tasks = [task for task in item.transfers if task.request_id == request.id]
        operations.append(
            html.Section(
                [
                    html.H3(request.project_name or "Proyecto sin nombre"),
                    html.P(
                        f"Solicitud {request.provenance.source_id} · {request.status} · "
                        f"Inicio {request.starts_on or 'sin fecha'}"
                    ),
                    html.Ul(
                        [
                            html.Li(
                                f"{task.code} · {task.status} · "
                                f"Destino: {task.destination_project_name or 'sin informar'}"
                            )
                            for task in tasks
                        ]
                    )
                    if tasks
                    else html.P("Sin tarea vinculada a esta solicitud."),
                    html.Details(
                        [
                            html.Summary("Procedencia de la solicitud"),
                            provenance(request.provenance),
                        ]
                    ),
                ],
                className="operation",
            )
        )
    all_tasks = [
        html.Details(
            [
                html.Summary(f"{task.code} · {task.status}"),
                html.P(f"Solicitud vinculada: {task.request_id or 'sin vínculo'}"),
                html.P(f"Destino: {task.destination_project_name or 'sin informar'}"),
                html.P(f"Motorista: {task.driver or 'sin informar'}"),
                provenance(task.provenance),
            ]
        )
        for task in item.transfers
    ]
    own_hub = hub.model_copy(
        update={
            "alerts": [alert for alert in hub.alerts if alert.equipment_id == item.id],
        }
    )
    return [
        back,
        heading(
            f"{equipment_label(item)} · {item.name}", item.project_name or "Sin proyecto informado"
        ),
        notice(RELATIONS[item.relation_status], item.relation_note),
        html.Div(
            [
                html.Div([html.Span(label), html.Strong(value)], className="fact")
                for label, value in facts
            ],
            className="facts",
        ),
        html.P(
            f"Observación de ubicación: {instant(item.location.observed_at)}"
            if item.location
            else "La ausencia de ubicación no indica que el equipo esté detenido.",
            className="table-hint",
        ),
        html.Section(
            [
                html.H2("Solicitud y traslado"),
                *(
                    operations
                    or [
                        empty(
                            "Sin solicitudes vinculadas",
                            "No hay una relación comprobada en esta consulta.",
                        )
                    ]
                ),
            ]
        ),
        html.Section(
            [html.H2("Atención para este equipo"), exceptions(own_hub, context, expanded=True)],
            className="detail-section",
        )
        if own_hub.alerts
        else None,
        html.Section(
            [
                html.H2("Evidencia y procedencia"),
                html.P(
                    f"Código: {item.code or 'sin código'} · "
                    f"Número de activo: {item.asset_number or 'sin número informado'}"
                ),
                html.Details([html.Summary("Registro de maquinaria"), provenance(item.provenance)]),
                *all_tasks,
                html.Details(
                    [html.Summary("Observación de ubicación"), provenance(item.location.provenance)]
                )
                if item.location
                else None,
            ],
            className="detail-section",
        ),
    ]


def sources(hub: HubResponse, context: QueryContext):
    equipment_total = hub.scope.equipment_total
    requests_total = hub.scope.requests_total
    links = {"nexus": "https://econ-key.maic.ai", "startrack": "https://staging.gps.gt"}
    records = []
    for source in hub.sources:
        platform = links[source.id]
        records.append(
            html.Section(
                [
                    html.Div(
                        [
                            html.H2(source.label),
                            html.Span(SOURCE_STATES[source.status], className="source-status"),
                        ],
                        className="section-heading",
                    ),
                    html.P(source.message),
                    html.Dl(
                        [
                            html.Dt("Entorno"),
                            html.Dd(source.environment),
                            html.Dt("Última lectura"),
                            html.Dd(instant(source.observed_at)),
                        ],
                        className="provenance",
                    ),
                    html.A(
                        "Abrir plataforma ↗",
                        href=platform,
                        target="_blank",
                        rel="noopener noreferrer",
                    ),
                ],
                className="source-section",
            )
        )
    return [
        heading(
            "Fuentes y cobertura",
            "Qué información está disponible y hasta dónde llega esta lectura.",
        ),
        *records,
        html.Section(
            [
                html.H2("Alcance de los datos"),
                html.P(hub.scope.description),
                html.P(
                    f"Equipos devueltos: {hub.scope.equipment_returned} / "
                    f"{equipment_total if equipment_total is not None else '—'}. "
                    f"Solicitudes devueltas: {hub.scope.requests_returned} / "
                    f"{requests_total if requests_total is not None else '—'}. "
                    "Un total desconocido se muestra como —."
                ),
                html.P(
                    "La lectura y la observación de ubicación tienen fechas diferentes. "
                    "Una lectura reciente no actualiza una posición antigua."
                ),
            ],
            className="detail-section",
        ),
    ]


def render_page(path: str, hub: HubResponse, context: QueryContext):
    pages = {
        "/": overview,
        "/maquinaria": machinery,
        "/solicitudes": requests,
        "/traslados": transfers,
        "/fuentes": sources,
    }
    if path.startswith("/maquinaria/"):
        content = equipment_detail(hub, context, unquote(path.removeprefix("/maquinaria/")))
    elif path == "/alertas":
        content = [
            heading(
                "Atención", "Condiciones que requieren revisión y la evidencia que las sustenta."
            ),
            exceptions(hub, context, expanded=True),
        ]
    elif path in pages:
        content = pages[path](hub, context)
    else:
        content = [
            heading("Página no encontrada", "La dirección no corresponde a una vista del hub."),
            dcc.Link("Ir a vista general", href=context.href()),
        ]
    return [*content, coverage(hub, context)]
