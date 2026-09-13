"""One evidence-backed next step per request, without urgency scores or clock inference."""

from dataclasses import dataclass

from app.dashboard.analytics import day, equipment_label, instant, readable
from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import matching_current_movements, requests_in_scope
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview

PENDING = {"PENDIENTE", "PENDING"}
APPROVED = {"APROBADA", "APPROVED"}
FINISHED = {"CANCELADA", "COMPLETADA", "RECHAZADA"}


@dataclass(frozen=True)
class DecisionItem:
    request: RequestRecord
    equipment: EquipmentRecord | None
    title: str
    evidence: str
    action: str
    href: str

    @property
    def subject(self) -> str:
        """What the action is about: the request and, when its record was read, the unit."""
        request = self.request
        parts = [
            f"Solicitud de {request.machinery_type or 'maquinaria'}",
            request.project_name or request.project_id or "Proyecto sin identificar",
        ]
        if self.equipment is not None:
            parts.append(f"Unidad {equipment_label(self.equipment)}")
        return " · ".join(parts)

    @property
    def dated_facts(self) -> list[tuple[str, str]]:
        """Source instants behind the decision, named by their origin; never the clock."""
        request = self.request
        if request.approved_at is not None:
            approved = instant(request.approved_at)
        elif request.status.strip().upper() in PENDING:
            approved = "Pendiente; sin approved_at"
        else:
            approved = "Sin approved_at"
        facts = [
            ("Solicitud creada", instant(request.created_at)),
            ("Aprobada", approved),
            ("Período solicitado", f"{day(request.starts_on)} — {day(request.ends_on)}"),
        ]
        unit = self.equipment
        if unit is not None and (unit.assignment_starts_on or unit.assignment_ends_on):
            facts.append(
                (
                    "Asignación vigente en Prisma",
                    f"{day(unit.assignment_starts_on)} — {day(unit.assignment_ends_on)}",
                )
            )
        return facts


def _equipment(hub: HubResponse, request: RequestRecord) -> EquipmentRecord | None:
    evidence = request.provenance
    return next(
        (
            item
            for item in hub.equipment
            if item.id == request.machinery_id
            and item.provenance.source == evidence.source == "nexus"
            and item.provenance.environment == evidence.environment
            and item.provenance.evidence_kind == evidence.evidence_kind
            and item.provenance.is_synthetic == evidence.is_synthetic
        ),
        None,
    )


def _decision(
    hub: HubResponse,
    context: QueryContext,
    request: RequestRecord,
    workflow: WorkflowOverview | None,
) -> DecisionItem | None:
    equipment = _equipment(hub, request)
    movements = sorted(
        matching_current_movements(hub, request, workflow),
        key=lambda movement: movement.id,
    )
    state = request.status.strip().upper()
    source_state = request.status or "Sin estado informado"
    unit = (
        f"Unidad {equipment_label(equipment)}; estado administrativo {equipment.machinery_status}."
        if equipment
        else ""
    )
    registry_available = workflow is not None and workflow.available

    def item(
        title: str,
        evidence: str,
        action: str = "Revisar solicitud",
        movement: MovementRecord | None = None,
    ) -> DecisionItem:
        return DecisionItem(
            request=request,
            equipment=equipment,
            title=title,
            evidence=evidence,
            action=action,
            href=context.movement_href(movement.id)
            if movement
            else context.request_href(request.id),
        )

    # Explicit dispatch incidents take precedence over proposing a new send.
    incidents = {
        "unknown": (
            "Conciliar el resultado del envío",
            "Resultado de envío incierto. Comprobar si existe una tarea sin repetir el envío.",
        ),
        "failed": (
            "Revisar el envío fallido",
            "El movimiento registra un envío fallido; no se reenvía automáticamente.",
        ),
        "blocked": (
            "Revisar la preparación bloqueada",
            "El movimiento tiene una preparación bloqueada; revisar los datos que la impiden.",
        ),
    }
    for incident, (title, explanation) in incidents.items():
        movement = next((row for row in movements if row.state == incident), None)
        if movement is not None:
            return item(title, explanation, "Revisar movimiento", movement)

    active = state in PENDING | APPROVED
    if active and equipment is not None and equipment.maintenance_is_stopped is True:
        return item(
            "Revisar el paro de la unidad",
            f"{unit} El origen registra paro explícito; revisar con Mantenimiento y Logística.",
        )
    if active and equipment is not None and equipment.maintenance_failure_id:
        return item(
            "Revisar la falla registrada",
            f"{unit} Hay una referencia de falla activa. La falla no confirma por sí sola un paro.",
        )

    if state in FINISHED:
        return None
    if not active:
        return item(
            "Revisar el estado de la solicitud",
            f"Estado original: {source_state}. No se ha interpretado como aprobación ni cierre.",
        )
    if state in PENDING:
        return item(
            "Resolver aprobación y asignación"
            if not request.machinery_id
            else "Resolver aprobación",
            f"Solicitud {source_state}; sin unidad asignada."
            if not request.machinery_id
            else f"Solicitud {source_state} con unidad identificada; la aprobación está pendiente.",
        )
    if not request.machinery_id:
        return item("Completar asignación", f"Solicitud {source_state}; falta el ID de la unidad.")
    if equipment is None:
        return item(
            "Verificar unidad asignada",
            "La solicitud tiene un ID de unidad; su registro no está en esta lectura compatible.",
        )

    # OBSOLETA is an administrative value, not a fabricated maintenance failure.
    if equipment.machinery_status.strip().upper() == "OBSOLETA":
        movement = next((row for row in movements if row.receipt is None), None)
        recorded_condition = (
            " Sin falla activa ni paro registrados."
            if equipment.maintenance_failure_id is None
            and equipment.maintenance_is_stopped is False
            else ""
        )
        detail = (
            "Registro de movimientos sin consultar."
            if not registry_available
            else "Sin correspondencias del traslado para esta asignación en el registro consultado."
            if not movements
            else "Revisar la condición administrativa junto con la evidencia del movimiento."
        )
        return item(
            "Revisar la asignación",
            f"{unit}{recorded_condition} {detail}",
            "Revisar movimiento" if movement else "Revisar solicitud",
            movement,
        )

    if not registry_available:
        return item(
            "Consultar el registro del traslado",
            f"{unit} Registro de movimientos sin consultar; no se confirma si existe un plan.",
        )
    if not movements and not workflow.complete:
        return item(
            "Consultar el registro completo del traslado",
            f"{unit} La lectura de movimientos es parcial; puede existir un plan fuera "
            "de esta ventana. Verificarlo antes de preparar otro traslado.",
        )
    if not movements:
        return item(
            "Preparar correspondencias del traslado",
            f"{unit} No hay un plan de esta asignación en el registro consultado.",
        )

    # A receipt on one movement never hides another movement without its own evidence.
    unresolved = [
        row for row in movements if row.state != "sent" or not row.job_id or row.receipt is None
    ]
    if not unresolved:
        if not workflow.complete:
            return item(
                "Consultar el registro completo del traslado",
                "Los movimientos consultados tienen recepción; la lectura parcial no permite "
                "descartar otros movimientos sin resolver.",
            )
        return None
    movement = unresolved[0]
    if movement.state == "draft":
        return item(
            "Revisar el plan local",
            "El movimiento está preparado como plan local; todavía no se ha enviado una tarea.",
            "Revisar movimiento",
            movement,
        )
    if movement.state == "queued":
        return item(
            "Consultar el movimiento en cola",
            "El movimiento está en cola de envío; aún no confirma una tarea en Startrack.",
            "Ver movimiento",
            movement,
        )
    if movement.state == "sending":
        return item(
            "Consultar el envío en curso",
            "El envío está en curso; esperar su resultado sin preparar un envío duplicado.",
            "Ver movimiento",
            movement,
        )
    if movement.state == "sent" and movement.job_id:
        arrival = any(event.kind == "arrival" for event in movement.events)
        return item(
            "Revisar la constancia de recepción"
            if arrival
            else "Consultar seguimiento y recepción",
            "Hay presencia GPS vinculada; no se ha registrado una constancia de recepción."
            if arrival
            else "Hay una tarea vinculada; no se ha registrado una constancia de recepción.",
            "Revisar movimiento",
            movement,
        )
    return item(
        "Verificar la evidencia del movimiento",
        "El registro requiere revisar el estado de envío y el identificador de la tarea.",
        "Revisar movimiento",
        movement,
    )


def decision_items(
    hub: HubResponse,
    context: QueryContext,
    workflow: WorkflowOverview | None = None,
) -> list[DecisionItem]:
    """Return at most one issue per selected request, with a stable identity order."""
    if context.mode != hub.mode or not readable(hub):
        return []
    result = []
    for request in sorted(requests_in_scope(hub, context, workflow), key=lambda row: row.id):
        decision = _decision(hub, context, request, workflow)
        if decision is not None:
            result.append(decision)
    return result
