"""Persisted plans, provider evidence and explicit receipts, kept separate."""

from typing import TYPE_CHECKING
from urllib.parse import unquote

import dash_mantine_components as dmc
from pydantic import ValidationError

from app.core.auth import Permission
from app.dashboard.analytics import instant
from app.dashboard.auth_views import denied, permitted
from app.dashboard.components import (
    accordion,
    back_link,
    disclosure,
    empty,
    facts,
    grid,
    heading,
    hint,
    link,
    markdown_link,
    provenance,
    rows_table,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
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
READ_ONLY = "Solo consulta: la gestión de movimientos no está habilitada en esta conexión."


def state_label(movement: MovementRecord):
    return state_text(STATES[movement.state], movement.state)


def task_status(movement: MovementRecord) -> str:
    if not movement.job_id:
        return "Sin tarea vinculada"
    return movement.status or "Estado no observado"


def arrival_label(movement: MovementRecord) -> str:
    arrivals = [event for event in movement.events if event.kind == "arrival"]
    if not arrivals:
        return "Sin evidencia de llegada vinculada"
    latest = max(arrivals, key=lambda event: event.recorded_at)
    when = instant(latest.event_time) if latest.event_time else "sin fecha de evento"
    return f"Llegada observada · {when}"


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


def event_description(event) -> str:
    if event.kind == "task_state":
        return "Estado de tarea: " + str(event.data.get("status") or "No informado")
    if event.kind == "arrival":
        vehicle = event.data.get("vehicle_id") or "sin ID informado"
        return f"Visita del activo GPS {vehicle}; no acredita recepción de la maquinaria."
    if event.kind == "receipt":
        return "Constancia: " + str(event.data.get("reference") or "Ver declaración de recepción")
    return STATES.get(event.state, event.state or EVENTS.get(event.kind, event.kind))


def remaining_evidence(missing: list[str], movements: list[MovementRecord]) -> list[str]:
    """Remove a gap only when every persisted movement has that distinct evidence."""
    if not movements:
        return list(missing)
    evidence = {
        "Traslado vinculado": all(movement.job_id for movement in movements),
        "Evidencia de llegada": all(
            any(event.kind == "arrival" for event in movement.events) for movement in movements
        ),
        "Recepción física": all(movement.receipt for movement in movements),
    }
    return [value for value in missing if not evidence.get(value, False)]


def matching_movements(
    workflow: "WorkflowOverview | None", request: RequestRecord
) -> list[MovementRecord]:
    if workflow is None or not workflow.available:
        return []
    return [
        movement
        for movement in workflow.movements
        if movement.request_source_id == request.provenance.source_id
        and movement.source_request.get("id") == request.id
        and movement.environment == request.provenance.environment
    ]


def source_evidence(label: str, source_record: dict | None):
    if source_record is None:
        return None
    try:
        evidence = Provenance.model_validate(source_record.get("provenance"))
    except ValidationError:
        return hint(f"{label}: procedencia incompleta en el registro.")
    return disclosure(label, provenance(evidence))


def workflow_table(movements: list[MovementRecord], context: QueryContext):
    return simple_table(
        ["Movimiento", "Preparación / envío", "Tarea de Startrack", "Llegada", "Recepción"],
        [
            [
                link(movement.movement_reference, context.movement_href(movement.id)),
                state_label(movement),
                task_status(movement),
                arrival_label(movement),
                receipt_label(movement),
            ]
            for movement in movements
        ],
        caption="Movimientos persistidos de esta solicitud",
    )


def request_workflow(workflow, context: QueryContext, request: RequestRecord, equipment):
    movements = matching_movements(workflow, request)
    available = workflow is not None and workflow.available
    allowed = permitted(Permission.manage_transfers)
    enabled = available and workflow.management_enabled and allowed
    has_identity = bool(
        request.provenance.source_id
        and request.project_id
        and equipment
        and equipment.provenance.source_id
    )
    notes = [
        "Guarda la correspondencia de la solicitud con el destino y los usuarios de Startrack. "
        "La preparación valida aprobación y unidad asignada.",
        "Las muestras permiten guardar planes locales. No envían tareas ni registran llegadas "
        "o recepciones."
        if context.mode == "fixture"
        else "Guardar el plan no envía la tarea. Revisa el movimiento antes de ponerlo en cola.",
        None
        if available
        else (workflow.message if workflow else "Consultando el registro de movimientos…"),
        READ_ONLY if available and allowed and not enabled else None,
        "Falta una unidad asignada o un identificador de origen. Completa la asignación en "
        "Prisma para preparar el movimiento."
        if not has_identity
        else None,
    ]
    return [
        hint(
            "Consulta parcial de operaciones. Puede haber movimientos fuera de esta ventana; "
            "revisa el registro antes de preparar otro traslado.",
            role="status",
        )
        if available and not workflow.complete
        else None,
        section(
            "Movimientos de esta solicitud",
            workflow_table(movements, context),
            link("Abrir operaciones", context.href("/operaciones"), mt="sm", display="block"),
        )
        if movements
        else None,
        accordion(
            disclosure(
                "Preparar traslado",
                *[hint(note) for note in notes if note],
                plan_form(
                    request_source_id=request.provenance.source_id or "",
                    machinery_source_id=equipment.provenance.source_id or "" if equipment else "",
                    project_source_id=request.project_id or "",
                    enabled=enabled and has_identity,
                )
                if allowed
                else denied(),
            ),
            mt="md",
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
    allowed = permitted(Permission.manage_transfers)
    content.append(
        dmc.Group(
            [
                action_button(
                    "sync",
                    "Sincronizar operación" if context.mode == "live" else "Guardar corte local",
                    enabled=workflow.available and workflow.management_enabled,
                    icon_name="refresh",
                )
                if allowed
                else denied(),
                dmc.Text(
                    f"Última sincronización: {instant(workflow.last_sync_at)}"
                    if workflow.last_sync_at
                    else "Sin sincronización registrada",
                    size="xs",
                    c="dimmed",
                ),
            ],
            gap="md",
            mb="md",
        )
    )
    if not workflow.available:
        # The empty state already carries the message; do not repeat it as a hint.
        return [*content, empty("Registro no disponible", workflow.message)]
    content.append(hint(workflow.message))
    if allowed and not workflow.management_enabled:
        content.append(hint(READ_ONLY))
    if workflow.coverage and not workflow.coverage.is_complete:
        content.append(hint(workflow.coverage.note, role="status"))
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
            "job": task_status(movement),
            "arrival": arrival_label(movement),
            "receipt": receipt_label(movement),
        }
        for movement in movements
    ]
    if rows:
        table = grid(
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
            state_field="state",
        )
    elif workflow.complete:
        table = empty(
            "Sin movimientos en este origen y búsqueda",
            "Abre una solicitud para preparar su traslado. Los planes se conservan por origen.",
        )
    else:
        table = empty(
            "Sin movimientos en la ventana consultada",
            "La consulta parcial no permite descartar otros movimientos. Revisa el registro "
            "antes de preparar un traslado.",
        )
    return [
        *content,
        table,
        hint(
            "Una llegada observada y una recepción son evidencias distintas. Los envíos con "
            "resultado incierto requieren conciliación; no se reenvían automáticamente."
        ),
    ]


def movement_detail(workflow: "WorkflowOverview | None", context: QueryContext, identifier: str):
    back = back_link("Volver a operaciones", context.href("/operaciones", filter=context.filter))
    if workflow is None:
        return [back, empty("Consultando movimiento…", "Cargando el registro del origen.")]
    if not workflow.available:
        return [back, empty("Registro de operaciones no disponible", workflow.message)]
    movement = next((item for item in workflow.movements if item.id == identifier), None)
    if movement is None:
        return [
            back,
            empty(
                "Movimiento fuera de la consulta",
                workflow.message
                if not workflow.complete
                else "Comprueba el origen seleccionado y el identificador del movimiento.",
            ),
        ]
    allowed = permitted(Permission.manage_transfers)
    enabled = workflow.available and workflow.management_enabled and allowed
    receipt = movement.receipt
    mapping = movement.mapping
    references = {
        "ID de movimiento": movement.id,
        "ID de solicitud": movement.request_source_id,
        "ID de maquinaria": movement.machinery_source_id,
        "ID de proyecto": movement.project_source_id,
        "ID de geocerca de destino": mapping.get("poi_id") or "Sin informar",
        "IDs de usuarios asignados": ", ".join(mapping.get("assigned_user_ids", []))
        or "Sin informar",
        "ID del activo GPS": movement.tracked_vehicle_id or "Sin correspondencia",
        "ID de tarea": movement.job_id or "Sin tarea vinculada",
        "Rol de ejecución": movement.workflow_role or "Sin rol observado",
        "Referencia del estado": movement.reason_code or "Sin incidencia registrada",
        "Creado en el registro": instant(movement.created_at),
        "Actualizado en el registro": instant(movement.updated_at),
    }
    prepared = {
        "Objetivo": (movement.payload or {}).get("objective") or "Sin objetivo",
        "Descripción": (movement.payload or {}).get("description") or "Sin descripción",
        "Referencia externa": (movement.payload or {}).get("remote_id") or "Sin referencia",
    }
    machine = movement.source_equipment or {}
    machine_sections = []
    try:
        equipment = EquipmentRecord.model_validate(machine)
    except ValidationError:
        equipment = None
    if equipment:
        from app.dashboard.evidence_views import interpretation_section, source_comparison

        machine_sections = [
            interpretation_section(equipment, [movement]),
            hint(
                "La comparación usa el corte de Prisma conservado al preparar o validar "
                "este movimiento. Su fecha no cambia al consultar el historial."
            ),
            source_comparison(equipment, [movement], workflow, context)[0],
        ]
    sending_note = (
        "Plan local sobre muestras: el envío está deshabilitado."
        if movement.mode == "fixture"
        else "El envío está deshabilitado en este servidor."
        if not workflow.sending_enabled
        else workflow.message
    )
    can_queue = (
        enabled
        and workflow.sending_enabled
        and movement.mode == "live"
        and movement.state == "draft"
    )
    can_receive = (
        movement.mode == "live" and movement.state == "sent" and movement.job_id and not receipt
    )
    return [
        back,
        heading(movement.movement_reference, "Evidencia y acciones de este traslado concreto."),
        facts(
            [
                ("Preparación / envío", state_label(movement)),
                ("Proyecto", movement.source_request.get("project_name") or "Sin nombre"),
                (
                    "Maquinaria",
                    machine.get("asset_number")
                    or machine.get("code")
                    or machine.get("name")
                    or "Sin nombre de unidad",
                ),
            ]
        ),
        link("Ver solicitud de origen", context.request_href(movement.source_request["id"]))
        if movement.source_request.get("id")
        else None,
        *machine_sections,
        section(
            "Programación",
            facts(
                [
                    ("Fecha programada", mapping.get("scheduled_date") or "Sin informar"),
                    ("Hora programada", mapping.get("scheduled_time") or "Sin informar"),
                ]
            ),
            hint(
                "La programación es independiente del período solicitado de uso. "
                "La correspondencia GPS puede identificar el transportador."
            ),
            accordion(
                disclosure(
                    "Referencias de integración y origen",
                    rows_table(references),
                    accordion(
                        source_evidence(
                            "Procedencia conservada de la solicitud", movement.source_request
                        ),
                        source_evidence(
                            "Procedencia conservada de la unidad", movement.source_equipment
                        ),
                    ),
                )
            ),
        ),
        section(
            "Tarea de Startrack",
            facts(
                [
                    ("Estado de tarea", task_status(movement)),
                    ("Envío registrado", instant(movement.sent_at)),
                ]
            ),
            dmc.List([dmc.ListItem(reason) for reason in pending_reasons(movement)], size="sm")
            if pending_reasons(movement)
            else None,
            accordion(
                disclosure(
                    "Contenido preparado para Startrack",
                    rows_table(prepared),
                    dmc.List(
                        [dmc.ListItem(note) for note in movement.preparation.get("notes", [])],
                        size="sm",
                    ),
                )
            )
            if movement.payload
            else None,
            hint(sending_note),
            dmc.Group(
                [
                    action_button(
                        "queue",
                        "Poner traslado en cola",
                        movement=movement.id,
                        enabled=can_queue,
                        primary=True,
                        icon_name="send",
                    ),
                    hint(
                        "La cola se procesa al sincronizar. El servidor vuelve a comprobar la "
                        "solicitud, la unidad y las correspondencias antes de crear la tarea."
                    ),
                ]
            )
            if movement.mode == "live" and allowed
            else denied()
            if movement.mode == "live"
            else None,
        ),
        section(
            "Llegada y recepción",
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
            hint(receipt.note) if receipt and receipt.note else None,
            hint(
                "Una entrada a geocerca o una tarea completada no acredita recepción. "
                "La constancia se registra con responsable, fecha y referencia explícitos."
            ),
            (
                receipt_form(
                    movement.id, enabled=workflow.available and workflow.management_enabled
                )
                if permitted(Permission.declare_reception)
                else denied()
            )
            if can_receive
            else None,
        ),
        section(
            "Historial y evidencia del movimiento",
            hint(
                "Eventos en orden de registro. La fecha del hecho y el momento de observación "
                "se muestran por separado; el historial puede ser parcial."
            ),
            simple_table(
                ["Evento", "Evidencia conservada", "Fecha del evento", "Observado", "Registrado"],
                [
                    [
                        EVENTS.get(event.kind, event.kind),
                        event_description(event),
                        instant(event.event_time),
                        instant(event.observed_at),
                        instant(event.recorded_at),
                    ]
                    for event in sorted(movement.events, key=lambda item: item.recorded_at)
                ],
                caption="Historial persistido, con fechas de origen y registro separadas",
            )
            if movement.events
            else hint("No se ha registrado un evento para este movimiento."),
            accordion(
                *[
                    disclosure(
                        f"Procedencia · {EVENTS.get(event.kind, event.kind)} · "
                        f"{instant(event.recorded_at)}",
                        facts(
                            [
                                ("ID del evento", event.id),
                                ("ID de origen", event.source_id or "Registro local"),
                            ]
                        ),
                        provenance(event.provenance),
                        value=event.id,
                    )
                    for event in movement.events
                    if event.provenance
                ]
            ),
        ),
    ]


def workflow_page(path: str, workflow: "WorkflowOverview | None", context: QueryContext):
    if path == "/operaciones":
        return operations(workflow, context)
    return movement_detail(workflow, context, unquote(path.removeprefix("/operaciones/")))
