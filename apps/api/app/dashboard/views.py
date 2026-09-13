"""Pages of the hub: registry, navigation, lists, details and sources."""

from urllib.parse import unquote

import dash_mantine_components as dmc

from app.core.auth import Permission, can
from app.dashboard.admin_views import admin_page
from app.dashboard.analytics import (
    day,
    equipment_label,
    instant,
    project_label,
    readable,
    request_operation,
)
from app.dashboard.auth_views import current_user
from app.dashboard.components import (
    accordion,
    breadcrumbs,
    disclosure,
    empty,
    facts,
    grid,
    heading,
    hint,
    icon,
    link,
    markdown_link,
    notice,
    provenance,
    rows_table,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.dashboard.coverage_analytics import coverage_figure, coverage_rows
from app.dashboard.decision_analytics import (
    graph,
    matching_current_movements,
    request_states,
    requests_in_scope,
    usage_figure,
    usage_timeline,
)
from app.dashboard.decision_priorities import decision_items
from app.dashboard.evidence_views import (
    SOURCE_STATES,
    equipment_movements,
    interpretation_section,
    location_facts,
    maintenance_facts,
    operation_read_message,
    request_timeline,
    source_comparison,
)
from app.dashboard.indicator_views import indicators_page
from app.dashboard.integration_views import integration_page
from app.dashboard.inventory_analytics import inventory_status_panel
from app.dashboard.suggestion_views import conflicts_section, suggestions_section
from app.dashboard.theme import state_color
from app.dashboard.workflow_views import (
    STATES,
    matching_movements,
    remaining_evidence,
    request_workflow,
    workflow_page,
    workflow_table,
)
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord

MODES = {"fixture": "Muestras proporcionadas", "live": "Sandbox actual (sintético)"}
# Only the lists let `q` narrow what is shown; every other page keeps the origin as text.
SEARCHABLE = frozenset({"/solicitudes", "/maquinaria", "/operaciones"})
RELATIONS = {
    "confirmed": "Vínculo confirmado",
    "candidate": "Vínculo por revisar",
    "unlinked": "Sin vínculo confirmado",
}
REQUEST_FILTERS = [
    ("all", "Todas las solicitudes"),
    ("unassigned", "Sin unidad asignada"),
    ("unlinked", "Sin traslado confirmado"),
    ("active_failures", "Con falla en la unidad"),
]
EQUIPMENT_FILTERS = [
    ("all", "Toda la maquinaria"),
    ("active_failures", "Con falla activa registrada"),
    ("unlinked", "Vínculo con Startrack por revisar"),
]
FILTER_LABELS = {
    "unassigned": "sin unidad",
    "unlinked": "sin tarea confirmada",
    "approved_unassigned": "aprobadas sin unidad",
    "active_failures": "con falla registrada",
    "pending_started": "pendientes con inicio alcanzado",
}
PLATFORMS = {"nexus": "https://econ-key.maic.ai", "startrack": "https://staging.gps.gt"}


def current_section(path: str) -> str | None:
    if path in {"/", "/resumen", "/decisiones"}:
        return "/"
    return next(
        (
            page["path"]
            for page in PAGES
            if page["path"] != "/" and (path == page["path"] or path.startswith(page["path"] + "/"))
        ),
        None,
    )


def visible_pages():
    """Pages the acting role may open; a page without `permission` is open to every role."""
    user = current_user()
    return [
        page
        for page in PAGES
        if not page.get("permission") or (user is not None and can(user.role, page["permission"]))
    ]


def navigation(path: str, context: QueryContext):
    """Navigation links for the sidebar and the mobile drawer; one section is current."""
    selected = current_section(path)
    pages = visible_pages()
    links = []
    for secondary, label in [(False, "Operación"), (True, "Sistema")]:
        group = [page for page in pages if bool(page.get("secondary")) == secondary]
        if not group:
            continue
        links.append(dmc.Text(label, size="xs", fw=600, className="nav-group-label"))
        links.extend(
            dmc.NavLink(
                label=page["label"],
                leftSection=icon(page["icon"]),
                href=QueryContext(mode=context.mode).href(page["path"]),
                active=selected == page["path"],
                className="nav-link" + (" nav-utility" if secondary else ""),
                **({"aria-current": "page"} if selected == page["path"] else {}),
            )
            for page in group
        )
    return links


def searchable(path: str | None) -> bool:
    """Whether this page shows the full query bar; details and utilities never do."""
    normalized = (path or "/").rstrip("/") or "/"
    return normalized in SEARCHABLE


def origin_link(context: QueryContext, path: str):
    """Change the data source from a page without the query bar, keeping mode/q/filter."""
    other = "live" if context.mode == "fixture" else "fixture"
    alternate = QueryContext(mode=other, query=context.query, filter=context.filter)
    return link(
        f"Cambiar a {MODES[other].lower()}",
        alternate.href(path, filter=context.filter),
        size="xs",
    )


def origin_line(context: QueryContext, path: str):
    """Scope line for pages without the query bar: origin as text plus one way to change it."""
    return dmc.Group(
        [
            dmc.Text(
                "Muestra documental" if context.mode == "fixture" else "Sandbox sintético",
                size="xs",
            ),
            reading_menu(context, path),
        ],
        gap="md",
        justify="space-between",
        className="scope-line",
    )


def reading_menu(context: QueryContext, path: str, *details):
    """Source details and real navigation links behind a keyboard-operable trigger."""
    return dmc.Menu(
        [
            dmc.MenuTarget(
                dmc.Button(
                    "Datos de la lectura",
                    variant="subtle",
                    size="compact-sm",
                    rightSection=icon("chevron-down", 14),
                    **{"aria-label": "Ver origen y cobertura de la lectura"},
                )
            ),
            dmc.MenuDropdown(
                dmc.Stack(
                    [
                        dmc.Text(MODES[context.mode], size="sm", fw=600),
                        *details,
                        origin_link(context, path),
                        link(
                            "Ver fuentes y cobertura",
                            QueryContext(mode=context.mode).href("/fuentes"),
                            size="sm",
                        ),
                    ],
                    gap="sm",
                    p="sm",
                )
            ),
        ],
        width=300,
        position="bottom-end",
        withinPortal=False,
        keepMounted=True,
    )


def scope(hub: HubResponse, context: QueryContext | None = None, workflow=None, path=None):
    context = context or QueryContext(mode=hub.mode)
    count = f"{hub.scope.requests_returned} solicitudes"
    if context is not None and context.filter != "all":
        selected = len(requests_in_scope(hub, context, workflow))
        count = f"{selected} de {hub.scope.requests_returned} solicitudes"
    equipment = (
        f"{hub.scope.equipment_returned} de {hub.scope.equipment_total} equipos"
        if hub.scope.equipment_total is not None
        else f"{hub.scope.equipment_returned} equipos · total desconocido"
    )
    coverage = "Cobertura completa" if hub.scope.complete else "Cobertura parcial"
    cutoff = instant(hub.data_as_of) if hub.data_as_of else "Sin corte de observación"
    return dmc.Group(
        [
            dmc.Text(
                f"{'Muestra documental' if hub.mode == 'fixture' else 'Sandbox sintético'} · "
                f"{coverage.lower()}",
                size="xs",
                className="scope-summary",
            ),
            reading_menu(
                context,
                path or "/",
                dmc.Text(f"{count} · {equipment}", size="sm"),
                dmc.Text(coverage, size="sm"),
                dmc.Text(cutoff, size="xs", c="dimmed"),
            ),
        ],
        gap="md",
        justify="space-between",
        className="scope-line",
    )


def filter_tabs(context: QueryContext, options: list[tuple[str, str]], label: str):
    values = {value for value, _ in options}
    return dmc.Tabs(
        dmc.TabsList([dmc.TabsTab(text, value=value) for value, text in options]),
        # Pattern id: pages without filters have no tabs, and the callback still registers.
        id={"type": "filter-tabs", "page": label},
        value=context.filter if context.filter in values else "all",
        mb="md",
        **{"aria-label": label},
    )


def unavailable(hub: HubResponse, context: QueryContext, subject: str):
    source = next((source for source in hub.sources if source.id == "nexus"), None)
    return notice(
        f"{subject}: origen no disponible",
        f"{SOURCE_STATES[source.status]}. {source.message}"
        if source
        else "La fuente principal no respondió a esta consulta.",
        error=True,
        children=[link("Revisar fuentes y cobertura", context.href("/fuentes"), mt="xs")],
    )


def state_legend(values: list[str]):
    return dmc.Group(
        [
            dmc.Group(
                [
                    dmc.Box(w=18, h=3, bg=state_color(value), **{"aria-hidden": "true"}),
                    state_text(value),
                ],
                gap="xs",
            )
            for value in dict.fromkeys(values)
        ],
        gap="lg",
        my="xs",
        **{"aria-label": "Leyenda de estados"},
    )


def decision_cards(hub, context, workflow):
    """The complete decision queue, with evidence beside the action it supports."""
    rows = [
        {
            "subject": markdown_link(item.title, context.request_href(item.request.id)),
            "project": item.request.project_name or "Sin proyecto",
            "equipment": equipment_label(item.equipment)
            if item.equipment is not None
            else "Sin unidad",
            "evidence": item.evidence.split(". ", 1)[0].removesuffix("."),
            "evidence_detail": item.evidence,
            "action": markdown_link(item.action, item.href),
        }
        for item in decision_items(hub, context, workflow)
    ]
    return grid(
        "decision-actions-grid",
        rows,
        [
            ("subject", "Asunto"),
            ("project", "Proyecto"),
            ("equipment", "Unidad"),
            ("evidence", "Motivo de revisión"),
            ("action", "Acción"),
        ],
        markdown_fields={"subject", "action"},
        column_overrides={
            "subject": {
                "width": 230,
                "minWidth": 180,
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
                "cellStyle": {"whiteSpace": "normal"},
            },
            "project": {"minWidth": 200, "flex": 1, "wrapText": True, "autoHeight": True},
            "equipment": {"width": 125, "minWidth": 125, "flex": 0, "filter": False},
            "evidence": {
                "width": 250,
                "minWidth": 190,
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
                "cellStyle": {"whiteSpace": "normal"},
                "tooltipField": "evidence_detail",
            },
            "action": {"width": 155, "minWidth": 155, "flex": 0, "filter": False},
        },
    )


def registry_hint(workflow):
    if workflow is None or not workflow.available:
        return hint(
            "Registro de tareas sin confirmar. Consulta las operaciones antes de concluir "
            "si un traslado está preparado o enviado.",
            role="status",
        )
    if not workflow.complete:
        return hint(
            "Registro de movimientos parcial. Una tarea sin confirmar en esta vista puede "
            "tener evidencia fuera de la ventana consultada.",
            role="status",
        )
    return None


def decisions(hub: HubResponse, context: QueryContext, workflow=None):
    """Source periods with assignment context, then the evidence-backed work queue."""
    context = QueryContext(mode=context.mode)
    content = [heading("Operación")]
    if context.mode != hub.mode or not readable(hub):
        return [*content, unavailable(hub, context, "Operación")]
    requests = requests_in_scope(hub, context, workflow)
    timeline = usage_timeline(requests)
    states = request_states(requests)
    agenda_chart = usage_figure(timeline)
    rows = [
        [
            link(
                period.request.project_name or "Sin proyecto",
                context.request_href(period.request.id),
            ),
            period.request.machinery_type or "Sin tipo",
            period.request.status,
            period.request.starts_on,
            period.request.ends_on,
            "Representado",
        ]
        for period in timeline.periods
    ]
    rows.extend(
        [
            link(
                item.request.project_name or "Sin proyecto", context.request_href(item.request.id)
            ),
            item.request.machinery_type or "Sin tipo",
            item.request.status,
            item.request.starts_on or "Sin informar",
            item.request.ends_on or "Sin informar",
            item.reason,
        ]
        for item in timeline.excluded
    )
    content.append(
        section(
            "Agenda de uso y asignación",
            hint("Fechas de uso solicitadas; no son plazos de entrega."),
            state_legend([request.status for request in requests]),
            graph("decision-request-usage", agenda_chart)
            if timeline.periods
            else hint(
                "Sin solicitudes en esta lectura."
                if not requests
                else "Sin períodos válidos para representar en esta lectura."
            ),
            hint(
                f"{len(timeline.excluded)} solicitudes con fechas no representables.", role="status"
            )
            if timeline.excluded
            else None,
            className="page-section agenda-panel",
        )
    )
    content.append(
        section(
            "Acciones por solicitud",
            decision_cards(hub, context, workflow),
            registry_hint(workflow),
        )
    )
    content.append(
        accordion(
            disclosure(
                "Datos de la agenda",
                simple_table(
                    ["Estado de solicitud", "Solicitudes"],
                    [[state, count] for state, count in states],
                    caption="Conteos por estado original de las solicitudes de esta lectura",
                ),
                simple_table(
                    [
                        "Proyecto / solicitud",
                        "Tipo",
                        "Estado",
                        "Inicio",
                        "Fin",
                        "Representación",
                    ],
                    rows,
                    caption="Períodos originales de uso y motivos de exclusión del gráfico",
                ),
                hint(
                    "Las fechas con hora se representan por su día en El Salvador. "
                    "La tabla conserva los valores originales."
                ),
            )
        ),
    )
    return content


def indicators(hub: HubResponse, context: QueryContext, workflow=None):
    """Indicators from the shared service over this very reading; guarded like every list."""
    if context.mode != hub.mode or not readable(hub):
        return [
            heading(
                "Indicadores",
                "Tiempos medidos y casos que requieren revisión.",
            ),
            unavailable(hub, context, "Indicadores"),
        ]
    return indicators_page(hub, context, workflow)


def overview(hub: HubResponse, context: QueryContext, workflow=None):
    """Start with operational decisions inside the regular application shell."""
    return decisions(hub, context, workflow)


def period_label(request: RequestRecord) -> str:
    return f"{day(request.starts_on)} — {day(request.ends_on)}"


def requests(hub: HubResponse, context: QueryContext, workflow=None):
    content = [
        heading(
            "Solicitudes de maquinaria",
            "Asignación, período y avance de cada solicitud.",
        ),
        filter_tabs(context, REQUEST_FILTERS, "Filtros de solicitudes"),
    ]
    if not readable(hub):
        return [*content, unavailable(hub, context, "Solicitudes")]
    next_steps = {item.request.id: item for item in decision_items(hub, context, workflow)}
    rows = []
    for request in requests_in_scope(hub, context, workflow):
        operation = request_operation(hub, request)
        item, tasks = operation.equipment, operation.transfers
        movements = matching_current_movements(hub, request, workflow)
        states = list(
            dict.fromkeys(movement.status or STATES[movement.state] for movement in movements)
        )
        if not states:
            states = list(dict.fromkeys(task.status for task in tasks if task.status))
        transfer = (
            states[0] if len(states) == 1 else "Varios estados" if states else "Sin tarea vinculada"
        )
        received = sum(movement.receipt is not None for movement in movements)
        receipt = (
            "Registrada"
            if received == 1 and len(movements) == 1
            else f"{received} registradas"
            if received
            else "Sin constancia"
        )
        unknown = operation_read_message(workflow)
        if unknown or hub.mode == "fixture":
            if not states:
                transfer = "No evaluable" if hub.mode == "fixture" else "Sin confirmar"
            if not received:
                receipt = "No evaluable" if hub.mode == "fixture" else "Sin confirmar"
        next_step = next_steps.get(request.id)
        unit = (
            equipment_label(item)
            if item
            else ("Unidad fuera de consulta" if request.machinery_id else "Sin unidad asignada")
        )
        rows.append(
            {
                "action": markdown_link(
                    next_step.action if next_step else "Ver solicitud",
                    next_step.href if next_step else context.request_href(request.id),
                ),
                "project": markdown_link(
                    request.project_name or "Proyecto sin nombre", context.request_href(request.id)
                ),
                "equipment": unit
                if item
                else f"{request.machinery_type or 'Tipo sin informar'} · {unit}",
                "period": period_label(request),
                "status": request.status,
                "transfer": transfer,
                "receipt": receipt,
            }
        )
    content.append(
        grid(
            "requests-grid",
            rows,
            [
                ("project", "Proyecto"),
                ("equipment", "Unidad"),
                ("period", "Período"),
                ("status", "Solicitud"),
                ("transfer", "Traslado"),
                ("receipt", "Recepción"),
                ("action", "Acción"),
            ],
            state_field="status",
            markdown_fields={"project", "action"},
            column_overrides={
                "project": {"width": 140, "minWidth": 120, "flex": 1},
                "equipment": {"width": 90, "minWidth": 80, "flex": 0},
                "period": {"width": 145, "minWidth": 135, "flex": 0},
                "status": {"width": 95, "minWidth": 85, "flex": 0},
                "transfer": {"width": 105, "minWidth": 90, "flex": 0},
                "receipt": {"width": 105, "minWidth": 90, "flex": 0},
                "action": {"width": 130, "minWidth": 120, "flex": 0},
            },
        )
        if rows
        else empty(
            "Sin solicitudes en esta consulta",
            "No se recibió una solicitud para este origen, búsqueda y filtro.",
        )
    )
    assigned_ids = {request.machinery_id for request in hub.requests}
    unassigned = [item for item in hub.equipment if item.id not in assigned_ids]
    if unassigned and context.filter == "all":
        content.append(
            accordion(
                disclosure(
                    "Maquinaria sin solicitud vinculada en esta consulta",
                    hint(
                        "Estos registros se conservan como referencia. Su proyecto administrativo "
                        "no establece una relación con una solicitud."
                    ),
                    simple_table(
                        ["Maquinaria", "Proyecto informado", "Estado administrativo", "Referencia"],
                        [
                            [
                                link(equipment_label(item), context.equipment_href(item.id)),
                                project_label(item),
                                state_text(item.machinery_status),
                                dmc.Code(item.provenance.source_id),
                            ]
                            for item in unassigned
                        ],
                        caption="Maquinaria recibida sin relación exacta con las solicitudes",
                    ),
                )
            )
        )
    return content


def equipment_inventory(hub: HubResponse, context: QueryContext, workflow=None):
    content = [
        heading(
            "Maquinaria",
            "Asignación y condición de las unidades leídas.",
        ),
        filter_tabs(context, EQUIPMENT_FILTERS, "Filtros de maquinaria"),
    ]
    if not readable(hub):
        return [*content, unavailable(hub, context, "Maquinaria")]
    equipment = hub.equipment
    if context.filter == "active_failures":
        equipment = [item for item in equipment if item.maintenance_failure_id]
    elif context.filter == "unlinked":
        equipment = [item for item in equipment if item.relation_status != "confirmed"]
    if not equipment:
        return [
            *content,
            empty(
                "Sin maquinaria que coincida",
                "No hay coincidencias en la lectura consultada. Su cobertura parcial "
                "no permite descartar equipos fuera de esta ventana.",
            ),
            link(
                "Ver maquinaria sin búsqueda ni filtros",
                QueryContext(mode=context.mode).href("/maquinaria"),
                mt="sm",
                display="block",
            ),
        ]
    rows = []
    for item in equipment:
        if item.maintenance_failure_id:
            maintenance = item.maintenance_status or "Falla activa registrada"
            if item.maintenance_is_stopped is True:
                maintenance += " · Paro registrado"
        elif item.maintenance_is_stopped is True:
            maintenance = "Paro registrado; sin ID de falla"
        else:
            maintenance = "Sin falla activa registrada"
        rows.append(
            {
                "equipment": markdown_link(
                    f"{equipment_label(item)} · {item.name}", context.equipment_href(item.id)
                ),
                "project": project_label(item),
                "administration": item.machinery_status,
                "maintenance": maintenance,
            }
        )
    return [
        *content,
        inventory_status_panel(
            equipment,
            read_total=len(hub.equipment),
            source_total=hub.scope.equipment_total,
        ),
        grid(
            "equipment-table",
            rows,
            [
                ("equipment", "Maquinaria"),
                ("project", "Proyecto en Prisma"),
                ("administration", "Estado administrativo"),
                ("maintenance", "Mantenimiento"),
            ],
            state_field="administration",
        ),
    ]


def machine_evidence(item: EquipmentRecord):
    return [
        facts([("Unidad", f"{equipment_label(item)} · {item.name}"), *maintenance_facts(item)]),
        facts(location_facts(item), cols=2),
        accordion(
            disclosure("Procedencia de la unidad", provenance(item.provenance)),
            disclosure("Procedencia de la ubicación", provenance(item.location.provenance))
            if item.location
            else None,
        ),
    ]


def task_record(task, item: EquipmentRecord):
    return dmc.Paper(
        [
            dmc.Group([dmc.Text(task.code, fw=600, size="sm"), state_text(task.status)], gap="md"),
            facts(
                [
                    ("Destino", task.destination_project_name or "Sin informar"),
                    ("Motorista", task.driver or "Sin informar"),
                    ("Vínculo", RELATIONS[item.relation_status]),
                ]
            ),
            hint(item.relation_note),
            accordion(
                disclosure(
                    "Referencias del traslado",
                    facts(
                        [
                            ("Solicitud vinculada", task.request_id or "Sin ID"),
                            ("ID del destino", task.destination_project_id or "Sin informar"),
                        ]
                    ),
                    provenance(task.provenance),
                )
            ),
        ],
        withBorder=True,
        p="md",
        mb="sm",
        className="transfer-record",
    )


def request_detail(hub: HubResponse, context: QueryContext, identifier: str, workflow=None):
    request = next((item for item in hub.requests if item.id == identifier), None)
    trail = breadcrumbs(
        "Solicitudes",
        context.href("/solicitudes", filter=context.filter),
        request.machinery_type if request and request.machinery_type else "Detalle",
    )
    if request is None:
        return [
            trail,
            empty(
                "Solicitud fuera de la consulta",
                "Comprueba el origen y limpia la búsqueda para ampliar el alcance.",
            ),
        ]
    operation = request_operation(hub, request)
    item = operation.equipment
    movements = matching_movements(workflow, request)
    current_movements = matching_current_movements(hub, request, workflow)
    next_step = next(
        (
            decision
            for decision in decision_items(hub, QueryContext(mode=context.mode), workflow)
            if decision.request.id == request.id
        ),
        None,
    )
    unknown = operation_read_message(workflow)
    request_alerts = [
        alert
        for alert in hub.alerts
        if alert.request_id == request.id
        or (item and alert.equipment_id == item.id and not alert.request_id)
    ]
    unit_title = (
        "Estado de la unidad · paro registrado"
        if item and item.maintenance_is_stopped
        else "Estado y mantenimiento de la unidad"
    )
    unit_missing = empty(
        "Registro de maquinaria fuera de la consulta"
        if request.machinery_id
        else "Sin unidad asignada",
        "La solicitud tiene una unidad asignada, pero su registro no está en esta "
        "consulta. Revisa las referencias de la solicitud."
        if request.machinery_id
        else "La solicitud no informa una unidad concreta. El proyecto o el tipo solicitado "
        "no permiten elegirla automáticamente.",
    )
    return [
        trail,
        heading(
            f"Solicitud de {request.machinery_type}"
            if request.machinery_type
            else "Solicitud de maquinaria",
            request.project_name or "Proyecto sin nombre",
        ),
        section(
            "Solicitud",
            facts(
                [
                    ("Estado de la solicitud", state_text(request.status)),
                    ("Período solicitado", period_label(request)),
                    (
                        "Unidad asignada",
                        link(equipment_label(item), context.equipment_href(item.id))
                        if item
                        else "Unidad fuera de consulta"
                        if request.machinery_id
                        else "Sin unidad asignada",
                    ),
                ]
            ),
            hint(f"Observaciones: {request.comments}") if request.comments else None,
            hint(
                "Los movimientos guardados no coinciden con la asignación actual. "
                "Revisa el traslado de esta unidad."
            )
            if movements and not current_movements
            else None,
            accordion(
                disclosure(
                    "Datos y referencias de la solicitud",
                    rows_table(
                        {
                            "Solicitante": request.requested_by or "Sin informar",
                            "ID de quien aprobó": request.approved_by_user_id or "No proporcionado",
                            "Fecha de aprobación": instant(request.approved_at),
                            "ID de proyecto": request.project_id or "Sin ID de proyecto",
                            "ID de maquinaria asignada": request.machinery_id or "Sin asignación",
                        }
                    ),
                    provenance(request.provenance),
                )
            ),
        ),
        section(
            next_step.title,
            hint(next_step.evidence),
            link(next_step.action, next_step.href)
            if next_step.href != context.request_href(request.id)
            else None,
        )
        if next_step
        else None,
        *request_workflow(workflow, context, request, item),
        suggestions_section(hub, request, workflow, context),
        conflicts_section(hub, request, workflow, context),
        accordion(
            disclosure(
                unit_title,
                interpretation_section(item, current_movements) if item else None,
                *(machine_evidence(item) if item else [unit_missing]),
            )
        ),
        *(
            []
            if movements
            else [
                accordion(
                    disclosure(
                        "Seguimiento y recepción",
                        section(
                            "Traslado de Startrack",
                            *(
                                [task_record(task, item) for task in operation.transfers]
                                or [
                                    empty(
                                        unknown or "Sin traslado vinculado a esta solicitud",
                                        "La consulta de operaciones no permite determinar "
                                        "los movimientos vinculados."
                                        if unknown
                                        else "Falta una tarea con correspondencia de solicitud y "
                                        "maquinaria validada en los registros consultados. Los "
                                        "nombres no confirman esa relación.",
                                    )
                                ]
                            ),
                        ),
                        section(
                            "Llegada y recepción",
                            facts(
                                [
                                    (
                                        "Llegada al destino",
                                        unknown or "Sin evidencia de llegada vinculada",
                                    ),
                                    ("Recepción física", unknown or "Sin constancia de recepción"),
                                ]
                            ),
                            hint(
                                "La tarea y la ubicación del GPS son hechos distintos. "
                                "Una entrada a geocerca no confirma que el proyecto haya recibido "
                                "la maquinaria."
                            ),
                        ),
                    )
                ),
            ]
        ),
        accordion(
            disclosure(
                "Revisar evidencia pendiente",
                dmc.List(
                    [
                        dmc.ListItem(value)
                        for value in (
                            [
                                "Consultar el registro de operaciones para determinar "
                                "la evidencia pendiente."
                            ]
                            if unknown
                            else remaining_evidence(operation.missing, current_movements)
                        )
                    ],
                    size="sm",
                ),
            ),
            request_timeline(request, movements, context),
            mt="md",
        ),
        accordion(
            disclosure(
                "Detalle de condiciones detectadas",
                simple_table(
                    ["Condición", "Descripción", "Área de revisión", "Evidencia"],
                    [
                        [alert.title, alert.description, alert.owner, ", ".join(alert.evidence)]
                        for alert in request_alerts
                    ],
                    caption="Condiciones detectadas por las reglas de lectura",
                ),
            )
        )
        if request_alerts
        else None,
    ]


def equipment_detail(hub: HubResponse, context: QueryContext, identifier: str, workflow=None):
    item = next((item for item in hub.equipment if item.id == identifier), None)
    trail = breadcrumbs(
        "Maquinaria",
        context.href("/maquinaria", filter=context.filter),
        equipment_label(item) if item else "Detalle",
    )
    if item is None:
        return [
            trail,
            empty(
                "Equipo fuera de la consulta",
                "Comprueba el origen y limpia la búsqueda para ampliar el alcance.",
            ),
        ]
    related = [request for request in hub.requests if request.machinery_id == item.id]
    movements = equipment_movements(hub, item, workflow)
    return [
        trail,
        heading(f"{equipment_label(item)} · {item.name}", "Evidencia de la maquinaria consultada."),
        interpretation_section(item, movements),
        conflicts_section(hub, item, workflow, context),
        accordion(
            disclosure(
                "Comparar fuentes y evidencia",
                *source_comparison(item, movements, workflow, context, hub),
            )
        ),
        section(
            "Solicitudes con esta unidad asignada",
            simple_table(
                ["Proyecto / solicitud", "Estado de solicitud", "Período solicitado"],
                [
                    [
                        link(project_label(request), context.request_href(request.id)),
                        state_text(request.status),
                        period_label(request),
                    ]
                    for request in related
                ],
                caption="Solicitudes que asignan esta maquinaria por su ID",
            )
            if related
            else hint(
                "No se recibió una solicitud que asigne esta unidad por su ID. "
                "El proyecto administrativo no prueba una solicitud ni un traslado."
            ),
        ),
        section(
            "Movimientos de la asignación consultada",
            workflow_table(movements, context),
            hint(
                "Los vínculos coinciden con los IDs, el origen y el período solicitado. "
                "Cada movimiento conserva su propia tarea y constancia."
            ),
        )
        if movements
        else None,
    ]


def sources(hub: HubResponse, context: QueryContext, workflow=None):
    chart = coverage_figure(hub)
    totals = {
        key: value if value is not None else "total desconocido"
        for key, value in [
            ("requests", hub.scope.requests_total),
            ("equipment", hub.scope.equipment_total),
        ]
    }
    records = [
        section(
            source.label,
            dmc.Group(
                [
                    state_text(
                        SOURCE_STATES[source.status],
                        "active"
                        if source.status == "connected"
                        else "pending"
                        if source.status == "partial"
                        else "issue"
                        if source.status == "error"
                        else "neutral",
                    ),
                    link(
                        dmc.Group(["Abrir plataforma", icon("external-link", 14)], gap=4),
                        PLATFORMS[source.id],
                        target="_blank",
                        anchorProps={"rel": "noopener noreferrer"},
                        size="xs",
                    ),
                ],
                gap="lg",
                mb="xs",
            ),
            dmc.Text(source.message, size="sm"),
            rows_table(
                [
                    ("Entorno", source.environment),
                    ("Última lectura", instant(source.observed_at)),
                    ("Fecha documental", day(source.observed_on)),
                    *(
                        [("Última evidencia conservada", instant(source.last_evidence_at))]
                        if source.id == "startrack"
                        else []
                    ),
                ]
            ),
            hint(
                "La ausencia de tareas en el corte de Prisma no determina si existen "
                "tareas o visitas en Startrack. Revisa la evidencia de cada movimiento."
            )
            if source.id == "startrack"
            else None,
        )
        for source in hub.sources
    ]
    return [
        heading(
            "Fuentes y cobertura",
        ),
        section(
            "Cobertura de la consulta",
            hint("Cada barra representa el total informado de su colección en Prisma."),
            graph("source-coverage", chart)
            if chart is not None
            else hint("Fuente no disponible; no se puede medir la cobertura de esta lectura."),
            hint(
                "Startrack se revisa por separado: sin lectura confirmada "
                "no hay un total de tareas."
            ),
            accordion(
                disclosure(
                    "Ver datos de cobertura",
                    simple_table(
                        ["Registro", "Leídos", "Total informado", "Fuera de la lectura"],
                        [
                            [
                                label,
                                loaded,
                                total if total is not None else "Desconocido",
                                total - loaded
                                if total is not None and total >= loaded
                                else "No determinable",
                            ]
                            for label, loaded, total in coverage_rows(hub)
                        ],
                        caption="Cobertura por colección; el total desconocido no es cero",
                    ),
                )
            ),
            className="page-section coverage-panel",
        ),
        simple_table(
            ["Fuente", "Estado", "Última lectura", "Situación"],
            [
                [
                    source.label,
                    state_text(
                        SOURCE_STATES[source.status],
                        "active"
                        if source.status == "connected"
                        else "pending"
                        if source.status == "partial"
                        else "issue"
                        if source.status == "error"
                        else "neutral",
                    ),
                    instant(source.observed_at)
                    if source.observed_at
                    else f"Muestra del {day(source.observed_on)}"
                    if source.observed_on
                    else "Sin lectura confirmada",
                    source.message,
                ]
                for source in hub.sources
            ],
            caption="Estado de las fuentes de esta lectura",
        ),
        accordion(
            disclosure("Procedencia y acceso a las fuentes", *records),
            disclosure(
                "Registro de operaciones y permisos",
                dmc.Text(
                    workflow.message if workflow else "Consultando el registro de movimientos…",
                    size="sm",
                ),
                rows_table(
                    [
                        (
                            "Última sincronización",
                            instant(workflow.last_sync_at)
                            if workflow and workflow.last_sync_at
                            else "Sin sincronización registrada",
                        ),
                        (
                            "Gestión de movimientos",
                            "Habilitada para esta sesión"
                            if workflow and workflow.management_enabled
                            else "Solo consulta: el rol o el servidor no la habilitan",
                        ),
                        (
                            "Envío a Startrack",
                            "Habilitado para los movimientos autorizados"
                            if workflow and workflow.sending_enabled
                            else "Deshabilitado",
                        ),
                    ]
                ),
                link("Revisar movimientos y evidencia", context.href("/operaciones")),
            ),
            disclosure(
                "Criterios de cobertura",
                dmc.Text(
                    "Esta consulta de solicitudes y maquinaria tiene cobertura parcial. "
                    "El registro de movimientos conserva por separado tareas, visitas y "
                    "constancias vinculadas por ID."
                    if hub.mode == "live"
                    else hub.scope.description,
                    size="sm",
                ),
                hint(
                    f"Solicitudes: {hub.scope.requests_returned} de {totals['requests']}. "
                    f"Maquinaria: {hub.scope.equipment_returned} de {totals['equipment']}. "
                    "La lectura y la observación de ubicación tienen fechas diferentes. "
                    "Una lectura reciente no actualiza una posición antigua."
                ),
            ),
        ),
    ]


# Page registry: navigation order, icon and renderers. A later phase appends its own pages.
PAGES = [
    {"path": "/", "label": "Resumen", "icon": "layout-dashboard", "render": overview},
    {
        "path": "/solicitudes",
        "label": "Solicitudes",
        "icon": "clipboard-list",
        "render": requests,
        "detail": request_detail,
    },
    {
        "path": "/maquinaria",
        "label": "Maquinaria",
        "icon": "bulldozer",
        "render": equipment_inventory,
        "detail": equipment_detail,
    },
    {"path": "/operaciones", "label": "Operaciones", "icon": "truck", "render": None},
    {
        "path": "/indicadores",
        "label": "Indicadores",
        "icon": "chart-bar",
        "render": indicators,
    },
    {
        "path": "/integracion",
        "label": "Integración",
        "icon": "arrows-exchange",
        "render": integration_page,
        "secondary": True,
    },
    {
        "path": "/fuentes",
        "label": "Fuentes",
        "icon": "database",
        "render": sources,
        "secondary": True,
    },
    {
        "path": "/administracion",
        "label": "Administración",
        "icon": "users",
        "render": admin_page,
        "secondary": True,
        "permission": Permission.manage_users,
    },
]


def render_page(path: str, hub: HubResponse, context: QueryContext, workflow=None):
    if path in {"/", "/resumen", "/decisiones"}:
        return overview(hub, context, workflow)
    if path == "/operaciones" or path.startswith("/operaciones/"):
        return workflow_page(path, workflow, context)
    for page in PAGES[1:]:
        if path == page["path"]:
            return page["render"](hub, context, workflow)
        if page.get("detail") and path.startswith(page["path"] + "/"):
            identifier = unquote(path.removeprefix(page["path"] + "/"))
            return page["detail"](hub, context, identifier, workflow)
    return [
        heading("Página no encontrada", "La dirección no corresponde a una vista de solicitudes."),
        link("Ir a solicitudes", context.href("/solicitudes")),
    ]
