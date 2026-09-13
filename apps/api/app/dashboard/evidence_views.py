"""Readable comparisons of separate source facts, without resolving remote state."""

import dash_mantine_components as dmc
from dash import html

from app.dashboard.analytics import day, instant
from app.dashboard.components import (
    accordion,
    disclosure,
    facts,
    hint,
    icon,
    link,
    provenance,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview

SOURCE_STATES = {
    "fixture": "Muestras del contrato",
    "connected": "Conectada",
    "partial": "Lectura parcial",
    "not_configured": "Pendiente de conexión",
    "disabled": "Consulta desactivada",
    "error": "Error de lectura",
    "not_queried": "Sin consulta actual",
}


def operation_read_message(workflow: WorkflowOverview | None) -> str | None:
    if workflow is None:
        return "Operaciones por consultar"
    if not workflow.available:
        return "Operaciones no disponibles"
    if not workflow.complete:
        return "Operaciones consultadas parcialmente"
    return None


def source_date(record) -> str:
    if record.observed_at:
        return f"Lectura: {instant(record.observed_at)}"
    if record.observed_on:
        return f"Fecha documental: {day(record.observed_on)} · sin hora de lectura"
    return "Sin lectura fechada"


def stopped_label(item: EquipmentRecord) -> str:
    if item.maintenance_is_stopped is None:
        return "Sin información"
    return "Sí" if item.maintenance_is_stopped else "No"


def maintenance_facts(item: EquipmentRecord) -> list[tuple[str, object]]:
    return [
        ("Estado administrativo", state_text(item.machinery_status)),
        ("Mantenimiento", item.maintenance_status or "Sin información"),
        ("Paro registrado", stopped_label(item)),
        ("Falla activa", item.maintenance_failure_id or "Sin referencia informada"),
    ]


def location_facts(item: EquipmentRecord) -> list[tuple[str, str]]:
    return [
        (
            "Ubicación observada",
            item.location.label if item.location else "Sin observación disponible",
        ),
        ("Fecha de la ubicación", instant(item.location.observed_at if item.location else None)),
    ]


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
    """The reading of the compared facts: a rule and a heading, not a colored panel."""
    title, explanation, next_step = interpretation(item, movements)
    return html.Div(
        [
            dmc.Group(
                [icon("eye-check", 16), html.Span("Interpretación de la evidencia")],
                gap=8,
                wrap="nowrap",
                className="interpretation-eyebrow",
            ),
            dmc.Title(title, order=3, size="h5", mt=6),
            dmc.Text(explanation, size="sm", maw="80ch", mt=6),
            dmc.Text([html.Strong("Siguiente paso: "), next_step], size="sm", maw="80ch", mt="xs"),
        ],
        className="interpretation",
    )


def audit_rows(rows: list[list], *, caption: str):
    """Audit layout for compared facts: source value, when it was observed and what it proves."""
    return simple_table(
        ["Hecho", "Valor", "Fecha de observación", "Qué acredita"], rows, caption=caption
    )


def _task_card(title, rows: list[tuple[str, object]], *children):
    return html.Div(
        [
            dmc.Text(title, fw=600, size="sm", className="record-title"),
            facts(rows, cols=2),
            *children,
        ],
        className="evidence-record",
    )


def source_comparison(
    item: EquipmentRecord,
    movements: list[MovementRecord],
    workflow: WorkflowOverview | None,
    context: QueryContext,
    hub: HubResponse | None = None,
):
    from app.dashboard.workflow_views import (
        arrival_label,
        declared_by_label,
        receipt_label,
        state_label,
        task_status,
    )

    reading = source_date(item.provenance)
    prisma = [
        audit_rows(
            [
                [
                    "Estado administrativo",
                    state_text(item.machinery_status),
                    reading,
                    "Ocupación administrativa en Prisma. No acredita ubicación ni "
                    "disponibilidad física.",
                ],
                [
                    "Mantenimiento",
                    item.maintenance_status or "Sin información",
                    reading,
                    "Condición informada por Prisma; la confirma Mantenimiento, no esta lectura.",
                ],
                [
                    "Paro registrado",
                    stopped_label(item),
                    reading,
                    "«Sin información» no equivale a «sin paro»: el dato no viene en la lectura.",
                ],
                [
                    "Falla activa",
                    item.maintenance_failure_id or "Sin referencia informada",
                    reading,
                    "Referencia de la falla registrada; por sí sola no acredita indisponibilidad.",
                ],
            ],
            caption="Hechos administrativos de Prisma con su fecha de lectura",
        ),
        accordion(
            disclosure(
                "Procedencia y valores de la unidad",
                facts(
                    [
                        ("Número de activo · no_activo", item.asset_number or "No proporcionado"),
                        ("Clave original · clave", item.code or "No proporcionada"),
                        ("Nombre", item.name),
                        (
                            "Proyecto administrativo",
                            item.project_name or item.project_id or "Sin informar",
                        ),
                        ("Actualización de origen", instant(item.updated_at)),
                    ],
                    cols=2,
                ),
                provenance(item.provenance),
            )
        ),
    ]
    tasks = [
        _task_card(
            task.code,
            [
                ("Estado de tarea", state_text(task.status or "Estado no observado", task.status)),
                ("Fecha del evento", instant(getattr(task, "event_time", None))),
                (
                    "Registro del vínculo"
                    if task.evidence_origin == "creation_acknowledgment"
                    else "Observación",
                    instant(task.provenance.observed_at),
                ),
                (
                    "Destino informado",
                    task.destination_project_name or task.destination_project_id or "Sin informar",
                ),
                (
                    "Señal de llegada GPS",
                    f"Observada en {task.arrival_poi_id} ({instant(task.arrival_event_time)})"
                    if task.arrival_observed
                    else "Sin señal de llegada observada",
                ),
                (
                    "Constancia de recepción",
                    f"Recibió {task.receipt.receiver} · {task.receipt.reference} "
                    f"({instant(task.receipt.received_at)})"
                    if task.receipt
                    else "Sin constancia de recepción",
                ),
            ],
            link("Abrir movimiento", context.movement_href(task.movement_id))
            if getattr(task, "movement_id", None)
            else None,
            hint(
                "La creación confirma el ID de la tarea. No acredita una observación "
                "posterior de su ejecución."
            )
            if task.evidence_origin == "creation_acknowledgment"
            else None,
            accordion(disclosure("Procedencia de la tarea", provenance(task.provenance))),
        )
        for task in item.transfers
    ]
    projected_ids = {task.provenance.source_id for task in item.transfers}
    for movement in movements:
        if movement.job_id in projected_ids:
            continue
        latest = max(
            (event for event in movement.events if event.kind == "task_state"),
            key=lambda event: event.recorded_at,
            default=None,
        )
        tasks.append(
            _task_card(
                link(movement.movement_reference, context.movement_href(movement.id)),
                [
                    ("Preparación / envío", state_label(movement)),
                    ("Estado de tarea", task_status(movement)),
                    ("Fecha del evento", instant(latest.event_time if latest else None)),
                    ("Observación", instant(latest.observed_at if latest else None)),
                ],
                hint("El plan guardado no acredita una tarea enviada.")
                if not movement.job_id
                else None,
            )
        )
    unknown = operation_read_message(workflow)
    source = (
        next((source for source in hub.sources if source.id == "startrack"), None) if hub else None
    )
    location = item.location
    observation_rows = [
        [
            "Ubicación observada",
            location.label if location else "Sin observación disponible",
            instant(location.observed_at) if location else "Sin lectura fechada",
            "Posición del activo vinculado. Una visita de geocerca puede corresponder al "
            "transportador y no acredita recepción.",
        ]
    ]
    if not tasks:
        observation_rows.insert(
            0,
            [
                "Estado de tarea",
                "No determinado",
                "Sin observación disponible",
                "Sin tarea vinculada en esta lectura; la ausencia no acredita que no exista.",
            ],
        )
    startrack = [
        dmc.Text(f"{SOURCE_STATES[source.status]} · {source.message}", size="xs", c="dimmed")
        if source
        else None,
        audit_rows(
            observation_rows,
            caption="Hechos observados en Startrack con su fecha de observación",
        ),
        hint(unknown + ". La ausencia de evidencia no confirma que no existan traslados.")
        if unknown
        else None,
        hint(
            "Sin traslado vinculado en los registros consultados. Falta evidencia "
            "de una tarea con correspondencia validada."
        )
        if not tasks and not unknown
        else None,
        hint(
            "Los estados conservan su fecha de observación; no representan una "
            "consulta actual del proveedor."
        ),
        accordion(disclosure("Procedencia de la ubicación", provenance(item.location.provenance)))
        if item.location
        else None,
        hint(
            "Una visita de geocerca puede corresponder al transportador o al teléfono. "
            "No se presenta como posición de la maquinaria ni acredita recepción."
        ),
        *([html.P("Tareas vinculadas", className="eyebrow spaced"), *tasks] if tasks else []),
    ]
    receipts = [
        _task_card(
            link(movement.movement_reference, context.movement_href(movement.id)),
            [
                ("Señal de llegada del activo vinculado", arrival_label(movement)),
                ("Recepción física", receipt_label(movement)),
                *(
                    [
                        ("Recibió", movement.receipt.receiver),
                        ("Constancia", movement.receipt.reference),
                        ("Registrada", instant(movement.receipt.recorded_at)),
                        *(
                            [("Declarada por", declared)]
                            if (declared := declared_by_label(movement.receipt))
                            else []
                        ),
                    ]
                    if movement.receipt
                    else []
                ),
            ],
        )
        for movement in movements
    ]
    return [
        section(
            "Comparación de fuentes",
            hint(
                "Cada fuente conserva su valor y su fecha de observación. Son hechos distintos: "
                "ninguno resuelve al otro y la ausencia no se cuenta como cero."
            ),
            *[
                html.Div(
                    [dmc.Title(title, order=3, size="h5", mb="xs"), *children],
                    className="source-audit",
                )
                for title, children in [("Prisma / Nexus", prisma), ("Startrack", startrack)]
            ],
        ),
        section(
            "Llegada y recepción por movimiento",
            *receipts,
            hint(unknown + ". La recepción no se puede determinar.") if unknown else None,
            hint(
                "Sin constancia de recepción en movimientos compatibles con la "
                "asignación consultada."
            )
            if not movements and not unknown
            else None,
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
    from app.dashboard.workflow_views import EVENTS, actor_label

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
            link(movement.movement_reference, context.movement_href(movement.id)),
            instant(event.event_time),
            f"Observado: {instant(event.observed_at)} · registrado: "
            f"{instant(event.recorded_at)} · {actor_label(event, movement)}",
        ]
        for movement in movements
        for event in sorted(movement.events, key=lambda item: item.recorded_at)
    )
    return disclosure(
        "Cronología documentada de la solicitud",
        hint(
            "Las fechas de origen, observación y registro se conservan por separado, junto "
            "con quién registró o declaró cada hecho. Los eventos de cada movimiento siguen "
            "el orden de registro; este historial puede ser parcial."
        ),
        simple_table(
            ["Hecho", "Origen / movimiento", "Fecha del hecho", "Lectura y registro"],
            rows,
            caption="Fechas documentadas de la solicitud y sus movimientos",
        )
        if rows
        else hint(
            "Las fuentes no aportan fechas de creación, aprobación ni eventos de "
            "movimiento para reconstruir una cronología."
        ),
    )
