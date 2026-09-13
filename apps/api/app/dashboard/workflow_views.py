"""Persisted plans, provider evidence and explicit receipts, kept separate."""

from typing import TYPE_CHECKING
from urllib.parse import unquote

from dash import dcc, html
from pydantic import ValidationError

from app.dashboard.analytics import instant
from app.dashboard.context import QueryContext
from app.dashboard.views import empty, facts, grid, heading, markdown_link, provenance, simple_table
from app.dashboard.workflow_forms import action_button, plan_form, receipt_form
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import MovementRecord

if TYPE_CHECKING:
    from app.models.workflow import WorkflowOverview

STATES = {
    "draft": "Plan local",
    "blocked": "Preparación bloqueada",
    "queued": "En cola de envío",
    "sending": "Envío en curso",
    "sent": "Tarea vinculada",
    "unknown": "Resultado de envío por conciliar",
    "failed": "Envío fallido",
}
EVENTS = {
    "planned": "Plan guardado",
    "prepared": "Preparación revisada",
    "revalidated": "Preparación validada de nuevo",
    "created": "Plan guardado",
    "queued": "Puesto en cola",
    "sending": "Envío iniciado",
    "sent": "Tarea vinculada",
    "unknown": "Resultado de envío incierto",
    "failed": "Envío fallido",
    "blocked": "Preparación bloqueada",
    "task_state": "Estado de tarea observado",
    "arrival": "Llegada observada",
    "receipt": "Recepción registrada",
}


def task_label(movement: MovementRecord) -> str:
    if movement.job_id:
        return f"{movement.job_id} · {movement.status or 'Estado no observado'}"
    return STATES[movement.state]


def source_evidence(label: str, source_record: dict | None):
    if source_record is None:
        return None
    try:
        evidence = Provenance.model_validate(source_record.get("provenance"))
    except ValidationError:
        return html.P(f"{label}: procedencia incompleta en el registro.")
    return html.Details([html.Summary(label), provenance(evidence)])


def arrival_label(movement: MovementRecord) -> str:
    arrivals = [event for event in movement.events if event.kind == "arrival"]
    if not arrivals:
        return "Sin evidencia de llegada vinculada"
    latest = max(arrivals, key=lambda event: event.recorded_at)
    return (
        f"Llegada observada · {instant(latest.event_time)}"
        if latest.event_time
        else "Llegada observada · sin fecha de evento"
    )


def receipt_label(movement: MovementRecord) -> str:
    if movement.receipt:
        return f"Recibida · {instant(movement.receipt.received_at)}"
    return "Sin constancia de recepción"


def pending_reasons(movement: MovementRecord) -> list[str]:
    reasons = [
        *movement.preparation.get("blocking_reasons", []),
        *movement.preparation.get("missing_fields", []),
    ]
    if movement.state == "unknown":
        reasons.append("Conciliar el resultado antes de intentar otro envío.")
    elif movement.state == "failed":
        reasons.append("Revisar el error registrado antes de preparar otro envío.")
    return list(dict.fromkeys(str(reason) for reason in reasons))


def remaining_evidence(missing: list[str], movements: list[MovementRecord]) -> list[str]:
    """Remove a gap only when every persisted movement has that distinct evidence."""
    result = list(missing)
    if not movements:
        return result
    evidence = {
        "Traslado vinculado": all(movement.job_id for movement in movements),
        "Evidencia de llegada": all(
            any(event.kind == "arrival" for event in movement.events) for movement in movements
        ),
        "Recepción física": all(movement.receipt for movement in movements),
    }
    return [value for value in result if not evidence.get(value, False)]


def matching_movements(
    workflow: "WorkflowOverview | None", request: RequestRecord
) -> list[MovementRecord]:
    if workflow is None:
        return []
    return [
        movement
        for movement in workflow.movements
        if movement.request_source_id == request.provenance.source_id
        and movement.source_request.get("id") == request.id
        and movement.environment == request.provenance.environment
    ]


def workflow_table(movements: list[MovementRecord], context: QueryContext):
    return simple_table(
        ["Movimiento", "Preparación / envío", "Tarea de Startrack", "Llegada", "Recepción"],
        [
            [
                dcc.Link(movement.movement_reference, href=context.movement_href(movement.id)),
                STATES[movement.state],
                movement.status or "Estado no observado"
                if movement.job_id
                else "Sin tarea vinculada",
                arrival_label(movement),
                receipt_label(movement),
            ]
            for movement in movements
        ],
        caption="Movimientos persistidos de esta solicitud",
    )


def request_workflow(
    workflow: "WorkflowOverview | None",
    context: QueryContext,
    request: RequestRecord,
    equipment: EquipmentRecord | None,
):
    movements = matching_movements(workflow, request)
    available = workflow is not None and workflow.available
    enabled = available and workflow.management_enabled
    has_identity = bool(
        request.provenance.source_id
        and request.project_id
        and equipment
        and equipment.provenance.source_id
    )
    message = (
        workflow.message if workflow is not None else "Consultando el registro de movimientos…"
    )
    return [
        html.Section(
            [
                html.H2("Movimientos de esta solicitud"),
                workflow_table(movements, context),
                dcc.Link("Abrir operaciones", href=context.href("/operaciones")),
            ],
            className="detail-section",
        )
        if movements
        else None,
        html.Details(
            [
                html.Summary("Preparar traslado"),
                html.P(
                    "Guarda la correspondencia de la solicitud con el destino y los usuarios "
                    "de Startrack. La preparación valida aprobación y unidad asignada."
                ),
                html.P(
                    "Las muestras permiten guardar planes locales. No envían tareas ni "
                    "registran llegadas o recepciones."
                    if context.mode == "fixture"
                    else "Guardar el plan no envía la tarea. Revisa el movimiento antes de "
                    "ponerlo en cola."
                ),
                html.P(message) if not available else None,
                html.P(
                    "Solo consulta: la gestión de movimientos no está habilitada en esta conexión."
                )
                if available and not enabled
                else None,
                html.P(
                    "Falta una unidad asignada o un identificador de origen. "
                    "Completa la asignación en Prisma para preparar el movimiento."
                )
                if not has_identity
                else None,
                plan_form(
                    request_source_id=request.provenance.source_id or "",
                    machinery_source_id=equipment.provenance.source_id or "" if equipment else "",
                    project_source_id=request.project_id or "",
                    enabled=enabled and has_identity,
                ),
            ],
            className="detail-section detail-disclosure",
        ),
    ]


def operations(workflow: "WorkflowOverview | None", context: QueryContext):
    content = [
        heading(
            "Operaciones",
            "Planes de traslado, envíos y evidencia conservados por solicitud y movimiento.",
        )
    ]
    if workflow is None:
        return [*content, empty("Consultando movimientos…", "Cargando el registro del origen.")]
    content.extend(
        [
            html.P(workflow.message, className="table-hint"),
            html.P(
                "Solo consulta: la gestión de movimientos no está habilitada en esta conexión.",
                className="table-hint",
            )
            if workflow.available and not workflow.management_enabled
            else None,
            html.Div(
                [
                    action_button(
                        "sync",
                        "Sincronizar operación"
                        if context.mode == "live"
                        else "Guardar corte local",
                        enabled=workflow.available and workflow.management_enabled,
                    ),
                    html.Span(
                        f"Última sincronización: {instant(workflow.last_sync_at)}"
                        if workflow.last_sync_at
                        else "Sin sincronización registrada"
                    ),
                ],
                className="workflow-actions",
            ),
        ]
    )
    if not workflow.available:
        return [*content, empty("Registro no disponible", workflow.message)]
    if workflow.coverage and not workflow.coverage.is_complete:
        content.append(html.P(workflow.coverage.note, className="table-hint coverage-note"))
    movements = workflow.movements
    if context.query:
        term = context.query.casefold()
        movements = [
            movement
            for movement in movements
            if any(
                term in str(value).casefold()
                for value in (
                    movement.movement_reference,
                    movement.request_source_id,
                    movement.machinery_source_id,
                    movement.project_source_id,
                    movement.source_request.get("project_name", ""),
                )
            )
        ]
    rows = [
        {
            "reference": markdown_link(
                movement.movement_reference, context.movement_href(movement.id)
            ),
            "project": movement.source_request.get("project_name") or "Proyecto sin nombre",
            "state": STATES[movement.state],
            "job": movement.status or "Estado no observado"
            if movement.job_id
            else "Sin tarea vinculada",
            "arrival": arrival_label(movement),
            "receipt": receipt_label(movement),
            "pending": "; ".join(pending_reasons(movement)) or "Sin incidencia de integración",
        }
        for movement in movements
    ]
    content.append(
        grid(
            "operations-grid",
            rows,
            [
                ("reference", "Movimiento"),
                ("project", "Proyecto"),
                ("state", "Preparación / envío"),
                ("job", "Tarea · Estado Startrack"),
                ("arrival", "Llegada"),
                ("receipt", "Recepción"),
            ],
            link_field="reference",
        )
        if rows
        else empty(
            "Sin movimientos en este origen y búsqueda",
            "Abre una solicitud para preparar su traslado. Los planes se conservan por origen.",
        )
    )
    content.append(
        html.P(
            "Una llegada observada y una recepción son evidencias distintas. "
            "Los envíos con resultado incierto requieren conciliación; "
            "no se reenvían automáticamente.",
            className="table-hint",
        )
    )
    return content


def movement_detail(workflow: "WorkflowOverview | None", context: QueryContext, identifier: str):
    back = dcc.Link(
        "← Volver a operaciones", href=context.href("/operaciones"), className="back-link"
    )
    if workflow is None:
        return [back, empty("Consultando movimiento…", "Cargando el registro del origen.")]
    movement = next((item for item in workflow.movements if item.id == identifier), None)
    if movement is None:
        return [
            back,
            empty(
                "Movimiento fuera de este origen",
                workflow.message
                if not workflow.available
                else "Comprueba el origen seleccionado y el identificador del movimiento.",
            ),
        ]
    enabled = workflow.available and workflow.management_enabled
    receipt = movement.receipt
    reasons = pending_reasons(movement)
    mapping = movement.mapping
    machine = movement.source_equipment or {}
    machine_label = machine.get("code") or machine.get("asset_number") or machine.get("name")
    content = [
        back,
        heading(movement.movement_reference, "Evidencia y acciones de este traslado concreto."),
        facts(
            [
                ("Preparación / envío", STATES[movement.state]),
                ("Proyecto", movement.source_request.get("project_name") or "Sin nombre"),
                ("Maquinaria", machine_label or "Sin nombre de unidad"),
            ]
        ),
        dcc.Link(
            "Ver solicitud de origen", href=context.request_href(movement.source_request["id"])
        )
        if movement.source_request.get("id")
        else None,
        html.Section(
            [
                html.H2("Programación"),
                facts(
                    [
                        ("Fecha programada", mapping.get("scheduled_date") or "Sin informar"),
                        ("Hora programada", mapping.get("scheduled_time") or "Sin informar"),
                    ]
                ),
                html.P(
                    "La programación es independiente del período solicitado de uso. "
                    "La correspondencia GPS puede identificar el transportador."
                ),
                html.Details(
                    [
                        html.Summary("Referencias de integración y origen"),
                        facts(
                            [
                                ("ID de movimiento", movement.id),
                                ("ID de solicitud", movement.request_source_id),
                                ("ID de maquinaria", movement.machinery_source_id),
                                ("ID de proyecto", movement.project_source_id),
                                (
                                    "ID de geocerca de destino",
                                    mapping.get("poi_id") or "Sin informar",
                                ),
                                (
                                    "IDs de usuarios asignados",
                                    ", ".join(mapping.get("assigned_user_ids", []))
                                    or "Sin informar",
                                ),
                                (
                                    "ID del activo GPS",
                                    movement.tracked_vehicle_id or "Sin correspondencia",
                                ),
                                ("ID de tarea", movement.job_id or "Sin tarea vinculada"),
                                ("Rol de ejecución", movement.workflow_role or "Sin rol observado"),
                                (
                                    "Referencia del estado",
                                    movement.reason_code or "Sin incidencia registrada",
                                ),
                                ("Creado en el registro", instant(movement.created_at)),
                                ("Actualizado en el registro", instant(movement.updated_at)),
                            ]
                        ),
                        source_evidence(
                            "Procedencia conservada de la solicitud", movement.source_request
                        ),
                        source_evidence(
                            "Procedencia conservada de la unidad", movement.source_equipment
                        ),
                    ],
                    className="integration-references",
                ),
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Tarea de Startrack"),
                facts(
                    [
                        (
                            "Estado de tarea",
                            movement.status or "Estado no observado"
                            if movement.job_id
                            else "Sin tarea vinculada",
                        ),
                        ("Envío registrado", instant(movement.sent_at)),
                    ]
                ),
                html.Ul([html.Li(reason) for reason in reasons]) if reasons else None,
                html.Details(
                    [
                        html.Summary("Contenido preparado para Startrack"),
                        facts(
                            [
                                ("Objetivo", movement.payload.get("objective") or "Sin objetivo"),
                                (
                                    "Descripción",
                                    movement.payload.get("description") or "Sin descripción",
                                ),
                                (
                                    "Referencia externa",
                                    movement.payload.get("remote_id") or "Sin referencia",
                                ),
                            ]
                        ),
                        html.Ul([html.Li(note) for note in movement.preparation.get("notes", [])]),
                    ]
                )
                if movement.payload
                else None,
                html.P("Plan local sobre muestras: el envío está deshabilitado.")
                if movement.mode == "fixture"
                else html.P("El envío está deshabilitado en este servidor.")
                if not workflow.sending_enabled
                else html.P(workflow.message),
                action_button(
                    "queue",
                    "Poner traslado en cola",
                    movement=movement.id,
                    enabled=enabled
                    and workflow.sending_enabled
                    and movement.mode == "live"
                    and movement.state == "draft",
                    primary=True,
                ),
                html.P(
                    "La cola se procesa al sincronizar. El servidor vuelve a comprobar "
                    "la solicitud, la unidad y las correspondencias antes de crear la tarea."
                )
                if movement.mode == "live"
                else None,
            ],
            className="detail-section",
        ),
        html.Section(
            [
                html.H2("Llegada y recepción"),
                facts(
                    [
                        ("Llegada al destino", arrival_label(movement)),
                        ("Recepción física", receipt_label(movement)),
                    ]
                ),
                facts(
                    [
                        ("Recibió", receipt.receiver),
                        ("Referencia", receipt.reference),
                        ("Registrada", instant(receipt.recorded_at)),
                    ]
                )
                if receipt
                else None,
                html.P(receipt.note) if receipt and receipt.note else None,
                html.P(
                    "Una entrada a geocerca o una tarea completada no acredita recepción. "
                    "La constancia se registra con responsable, fecha y referencia explícitos."
                ),
                receipt_form(movement.id, enabled=enabled)
                if movement.mode == "live"
                and movement.state == "sent"
                and movement.job_id
                and not receipt
                else None,
            ],
            className="detail-section",
        ),
        html.Details(
            [
                html.Summary("Historial y evidencia del movimiento"),
                simple_table(
                    [
                        "Evento",
                        "Estado de integración",
                        "Fecha del evento",
                        "Observado",
                        "Registrado",
                        "ID de origen",
                    ],
                    [
                        [
                            EVENTS.get(event.kind, event.kind),
                            STATES.get(event.state, event.state or "—"),
                            instant(event.event_time),
                            instant(event.observed_at),
                            instant(event.recorded_at),
                            event.source_id or "Registro local",
                        ]
                        for event in movement.events
                    ],
                    caption="Historial persistido, con fechas de origen y registro separadas",
                )
                if movement.events
                else html.P("No se ha registrado un evento para este movimiento."),
                *[
                    html.Details(
                        [
                            html.Summary(
                                f"Procedencia · {EVENTS.get(event.kind, event.kind)} · "
                                f"{instant(event.recorded_at)}"
                            ),
                            provenance(event.provenance),
                        ]
                    )
                    for event in movement.events
                    if event.provenance
                ],
            ],
            className="detail-section detail-disclosure",
        ),
    ]
    return content


def workflow_page(path: str, workflow: "WorkflowOverview | None", context: QueryContext):
    if path == "/operaciones":
        return operations(workflow, context)
    return movement_detail(workflow, context, unquote(path.removeprefix("/operaciones/")))
