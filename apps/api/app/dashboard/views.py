"""Pages of the hub: registry, navigation, lists, details and sources."""

from collections import Counter
from urllib.parse import unquote

import dash_mantine_components as dmc
from dash import dcc

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
    back_link,
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
from app.dashboard.decision_analytics import (
    matching_current_movements,
    request_states,
    requests_in_scope,
    short_date,
    states_figure,
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
from app.dashboard.integration_views import integration_page
from app.dashboard.workflow_views import (
    STATES,
    matching_movements,
    receipt_label,
    remaining_evidence,
    request_workflow,
    workflow_page,
    workflow_table,
)
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord

MODES = {"fixture": "Muestras proporcionadas", "live": "Sandbox actual (sintético)"}
# Only the lists let `q` narrow what is shown; every other page keeps the origin as text.
SEARCHABLE = frozenset({"/", "/solicitudes", "/maquinaria", "/operaciones"})
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
    if path in {"/", "/resumen"}:
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
    return [
        dmc.NavLink(
            label=page["label"],
            leftSection=icon(page["icon"]),
            href=context.href(page["path"]),
            active=selected == page["path"],
            className="nav-link" + (" nav-utility" if page.get("secondary") else ""),
            **({"aria-current": "page"} if selected == page["path"] else {}),
        )
        for page in visible_pages()
    ]


def searchable(path: str | None) -> bool:
    """Whether this page shows the full query bar; details and utilities never do."""
    normalized = (path or "/").rstrip("/") or "/"
    return normalized in SEARCHABLE or normalized == "/resumen"


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
        [dmc.Text(MODES[context.mode], size="xs", fw=500), origin_link(context, path)],
        gap="md",
        className="scope-line",
    )


def scope(hub: HubResponse, context: QueryContext | None = None, workflow=None, path=None):
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
    return dmc.Group(
        [
            dmc.Text(MODES[hub.mode], size="xs", fw=500),
            dmc.Text(count, size="xs", c="dimmed"),
            dmc.Text(coverage, size="xs", c="dimmed"),
            dmc.Text(equipment, size="xs", c="dimmed"),
            link("Fuentes y cobertura", (context or QueryContext()).href("/fuentes"), size="xs"),
            origin_link(context, path) if context is not None and not searchable(path) else None,
        ],
        gap="md",
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
        [state_text(value) for value in dict.fromkeys(values)],
        gap="lg",
        my="xs",
        **{"aria-label": "Leyenda de estados"},
    )


def graph(identifier: str, chart):
    return dcc.Graph(
        id=identifier,
        figure=chart,
        responsive=True,
        config={"displayModeBar": False, "responsive": True, "locale": "es"},
        style={"height": f"{chart.layout.height}px"},
    )


def decision_cards(hub, context, workflow):
    cards = []
    for item in decision_items(hub, context, workflow):
        request = item.request
        timeline = usage_timeline([request])
        dates = (
            f"{short_date(timeline.periods[0].starts_on)} – "
            f"{short_date(timeline.periods[0].ends_on, year=True)}"
            if timeline.periods
            else "Período por verificar"
        )
        cards.append(
            dmc.Paper(
                dmc.Grid(
                    [
                        dmc.GridCol(
                            [
                                link(
                                    request.project_name or "Proyecto sin identificar",
                                    context.request_href(request.id),
                                    fw=500,
                                    c="dark",
                                ),
                                dmc.Text(request.machinery_type or "Tipo sin informar", size="xs"),
                                dmc.Text(dates, size="xs", c="dimmed"),
                                state_text(request.status),
                            ],
                            span={"base": 12, "md": 4},
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text("Qué requiere revisión", size="xs", c="dimmed"),
                                dmc.Title(item.title, order=3, size="h5"),
                                dmc.Text(item.evidence, size="sm", c="dimmed"),
                            ],
                            span={"base": 12, "md": 6},
                        ),
                        dmc.GridCol(
                            link(
                                dmc.Group([item.action, icon("arrow-right", 15)], gap=4),
                                item.href,
                                fw=500,
                            ),
                            span={"base": 12, "md": 2},
                        ),
                    ],
                    gutter="md",
                ),
                withBorder=True,
                p="md",
                className="decision-card",
            )
        )
    if not cards:
        return hint("No se identificaron asuntos por revisar con la evidencia de esta consulta.")
    return dmc.Stack(cards, gap="sm")


def overview(hub: HubResponse, context: QueryContext, workflow=None):
    content = [
        heading(
            "Qué requiere atención",
            "Decisiones sobre la asignación y el traslado de maquinaria a cada proyecto.",
        )
    ]
    if context.mode != hub.mode or not readable(hub):
        return [*content, unavailable(hub, context, "Resumen")]
    requests = requests_in_scope(hub, context, workflow)
    if context.filter in FILTER_LABELS:
        content.append(hint(f"Filtro aplicado: {FILTER_LABELS[context.filter]}."))
    if not requests:
        return [
            *content,
            empty(
                "Sin solicitudes para representar",
                "Amplía la búsqueda o cambia el filtro de solicitudes.",
            ),
        ]
    content.append(decision_cards(hub, context, workflow))
    if workflow is None or not workflow.available:
        content.append(
            hint(
                "Registro de tareas sin confirmar. Consulta las operaciones antes de concluir "
                "si un traslado está preparado o enviado.",
                role="status",
            )
        )
    elif not workflow.complete:
        content.append(
            hint(
                "Registro de movimientos parcial. Una tarea sin confirmar en esta vista puede "
                "tener evidencia fuera de la ventana consultada.",
                role="status",
            )
        )
    source = next(source for source in hub.sources if source.id == "nexus")
    cutoff = (
        f"Corte de lectura: {instant(hub.data_as_of)} (El Salvador)."
        if hub.data_as_of is not None
        else f"Fecha documental: {day(source.observed_on)}; sin instante común de observación."
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
        hint(
            f"Revisiones basadas en la evidencia disponible; no indican atraso. "
            f"{'Muestras del archivo' if hub.mode == 'fixture' else 'Lectura del sandbox'} · "
            f"Datos sintéticos. Solicitudes en esta vista: {len(requests)}; devueltas por la "
            f"consulta: {len(hub.requests)}. {total} {cutoff} "
            + ("Cobertura integrada parcial." if not hub.scope.complete else ""),
            mt="md",
        )
    )
    timeline = usage_timeline(requests)
    period_note = (
        f"Solicitudes con período representable: {len(timeline.periods)} de {len(requests)}. "
        "Inicio y fin incluidos; no son plazos de entrega."
    )
    if timeline.periods:
        start = min(period.starts_on for period in timeline.periods)
        end = max(period.ends_on for period in timeline.periods)
        period_note = f"{short_date(start)} – {short_date(end, year=True)}. {period_note}"
    excluded_rows = [
        [
            link(
                item.request.provenance.source_id or item.request.id,
                context.request_href(item.request.id),
            ),
            item.request.starts_on or "Sin informar",
            item.request.ends_on or "Sin informar",
            item.reason,
        ]
        for item in timeline.excluded
    ]
    content.append(
        section(
            "Período de uso solicitado",
            hint(period_note),
            [
                graph("decision-request-usage", usage_figure(timeline)),
                state_legend([period.request.status for period in timeline.periods]),
            ]
            if timeline.periods
            else hint("No hay períodos con inicio y fin válidos para representar."),
            hint(
                f"{len(timeline.excluded)} solicitud(es) no representadas por fechas incompletas, "
                "ambiguas o invertidas. Consulta el detalle en la tabla.",
                role="status",
            )
            if timeline.excluded
            else None,
            accordion(
                disclosure(
                    "Ver datos de períodos",
                    simple_table(
                        ["Solicitud", "Proyecto", "Inicio solicitado", "Fin solicitado"],
                        [
                            [
                                link(
                                    period.request.provenance.source_id or period.request.id,
                                    context.request_href(period.request.id),
                                ),
                                period.request.project_name
                                or period.request.project_id
                                or "Sin proyecto",
                                period.request.starts_on,
                                period.request.ends_on,
                            ]
                            for period in timeline.periods
                        ],
                        caption="Períodos originales de uso de las solicitudes representadas",
                    ),
                    dmc.Title("Solicitudes no representadas", order=3, size="h6", mt="md")
                    if excluded_rows
                    else None,
                    simple_table(
                        ["Solicitud", "Inicio original", "Fin original", "Motivo"],
                        excluded_rows,
                        caption="Solicitudes excluidas del gráfico y motivo de exclusión",
                    )
                    if excluded_rows
                    else None,
                    hint(
                        "Fechas con hora y zona se representan por su día en El Salvador. "
                        "La tabla conserva los valores originales."
                    ),
                ),
                disclosure(
                    "Ver distribución por estado de solicitud",
                    hint(f"Solicitudes de esta vista por estado administrativo: {len(requests)}."),
                    graph("decision-request-states", states_figure(request_states(requests))),
                    accordion(
                        disclosure(
                            "Ver datos de estados",
                            simple_table(
                                ["Estado original", "Solicitudes"],
                                [[state, count] for state, count in request_states(requests)],
                                caption="Solicitudes por estado administrativo original",
                            ),
                        )
                    ),
                ),
            ),
            **{"aria-label": "Períodos de uso solicitados"},
        )
    )
    return content


def period_label(request: RequestRecord) -> str:
    return f"{day(request.starts_on)} — {day(request.ends_on)}"


def requests(hub: HubResponse, context: QueryContext, workflow=None):
    content = [
        heading(
            "Solicitudes de maquinaria",
            "Del proyecto y la unidad asignada al traslado, la llegada y la recepción.",
        ),
        filter_tabs(context, REQUEST_FILTERS, "Filtros de solicitudes"),
    ]
    if not readable(hub):
        return [*content, unavailable(hub, context, "Solicitudes")]
    rows = []
    for request in requests_in_scope(hub, context, workflow):
        operation = request_operation(hub, request)
        item, tasks = operation.equipment, operation.transfers
        movements = matching_current_movements(hub, request, workflow)
        states = Counter(movement.status or STATES[movement.state] for movement in movements)
        transfer = " · ".join(
            f"{state} ({count})" if count > 1 else state for state, count in states.items()
        ) or " · ".join(dict.fromkeys(task.status for task in tasks))
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
                "equipment": f"{request.machinery_type or 'Tipo sin informar'} · {unit}",
                "period": period_label(request),
                "status": request.status,
                "transfer": transfer or "Sin traslado vinculado",
                "receipt": receipt,
            }
        )
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
            state_field="status",
        )
        if rows
        else empty(
            "Sin solicitudes en esta consulta",
            "No se recibió una solicitud para este origen, búsqueda y filtro.",
        )
    )
    content.append(
        hint(
            "Abre una solicitud para revisar la cadena completa. Una tarea completada o una "
            "entrada a geocerca no acredita recepción física."
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
            "Consulta una unidad para comparar su estado en Prisma, el seguimiento "
            "de Startrack y la evidencia de recepción.",
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
    content.append(
        hint(
            f"{len(equipment)} de {hub.scope.equipment_returned} unidades en esta consulta. "
            "El estado administrativo no confirma disponibilidad física. "
            "Las tareas y ubicaciones se muestran con su propia fecha en el detalle."
        )
    )
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
            maintenance = "Sin falla activa registrada; disponibilidad no verificada"
        rows.append(
            {
                "equipment": markdown_link(
                    f"{equipment_label(item)} · {item.name}", context.equipment_href(item.id)
                ),
                "project": project_label(item),
                "administration": item.machinery_status,
                "maintenance": maintenance,
                "tracking": (
                    f"{len(item.transfers)} tareas vinculadas · Revisar fecha y estado"
                    if item.transfers and item.relation_status == "confirmed"
                    else "Sin evidencia vinculada en esta lectura"
                ),
                "location": (
                    f"{item.location.label} · {instant(item.location.observed_at)}"
                    if item.location
                    else "Sin ubicación fechada de la maquinaria"
                ),
            }
        )
    return [
        *content,
        grid(
            "equipment-table",
            rows,
            [
                ("equipment", "Maquinaria"),
                ("project", "Proyecto en Prisma"),
                ("administration", "Estado administrativo"),
                ("maintenance", "Mantenimiento"),
                ("tracking", "Seguimiento Startrack"),
                ("location", "Ubicación de maquinaria"),
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
    back = back_link("Volver a solicitudes", context.href("/solicitudes", filter=context.filter))
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
        back,
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
        interpretation_section(item, current_movements) if item else None,
        accordion(disclosure(unit_title, *(machine_evidence(item) if item else [unit_missing]))),
        *request_workflow(workflow, context, request, item),
        *(
            []
            if movements
            else [
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
                            ("Llegada al destino", unknown or "Sin evidencia de llegada vinculada"),
                            ("Recepción física", unknown or "Sin constancia de recepción"),
                        ]
                    ),
                    hint(
                        "El estado de una tarea y la ubicación del GPS son hechos distintos. "
                        "Una entrada a geocerca no confirma que el proyecto haya recibido "
                        "la maquinaria."
                    ),
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
        section(
            "Condiciones que requieren revisión",
            simple_table(
                ["Condición", "Descripción", "Área de revisión", "Evidencia"],
                [
                    [alert.title, alert.description, alert.owner, ", ".join(alert.evidence)]
                    for alert in request_alerts
                ],
                caption="Condiciones detectadas por las reglas de lectura",
            ),
        )
        if request_alerts
        else None,
    ]


def equipment_detail(hub: HubResponse, context: QueryContext, identifier: str, workflow=None):
    item = next((item for item in hub.equipment if item.id == identifier), None)
    back = back_link("Volver a maquinaria", context.href("/maquinaria", filter=context.filter))
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
                        if source.status in {"fixture", "connected"}
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
            "Procedencia de las solicitudes, unidades y tareas disponibles en esta consulta.",
        ),
        *records,
        section(
            "Registro de operaciones",
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
        section(
            "Alcance de la lectura",
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
        "path": "/integracion",
        "label": "Integración",
        "icon": "arrows-exchange",
        "render": integration_page,
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
    if path in {"/", "/resumen"}:
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
