"""Transactional movement ledger and durable outbox, with no provider calls or DDL.

The claim transaction commits before a caller can issue a POST. A crash after
that commit is ambiguous: recovery changes sending to unknown, never to queued.

Since migration 0004 the database itself guards two invariants that Python only
announces with a clearer message: one movement in flight (queued/sending/unknown)
per (mode, environment, machinery_source_id), and one movement per job_id within
(mode, environment). Every transition accepts an optional `Actor`; when the caller
has none (CLI worker, local development without a login) nothing is invented.

Storage hygiene (ADR 0006): a read that changes nothing writes nothing durable. A hub
cut is inserted only when its stable content differs from the latest cut of the mode
(otherwise `last_confirmed_at` moves), and `revalidate` emits its event only when the
source fingerprints change. Cuts are pruned solely by the explicit CLI
(`app.cli.prune_snapshots`); events and movements are never pruned here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import Engine, case, delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.hub import DataMode, EquipmentRecord, HubResponse, Provenance, RequestRecord
from app.models.operations import (
    INFLIGHT_STATES,
    RECEIPT_DECLARATION_FIELDS,
    Actor,
    Movement,
    MovementEventRecord,
    MovementRecord,
    ObservationKind,
    OperationEvent,
    ReceiptRecord,
    SnapshotRecord,
    SourceSnapshot,
    TrackedVehicleKind,
)
from app.services.transfers import TransferMapping, compatible_evidence, prepare_transfer

SAFE_REASON_CODES = frozenset(
    (
        "provider_rejected provider_unavailable provider_timeout invalid_response "
        "ambiguous_response worker_interrupted dispatch_blocked mapping_conflict "
        "source_changed not_approved operator_resolved unknown"
    ).split()
)
TRACKED_VEHICLE_KINDS: tuple[str, ...] = ("machine_device", "transporter")
# Read timestamps of a source record change on every read; they never alter its fingerprint.
VOLATILE_PROVENANCE_FIELDS = frozenset({"observed_at", "observed_on"})
# Keys added after the first deployments: stored only when present so that evidence hashes
# of repeated reads keep matching the events recorded before they existed.
OPTIONAL_OBSERVATION_KEYS = frozenset({"creation_date", "end_date_raw", "tracked_asset_kind"})
# Hub cut fields that move on every read without any source change. `data_as_of` is the
# Nexus read completion instant in live mode (and a constant in fixture mode).
VOLATILE_SNAPSHOT_FIELDS = frozenset({"generated_at", "data_as_of"})
VOLATILE_SOURCE_STATUS_FIELDS = frozenset({"observed_at", "observed_on", "last_evidence_at"})
VOLATILE_EVIDENCE_STATUS_FIELDS = frozenset({"checked_at"})


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
    # Job Data Object facts kept as provider strings: expected duration and closing place.
    start_time: Fact = None
    duration: Fact = None
    poi_name: Fact = None
    completed_lat: Fact = None
    completed_lon: Fact = None
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    # Later additions (see OPTIONAL_OBSERVATION_KEYS): creation date of the job, raw end of
    # the visit and whether the tracked device is the machine's own or the transporter's.
    creation_date: Fact = None
    end_date_raw: Fact = None
    tracked_asset_kind: TrackedVehicleKind | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def stable_fingerprint(record: BaseModel | dict[str, Any]) -> str:
    """Hash of a source record without its read timestamps.

    A repeated, unchanged read of Prisma yields the same fingerprint even though
    `provenance.observed_at` moved. The stored JSON keeps the full provenance; only
    the hash ignores when the record was read.
    """
    data = dict(record.model_dump(mode="json") if isinstance(record, BaseModel) else record)
    provenance = data.get("provenance")
    if isinstance(provenance, dict):
        data["provenance"] = {
            key: value for key, value in provenance.items() if key not in VOLATILE_PROVENANCE_FIELDS
        }
    return _hash(data)


def _without_read_times(value: Any) -> Any:
    """Copy of a JSON structure with the read timestamps of every provenance block removed."""
    if isinstance(value, dict):
        return {
            key: (
                {k: v for k, v in item.items() if k not in VOLATILE_PROVENANCE_FIELDS}
                if key == "provenance" and isinstance(item, dict)
                else _without_read_times(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_without_read_times(item) for item in value]
    return value


def stable_snapshot_hash(content: dict[str, Any]) -> str:
    """Fingerprint of a hub cut (`HubResponse` as JSON) without its read timestamps.

    Excluded: `generated_at`, `data_as_of`, `operation_evidence.checked_at`,
    `sources[].observed_at/observed_on/last_evidence_at` and the `observed_at/observed_on`
    of every `provenance` block (requests, equipment, transfers, location). Two consecutive
    reads that return the same source facts and the same local evidence therefore share
    one fingerprint even though every read stamp moved. It is an integrity check for
    accidental change, not a signature: anyone able to write the row can recompute it.
    """
    data = {key: value for key, value in content.items() if key not in VOLATILE_SNAPSHOT_FIELDS}
    data["sources"] = [
        {key: value for key, value in source.items() if key not in VOLATILE_SOURCE_STATUS_FIELDS}
        for source in content.get("sources") or []
        if isinstance(source, dict)
    ]
    evidence = content.get("operation_evidence")
    if isinstance(evidence, dict):
        data["operation_evidence"] = {
            key: value
            for key, value in evidence.items()
            if key not in VOLATILE_EVIDENCE_STATUS_FIELDS
        }
    return _hash(_without_read_times(data))


def last_read_at(snapshot: SnapshotRecord) -> datetime:
    """Instant of the latest read that produced or confirmed a cut.

    A cut is recorded once and then confirmed by every later read with the same stable
    content; the latest read is therefore max(recorded_at, last_confirmed_at).
    """
    confirmed = _aware(snapshot.last_confirmed_at)
    recorded = _aware(snapshot.recorded_at)
    return recorded if confirmed is None else max(recorded, confirmed)


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


def _vehicle_kind(kind: str | None, tracked_vehicle_id: str | None) -> str | None:
    if kind is None:
        return None
    if kind not in TRACKED_VEHICLE_KINDS:
        raise LedgerError("El tipo del dispositivo GPS debe ser machine_device o transporter.")
    if tracked_vehicle_id is None:
        raise LedgerError("El tipo del dispositivo GPS requiere el vehículo rastreado.")
    return kind


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
    tracked_vehicle_kind: str | None = None,
) -> dict[str, Any]:
    """Column values derived from current source evidence; identity covers mapping and payload."""
    preparation = prepare_transfer(request, equipment, mapping)
    payload = preparation.draft.payload() if preparation.draft else None
    source_request = request.model_dump(mode="json")
    source_equipment = equipment.model_dump(mode="json") if equipment else None
    identity = {
        "mapping": mapping.model_dump(mode="json"),
        "payload": payload,
        "tracked_vehicle_id": tracked_vehicle_id,
    }
    if tracked_vehicle_kind is not None:
        # Only an explicit kind joins the identity: rows created before migration 0004
        # keep exactly the same hash, so a repeated plan still resolves to them.
        identity["tracked_vehicle_kind"] = tracked_vehicle_kind
    return {
        "source_request": source_request,
        "source_equipment": source_equipment,
        "source_request_hash": stable_fingerprint(request),
        "source_equipment_hash": stable_fingerprint(equipment) if equipment else None,
        "payload": payload,
        "preparation": preparation.model_dump(mode="json"),
        "identity_hash": _hash(identity),
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


def _inflight_message(blocker: Movement | None) -> str:
    if blocker is None:
        return "Ya hay un movimiento en vuelo para esta máquina; concilia antes de encolar otro."
    return (
        f"Ya hay un movimiento en vuelo para esta máquina ({blocker.id}, estado "
        f"{blocker.state}); concilia antes de encolar otro."
    )


def _job_message(job_id: str, holder: tuple[str, str] | None) -> str:
    if holder is None:
        return f"La tarea {job_id} ya está vinculada a otro movimiento; no se vincula dos veces."
    return (
        f"La tarea {job_id} ya está vinculada al movimiento {holder[0]} (estado {holder[1]}); "
        "no se vincula dos veces."
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
    def _event(
        session: Session, row: Movement, kind: str, *, actor: Actor | None = None, **values: Any
    ) -> None:
        actor = _fresh(actor)
        session.add(
            OperationEvent(
                id=str(uuid4()),
                movement_id=row.id,
                kind=kind,
                state=row.state,
                recorded_at=_now(),
                actor_user_id=actor.user_id if actor else None,
                actor_role=actor.role if actor else None,
                actor_kind=actor.kind if actor else None,
                **values,
            )
        )

    @staticmethod
    def _events(session: Session, movement_ids: list[str]) -> dict[str, list[MovementEventRecord]]:
        """Events of many movements in one statement, grouped in their per-movement order."""
        grouped: dict[str, list[MovementEventRecord]] = {item: [] for item in movement_ids}
        if not movement_ids:
            return grouped
        events = session.exec(
            select(OperationEvent)
            .where(OperationEvent.movement_id.in_(movement_ids))
            .order_by(OperationEvent.movement_id, OperationEvent.recorded_at, OperationEvent.id)
        ).all()
        for event in events:
            grouped[event.movement_id].append(
                MovementEventRecord.model_validate(event.model_dump())
            )
        return grouped

    @staticmethod
    def _movement_record(row: Movement, events: list[MovementEventRecord]) -> MovementRecord:
        return MovementRecord(**row.model_dump(exclude={"identity_hash"}), events=events)

    @staticmethod
    def _record(session: Session, row: Movement) -> MovementRecord:
        """Single-row path: one statement for the events of this movement."""
        return OperationsLedger._movement_record(
            row, OperationsLedger._events(session, [row.id])[row.id]
        )

    def _records(self, query) -> list[MovementRecord]:
        """List path: one statement for the rows and one for all their events (no N+1)."""
        with Session(self.engine) as session:
            rows = session.exec(query).all()
            events = self._events(session, [row.id for row in rows])
            return [self._movement_record(row, events[row.id]) for row in rows]

    def _apply(
        self,
        session: Session,
        row: Movement,
        statement,
        error: type[LedgerError],
        kind: str,
        *,
        actor: Actor | None = None,
        **event,
    ) -> MovementRecord:
        """Guarded single-row transition followed by its event, in one transaction."""
        if session.execute(statement).rowcount != 1:
            raise error()
        session.refresh(row)
        self._event(session, row, kind, actor=actor, **event)
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

    @staticmethod
    def _inflight_blocker(session: Session, row: Movement) -> Movement | None:
        """Another movement holding the machine's single in-flight slot, if any."""
        return session.exec(
            select(Movement)
            .where(
                Movement.mode == row.mode,
                Movement.environment == row.environment,
                Movement.machinery_source_id == row.machinery_source_id,
                Movement.state.in_(INFLIGHT_STATES),
                Movement.id != row.id,
            )
            .order_by(Movement.updated_at.desc(), Movement.id)
        ).first()

    @staticmethod
    def _job_holder(
        session: Session, movement_id: str, environment: str, job_id: str
    ) -> tuple[str, str] | None:
        """Another live movement of the same environment already linked to this job."""
        return session.exec(
            select(Movement.id, Movement.state).where(
                Movement.mode == "live",
                Movement.environment == environment,
                Movement.job_id == job_id,
                Movement.id != movement_id,
            )
        ).first()

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
        tracked_vehicle_kind: str | None = None,
        actor: Actor | None = None,
    ) -> MovementRecord:
        request, equipment = _source_pair(mode, request, equipment)
        mapping = _fresh(mapping)
        tracked_vehicle_id = _text(tracked_vehicle_id)
        tracked_vehicle_kind = _vehicle_kind(tracked_vehicle_kind, tracked_vehicle_id)
        values = _plan_values(request, equipment, mapping, tracked_vehicle_id, tracked_vehicle_kind)
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
            tracked_vehicle_kind=tracked_vehicle_kind,
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
                    self._event(session, row, "created", actor=actor, data=event)
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
        *,
        actor: Actor | None = None,
    ) -> MovementRecord:
        """Refresh unsent source evidence; retained events preserve earlier snapshots.

        A re-read whose stable fingerprints (`source_request_hash`, `source_equipment_hash`)
        equal the stored ones changes nothing: no UPDATE, no `revalidated` event, and the
        row keeps the read time of its last real change. Advancing the review schedule
        stays with the caller (`workflow._review`). When a fingerprint changes, the event
        keeps both fingerprints and a full copy of the new source records.
        """
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
            values = _plan_values(
                request, equipment, mapping, row.tracked_vehicle_id, row.tracked_vehicle_kind
            )
            previous = {
                "request_hash": row.source_request_hash,
                "equipment_hash": row.source_equipment_hash,
            }
            current = {
                "request_hash": values["source_request_hash"],
                "equipment_hash": values["source_equipment_hash"],
            }
            if previous == current:
                return self._record(session, row)
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
                actor=actor,
                data={
                    "previous": previous,
                    "current": current,
                    "request": values["source_request"],
                    "equipment": values["source_equipment"],
                },
            )

    def queue(
        self, movement_id: str, mode: DataMode = "live", *, actor: Actor | None = None
    ) -> MovementRecord:
        """Queue a draft for dispatch; one movement in flight per machine.

        The Python pre-check only names the movement that blocks; the partial unique
        index `uq_operation_movements_inflight_machine` is the actual guarantee, so a
        concurrent loser gets the same MovementConflict after its transaction rolls back.
        """
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
            if row.state != "draft":
                raise InvalidMovementTransition()
            blocker = self._inflight_blocker(session, row)
            if blocker is not None:
                raise MovementConflict(_inflight_message(blocker))
            now = _now()
            try:
                return self._apply(
                    session,
                    row,
                    update(Movement)
                    .where(
                        Movement.id == movement_id, Movement.mode == mode, Movement.state == "draft"
                    )
                    .values(state="queued", queued_at=now, updated_at=now),
                    InvalidMovementTransition,
                    "queued",
                    actor=actor,
                )
            except IntegrityError:
                session.rollback()
                raise MovementConflict(
                    _inflight_message(self._inflight_blocker(session, row))
                ) from None

    def claim(
        self, movement_id: str | None = None, *, actor: Actor | None = None
    ) -> MovementRecord | None:
        """Atomically claim at most one queued live movement, committing before return."""
        with Session(self.engine) as session:
            criteria = [Movement.mode == "live", Movement.state == "queued"]
            if movement_id is None:
                candidate = (
                    select(Movement.id)
                    .where(*criteria)
                    .order_by(Movement.queued_at, Movement.id)
                    .limit(1)
                    # A head of queue locked by another worker is skipped, not awaited.
                    # PostgreSQL renders FOR UPDATE SKIP LOCKED; SQLite compiles it away
                    # and serializes writers instead.
                    .with_for_update(skip_locked=True)
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
            self._event(session, row, "sending", actor=actor)
            session.commit()
            return self._record(session, row)

    def _finish(
        self, movement_id: str, state: str, *, actor: Actor | None = None, **values: Any
    ) -> MovementRecord:
        with Session(self.engine) as session:
            environment = session.exec(
                select(Movement.environment).where(
                    Movement.id == movement_id, Movement.mode == "live"
                )
            ).first()
            if environment is None:
                raise MovementNotFound()
            job_id = values.get("job_id")
            if state == "sent":
                holder = self._job_holder(session, movement_id, environment, job_id)
                if holder is not None:
                    raise MovementConflict(_job_message(job_id, holder))
            statement = (
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
            )
            try:
                row = session.execute(statement).scalar_one_or_none()
            except IntegrityError:
                # uq_operation_movements_job_identity: the movement keeps its current state.
                session.rollback()
                holder = self._job_holder(session, movement_id, environment, job_id)
                raise MovementConflict(_job_message(job_id, holder)) from None
            if row is None:
                raise InvalidMovementTransition()
            self._event(session, row, state, actor=actor, data={"reason_code": row.reason_code})
            session.commit()
            return self._record(session, row)

    def finish_sent(
        self,
        movement_id: str,
        job_id: str,
        *,
        status: str | None = None,
        workflow_role: str | None = None,
        actor: Actor | None = None,
    ) -> MovementRecord:
        """Link the created or verified job; sending/unknown become sent.

        A job_id already linked to another live movement of the same environment raises
        MovementConflict without changing this movement's state (the unique partial index
        `uq_operation_movements_job_identity` guarantees it under concurrency). The
        dispatcher decides what that means for the movement; the ledger never guesses.
        """
        return self._finish(
            movement_id,
            "sent",
            actor=actor,
            job_id=_text(job_id),
            status=_text(status),
            workflow_role=_text(workflow_role),
            sent_at=_now(),
            reason_code=None,
        )

    def finish_unknown(
        self, movement_id: str, reason_code: str = "unknown", *, actor: Actor | None = None
    ) -> MovementRecord:
        return self._finish(
            movement_id, "unknown", actor=actor, reason_code=_safe_reason(reason_code)
        )

    def finish_failed(
        self,
        movement_id: str,
        reason_code: str = "provider_rejected",
        *,
        actor: Actor | None = None,
    ) -> MovementRecord:
        return self._finish(
            movement_id, "failed", actor=actor, reason_code=_safe_reason(reason_code)
        )

    def resolve_unknown(
        self,
        movement_id: str,
        mode: DataMode,
        *,
        reason_code: str,
        actor: Actor | None = None,
    ) -> MovementRecord:
        """Explicit operator exit from `unknown` to `failed`, freeing the machine's slot.

        Never automatic and never a re-POST: the operator closes the movement with a
        permitted code after checking the provider. A verified remote task is linked with
        `finish_sent` instead. The `resolved` event records who decided it.
        """
        if mode != "live":
            raise EvidenceMismatch()
        if reason_code not in SAFE_REASON_CODES:
            raise LedgerError("El motivo de la resolución debe ser un código permitido.")
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            if row.state != "unknown":
                raise InvalidMovementTransition()
            now = _now()
            return self._apply(
                session,
                row,
                update(Movement)
                .where(
                    Movement.id == movement_id, Movement.mode == mode, Movement.state == "unknown"
                )
                .values(
                    state="failed", reason_code=reason_code, updated_at=now, next_review_at=now
                ),
                InvalidMovementTransition,
                "resolved",
                actor=actor,
                data={"reason_code": reason_code, "previous_state": "unknown"},
            )

    def recover_stale_sending(self, before: datetime, *, actor: Actor | None = None) -> int:
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
                self._event(
                    session, row, "unknown", actor=actor, data={"reason_code": "worker_interrupted"}
                )
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
        declared_by: Actor | None = None,
    ) -> MovementRecord:
        """Store the declared reception once; the declaring session is kept apart.

        `receiver` is the name written on the declaration and is never replaced by the
        session. `declared_by_*` come only from a real session; a repeated identical
        declaration (even by another user) returns the stored record instead of 409.
        """
        if mode != "live":
            raise EvidenceMismatch()
        declared_by = _fresh(declared_by)
        declaration: dict[str, str | None] = {}
        if declared_by is not None and declared_by.kind == "session":
            declaration = {
                "declared_by_user_id": declared_by.user_id,
                "declared_by_email": declared_by.email,
                "declared_by_role": declared_by.role,
            }
        receipt = ReceiptRecord(
            receiver=_text(receiver),
            received_at=_explicit_time(received_at),
            reference=_text(reference),
            note=_text(note, maximum=2000),
            recorded_at=_now(),
            **declaration,
        )
        data = receipt.model_dump(mode="json")
        with Session(self.engine) as session:
            row = self._row(session, movement_id, mode)
            if row.state != "sent" or not row.job_id:
                raise InvalidMovementTransition()
            if row.receipt is not None:
                previous = ReceiptRecord.model_validate(row.receipt)
                if previous.model_dump(exclude=RECEIPT_DECLARATION_FIELDS) != receipt.model_dump(
                    exclude=RECEIPT_DECLARATION_FIELDS
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
                actor=declared_by,
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
        actor: Actor | None = None,
    ) -> MovementRecord:
        if kind not in {"task_state", "arrival"}:
            raise LedgerError("El tipo de observación no está permitido.")
        if kind == "arrival" and event_time is None:
            # A visit without its own date is not a dated fact; the read time cannot stand in.
            raise LedgerError(
                "La llegada observada requiere la fecha del hecho en el origen; "
                "la hora de lectura no la sustituye."
            )
        provenance = _fresh(provenance)
        _provenance_matches(mode, provenance)
        source_id = _text(source_id)
        observed_at = _explicit_time(observed_at)
        event_time = _explicit_time(event_time) if event_time else None
        try:
            data = ObservationData.model_validate(data).model_dump(exclude_unset=True)
        except ValidationError:
            raise LedgerError("La observación contiene campos de evidencia no válidos.") from None
        data = {
            key: value
            for key, value in data.items()
            if value is not None or key not in OPTIONAL_OBSERVATION_KEYS
        }
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
                actor=actor,
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

    @staticmethod
    def _latest_snapshot(session: Session, mode: DataMode) -> SourceSnapshot | None:
        """Latest cut of the mode; served by ix_operation_snapshots_mode_recorded (0004)."""
        if mode not in {"fixture", "live"}:
            raise EvidenceMismatch()
        return session.exec(
            select(SourceSnapshot)
            .where(SourceSnapshot.mode == mode)
            .order_by(SourceSnapshot.recorded_at.desc(), SourceSnapshot.id)
            .limit(1)
        ).first()

    def record_snapshot(self, hub: HubResponse) -> SnapshotRecord:
        """Persist the bounded source response once per distinct stable content.

        `content_hash` is the stable fingerprint (`stable_snapshot_hash`): read timestamps
        are left out, the stored JSON keeps them all. When the latest cut of the mode
        already carries that fingerprint nothing is inserted; its `last_confirmed_at`
        moves to now so the latest read stays visible (`last_read_at`). A stored cut is
        otherwise immutable. Two processes reading at once could still insert two equal
        cuts: the deduplication saves space, it is not an invariant (the cycle lock of
        `workflow.sync` is what keeps one cycle per mode).
        """
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
        fingerprint = stable_snapshot_hash(content)
        now = _now()
        with Session(self.engine) as session:
            latest = self._latest_snapshot(session, hub.mode)
            if latest is not None and latest.content_hash == fingerprint:
                session.execute(
                    update(SourceSnapshot)
                    .where(SourceSnapshot.id == latest.id)
                    .values(last_confirmed_at=now)
                )
                session.commit()
                session.refresh(latest)
                return SnapshotRecord.model_validate(latest.model_dump())
            row = SourceSnapshot(
                id=str(uuid4()),
                mode=hub.mode,
                recorded_at=now,
                generated_at=_explicit_time(hub.generated_at),
                data_as_of=_explicit_time(hub.data_as_of) if hub.data_as_of else None,
                content_hash=fingerprint,
                content=content,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return SnapshotRecord.model_validate(row.model_dump())

    def last_snapshot(self, mode: DataMode) -> SnapshotRecord | None:
        with Session(self.engine) as session:
            row = self._latest_snapshot(session, mode)
            return SnapshotRecord.model_validate(row.model_dump()) if row else None

    def prune_snapshots(
        self,
        mode: DataMode,
        *,
        keep_days: int,
        keep_latest: int = 1,
        dry_run: bool = False,
    ) -> int:
        """Delete old cuts of one mode and return how many; never events or movements.

        A cut is old when its latest read (`last_confirmed_at`, else `recorded_at`) is
        older than `keep_days`; the `keep_latest` most recent cuts by `recorded_at` are
        always kept, so the current read model of the mode survives any retention. Only
        `operation_snapshots` is touched: the event history is append-only by design and
        the migration trigger rejects its deletion anyway. `dry_run` counts without deleting.
        """
        if mode not in {"fixture", "live"}:
            raise EvidenceMismatch()
        if keep_days < 1 or keep_latest < 1:
            raise LedgerError("La poda conserva al menos un día y un corte por modo.")
        cutoff = _now() - timedelta(days=keep_days)
        with Session(self.engine) as session:
            protected = session.exec(
                select(SourceSnapshot.id)
                .where(SourceSnapshot.mode == mode)
                .order_by(SourceSnapshot.recorded_at.desc(), SourceSnapshot.id)
                .limit(keep_latest)
            ).all()
            last_read = func.coalesce(SourceSnapshot.last_confirmed_at, SourceSnapshot.recorded_at)
            criteria = [
                SourceSnapshot.mode == mode,
                last_read < cutoff,
                SourceSnapshot.id.not_in(list(protected)),
            ]
            if dry_run:
                return session.exec(select(func.count(SourceSnapshot.id)).where(*criteria)).one()
            result = session.execute(delete(SourceSnapshot).where(*criteria))
            session.commit()
            return result.rowcount
