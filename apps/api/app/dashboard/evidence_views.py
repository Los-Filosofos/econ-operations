"""Readable comparisons of separate source facts, without resolving remote state."""

from dash import dcc, html

from app.dashboard.analytics import instant
from app.dashboard.context import QueryContext
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview


def operation_read_message(workflow: WorkflowOverview | None) -> str | None:
    if workflow is None:
        return "Operaciones por consultar"
    if not workflow.available:
        return "Operaciones no disponibles"
    if not workflow.complete:
        return "Operaciones consultadas parcialmente"
    return None


def _source_date(record) -> str:
    if record.observed_at:
        return f"Lectura: {instant(record.observed_at)}"
    if record.observed_on:
        return f"Fecha documental: {record.observed_on.strftime('%d/%m/%Y')} · sin hora de lectura"
    return "Sin lectura fechada"


def _task_evidence(item: EquipmentRecord, movements: list[MovementRecord]):
    """Use persisted exact matches when present and retain dated hub task evidence."""
    values = [
        (movement.status or "Estado no observado", movement.workflow_role, True)
        for movement in movements
        if movement.state == "sent" and movement.job_id
    ]
    known = {movement.job_id for movement in movements}
    values.extend(
        (
            task.status or "Estado no observado",
            getattr(task, "workflow_role", None),
            item.relation_status == "confirmed",
        )
        for task in item.transfers
        if task.provenance.source_id not in known
    )
    return values


def interpretation(item: EquipmentRecord, movements: list[MovementRecord]):
    tasks = _task_evidence(item, movements)
    pending = any(
        confirmed
        and (role == "pending" or (role is None and state.upper() in {"PENDIENTE", "PENDING"}))
        for state, role, confirmed in tasks
    )
    completed = any(
        confirmed
        and (role == "completed" or (role is None and state.upper() in {"COMPLETADA", "COMPLETED"}))
        for state, role, confirmed in tasks
    )
    if (item.maintenance_failure_id or item.maintenance_is_stopped is True) and pending:
        return (
            "Mantenimiento y traslado pendiente requieren revisión",
            "Prisma registra una falla activa o un paro y Startrack conserva una tarea pendiente. "
            "La evidencia no confirma que la unidad pueda ejecutar el traslado.",
            "Mantenimiento debe confirmar la condición de la unidad y Logística revisar la "
            "asignación y la tarea antes de continuar. Esta lectura no modifica los proveedores.",
        )
    if item.machinery_status.upper() in {"OCUPADA", "OCCUPIED"} and completed:
        return (
            "Ocupada y tarea completada son estados compatibles",
            "Prisma describe la ocupación administrativa de la unidad; Startrack describe la "
            "ejecución de una tarea. Completar el traslado no libera automáticamente "
            "la maquinaria.",
            "Revisar la constancia del movimiento y mantener la asignación hasta confirmar "
            "su cierre en Prisma. La tarea completada no acredita recepción física.",
        )
    if item.machinery_status.upper() == "OBSOLETA":
        return (
            "Revisar el estado administrativo antes de continuar",
            "Prisma informa OBSOLETA. Ese estado administrativo no demuestra por sí solo "
            "una avería.",
            "Logística debe confirmar si corresponde mantener la asignación y consultar "
            "a Mantenimiento cuando falte evidencia de la condición de la unidad.",
        )
    if item.maintenance_failure_id or item.maintenance_is_stopped is True:
        return (
            "Confirmar la condición de la unidad",
            "Prisma registra una falla activa o un paro. El estado de la tarea y la ubicación "
            "no resuelven esa condición de mantenimiento.",
            "Revisar la falla o el paro con Mantenimiento antes de confirmar "
            "disponibilidad física.",
        )
    return (
        "Contrastar la asignación con la evidencia de ejecución",
        "Administración, mantenimiento, tarea, ubicación y recepción describen hechos distintos. "
        "La evidencia ausente no permite confirmar disponibilidad física ni una discrepancia.",
        "Revisar la solicitud y los movimientos vinculados; completar las correspondencias y "
        "consultar la evidencia faltante antes de decidir.",
    )


def interpretation_section(item: EquipmentRecord, movements: list[MovementRecord]):
    title, explanation, next_step = interpretation(item, movements)
    return html.Section(
        [
            html.H2("Lectura operativa"),
            html.H3(title),
            html.P(explanation),
            html.P([html.Strong("Siguiente paso: "), next_step]),
        ],
        className="detail-section evidence-interpretation",
    )


def source_comparison(
    item: EquipmentRecord,
    movements: list[MovementRecord],
    workflow: WorkflowOverview | None,
    context: QueryContext,
    hub: HubResponse | None = None,
):
    from app.dashboard.views import SOURCE_STATES, facts, provenance
    from app.dashboard.workflow_views import STATES, arrival_label, receipt_label

    stopped = (
        "Sí"
        if item.maintenance_is_stopped is True
        else "No"
        if item.maintenance_is_stopped is False
        else "Sin información"
    )
    prisma = html.Section(
        [
            html.H3("Prisma / Nexus"),
            html.P(_source_date(item.provenance), className="evidence-date"),
            facts(
                [
                    ("Estado administrativo", item.machinery_status),
                    ("Mantenimiento", item.maintenance_status or "Sin información"),
                    ("Paro registrado", stopped),
                    ("Falla activa", item.maintenance_failure_id or "Sin referencia informada"),
                ]
            ),
            html.P("La ocupación administrativa no acredita ubicación ni disponibilidad física."),
            html.Details(
                [
                    html.Summary("Procedencia y valores de la unidad"),
                    facts(
                        [
                            (
                                "Número de activo · no_activo",
                                item.asset_number or "No proporcionado",
                            ),
                            ("Clave original · clave", item.code or "No proporcionada"),
                            ("Nombre", item.name),
                            (
                                "Proyecto administrativo",
                                item.project_name or item.project_id or "Sin informar",
                            ),
                            ("Actualización de origen", instant(item.updated_at)),
                        ]
                    ),
                    provenance(item.provenance),
                ]
            ),
        ],
        className="source-comparison-column",
    )
    tasks = []
    projected_ids = {task.provenance.source_id for task in item.transfers}
    for task in item.transfers:
        tasks.append(
            html.Div(
                [
                    html.H4(task.code),
                    facts(
                        [
                            ("Estado de tarea", task.status or "Estado no observado"),
                            ("Fecha del evento", instant(getattr(task, "event_time", None))),
                            (
                                "Registro del vínculo"
                                if task.evidence_origin == "creation_acknowledgment"
                                else "Observación",
                                instant(task.provenance.observed_at),
                            ),
                            (
                                "Destino informado",
                                task.destination_project_name
                                or task.destination_project_id
                                or "Sin informar",
                            ),
                        ]
                    ),
                    dcc.Link("Abrir movimiento", href=context.movement_href(task.movement_id))
                    if getattr(task, "movement_id", None)
                    else None,
                    html.P(
                        "La creación confirma el ID de la tarea. No acredita una "
                        "observación posterior de su ejecución."
                    )
                    if task.evidence_origin == "creation_acknowledgment"
                    else None,
                    html.Details(
                        [html.Summary("Procedencia de la tarea"), provenance(task.provenance)]
                    ),
                ],
                className="transfer-record",
            )
        )
    for movement in movements:
        if movement.job_id in projected_ids:
            continue
        latest = max(
            (event for event in movement.events if event.kind == "task_state"),
            key=lambda event: event.recorded_at,
            default=None,
        )
        tasks.append(
            html.Div(
                [
                    html.H4(
                        dcc.Link(
                            movement.movement_reference, href=context.movement_href(movement.id)
                        )
                    ),
                    facts(
                        [
                            ("Preparación / envío", STATES[movement.state]),
                            (
                                "Estado de tarea",
                                movement.status or "Estado no observado"
                                if movement.job_id
                                else "Sin tarea vinculada",
                            ),
                            ("Fecha del evento", instant(latest.event_time if latest else None)),
                            ("Observación", instant(latest.observed_at if latest else None)),
                        ]
                    ),
                    html.P("El plan guardado no acredita una tarea enviada.")
                    if not movement.job_id
                    else None,
                ],
                className="transfer-record",
            )
        )
    unknown = operation_read_message(workflow)
    source = (
        next((source for source in hub.sources if source.id == "startrack"), None) if hub else None
    )
    startrack = html.Section(
        [
            html.H3("Startrack"),
            html.P(f"{SOURCE_STATES[source.status]} · {source.message}") if source else None,
            *tasks,
            facts(
                [
                    ("Estado de tarea", "No determinado"),
                    ("Observación de tarea", "Sin observación disponible"),
                ]
            )
            if not tasks
            else None,
            html.P(unknown + ". La ausencia de evidencia no confirma que no existan traslados.")
            if unknown
            else None,
            html.P(
                "Sin traslado vinculado en los registros consultados. Falta evidencia "
                "de una tarea con correspondencia validada."
            )
            if not tasks and not unknown
            else None,
            html.P(
                "Los estados conservan su fecha de observación; no representan una "
                "consulta actual del proveedor."
            ),
            facts(
                [
                    (
                        "Ubicación observada",
                        item.location.label if item.location else "Sin observación disponible",
                    ),
                    (
                        "Fecha de la ubicación",
                        instant(item.location.observed_at if item.location else None),
                    ),
                ]
            ),
            html.Details(
                [html.Summary("Procedencia de la ubicación"), provenance(item.location.provenance)]
            )
            if item.location
            else None,
            html.P(
                "Una visita de geocerca puede corresponder al transportador o al teléfono. "
                "No se presenta como posición de la maquinaria ni acredita recepción."
            ),
        ],
        className="source-comparison-column",
    )
    receipts = [
        html.Div(
            [
                html.H3(
                    dcc.Link(movement.movement_reference, href=context.movement_href(movement.id))
                ),
                facts(
                    [
                        ("Señal de llegada del activo vinculado", arrival_label(movement)),
                        ("Recepción física", receipt_label(movement)),
                    ]
                ),
                facts(
                    [
                        ("Recibió", movement.receipt.receiver),
                        ("Constancia", movement.receipt.reference),
                        ("Registrada", instant(movement.receipt.recorded_at)),
                    ]
                )
                if movement.receipt
                else None,
            ],
            className="transfer-record",
        )
        for movement in movements
    ]
    return [
        html.Section(
            [
                html.H2("Comparación de fuentes"),
                html.Div([prisma, startrack], className="source-comparison"),
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Llegada y recepción por movimiento"),
                *receipts,
                html.P(unknown + ". La recepción no se puede determinar.") if unknown else None,
                html.P(
                    "Sin constancia de recepción en movimientos compatibles con la "
                    "asignación consultada."
                )
                if not movements and not unknown
                else None,
            ],
            className="detail-section",
        ),
    ]


def equipment_movements(hub: HubResponse, item: EquipmentRecord, workflow: WorkflowOverview | None):
    from app.dashboard.decision_analytics import matching_current_movements

    result = {}
    for request in hub.requests:
        if request.machinery_id == item.id:
            for movement in matching_current_movements(hub, request, workflow):
                result[movement.id] = movement
    return list(result.values())


def request_timeline(
    request: RequestRecord, movements: list[MovementRecord], context: QueryContext
):
    from app.dashboard.views import simple_table
    from app.dashboard.workflow_views import EVENTS

    rows = [
        [label, "Prisma / Nexus", instant(value), "Fecha de origen"]
        for label, value in [
            ("Solicitud creada", request.created_at),
            ("Solicitud aprobada", request.approved_at),
            ("Solicitud actualizada", request.updated_at),
        ]
        if value
    ]
    rows.extend(
        [
            EVENTS.get(event.kind, event.kind),
            dcc.Link(movement.movement_reference, href=context.movement_href(movement.id)),
            instant(event.event_time),
            f"Observado: {instant(event.observed_at)} · registrado: {instant(event.recorded_at)}",
        ]
        for movement in movements
        for event in sorted(movement.events, key=lambda item: item.recorded_at)
    )
    return html.Details(
        [
            html.Summary("Cronología documentada de la solicitud"),
            html.P(
                "Las fechas de origen, observación y registro se conservan por separado. "
                "Los eventos de cada movimiento siguen el orden de registro; este "
                "historial puede ser parcial."
            ),
            simple_table(
                ["Hecho", "Origen / movimiento", "Fecha del hecho", "Lectura y registro"],
                rows,
                caption="Fechas documentadas de la solicitud y sus movimientos",
            )
            if rows
            else html.P(
                "Las fuentes no aportan fechas de creación, aprobación ni eventos de "
                "movimiento para reconstruir una cronología."
            ),
        ],
        className="detail-section detail-disclosure evidence-timeline",
    )
