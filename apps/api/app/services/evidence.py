"""Shared, read-only projection of persisted evidence onto current source identities."""

from collections.abc import Iterable
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.models.hub import (
    HubResponse,
    OperationEvidenceStatus,
    Provenance,
    RequestRecord,
    TransferRecord,
)
from app.models.operations import MovementEventRecord, MovementRecord
from app.services.ledger import LedgerError, OperationsLedger, effective_event_sort_key

MOVEMENT_LIMIT = 100


def _compatible(left: Provenance, right: Provenance, *, source: bool = True) -> bool:
    return (
        (not source or left.source == right.source)
        and left.environment == right.environment
        and left.evidence_kind == right.evidence_kind
        and left.is_synthetic == right.is_synthetic
    )


def matching_current_movements(
    hub: HubResponse, request: RequestRecord, movements: Iterable[MovementRecord]
) -> list[MovementRecord]:
    """Match exact current assignment and period; never join by names or remote references."""
    evidence = request.provenance
    if (
        evidence.source != "nexus"
        or not evidence.source_id
        or not request.project_id
        or not request.machinery_id
        or (hub.mode == "live") != (evidence.evidence_kind == "live_read")
    ):
        return []
    equipment = next(
        (
            item
            for item in hub.equipment
            if item.id == request.machinery_id
            and item.provenance.source_id
            and _compatible(item.provenance, evidence)
        ),
        None,
    )
    if equipment is None:
        return []
    matches = []
    current_request = request.model_dump(mode="json")
    for movement in movements:
        stored_request = movement.source_request
        stored_equipment = movement.source_equipment or {}
        try:
            stored_evidence = Provenance.model_validate(stored_request.get("provenance"))
            machine_evidence = Provenance.model_validate(stored_equipment.get("provenance"))
        except ValidationError:
            continue
        if (
            movement.mode == hub.mode
            and movement.environment == evidence.environment
            and movement.request_source_id == evidence.source_id == stored_evidence.source_id
            and movement.project_source_id == request.project_id == stored_request.get("project_id")
            and movement.machinery_source_id
            == equipment.provenance.source_id
            == machine_evidence.source_id
            and stored_request.get("id") == request.id
            and stored_request.get("machinery_id") == request.machinery_id
            and stored_equipment.get("id") == equipment.id
            and all(
                stored_request.get(field) == current_request.get(field)
                for field in ("starts_on", "ends_on", "approved_at")
            )
            and _compatible(stored_evidence, evidence)
            and _compatible(machine_evidence, equipment.provenance)
        ):
            matches.append(movement)
    return matches


def _source_event(movement: MovementRecord, event: MovementEventRecord) -> bool:
    provenance = event.provenance
    try:
        source = Provenance.model_validate(movement.source_request.get("provenance"))
    except ValidationError:
        return False
    return bool(
        provenance
        and provenance.source == "startrack"
        and provenance.source_id == event.source_id
        and provenance.observed_at == event.observed_at
        and provenance.environment == movement.environment
        and _compatible(provenance, source, source=False)
        and (movement.mode == "live") == (provenance.evidence_kind == "live_read")
    )


def _instant(value: datetime | None) -> datetime:
    """Stored ledger timestamps are UTC; tolerate legacy naive values for stable ordering."""
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _transfer(movement: MovementRecord, request: RequestRecord) -> TransferRecord:
    events = [
        event
        for event in movement.events
        if event.kind == "task_state"
        and event.source_id == movement.job_id
        and event.data.get("job_id") == movement.job_id
        and _source_event(movement, event)
    ]
    latest = max(
        events,
        key=effective_event_sort_key,
        default=None,
    )
    provenance = (
        latest.provenance
        if latest
        else Provenance(
            source="startrack",
            source_id=movement.job_id,
            environment=request.provenance.environment,
            observed_at=movement.sent_at,
            is_synthetic=request.provenance.is_synthetic,
            evidence_kind=request.provenance.evidence_kind,
            source_reference=f"operation_movements/{movement.id}",
        )
    )
    return TransferRecord(
        id=f"startrack:job:{movement.job_id}",
        code=movement.job_id or "",
        status=(latest.data.get("status") if latest else movement.status) or "",
        request_id=request.id,
        destination_project_id=movement.project_source_id,
        destination_project_name=request.project_name,
        movement_id=movement.id,
        workflow_role=latest.data.get("workflow_role") if latest else movement.workflow_role,
        event_time=latest.event_time if latest else None,
        recorded_at=latest.recorded_at if latest else movement.sent_at,
        evidence_origin="task_observation" if latest else "creation_acknowledgment",
        source_data=latest.data if latest else {},
        provenance=provenance,
    )


def project_operation_evidence(hub: HubResponse, engine: Engine | None) -> HubResponse:
    """Read a bounded ledger window without provider calls, writes or historical fallback."""
    if engine is None:
        return hub
    checked_at = datetime.now(UTC)
    try:
        candidates = OperationsLedger(engine).list(hub.mode, limit=MOVEMENT_LIMIT + 1)
    except (SQLAlchemyError, LedgerError, ValidationError):
        hub.operation_evidence = OperationEvidenceStatus(
            status="error",
            checked_at=checked_at,
            message="Registro no disponible: revisa la conexión y la migración del servidor.",
        )
        return hub
    movements = candidates[:MOVEMENT_LIMIT]
    complete = len(candidates) <= MOVEMENT_LIMIT
    hub.operation_evidence = OperationEvidenceStatus(
        status="available" if complete else "partial",
        checked_at=checked_at,
        movements_returned=len(movements),
        complete=complete,
        message=(
            "Registro local consultado. Se relacionan solo la asignación y el período vigentes; "
            "la evidencia histórica conserva sus fechas y no acredita conexión actual."
            if complete
            else "Registro parcial: se consultaron los 100 movimientos más recientes del modo. "
            "Puede existir evidencia fuera de esta ventana."
        ),
    )
    equipment_by_id = {item.id: item for item in hub.equipment}
    for request in hub.requests:
        transfers = [
            _transfer(movement, request)
            for movement in matching_current_movements(hub, request, movements)
            if movement.state == "sent" and movement.job_id
        ]
        if transfers:
            equipment = equipment_by_id[request.machinery_id]
            equipment.transfers.extend(transfers)
            equipment.relation_status = "confirmed"
            equipment.relation_note = (
                "Tarea registrada para los IDs, asignación y período de esta solicitud. "
                "La observación conservada no acredita ubicación actual ni recepción."
            )
    source = next((item for item in hub.sources if item.id == "startrack"), None)
    if source:
        observations = [
            event.observed_at
            for movement in movements
            if movement.environment == source.environment
            for event in movement.events
            if event.kind in {"task_state", "arrival"}
            and event.observed_at is not None
            and _source_event(movement, event)
        ]
        source.last_evidence_at = max(observations, key=_instant, default=None)
        if source.last_evidence_at:
            source.message += " Hay evidencia histórica conservada; no es una consulta actual."
    return hub
