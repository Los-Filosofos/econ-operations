"""Durable operation records; source facts and receipt remain separate evidence."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    TypeDecorator,
    UniqueConstraint,
    text,
)
from sqlalchemy.sql.naming import conv
from sqlmodel import Field, SQLModel

from app.models.hub import DataMode, Provenance

MovementState = Literal["draft", "blocked", "queued", "sending", "sent", "unknown", "failed"]
ObservationKind = Literal["task_state", "arrival"]
# The GPS device may belong to the machine itself or to the transporter carrying it.
TrackedVehicleKind = Literal["machine_device", "transporter"]
ActorKind = Literal["session", "local_dev", "cli_worker"]
# States that hold the single in-flight slot of a machine; leaving `unknown` is an explicit
# operator decision (OperationsLedger.resolve_unknown or a verified finish_sent), never automatic.
INFLIGHT_STATES: tuple[str, ...] = ("queued", "sending", "unknown")
INFLIGHT_PREDICATE = "state IN ('queued', 'sending', 'unknown')"
JOB_PREDICATE = "job_id IS NOT NULL"
# Explicit constraint names shared verbatim with migration 0004 (op.f) so both sides agree.
TRACKED_VEHICLE_KIND_CHECK = "ck_operation_movements_tracked_vehicle_kind"
TRACKED_VEHICLE_KIND_PREDICATE = (
    "tracked_vehicle_kind IS NULL OR tracked_vehicle_kind IN ('machine_device', 'transporter')"
)


class UTCDateTime(TypeDecorator):
    """Timezone-aware column on PostgreSQL; SQLite stores naive text that is read back as UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.astimezone(UTC) if value is not None and value.tzinfo else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # PostgreSQL returns the session zone; every instant leaves the ledger as UTC.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _instant(nullable: bool = False) -> Any:
    return Field(
        default=None if nullable else ..., sa_column=Column(UTCDateTime, nullable=nullable)
    )


def _json(nullable: bool = False) -> Any:
    if nullable:
        return Field(default=None, sa_column=Column(JSON(none_as_null=True)))
    return Field(sa_column=Column(JSON, nullable=False))


class Movement(SQLModel, table=True):
    __tablename__ = "operation_movements"
    __table_args__ = (
        UniqueConstraint("mode", "environment", "movement_reference", name="movement_identity"),
        CheckConstraint("mode IN ('fixture', 'live')", name="movement_mode"),
        CheckConstraint(
            "state IN ('draft', 'blocked', 'queued', 'sending', 'sent', 'unknown', 'failed')",
            name="movement_state",
        ),
        CheckConstraint(TRACKED_VEHICLE_KIND_PREDICATE, name=conv(TRACKED_VEHICLE_KIND_CHECK)),
        # Every query filters by mode first; the review index covers dispatch and review scans.
        Index("ix_operation_movements_review", "mode", "state", "next_review_at"),
        # One job may only ever be linked to one movement per mode and environment.
        Index(
            "uq_operation_movements_job_identity",
            "mode",
            "environment",
            "job_id",
            unique=True,
            postgresql_where=text(JOB_PREDICATE),
            sqlite_where=text(JOB_PREDICATE),
        ),
        # At most one movement in flight per machine; the database, not Python, guarantees it.
        Index(
            "uq_operation_movements_inflight_machine",
            "mode",
            "environment",
            "machinery_source_id",
            unique=True,
            postgresql_where=text(INFLIGHT_PREDICATE),
            sqlite_where=text(INFLIGHT_PREDICATE),
        ),
    )

    id: str = Field(primary_key=True, max_length=36)
    mode: str = Field(max_length=16)
    environment: str = Field(max_length=32)
    movement_reference: str = Field(max_length=255)
    request_source_id: str = Field(max_length=255, index=True)
    machinery_source_id: str = Field(max_length=255)
    project_source_id: str = Field(max_length=255)
    tracked_vehicle_id: str | None = Field(default=None, max_length=255)
    tracked_vehicle_kind: str | None = Field(default=None, max_length=16)
    mapping: dict = _json()
    source_request: dict = _json()
    source_equipment: dict | None = _json(nullable=True)
    source_request_hash: str = Field(max_length=64)
    source_equipment_hash: str | None = Field(default=None, max_length=64)
    identity_hash: str = Field(max_length=64)
    payload: dict | None = _json(nullable=True)
    preparation: dict = _json()
    state: str = Field(max_length=16)
    job_id: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)
    workflow_role: str | None = Field(default=None, max_length=255)
    reason_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = _instant()
    updated_at: datetime = _instant()
    next_review_at: datetime = _instant()
    queued_at: datetime | None = _instant(nullable=True)
    sending_at: datetime | None = _instant(nullable=True)
    sent_at: datetime | None = _instant(nullable=True)
    receipt: dict | None = _json(nullable=True)


class OperationEvent(SQLModel, table=True):
    __tablename__ = "operation_events"
    __table_args__ = (
        UniqueConstraint("movement_id", "evidence_hash", name="event_evidence_identity"),
    )

    id: str = Field(primary_key=True, max_length=36)
    movement_id: str = Field(foreign_key="operation_movements.id", index=True, max_length=36)
    kind: str = Field(max_length=32)
    state: str | None = Field(default=None, max_length=16)
    source_id: str | None = Field(default=None, max_length=255)
    evidence_hash: str | None = Field(default=None, max_length=64)
    event_time: datetime | None = _instant(nullable=True)
    observed_at: datetime | None = _instant(nullable=True)
    recorded_at: datetime = _instant()
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    provenance: dict | None = _json(nullable=True)
    # Who caused the transition; all nullable because an actor is recorded, never fabricated.
    actor_user_id: str | None = Field(default=None, max_length=64)
    actor_role: str | None = Field(default=None, max_length=32)
    actor_kind: str | None = Field(default=None, max_length=16)


class SourceSnapshot(SQLModel, table=True):
    __tablename__ = "operation_snapshots"
    __table_args__ = (
        CheckConstraint("mode IN ('fixture', 'live')", name="snapshot_mode"),
        Index("ix_operation_snapshots_mode_recorded", "mode", "recorded_at"),
    )

    id: str = Field(primary_key=True, max_length=36)
    mode: str = Field(max_length=16)
    recorded_at: datetime = _instant()
    generated_at: datetime = _instant()
    data_as_of: datetime | None = _instant(nullable=True)
    content_hash: str = Field(max_length=64)
    content: dict = _json()
    last_confirmed_at: datetime | None = _instant(nullable=True)


class Actor(BaseModel):
    """Who performs a ledger transition. Built by the caller from a real session or process.

    `session` carries the authenticated user; `local_dev` (AUTH_REQUIRED=false without a
    login) and `cli_worker` carry no user at all. A caller that has no actor passes None.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str | None = None
    email: str | None = None
    role: str | None = None
    kind: ActorKind

    @model_validator(mode="after")
    def _never_fabricated(self) -> "Actor":
        if self.kind == "session":
            if not self.user_id:
                raise ValueError("Un actor de sesión requiere el identificador del usuario.")
        elif self.user_id is not None or self.email is not None or self.role is not None:
            raise ValueError("Un actor sin sesión no puede declarar usuario, correo ni rol.")
        return self


ActorRef = Actor


class ReceiptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `receiver` is the declared name on the record; the declaring session is kept apart.
    receiver: str
    received_at: datetime
    reference: str
    recorded_at: datetime
    note: str | None = None
    source: Literal["manual_declaration"] = "manual_declaration"
    declared_by_user_id: str | None = None
    declared_by_email: str | None = None
    declared_by_role: str | None = None


RECEIPT_DECLARATION_FIELDS = frozenset(
    {"recorded_at", "declared_by_user_id", "declared_by_email", "declared_by_role"}
)


class MovementEventRecord(BaseModel):
    id: str
    kind: str
    state: MovementState | None = None
    source_id: str | None = None
    event_time: datetime | None = None
    observed_at: datetime | None = None
    recorded_at: datetime
    data: dict[str, Any]
    provenance: Provenance | None = None
    actor_user_id: str | None = None
    actor_role: str | None = None
    actor_kind: ActorKind | None = None


class MovementRecord(BaseModel):
    id: str
    mode: DataMode
    environment: str
    movement_reference: str
    request_source_id: str
    machinery_source_id: str
    project_source_id: str
    tracked_vehicle_id: str | None = None
    tracked_vehicle_kind: TrackedVehicleKind | None = None
    mapping: dict[str, Any]
    source_request: dict[str, Any]
    source_equipment: dict[str, Any] | None
    source_request_hash: str
    source_equipment_hash: str | None
    payload: dict[str, Any] | None
    preparation: dict[str, Any]
    state: MovementState
    job_id: str | None = None
    status: str | None = None
    workflow_role: str | None = None
    reason_code: str | None = None
    created_at: datetime
    updated_at: datetime
    next_review_at: datetime | None = None
    queued_at: datetime | None = None
    sending_at: datetime | None = None
    sent_at: datetime | None = None
    receipt: ReceiptRecord | None = None
    events: list[MovementEventRecord]


class SnapshotRecord(BaseModel):
    id: str
    mode: DataMode
    recorded_at: datetime
    generated_at: datetime
    data_as_of: datetime | None = None
    content_hash: str
    content: dict[str, Any]
    last_confirmed_at: datetime | None = None
