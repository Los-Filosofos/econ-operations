"""Transactional movement ledger and durable outbox, with no provider calls or DDL.

The claim transaction commits before a caller can issue a POST. A crash after
that commit is ambiguous: recovery changes sending to unknown, never to queued.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Engine, update
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
from app.services.transfers import TransferMapping, TransferPreparation, prepare_transfer

SAFE_REASON_CODES = frozenset(
    {
        "provider_rejected",
        "provider_unavailable",
        "provider_timeout",
        "invalid_response",
        "ambiguous_response",
        "worker_interrupted",
        "dispatch_blocked",
        "mapping_conflict",
        "source_changed",
        "not_approved",
        "unknown",
    }
)


class LedgerError(Exception):
    """Safe domain error; never wrap provider bodies or database exceptions."""


class MovementNotFound(LedgerError):
    def __init__(self):
        super().__init__("No se encontró el movimiento en el origen seleccionado.")


class MovementConflict(LedgerError):
    def __init__(self):
        super().__init__("La referencia ya existe con otra correspondencia o contenido.")


class InvalidMovementTransition(LedgerError):
    def __init__(self):
        super().__init__("El estado actual no permite esta operación; no se repetirá el envío.")


class EvidenceMismatch(LedgerError):
    def __init__(self):
        super().__init__("La evidencia no coincide con el origen y entorno del movimiento.")


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _stored_time(value: datetime | None) -> datetime | None:
    # SQLite drops tzinfo from DateTime; all SQL datetime writes use UTC.
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _explicit_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LedgerError("La fecha de evidencia requiere una zona horaria explícita.")
    return value.astimezone(UTC)


def _text(value: str, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise LedgerError("La evidencia requiere un texto explícito dentro del límite permitido.")
    return value.strip()


def _mode(mode: DataMode) -> None:
    if mode not in {"fixture", "live"}:
        raise EvidenceMismatch()


def _provenance_matches(mode: DataMode, provenance: Provenance) -> None:
    _mode(mode)
    if (mode == "live") != (provenance.evidence_kind == "live_read"):
        raise EvidenceMismatch()
    if mode == "live" and (provenance.environment != "sandbox" or not provenance.observed_at):
        raise EvidenceMismatch()


def _safe_reason(reason_code: str) -> str:
    # This boundary accepts codes, never arbitrary exception strings.
    return reason_code if reason_code in SAFE_REASON_CODES else "unknown"


class OperationsLedger:
    """Each method owns its transaction, suitable for web requests and workers."""

    def __init__(self, engine: Engine):
        self.engine = engine

    @staticmethod
    def _row(session: Session, movement_id: str, mode: DataMode) -> Movement:
        _mode(mode)
        row = session.exec(
            select(Movement).where(Movement.id == movement_id, Movement.mode == mode)
        ).first()
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
        data = row.model_dump(exclude={"identity_hash"})
        for field in ("created_at", "updated_at", "queued_at", "sending_at", "sent_at"):
            data[field] = _stored_time(data[field])
        data["events"] = [
            MovementEventRecord(
                **event.model_dump(
                    exclude={
                        "movement_id",
                        "evidence_hash",
                        "event_time",
                        "observed_at",
                        "recorded_at",
                    }
                ),
                event_time=_stored_time(event.event_time),
                observed_at=_stored_time(event.observed_at),
                recorded_at=_stored_time(event.recorded_at),
            )
            for event in events
        ]
        return MovementRecord.model_validate(data)

    def get(self, movement_id: str, mode: DataMode) -> MovementRecord:
        with Session(self.engine) as session:
            return self._record(session, self._row(session, movement_id, mode))

    def list(
        self,
        mode: DataMode,
        *,
        environment: str | None = None,
        request_source_id: str | None = None,
        limit: int = 100,
    ) -> list[MovementRecord]:
        _mode(mode)
        query = select(Movement).where(Movement.mode == mode)
        if environment is not None:
            query = query.where(Movement.environment == environment)
        if request_source_id is not None:
            query = query.where(Movement.request_source_id == request_source_id)
        query = query.order_by(Movement.created_at.desc(), Movement.id).limit(
            max(1, min(limit, 500))
        )
        with Session(self.engine) as session:
            return [self._record(session, row) for row in session.exec(query).all()]

    def create(
        self,
        mode: DataMode,
        request: RequestRecord,
        equipment: EquipmentRecord | None,
        mapping: TransferMapping,
        preparation: TransferPreparation | None = None,
        *,
        tracked_vehicle_id: str | None = None,
    ) -> MovementRecord:
        # Revalidate mutable/copy-created models; caller-supplied preparation is
        # informational only and cannot bypass the shared domain rules.
        request = RequestRecord.model_validate(request.model_dump())
        equipment = (
            EquipmentRecord.model_validate(equipment.model_dump())
            if equipment is not None
            else None
        )
        mapping = TransferMapping.model_validate(mapping.model_dump())
        _provenance_matches(mode, request.provenance)
        if equipment is not None:
            _provenance_matches(mode, equipment.provenance)
            if (
                request.provenance.environment != equipment.provenance.environment
                or request.provenance.evidence_kind != equipment.provenance.evidence_kind
                or request.provenance.is_synthetic != equipment.provenance.is_synthetic
            ):
                raise EvidenceMismatch()
        actual_preparation = prepare_transfer(request, equipment, mapping)
        payload = actual_preparation.draft.payload() if actual_preparation.draft else None
        mapping_data = mapping.model_dump(mode="json")
        tracked_vehicle_id = _text(tracked_vehicle_id) if tracked_vehicle_id is not None else None
        identity_hash = _hash(
            {"mapping": mapping_data, "payload": payload, "tracked_vehicle_id": tracked_vehicle_id}
        )
        source_request = request.model_dump(mode="json")
        source_equipment = equipment.model_dump(mode="json") if equipment else None
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
            mapping=mapping_data,
            source_request=source_request,
            source_equipment=source_equipment,
            source_request_hash=_hash(source_request),
            source_equipment_hash=_hash(source_equipment) if source_equipment else None,
            identity_hash=identity_hash,
            payload=payload,
            preparation=actual_preparation.model_dump(mode="json"),
            state="draft" if payload else "blocked",
            created_at=now,
            updated_at=now,
        )
        with Session(self.engine) as session:
            existing = session.exec(
                select(Movement).where(
                    Movement.mode == mode,
                    Movement.environment == row.environment,
                    Movement.movement_reference == row.movement_reference,
                )
            ).first()
            if existing is not None:
                if existing.identity_hash != identity_hash:
                    raise MovementConflict()
                return self._record(session, existing)
            session.add(row)
            try:
                session.flush()
                self._event(
                    session,
                    row,
                    "created",
                    data={"request": source_request, "equipment": source_equipment},
                )
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.exec(
                    select(Movement).where(
                        Movement.mode == mode,
                        Movement.environment == row.environment,
                        Movement.movement_reference == row.movement_reference,
                    )
                ).first()
                if existing is None or existing.identity_hash != identity_hash:
                    raise MovementConflict() from None
                return self._record(session, existing)
            return self._record(session, row)

    def revalidate(
        self,
        movement_id: str,
        mode: DataMode,
        request: RequestRecord,
        equipment: EquipmentRecord | None,
        preparation: TransferPreparation | None = None,
    ) -> MovementRecord:
        """Refresh unsent source evidence; retained events preserve earlier snapshots."""
        request = RequestRecord.model_validate(request.model_dump())
        equipment = (
            EquipmentRecord.model_validate(equipment.model_dump())
            if equipment is not None
            else None
        )
        _provenance_matches(mode, request.provenance)
        if equipment is not None:
            _provenance_matches(mode, equipment.provenance)
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            if row.state not in {"draft", "blocked"}:
                raise InvalidMovementTransition()
            original_provenance = Provenance.model_validate(row.source_request["provenance"])
            if (
                request.provenance.source != "nexus"
                or request.provenance.source_id != row.request_source_id
                or request.provenance.environment != row.environment
                or request.provenance.evidence_kind != original_provenance.evidence_kind
                or request.provenance.is_synthetic != original_provenance.is_synthetic
                or request.project_id != row.project_source_id
            ):
                raise EvidenceMismatch()
            if equipment is not None and (
                equipment.provenance.source != "nexus"
                or equipment.provenance.source_id != row.machinery_source_id
                or equipment.provenance.environment != row.environment
                or equipment.provenance.evidence_kind != request.provenance.evidence_kind
                or equipment.provenance.is_synthetic != request.provenance.is_synthetic
            ):
                raise EvidenceMismatch()
            mapping = TransferMapping.model_validate(row.mapping)
            actual = prepare_transfer(request, equipment, mapping)
            payload = actual.draft.payload() if actual.draft else None
            request_data = request.model_dump(mode="json")
            equipment_data = equipment.model_dump(mode="json") if equipment else None
            values = {
                "source_request": request_data,
                "source_equipment": equipment_data,
                "source_request_hash": _hash(request_data),
                "source_equipment_hash": _hash(equipment_data) if equipment_data else None,
                "preparation": actual.model_dump(mode="json"),
                "payload": payload,
                "identity_hash": _hash(
                    {
                        "mapping": row.mapping,
                        "payload": payload,
                        "tracked_vehicle_id": row.tracked_vehicle_id,
                    }
                ),
                "state": "draft" if payload else "blocked",
                "updated_at": _now(),
            }
            changed = session.execute(
                update(Movement)
                .where(
                    Movement.id == row.id,
                    Movement.state.in_(["draft", "blocked"]),
                    Movement.updated_at == row.updated_at,
                )
                .values(**values)
            ).rowcount
            if changed != 1:
                raise InvalidMovementTransition()
            session.refresh(row)
            self._event(
                session,
                row,
                "revalidated",
                data={"request": request_data, "equipment": equipment_data},
            )
            session.commit()
            return self._record(session, row)

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
            changed = session.execute(
                update(Movement)
                .where(Movement.id == movement_id, Movement.mode == mode, Movement.state == "draft")
                .values(state="queued", queued_at=now, updated_at=now)
            ).rowcount
            if changed != 1:
                raise InvalidMovementTransition()
            session.refresh(row)
            self._event(session, row, "queued")
            session.commit()
            return self._record(session, row)

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
                .values(state=state, updated_at=_now(), **values)
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
            status=_text(status) if status is not None else None,
            workflow_role=_text(workflow_role) if workflow_role is not None else None,
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
                    .values(state="unknown", reason_code="worker_interrupted", updated_at=_now())
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
            note=_text(note, maximum=2000) if note is not None else None,
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
            changed = session.execute(
                update(Movement)
                .where(Movement.id == movement_id, Movement.receipt.is_(None))
                .values(receipt=data, updated_at=_now())
            ).rowcount
            if changed != 1:
                raise MovementConflict()
            session.refresh(row)
            self._event(session, row, "receipt", event_time=receipt.received_at, data=data)
            session.commit()
            return self._record(session, row)

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
        provenance = Provenance.model_validate(provenance.model_dump())
        _provenance_matches(mode, provenance)
        source_id = _text(source_id)
        observed_at = _explicit_time(observed_at)
        event_time = _explicit_time(event_time) if event_time else None
        # Keep only explicit, typed source facts; never persist provider error bodies.
        allowed = {
            "job_id",
            "status",
            "workflow_role",
            "poi_id",
            "tracked_asset_id",
            "latitude",
            "longitude",
            "label",
            "reference",
            "event_time_raw",
            "visit_id",
            "start_date",
            "changed_date",
            "closed_date",
            "last_status_change_date",
            "objective",
            "remote_id",
        }
        if set(data) - allowed:
            raise LedgerError("La observación contiene campos no admitidos como evidencia.")
        for key, value in data.items():
            if value is None:
                continue
            if key in {"latitude", "longitude"}:
                if type(value) not in {int, float}:
                    raise LedgerError("La observación contiene coordenadas no válidas.")
                bound = 90 if key == "latitude" else 180
                if not -bound <= value <= bound:
                    raise LedgerError("La observación contiene coordenadas no válidas.")
            elif not isinstance(value, str) or len(value) > 2000:
                raise LedgerError("La observación contiene campos de evidencia no válidos.")
        try:
            serialized_data = json.loads(json.dumps(data, ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError):
            raise LedgerError("La observación contiene campos de evidencia no válidos.") from None
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            request_provenance = Provenance.model_validate(row.source_request["provenance"])
            if (
                provenance.source != "startrack"
                or provenance.environment != row.environment
                or provenance.evidence_kind != request_provenance.evidence_kind
                or provenance.is_synthetic != request_provenance.is_synthetic
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
            evidence = {
                "kind": kind,
                "source_id": source_id,
                "event_time": event_time.isoformat() if event_time else None,
                "data": serialized_data,
                "provenance": provenance.model_dump(mode="json", exclude={"observed_at"}),
            }
            evidence_hash = _hash(evidence)
            existing = session.exec(
                select(OperationEvent).where(
                    OperationEvent.movement_id == row.id,
                    OperationEvent.evidence_hash == evidence_hash,
                )
            ).first()
            if existing is not None:
                return self._record(session, row)
            self._event(
                session,
                row,
                kind,
                source_id=source_id,
                evidence_hash=evidence_hash,
                event_time=event_time,
                observed_at=observed_at,
                data=serialized_data,
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
                    .order_by(OperationEvent.event_time.desc(), OperationEvent.observed_at.desc())
                    .limit(1)
                ).first()
                previous_time = (
                    _stored_time(latest.event_time or latest.observed_at) if latest else None
                )
                if previous_time is None or (event_time or observed_at) >= previous_time:
                    row.status = data.get("status", row.status)
                    row.workflow_role = data.get("workflow_role", row.workflow_role)
            row.updated_at = _now()
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if (
                    session.exec(
                        select(OperationEvent.id).where(
                            OperationEvent.movement_id == row.id,
                            OperationEvent.evidence_hash == evidence_hash,
                        )
                    ).first()
                    is None
                ):
                    raise MovementConflict() from None
            return self._record(session, row)

    def record_snapshot(self, hub: HubResponse) -> SnapshotRecord:
        """Persist the bounded source response including coverage and original timestamps."""
        hub = HubResponse.model_validate(hub.model_dump())
        for record in [*hub.requests, *hub.equipment]:
            _provenance_matches(hub.mode, record.provenance)
        for equipment in hub.equipment:
            for transfer in equipment.transfers:
                _provenance_matches(hub.mode, transfer.provenance)
                if transfer.provenance.environment != equipment.provenance.environment:
                    raise EvidenceMismatch()
            if equipment.location is not None:
                _provenance_matches(hub.mode, equipment.location.provenance)
                if equipment.location.provenance.environment != equipment.provenance.environment:
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
            data = row.model_dump()
            for field in ("recorded_at", "generated_at", "data_as_of"):
                data[field] = _stored_time(data[field])
            return SnapshotRecord.model_validate(data)

    def get_snapshot(self, snapshot_id: str, mode: DataMode) -> SnapshotRecord:
        _mode(mode)
        with Session(self.engine) as session:
            row = session.exec(
                select(SourceSnapshot).where(
                    SourceSnapshot.id == snapshot_id, SourceSnapshot.mode == mode
                )
            ).first()
            if row is None:
                raise MovementNotFound()
            data = row.model_dump()
            for field in ("recorded_at", "generated_at", "data_as_of"):
                data[field] = _stored_time(data[field])
            return SnapshotRecord.model_validate(data)

    def last_snapshot(self, mode: DataMode) -> SnapshotRecord | None:
        _mode(mode)
        with Session(self.engine) as session:
            row = session.exec(
                select(SourceSnapshot)
                .where(SourceSnapshot.mode == mode)
                .order_by(SourceSnapshot.recorded_at.desc(), SourceSnapshot.id)
                .limit(1)
            ).first()
            if row is None:
                return None
            data = row.model_dump()
            for field in ("recorded_at", "generated_at", "data_as_of"):
                data[field] = _stored_time(data[field])
            return SnapshotRecord.model_validate(data)
