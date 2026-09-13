"""Request-centered operational views with explicit gaps in source evidence."""

import re
from collections import Counter
from datetime import date
from urllib.parse import unquote

import dash_ag_grid as dag
from dash import dcc, html

from app.dashboard.analytics import (
    equipment_label,
    instant,
    readable,
    request_operation,
)
from app.dashboard.context import QueryContext
from app.dashboard.icons import icon
from app.models.hub import EquipmentRecord, HubResponse, Provenance, RequestRecord

NAVIGATION = [
    ("/", "Resumen"),
    ("/maquinaria", "Maquinaria"),
    ("/solicitudes", "Solicitudes"),
    ("/operaciones", "Operaciones"),
    ("/fuentes", "Fuentes"),
]
NAVIGATION_ICONS = {
    "/": "overview",
    "/maquinaria": "equipment",
    "/solicitudes": "requests",
    "/operaciones": "operations",
    "/fuentes": "sources",
}
SOURCE_STATES = {
    "fixture": "Muestras del contrato",
    "connected": "Conectada",
    "partial": "Lectura parcial",
    "not_configured": "Pendiente de conexión",
    "disabled": "Consulta desactivada",
    "error": "Error de lectura",
    "not_queried": "Sin consulta actual",
}
RELATIONS = {
    "confirmed": "Vínculo confirmado",
    "candidate": "Vínculo por revisar",
    "unlinked": "Sin vínculo confirmado",
}


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
    selected = (
        "/"
        if path in {"/", "/resumen"}
        else "/solicitudes"
        if path.startswith("/solicitudes")
        else "/maquinaria"
        if path == "/maquinaria" or path.startswith("/maquinaria/")
        else "/operaciones"
        if path.startswith("/operaciones")
        else "/fuentes"
        if path == "/fuentes"
        else None
    )
    return [
        dcc.Link(
            html.Span(
                [icon(NAVIGATION_ICONS[route]), html.Span(label)],
                className="nav-label",
                **({"aria-current": "page"} if selected == route else {}),
            ),
            href=context.href(route),
            className="nav-link"
            + (" active" if selected == route else "")
            + (" nav-utility" if route == "/fuentes" else ""),
        )
        for route, label in NAVIGATION
    ]


def scope(hub: HubResponse, context: QueryContext | None = None, workflow=None):
    mode = "Muestras proporcionadas" if hub.mode == "fixture" else "Sandbox actual (sintético)"
    count = f"{hub.scope.requests_returned} solicitudes"
    if context is not None and context.filter != "all":
        from app.dashboard.decision_analytics import requests_in_scope

        selected = len(requests_in_scope(hub, context, workflow))
        count = f"{selected} de {hub.scope.requests_returned} solicitudes"
    return html.Div(
        [
            html.Span(mode, className="scope-mode"),
            html.Span(count),
            html.Span("Cobertura completa" if hub.scope.complete else "Cobertura parcial"),
            html.Span(
                f"{hub.scope.equipment_returned} de {hub.scope.equipment_total} equipos"
                if hub.scope.equipment_total is not None
                else f"{hub.scope.equipment_returned} equipos · total desconocido"
            ),
        ],
        className="scope-line",
    )


def coverage(hub: HubResponse, context: QueryContext):
    return html.Div(
        dcc.Link("Consultar fuentes y cobertura", href=context.href("/fuentes")),
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
        role="region",
        tabIndex=0,
        **{"aria-label": caption},
    )


def grid(
    identifier: str,
    rows: list[dict],
    columns: list[tuple[str, str]],
    *,
    links=False,
    link_field: str | None = None,
):
    definitions = [{"field": key, "headerName": title} for key, title in columns]
    for definition in definitions:
        if definition["field"] == link_field:
            definition["cellRenderer"] = "markdown"
    if links:
        definitions.insert(
            1,
            {
                "field": "detail",
                "headerName": "Evidencia",
                "cellRenderer": "markdown",
                "filter": False,
                "sortable": False,
                "minWidth": 125,
                "maxWidth": 135,
            },
        )
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
            "theme": {
                "function": (
                    "themeQuartz.withParams({fontFamily:'Inter, sans-serif',fontSize:13,"
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
            "rowHeight": 76,
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
    )


def equipment_link(item: EquipmentRecord, context: QueryContext):
    return dcc.Link(equipment_label(item), href=context.equipment_href(item.id))


def project_label(request: RequestRecord) -> str:
    return " · ".join(filter(None, [request.project_id, request.project_name])) or "Sin proyecto"


def period_label(request: RequestRecord) -> str:
    def display(value):
        try:
            return date.fromisoformat(value).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return value or "Sin fecha"

    return f"{display(request.starts_on)} — {display(request.ends_on)}"


def markdown_link(label: str, href: str) -> str:
    escaped = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", label)
    return f"[{escaped}]({href})"


def request_label(request: RequestRecord) -> str:
    return request.provenance.source_id or "Sin ID de origen"


def filter_links(context: QueryContext):
    return html.Nav(
        [
            dcc.Link(
                label,
                href=context.href("/solicitudes", filter=value),
                className="filter-link selected" if context.filter == value else "filter-link",
            )
            for value, label in [
                ("all", "Todas las solicitudes"),
                ("unassigned", "Sin unidad asignada"),
                ("unlinked", "Sin traslado confirmado"),
                ("active_failures", "Con falla en la unidad"),
            ]
        ],
        className="filters",
        **{"aria-label": "Filtros de solicitudes"},
    )


def requests(hub: HubResponse, context: QueryContext, workflow=None):
    from app.dashboard.decision_analytics import matching_current_movements, requests_in_scope
    from app.dashboard.evidence_views import operation_read_message
    from app.dashboard.workflow_views import (
        STATES,
        receipt_label,
    )

    operations = [
        request_operation(hub, request) for request in requests_in_scope(hub, context, workflow)
    ]
    rows = []
    for operation in operations:
        request, item, tasks = operation.request, operation.equipment, operation.transfers
        movements = matching_current_movements(hub, request, workflow)
        states = Counter(movement.status or STATES[movement.state] for movement in movements)
        transfer = " · ".join(
            f"{state} ({count})" if count > 1 else state for state, count in states.items()
        )
        if not transfer:
            transfer = " · ".join(dict.fromkeys(task.status for task in tasks))
        arrived = sum(
            any(event.kind == "arrival" for event in movement.events) for movement in movements
        )
        if arrived:
            transfer += " · Llegada observada" + (
                f" ({arrived}/{len(movements)})" if len(movements) > 1 else ""
            )
        received = sum(movement.receipt is not None for movement in movements)
        receipt = (
            receipt_label(movements[0])
            if len(movements) == 1
            else f"{received} de {len(movements)} con constancia"
            if received
            else "Sin constancia"
        )
        unknown = operation_read_message(workflow)
        if unknown:
            transfer = f"{transfer} · {unknown}" if transfer else unknown
            receipt = unknown
        unit = (
            equipment_label(item)
            if item
            else ("Unidad fuera de consulta" if request.machinery_id else "Sin unidad asignada")
        )
        rows.append(
            {
                "project": markdown_link(
                    request.project_name or "Proyecto sin nombre", context.request_href(request.id)
                ),
                "status": request.status,
                "period": period_label(request),
                "equipment": f"{request.machinery_type or 'Tipo sin informar'} · {unit}",
                "transfer": transfer or "Sin traslado vinculado",
                "receipt": receipt,
            }
        )
    content = [
        heading(
            "Solicitudes de maquinaria",
            "Del proyecto y la unidad asignada al traslado, la llegada y la recepción.",
        ),
        filter_links(context),
    ]
    if not readable(hub):
        content.append(
            empty(
                "Sin datos para consultar la operación",
                "Las fuentes no aportaron solicitudes. Revisa su estado en Fuentes y cobertura.",
            )
        )
    elif rows:
        content.append(
            grid(
                "requests-grid",
                rows,
                [
                    ("project", "Proyecto · solicitud"),
                    ("equipment", "Maquinaria"),
                    ("period", "Período solicitado"),
                    ("status", "Estado de solicitud"),
                    ("transfer", "Traslado"),
                    ("receipt", "Recepción"),
                ],
                link_field="project",
            )
        )
    else:
        content.append(
            empty(
                "Sin solicitudes en esta consulta",
                "No se recibió una solicitud para este origen, búsqueda y filtro.",
            )
        )
    content.append(
        html.P(
            "Abre una solicitud para revisar la cadena completa. "
            "Una tarea completada o una entrada a geocerca no acredita recepción física.",
            className="table-hint",
        )
    )
    assigned_ids = {request.machinery_id for request in hub.requests}
    unassigned = [item for item in hub.equipment if item.id not in assigned_ids]
    if unassigned and context.filter == "all":
        content.append(
            html.Details(
                [
                    html.Summary("Maquinaria sin solicitud vinculada en esta consulta"),
                    html.P(
                        "Estos registros se conservan como referencia. Su proyecto administrativo "
                        "no establece una relación con una solicitud."
                    ),
                    simple_table(
                        ["Maquinaria", "Proyecto informado", "Estado administrativo", "Referencia"],
                        [
                            [
                                equipment_link(item, context),
                                " · ".join(filter(None, [item.project_id, item.project_name]))
                                or "Sin proyecto",
                                item.machinery_status,
                                html.Code(item.provenance.source_id),
                            ]
                            for item in unassigned
                        ],
                        caption="Maquinaria recibida sin relación exacta con las solicitudes",
                    ),
                ],
                className="reference-records",
            )
        )
    return content


def provenance(record: Provenance):
    nature = {
        "provided_sample": "Muestra del contrato proporcionado",
        "test_case": "Caso interno de prueba",
        "live_read": "Lectura del sandbox",
    }
    return html.Dl(
        [
            html.Dt("Fuente"),
            html.Dd("Prisma / Nexus" if record.source == "nexus" else "Startrack"),
            html.Dt("ID original"),
            html.Dd(html.Code(record.source_id) if record.source_id else "No proporcionado"),
            html.Dt("Entorno"),
            html.Dd("Local" if record.environment == "local" else "Sandbox"),
            html.Dt("Lectura"),
            html.Dd(instant(record.observed_at) if record.observed_at else "Sin lectura fechada"),
            html.Dt("Naturaleza"),
            html.Dd(nature[record.evidence_kind]),
            html.Dt("Datos"),
            html.Dd("Sintéticos del sandbox" if record.is_synthetic else "De la fuente"),
            html.Dt("Referencia"),
            html.Dd(record.source_reference or "Sin referencia adicional"),
            html.Dt("Fecha documental"),
            html.Dd(record.observed_on.strftime("%d/%m/%Y") if record.observed_on else "Sin fecha"),
        ],
        className="provenance",
    )


def facts(values: list[tuple[str, str]]):
    return html.Dl(
        [html.Div([html.Dt(label), html.Dd(value)], className="fact") for label, value in values],
        className="facts",
    )


def machine_evidence(item: EquipmentRecord, context: QueryContext):
    stopped = (
        "Sí"
        if item.maintenance_is_stopped is True
        else "No"
        if item.maintenance_is_stopped is False
        else "Sin información"
    )
    return [
        facts(
            [
                ("Unidad", f"{equipment_label(item)} · {item.name}"),
                ("Estado administrativo", item.machinery_status),
                ("Mantenimiento", item.maintenance_status or "Sin información"),
                ("Paro registrado", stopped),
            ]
        ),
        html.P(f"Falla activa: {item.maintenance_failure_id or 'Sin referencia informada'}"),
        html.P(
            f"Última ubicación: {item.location.label} · {instant(item.location.observed_at)}"
            if item.location
            else "Ubicación: sin observación disponible."
        ),
        html.Details([html.Summary("Procedencia de la unidad"), provenance(item.provenance)]),
        html.Details(
            [html.Summary("Procedencia de la ubicación"), provenance(item.location.provenance)]
        )
        if item.location
        else None,
    ]


def request_detail(hub: HubResponse, context: QueryContext, identifier: str, workflow=None):
    from app.dashboard.decision_analytics import matching_current_movements
    from app.dashboard.evidence_views import (
        interpretation_section,
        operation_read_message,
        request_timeline,
    )
    from app.dashboard.workflow_views import (
        matching_movements,
        remaining_evidence,
        request_workflow,
    )

    request = next((item for item in hub.requests if item.id == identifier), None)
    back = dcc.Link(
        [icon("back"), "Volver a solicitudes"],
        href=context.href("/solicitudes", filter=context.filter),
        className="back-link",
    )
    if request is None:
        return [
            back,
            empty(
                "Solicitud fuera de la consulta",
                "Comprueba el origen y limpia la búsqueda para ampliar el alcance.",
            ),
        ]
    operation = request_operation(hub, request)
    item = operation.equipment
    movements = matching_movements(workflow, request)
    current_movements = matching_current_movements(hub, request, workflow)
    unknown = operation_read_message(workflow)
    task_sections = []
    for task in operation.transfers:
        task_sections.append(
            html.Div(
                [
                    html.H3(f"{task.code} · {task.status}"),
                    facts(
                        [
                            ("Destino", task.destination_project_name or "Sin informar"),
                            ("Motorista", task.driver or "Sin informar"),
                        ]
                    ),
                    html.P(RELATIONS[item.relation_status]),
                    html.P(item.relation_note),
                    html.Details(
                        [
                            html.Summary("Referencias del traslado"),
                            facts(
                                [
                                    ("Solicitud vinculada", task.request_id or "Sin ID"),
                                    (
                                        "ID del destino",
                                        task.destination_project_id or "Sin informar",
                                    ),
                                ]
                            ),
                            provenance(task.provenance),
                        ]
                    ),
                ],
                className="transfer-record",
            )
        )
    request_alerts = [
        alert
        for alert in hub.alerts
        if alert.request_id == request.id
        or (item and alert.equipment_id == item.id and not alert.request_id)
    ]
    content = [
        back,
        heading(
            f"Solicitud de {request.machinery_type}"
            if request.machinery_type
            else "Solicitud de maquinaria",
            request.project_name or "Proyecto sin nombre",
        ),
        html.Section(
            [
                html.H2("Solicitud"),
                facts(
                    [
                        ("Estado de la solicitud", request.status),
                        ("Período solicitado", period_label(request)),
                        (
                            "Unidad asignada",
                            equipment_link(item, context)
                            if item
                            else "Unidad fuera de consulta"
                            if request.machinery_id
                            else "Sin unidad asignada",
                        ),
                    ]
                ),
                html.P(f"Observaciones: {request.comments}") if request.comments else None,
                html.P(
                    "Los movimientos guardados no coinciden con la asignación actual. "
                    "Revisa el traslado de esta unidad."
                )
                if movements and not current_movements
                else None,
                html.Details(
                    [
                        html.Summary("Datos y referencias de la solicitud"),
                        facts(
                            [
                                ("Solicitante", request.requested_by or "Sin informar"),
                                (
                                    "ID de quien aprobó",
                                    getattr(request, "approved_by_user_id", None)
                                    or "No proporcionado",
                                ),
                                ("Fecha de aprobación", instant(request.approved_at)),
                                ("ID de proyecto", request.project_id or "Sin ID de proyecto"),
                                (
                                    "ID de maquinaria asignada",
                                    request.machinery_id or "Sin asignación",
                                ),
                            ]
                        ),
                        provenance(request.provenance),
                    ]
                ),
            ],
            className="detail-section",
        ),
        html.Details(
            [
                html.Summary(
                    "Estado de la unidad · paro registrado"
                    if item and item.maintenance_is_stopped
                    else "Estado y mantenimiento de la unidad"
                ),
                *(
                    machine_evidence(item, context)
                    if item
                    else [
                        empty(
                            "Registro de maquinaria fuera de la consulta"
                            if request.machinery_id
                            else "Sin unidad asignada",
                            "La solicitud tiene una unidad asignada, pero su registro no está "
                            "en esta consulta. Revisa las referencias de la solicitud."
                            if request.machinery_id
                            else "La solicitud no informa una unidad concreta. "
                            "El proyecto o el tipo solicitado no permiten "
                            "elegirla automáticamente.",
                        )
                    ]
                ),
            ],
            className="detail-section detail-disclosure",
        ),
        html.Section(
            [
                html.H2("Traslado de Startrack"),
                *(
                    task_sections
                    or [
                        empty(
                            unknown or "Sin traslado vinculado a esta solicitud",
                            "La consulta de operaciones no permite determinar "
                            "los movimientos vinculados."
                            if unknown
                            else "Falta una tarea con correspondencia de solicitud y maquinaria "
                            "validada en los registros consultados. Los nombres "
                            "no confirman esa relación.",
                        )
                    ]
                ),
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Llegada y recepción"),
                facts(
                    [
                        ("Llegada al destino", unknown or "Sin evidencia de llegada vinculada"),
                        ("Recepción física", unknown or "Sin constancia de recepción"),
                    ]
                ),
                html.P(
                    "El estado de una tarea y la ubicación del GPS son hechos distintos. "
                    "Una entrada a geocerca no confirma que el proyecto haya recibido "
                    "la maquinaria."
                ),
            ],
            className="detail-section",
        ),
        html.Details(
            [
                html.Summary("Revisar evidencia pendiente"),
                html.Ul(
                    [
                        html.Li(value)
                        for value in (
                            [
                                "Consultar el registro de operaciones para determinar "
                                "la evidencia pendiente."
                            ]
                            if unknown
                            else remaining_evidence(operation.missing, current_movements)
                        )
                    ]
                ),
            ],
            className="detail-section detail-disclosure",
        ),
    ]
    if movements:
        content[4:6] = []
    content[4:4] = request_workflow(workflow, context, request, item)
    if item:
        content.insert(3, interpretation_section(item, current_movements))
    content.append(request_timeline(request, movements, context))
    if request_alerts:
        content.append(
            html.Section(
                [
                    html.H2("Condiciones que requieren revisión"),
                    *[
                        html.Div(
                            [
                                html.H3(alert.title),
                                html.P(alert.description),
                                html.P(f"Área de revisión: {alert.owner}"),
                                html.Details(
                                    [
                                        html.Summary("Evidencia de la condición"),
                                        html.Ul(
                                            [html.Li(html.Code(value)) for value in alert.evidence]
                                        ),
                                    ]
                                ),
                            ],
                            className="alert-reason",
                        )
                        for alert in request_alerts
                    ],
                ],
                className="detail-section",
            )
        )
    return content


def equipment_detail(hub: HubResponse, context: QueryContext, identifier: str, workflow=None):
    from app.dashboard.evidence_views import (
        equipment_movements,
        interpretation_section,
        source_comparison,
    )
    from app.dashboard.workflow_views import workflow_table

    item = next((item for item in hub.equipment if item.id == identifier), None)
    back = dcc.Link(
        [icon("back"), "Volver a maquinaria"],
        href=context.href("/maquinaria", filter=context.filter),
        className="back-link",
    )
    if item is None:
        return [
            back,
            empty(
                "Equipo fuera de la consulta",
                "Comprueba el origen y limpia la búsqueda para ampliar el alcance.",
            ),
        ]
    related = [request for request in hub.requests if request.machinery_id == item.id]
    movements = equipment_movements(hub, item, workflow)
    return [
        back,
        heading(f"{equipment_label(item)} · {item.name}", "Evidencia de la maquinaria consultada."),
        interpretation_section(item, movements),
        *source_comparison(item, movements, workflow, context, hub),
        html.Section(
            [
                html.H2("Solicitudes con esta unidad asignada"),
                simple_table(
                    ["Proyecto / solicitud", "Estado de solicitud", "Período solicitado"],
                    [
                        [
                            dcc.Link(project_label(request), href=context.request_href(request.id)),
                            request.status,
                            period_label(request),
                        ]
                        for request in related
                    ],
                    caption="Solicitudes que asignan esta maquinaria por su ID",
                )
                if related
                else html.P(
                    "No se recibió una solicitud que asigne esta unidad por su ID. "
                    "El proyecto administrativo no prueba una solicitud ni un traslado."
                ),
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Movimientos de la asignación consultada"),
                workflow_table(movements, context),
                html.P(
                    "Los vínculos coinciden con los IDs, el origen y el período solicitado. "
                    "Cada movimiento conserva su propia tarea y constancia."
                ),
            ],
            className="detail-section",
        )
        if movements
        else None,
    ]


def sources(hub: HubResponse, context: QueryContext, workflow=None):
    links = {"nexus": "https://econ-key.maic.ai", "startrack": "https://staging.gps.gt"}
    request_total = (
        hub.scope.requests_total if hub.scope.requests_total is not None else "total desconocido"
    )
    equipment_total = (
        hub.scope.equipment_total if hub.scope.equipment_total is not None else "total desconocido"
    )
    records = []
    for source in hub.sources:
        records.append(
            html.Section(
                [
                    html.Div(
                        [
                            html.H2(source.label),
                            html.Span(
                                SOURCE_STATES[source.status],
                                className="source-status",
                            ),
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
                            html.Dt("Fecha documental"),
                            html.Dd(
                                source.observed_on.strftime("%d/%m/%Y")
                                if source.observed_on
                                else "Sin fecha"
                            ),
                        ],
                        className="provenance",
                    ),
                    html.P(
                        "La ausencia de tareas en el corte de Prisma no determina si existen "
                        "tareas o visitas en Startrack. Revisa la evidencia de cada movimiento."
                    )
                    if source.id == "startrack"
                    else None,
                    html.P(
                        "Última evidencia conservada: "
                        f"{instant(getattr(source, 'last_evidence_at', None))}"
                    )
                    if source.id == "startrack"
                    else None,
                    html.A(
                        "Abrir plataforma ↗",
                        href=links[source.id],
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
            "Procedencia de las solicitudes, unidades y tareas disponibles en esta consulta.",
        ),
        *records,
        html.Section(
            [
                html.H2("Registro de operaciones"),
                html.P(workflow.message if workflow else "Consultando el registro de movimientos…"),
                html.P(
                    f"Última sincronización registrada: {instant(workflow.last_sync_at)}. "
                    "Cada evidencia conserva su propia fecha de origen."
                    if workflow and workflow.last_sync_at
                    else "Sin sincronización registrada."
                ),
                html.P(
                    "Gestión local habilitada."
                    if workflow and workflow.management_enabled
                    else "Solo consulta: la gestión no está habilitada en esta conexión."
                ),
                html.P(
                    "Envío a Startrack habilitado para los movimientos autorizados."
                    if workflow and workflow.sending_enabled
                    else "Envío a Startrack deshabilitado."
                ),
                dcc.Link("Revisar movimientos y evidencia", href=context.href("/operaciones")),
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Alcance de la lectura"),
                html.P(
                    "Esta consulta de solicitudes y maquinaria tiene cobertura parcial. "
                    "El registro de movimientos conserva por separado tareas, visitas y "
                    "constancias vinculadas por ID."
                    if hub.mode == "live"
                    else hub.scope.description
                ),
                html.P(
                    f"Solicitudes: {hub.scope.requests_returned} de {request_total}. "
                    f"Maquinaria: {hub.scope.equipment_returned} de {equipment_total}."
                ),
                html.P(
                    "La lectura y la observación de ubicación tienen fechas diferentes. "
                    "Una lectura reciente no actualiza una posición antigua."
                ),
            ],
            className="detail-section",
        ),
    ]


def render_page(path: str, hub: HubResponse, context: QueryContext, workflow=None):
    if path in {"/", "/resumen"}:
        from app.dashboard.decision_views import overview

        content = [overview(hub, context, workflow)]
    elif path == "/solicitudes":
        content = requests(hub, context, workflow)
    elif path.startswith("/solicitudes/"):
        content = request_detail(
            hub, context, unquote(path.removeprefix("/solicitudes/")), workflow
        )
    elif path == "/operaciones" or path.startswith("/operaciones/"):
        from app.dashboard.workflow_views import workflow_page

        content = workflow_page(path, workflow, context)
    elif path == "/maquinaria":
        from app.dashboard.equipment_views import equipment_inventory

        content = equipment_inventory(hub, context)
    elif path.startswith("/maquinaria/"):
        content = equipment_detail(
            hub, context, unquote(path.removeprefix("/maquinaria/")), workflow
        )
    elif path == "/fuentes":
        content = sources(hub, context, workflow)
    else:
        content = [
            heading(
                "Página no encontrada", "La dirección no corresponde a una vista de solicitudes."
            ),
            dcc.Link("Ir a solicitudes", href=context.href("/solicitudes")),
        ]
    return content
