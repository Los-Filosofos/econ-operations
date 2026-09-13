"""Transactional movement ledger and durable outbox, with no provider calls or DDL.

The claim transaction commits before a caller can issue a POST. A crash after
that commit is ambiguous: recovery changes sending to unknown, never to queued.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import Engine, case, func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.hub import DataMode, EquipmentRecord, HubResponse, Provenance, RequestRecord
from app.models.operations import (
    Movement,
    MovementEventRecord,
    MovementRecord,
    ObservationKind,
    OperationEvent,
    ReceiptRecord,
    SnapshotRecord,
    SourceSnapshot,
)
from app.services.transfers import TransferMapping, compatible_evidence, prepare_transfer

SAFE_REASON_CODES = frozenset(
    (
        "provider_rejected provider_unavailable provider_timeout invalid_response "
        "ambiguous_response worker_interrupted dispatch_blocked mapping_conflict "
        "source_changed not_approved unknown"
    ).split()
)


class LedgerError(Exception):
    """Safe domain error; never wrap provider bodies or database exceptions."""

    message = "La operación del registro no es válida."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)


class MovementNotFound(LedgerError):
    message = "No se encontró el movimiento en el origen seleccionado."


class MovementConflict(LedgerError):
    message = "La referencia ya existe con otra correspondencia o contenido."


class InvalidMovementTransition(LedgerError):
    message = "El estado actual no permite esta operación; no se repetirá el envío."


class EvidenceMismatch(LedgerError):
    message = "La evidencia no coincide con el origen y entorno del movimiento."


Fact = Annotated[str, StringConstraints(strict=True, max_length=2000)] | None


class ObservationData(BaseModel):
    """Only explicit, typed source facts are stored; provider error bodies never are."""

    model_config = ConfigDict(extra="forbid", strict=True)

    job_id: Fact = None
    status: Fact = None
    workflow_role: Fact = None
    poi_id: Fact = None
    tracked_asset_id: Fact = None
    label: Fact = None
    reference: Fact = None
    event_time_raw: Fact = None
    visit_id: Fact = None
    start_date: Fact = None
    changed_date: Fact = None
    closed_date: Fact = None
    last_status_change_date: Fact = None
    objective: Fact = None
    remote_id: Fact = None
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _explicit_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LedgerError("La fecha de evidencia requiere una zona horaria explícita.")
    return value.astimezone(UTC)


def _text(value: str | None, maximum: int = 255) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise LedgerError("La evidencia requiere un texto explícito dentro del límite permitido.")
    return value.strip()


def _provenance_matches(mode: DataMode, provenance: Provenance) -> None:
    if mode not in {"fixture", "live"} or (mode == "live") != (
        provenance.evidence_kind == "live_read"
    ):
        raise EvidenceMismatch()
    if mode == "live" and (provenance.environment != "sandbox" or not provenance.observed_at):
        raise EvidenceMismatch()


def _fresh[T: BaseModel](model: T | None) -> T | None:
    # Revalidate mutable or copy-updated models so callers cannot bypass domain rules.
    return None if model is None else type(model).model_validate(model.model_dump())


def _source_pair(
    mode: DataMode, request: RequestRecord, equipment: EquipmentRecord | None
) -> tuple[RequestRecord, EquipmentRecord | None]:
    request, equipment = _fresh(request), _fresh(equipment)
    _provenance_matches(mode, request.provenance)
    if equipment is not None:
        _provenance_matches(mode, equipment.provenance)
        if not compatible_evidence(request.provenance, equipment.provenance, source=False):
            raise EvidenceMismatch()
    return request, equipment


def _safe_reason(reason_code: str) -> str:
    # This boundary accepts codes, never arbitrary exception strings.
    return reason_code if reason_code in SAFE_REASON_CODES else "unknown"


def _plan_values(
    request: RequestRecord,
    equipment: EquipmentRecord | None,
    mapping: TransferMapping,
    tracked_vehicle_id: str | None,
) -> dict[str, Any]:
    """Column values derived from current source evidence; identity covers mapping and payload."""
    preparation = prepare_transfer(request, equipment, mapping)
    payload = preparation.draft.payload() if preparation.draft else None
    source_request = request.model_dump(mode="json")
    source_equipment = equipment.model_dump(mode="json") if equipment else None
    return {
        "source_request": source_request,
        "source_equipment": source_equipment,
        "source_request_hash": _hash(source_request),
        "source_equipment_hash": _hash(source_equipment) if source_equipment else None,
        "payload": payload,
        "preparation": preparation.model_dump(mode="json"),
        "identity_hash": _hash(
            {
                "mapping": mapping.model_dump(mode="json"),
                "payload": payload,
                "tracked_vehicle_id": tracked_vehicle_id,
            }
        ),
        "state": "draft" if payload else "blocked",
    }


def _aware(value: datetime | None) -> datetime | None:
    """Naive timestamps are UTC; compare only timezone-aware values."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def effective_event_sort_key(
    event: OperationEvent | MovementEventRecord,
) -> tuple[int, datetime, datetime, str]:
    """Total ordering policy for operation events.

    Rules:
    1. Known fact date (has_event_time): Events with an explicit event_time
       represent verified physical occurrences. They take absolute precedence
       over events that only have an observation/read timestamp (observed_at).
       Per policy, reading timestamps never assert actuality over known fact dates.
    2. Primary time: Compares event_time if present, otherwise observed_at
       (or recorded_at as final fallback).
    3. Tie breaking (recorded_at): If two events have identical primary times,
       the one recorded later in the ledger wins.
    4. Deterministic tie breaking (id): Final fallback on event ID.
    """
    return _event_sort_key(
        event.event_time,
        event.observed_at,
        event.recorded_at,
        event.id,
    )


def _event_sort_key(
    event_time: datetime | None,
    observed_at: datetime | None,
    recorded_at: datetime | None = None,
    event_id: str | None = None,
) -> tuple[int, datetime, datetime, str]:
    has_event_time = 1 if event_time is not None else 0
    t_event = _aware(event_time)
    t_observed = _aware(observed_at)
    t_recorded = _aware(recorded_at) or datetime.min.replace(tzinfo=UTC)
    primary_time = t_event or t_observed or t_recorded
    return (
        has_event_time,
        primary_time,
        t_recorded,
        event_id or "",
    )


class OperationsLedger:
    """Each method owns its transaction, suitable for web requests and workers."""

    def __init__(self, engine: Engine):
        self.engine = engine

    @staticmethod
    def _row(
        session: Session, movement_id: str, mode: DataMode, for_update: bool = False
    ) -> Movement:
        if mode not in {"fixture", "live"}:
            raise EvidenceMismatch()
        statement = select(Movement).where(Movement.id == movement_id, Movement.mode == mode)
        if for_update:
            statement = statement.with_for_update()
        row = session.exec(statement).first()
        if row is None:
            raise MovementNotFound()
        return row

    @staticmethod
    def _event(session: Session, row: Movement, kind: str, **values: Any) -> None:
        session.add(
            OperationEvent(
                id=str(uuid4()),
                movement_id=row.id,
                kind=kind,
                state=row.state,
                recorded_at=_now(),
                **values,
            )
        )

    @staticmethod
    def _record(session: Session, row: Movement) -> MovementRecord:
        events = session.exec(
            select(OperationEvent)
            .where(OperationEvent.movement_id == row.id)
            .order_by(OperationEvent.recorded_at, OperationEvent.id)
        ).all()
        return MovementRecord(
            **row.model_dump(exclude={"identity_hash"}),
            events=[MovementEventRecord.model_validate(event.model_dump()) for event in events],
        )

    def _records(self, query) -> list[MovementRecord]:
        with Session(self.engine) as session:
            return [self._record(session, row) for row in session.exec(query).all()]

    def _apply(
        self,
        session: Session,
        row: Movement,
        statement,
        error: type[LedgerError],
        kind: str,
        **event,
    ) -> MovementRecord:
        """Guarded single-row transition followed by its event, in one transaction."""
        if session.execute(statement).rowcount != 1:
            raise error()
        session.refresh(row)
        self._event(session, row, kind, **event)
        session.commit()
        return self._record(session, row)

    @staticmethod
    def _criteria(mode: DataMode, request_source_id: str | None) -> list:
        if mode not in {"fixture", "live"}:
            raise EvidenceMismatch()
        criteria = [Movement.mode == mode]
        if request_source_id is not None:
            criteria.append(Movement.request_source_id == request_source_id)
        return criteria

    def get(self, movement_id: str, mode: DataMode) -> MovementRecord:
        with Session(self.engine) as session:
            return self._record(session, self._row(session, movement_id, mode))

    def count(self, mode: DataMode, *, request_source_id: str | None = None) -> int:
        query = select(func.count(Movement.id)).where(*self._criteria(mode, request_source_id))
        with Session(self.engine) as session:
            return session.exec(query).one()

    def list(
        self,
        mode: DataMode,
        *,
        request_source_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[MovementRecord]:
        return self._records(
            select(Movement)
            .where(*self._criteria(mode, request_source_id))
            .order_by(Movement.created_at.desc(), Movement.id)
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )

    def list_page(
        self,
        mode: DataMode,
        *,
        request_source_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[MovementRecord], int]:
        items = self.list(mode, request_source_id=request_source_id, offset=offset, limit=limit)
        return items, self.count(mode, request_source_id=request_source_id)

    def select_for_review(
        self, mode: DataMode, states: tuple[str, ...] | list[str], *, limit: int = 25
    ) -> list[MovementRecord]:
        return self._records(
            select(Movement)
            .where(*self._criteria(mode, None), Movement.state.in_(states))
            .order_by(Movement.next_review_at.asc(), Movement.created_at.asc(), Movement.id.asc())
            .limit(max(1, min(limit, 100)))
        )

    def advance_review(self, movement_id: str, mode: DataMode, *, delay_seconds: int = 0) -> None:
        with Session(self.engine) as session:
            session.execute(
                update(Movement)
                .where(Movement.id == movement_id, *self._criteria(mode, None))
                .values(next_review_at=_now() + timedelta(seconds=delay_seconds))
            )
            session.commit()

    @staticmethod
    def _existing(session: Session, mode: str, environment: str, reference: str) -> Movement | None:
        return session.exec(
            select(Movement).where(
                Movement.mode == mode,
                Movement.environment == environment,
                Movement.movement_reference == reference,
            )
        ).first()

    def create(
        self,
        mode: DataMode,
        request: RequestRecord,
        equipment: EquipmentRecord | None,
        mapping: TransferMapping,
        *,
        tracked_vehicle_id: str | None = None,
    ) -> MovementRecord:
        request, equipment = _source_pair(mode, request, equipment)
        mapping = _fresh(mapping)
        tracked_vehicle_id = _text(tracked_vehicle_id)
        values = _plan_values(request, equipment, mapping, tracked_vehicle_id)
        now = _now()
        row = Movement(
            id=str(uuid4()),
            mode=mode,
            environment=request.provenance.environment,
            movement_reference=_text(mapping.movement_reference),
            request_source_id=_text(mapping.request_source_id),
            machinery_source_id=_text(mapping.machinery_source_id),
            project_source_id=_text(mapping.project_source_id),
            tracked_vehicle_id=tracked_vehicle_id,
            mapping=mapping.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
            next_review_at=now,
            **values,
        )
        identity = (mode, row.environment, row.movement_reference, row.identity_hash)
        event = {"request": values["source_request"], "equipment": values["source_equipment"]}
        with Session(self.engine) as session:
            existing = self._existing(session, *identity[:3])
            if existing is None:
                session.add(row)
                try:
                    session.flush()
                    self._event(session, row, "created", data=event)
                    session.commit()
                    return self._record(session, row)
                except IntegrityError:
                    session.rollback()
                    existing = self._existing(session, *identity[:3])
            if existing is None or existing.identity_hash != identity[3]:
                raise MovementConflict()
            return self._record(session, existing)

    def revalidate(
        self,
        movement_id: str,
        mode: DataMode,
        request: RequestRecord,
        equipment: EquipmentRecord | None,
    ) -> MovementRecord:
        """Refresh unsent source evidence; retained events preserve earlier snapshots."""
        request, equipment = _source_pair(mode, request, equipment)
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            if row.state not in {"draft", "blocked"}:
                raise InvalidMovementTransition()
            original = Provenance.model_validate(row.source_request["provenance"])
            if (
                request.provenance.source != "nexus"
                or request.provenance.source_id != row.request_source_id
                or request.provenance.environment != row.environment
                or not compatible_evidence(request.provenance, original, source=False)
                or request.project_id != row.project_source_id
            ):
                raise EvidenceMismatch()
            if equipment is not None and (
                equipment.provenance.source != "nexus"
                or equipment.provenance.source_id != row.machinery_source_id
            ):
                raise EvidenceMismatch()
            mapping = TransferMapping.model_validate(row.mapping)
            values = _plan_values(request, equipment, mapping, row.tracked_vehicle_id)
            return self._apply(
                session,
                row,
                update(Movement)
                .where(
                    Movement.id == row.id,
                    Movement.state.in_(["draft", "blocked"]),
                    Movement.updated_at == row.updated_at,
                )
                .values(updated_at=_now(), next_review_at=_now(), **values),
                InvalidMovementTransition,
                "revalidated",
                data={"request": values["source_request"], "equipment": values["source_equipment"]},
            )

    def queue(self, movement_id: str, mode: DataMode = "live") -> MovementRecord:
        if mode != "live":
            raise EvidenceMismatch()
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            _provenance_matches(mode, Provenance.model_validate(row.source_request["provenance"]))
            if row.source_equipment is None or row.payload is None:
                raise InvalidMovementTransition()
            _provenance_matches(mode, Provenance.model_validate(row.source_equipment["provenance"]))
            if row.state == "queued":
                return self._record(session, row)
            now = _now()
            return self._apply(
                session,
                row,
                update(Movement)
                .where(Movement.id == movement_id, Movement.mode == mode, Movement.state == "draft")
                .values(state="queued", queued_at=now, updated_at=now),
                InvalidMovementTransition,
                "queued",
            )

    def claim(self, movement_id: str | None = None) -> MovementRecord | None:
        """Atomically claim at most one queued live movement, committing before return."""
        with Session(self.engine) as session:
            criteria = [Movement.mode == "live", Movement.state == "queued"]
            if movement_id is None:
                candidate = (
                    select(Movement.id)
                    .where(*criteria)
                    .order_by(Movement.queued_at, Movement.id)
                    .limit(1)
                    .scalar_subquery()
                )
                criteria.append(Movement.id == candidate)
            else:
                criteria.append(Movement.id == movement_id)
            now = _now()
            row = session.execute(
                update(Movement)
                .where(*criteria)
                .values(state="sending", sending_at=now, updated_at=now)
                .returning(Movement)
            ).scalar_one_or_none()
            if row is None:
                return None
            self._event(session, row, "sending")
            session.commit()
            return self._record(session, row)

    def _finish(self, movement_id: str, state: str, **values: Any) -> MovementRecord:
        with Session(self.engine) as session:
            row = session.execute(
                update(Movement)
                .where(
                    Movement.id == movement_id,
                    Movement.mode == "live",
                    Movement.state.in_(["sending", "unknown"])
                    if state == "sent"
                    else Movement.state == "sending",
                )
                .values(state=state, updated_at=_now(), next_review_at=_now(), **values)
                .returning(Movement)
            ).scalar_one_or_none()
            if row is None:
                self._row(session, movement_id, "live")
                raise InvalidMovementTransition()
            self._event(session, row, state, data={"reason_code": row.reason_code})
            session.commit()
            return self._record(session, row)

    def finish_sent(
        self,
        movement_id: str,
        job_id: str,
        *,
        status: str | None = None,
        workflow_role: str | None = None,
    ) -> MovementRecord:
        return self._finish(
            movement_id,
            "sent",
            job_id=_text(job_id),
            status=_text(status),
            workflow_role=_text(workflow_role),
            sent_at=_now(),
            reason_code=None,
        )

    def finish_unknown(self, movement_id: str, reason_code: str = "unknown") -> MovementRecord:
        return self._finish(movement_id, "unknown", reason_code=_safe_reason(reason_code))

    def finish_failed(
        self, movement_id: str, reason_code: str = "provider_rejected"
    ) -> MovementRecord:
        return self._finish(movement_id, "failed", reason_code=_safe_reason(reason_code))

    def recover_stale_sending(self, before: datetime) -> int:
        before = _explicit_time(before)
        with Session(self.engine) as session:
            rows = (
                session.execute(
                    update(Movement)
                    .where(
                        Movement.mode == "live",
                        Movement.state == "sending",
                        Movement.sending_at < before,
                    )
                    .values(
                        state="unknown",
                        reason_code="worker_interrupted",
                        updated_at=_now(),
                        next_review_at=_now(),
                    )
                    .returning(Movement)
                )
                .scalars()
                .all()
            )
            for row in rows:
                self._event(session, row, "unknown", data={"reason_code": "worker_interrupted"})
            session.commit()
            return len(rows)

    def record_receipt(
        self,
        movement_id: str,
        mode: DataMode,
        *,
        receiver: str,
        received_at: datetime,
        reference: str,
        note: str | None = None,
    ) -> MovementRecord:
        if mode != "live":
            raise EvidenceMismatch()
        receipt = ReceiptRecord(
            receiver=_text(receiver),
            received_at=_explicit_time(received_at),
            reference=_text(reference),
            note=_text(note, maximum=2000),
            recorded_at=_now(),
        )
        data = receipt.model_dump(mode="json")
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            if row.state != "sent" or not row.job_id:
                raise InvalidMovementTransition()
            if row.receipt is not None:
                previous = ReceiptRecord.model_validate(row.receipt)
                if previous.model_dump(exclude={"recorded_at"}) != receipt.model_dump(
                    exclude={"recorded_at"}
                ):
                    raise MovementConflict()
                return self._record(session, row)
            return self._apply(
                session,
                row,
                update(Movement)
                .where(Movement.id == movement_id, Movement.receipt.is_(None))
                .values(receipt=data, updated_at=_now()),
                MovementConflict,
                "receipt",
                event_time=receipt.received_at,
                data=data,
            )

    def record_observation(
        self,
        movement_id: str,
        mode: DataMode,
        *,
        kind: ObservationKind,
        source_id: str,
        event_time: datetime | None,
        observed_at: datetime,
        data: dict[str, Any],
        provenance: Provenance,
    ) -> MovementRecord:
        if kind not in {"task_state", "arrival"}:
            raise LedgerError("El tipo de observación no está permitido.")
        provenance = _fresh(provenance)
        _provenance_matches(mode, provenance)
        source_id = _text(source_id)
        observed_at = _explicit_time(observed_at)
        event_time = _explicit_time(event_time) if event_time else None
        try:
            data = ObservationData.model_validate(data).model_dump(exclude_unset=True)
        except ValidationError:
            raise LedgerError("La observación contiene campos de evidencia no válidos.") from None
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode, for_update=True)
            request_provenance = Provenance.model_validate(row.source_request["provenance"])
            if (
                provenance.source != "startrack"
                or provenance.environment != row.environment
                or not compatible_evidence(provenance, request_provenance, source=False)
                or provenance.observed_at != observed_at
                or provenance.source_id != source_id
                or (data.get("job_id") is not None and data["job_id"] != row.job_id)
            ):
                raise EvidenceMismatch()
            if kind == "task_state" and (
                not row.job_id or source_id != row.job_id or data.get("job_id") != row.job_id
            ):
                raise EvidenceMismatch()
            if kind == "arrival" and (
                not row.tracked_vehicle_id
                or data.get("tracked_asset_id") != row.tracked_vehicle_id
                or data.get("poi_id") != row.mapping["poi_id"]
            ):
                raise EvidenceMismatch()
            evidence_hash = _hash(
                {
                    "kind": kind,
                    "source_id": source_id,
                    "event_time": event_time.isoformat() if event_time else None,
                    "data": data,
                    "provenance": provenance.model_dump(mode="json", exclude={"observed_at"}),
                }
            )
            duplicate = select(OperationEvent.id).where(
                OperationEvent.movement_id == row.id, OperationEvent.evidence_hash == evidence_hash
            )
            if session.exec(duplicate).first() is not None:
                return self._record(session, row)
            self._event(
                session,
                row,
                kind,
                source_id=source_id,
                evidence_hash=evidence_hash,
                event_time=event_time,
                observed_at=observed_at,
                data=data,
                provenance=provenance.model_dump(mode="json"),
            )
            if kind == "task_state":
                # A late source event must not overwrite a newer task status.
                latest = session.exec(
                    select(OperationEvent)
                    .where(
                        OperationEvent.movement_id == row.id,
                        OperationEvent.kind == "task_state",
                        OperationEvent.evidence_hash != evidence_hash,
                    )
                    .order_by(
                        case((OperationEvent.event_time.is_not(None), 1), else_=0).desc(),
                        func.coalesce(
                            OperationEvent.event_time,
                            OperationEvent.observed_at,
                            OperationEvent.recorded_at,
                        ).desc(),
                        OperationEvent.recorded_at.desc(),
                        OperationEvent.id.desc(),
                    )
                    .limit(1)
                ).first()
                incoming_key = _event_sort_key(
                    event_time,
                    observed_at,
                    _now(),
                    None,
                )
                latest_key = effective_event_sort_key(latest) if latest is not None else None
                if latest_key is None or incoming_key >= latest_key:
                    row.status = data.get("status", row.status)
                    row.workflow_role = data.get("workflow_role", row.workflow_role)
            row.updated_at = _now()
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if session.exec(duplicate).first() is None:
                    raise MovementConflict() from None
            return self._record(session, row)

    def record_snapshot(self, hub: HubResponse) -> SnapshotRecord:
        """Persist the bounded source response including coverage and original timestamps."""
        hub = _fresh(hub)
        for record in [*hub.requests, *hub.equipment]:
            _provenance_matches(hub.mode, record.provenance)
        for equipment in hub.equipment:
            nested = [transfer.provenance for transfer in equipment.transfers]
            if equipment.location is not None:
                nested.append(equipment.location.provenance)
            for provenance in nested:
                _provenance_matches(hub.mode, provenance)
                if provenance.environment != equipment.provenance.environment:
                    raise EvidenceMismatch()
        content = hub.model_dump(mode="json")
        row = SourceSnapshot(
            id=str(uuid4()),
            mode=hub.mode,
            recorded_at=_now(),
            generated_at=_explicit_time(hub.generated_at),
            data_as_of=_explicit_time(hub.data_as_of) if hub.data_as_of else None,
            content_hash=_hash(content),
            content=content,
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return SnapshotRecord.model_validate(row.model_dump())

    def last_snapshot(self, mode: DataMode) -> SnapshotRecord | None:
        if mode not in {"fixture", "live"}:
            raise EvidenceMismatch()
        with Session(self.engine) as session:
            row = session.exec(
                select(SourceSnapshot)
                .where(SourceSnapshot.mode == mode)
                .order_by(SourceSnapshot.recorded_at.desc(), SourceSnapshot.id)
                .limit(1)
            ).first()
            return SnapshotRecord.model_validate(row.model_dump()) if row else None
