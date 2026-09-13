"""Durable operation records; source facts and receipt remain separate evidence."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, CheckConstraint, Column, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.hub import DataMode, Provenance

MovementState = Literal["draft", "blocked", "queued", "sending", "sent", "unknown", "failed"]
ObservationKind = Literal["task_state", "arrival"]


class Movement(SQLModel, table=True):
    __tablename__ = "operation_movements"
    __table_args__ = (
        UniqueConstraint("mode", "environment", "movement_reference", name="movement_identity"),
        CheckConstraint("mode IN ('fixture', 'live')", name="movement_mode"),
        CheckConstraint(
            "state IN ('draft', 'blocked', 'queued', 'sending', 'sent', 'unknown', 'failed')",
            name="movement_state",
        ),
        Index("ix_operation_movements_dispatch", "state", "created_at"),
        Index("ix_operation_movements_review", "mode", "state", "next_review_at"),
    )

    id: str = Field(primary_key=True, max_length=36)
    mode: str = Field(max_length=16, index=True)
    environment: str = Field(max_length=32)
    movement_reference: str = Field(max_length=255)
    request_source_id: str = Field(max_length=255, index=True)
    machinery_source_id: str = Field(max_length=255)
    project_source_id: str = Field(max_length=255)
    tracked_vehicle_id: str | None = Field(default=None, max_length=255)
    mapping: dict = Field(sa_column=Column(JSON, nullable=False))
    source_request: dict = Field(sa_column=Column(JSON, nullable=False))
    source_equipment: dict | None = Field(default=None, sa_column=Column(JSON(none_as_null=True)))
    source_request_hash: str = Field(max_length=64)
    source_equipment_hash: str | None = Field(default=None, max_length=64)
    identity_hash: str = Field(max_length=64)
    payload: dict | None = Field(default=None, sa_column=Column(JSON(none_as_null=True)))
    preparation: dict = Field(sa_column=Column(JSON, nullable=False))
    state: str = Field(max_length=16)
    job_id: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)
    workflow_role: str | None = Field(default=None, max_length=255)
    reason_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    next_review_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    queued_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    sending_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    sent_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    receipt: dict | None = Field(default=None, sa_column=Column(JSON(none_as_null=True)))


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
    event_time: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    observed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    recorded_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    provenance: dict | None = Field(default=None, sa_column=Column(JSON(none_as_null=True)))


class SourceSnapshot(SQLModel, table=True):
    __tablename__ = "operation_snapshots"
    __table_args__ = (CheckConstraint("mode IN ('fixture', 'live')", name="snapshot_mode"),)

    id: str = Field(primary_key=True, max_length=36)
    mode: str = Field(max_length=16, index=True)
    recorded_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    generated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    data_as_of: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    content_hash: str = Field(max_length=64)
    content: dict = Field(sa_column=Column(JSON, nullable=False))


class ReceiptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receiver: str
    received_at: datetime
    reference: str
    recorded_at: datetime
    note: str | None = None
    source: Literal["manual_declaration"] = "manual_declaration"


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


class MovementRecord(BaseModel):
    id: str
    mode: DataMode
    environment: str
    movement_reference: str
    request_source_id: str
    machinery_source_id: str
    project_source_id: str
    tracked_vehicle_id: str | None = None
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
