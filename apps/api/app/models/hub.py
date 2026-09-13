"""Public read models: source states are intentionally not collapsed into one status."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

DataMode = Literal["fixture", "live"]
SourceId = Literal["nexus", "startrack"]


class Provenance(BaseModel):
    source: SourceId
    source_id: str | None
    environment: Literal["local", "sandbox"]
    observed_at: datetime | None
    is_synthetic: bool
    evidence_kind: Literal["live_read", "provided_sample", "test_case"] = "live_read"
    source_reference: str | None = None
    observed_on: date | None = None


class SourceStatus(BaseModel):
    id: SourceId
    label: str
    status: Literal[
        "fixture", "connected", "partial", "not_configured", "not_queried", "disabled", "error"
    ]
    environment: Literal["local", "sandbox"]
    observed_at: datetime | None = None
    observed_on: date | None = None
    configured: bool | None = None
    last_evidence_at: datetime | None = None
    message: str


class TransferRecord(BaseModel):
    id: str
    code: str
    status: str
    request_id: str | None = None
    destination_project_id: str | None = None
    destination_project_name: str | None = None
    driver: str | None = None
    movement_id: str | None = None
    workflow_role: str | None = None
    event_time: datetime | None = None
    recorded_at: datetime | None = None
    evidence_current_assignment: bool = True
    evidence_origin: Literal["task_observation", "creation_acknowledgment"] = "task_observation"
    source_data: dict[str, str | float | int | None] = Field(default_factory=dict)
    provenance: Provenance


class LocationObservation(BaseModel):
    label: str
    observed_at: datetime
    provenance: Provenance


class EquipmentRecord(BaseModel):
    id: str
    code: str | None
    asset_number: str | None = None
    name: str
    company: str | None = None
    equipment_class: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    driver: str | None = None
    machinery_status: str
    maintenance_failure_id: str | None = None
    maintenance_status: str | None = None
    maintenance_is_stopped: bool | None = None
    request_ids: list[str] = Field(default_factory=list)
    transfers: list[TransferRecord] = Field(default_factory=list)
    location: LocationObservation | None = None
    relation_status: Literal["confirmed", "candidate", "unlinked"]
    relation_note: str
    provenance: Provenance
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RequestRecord(BaseModel):
    id: str
    project_id: str | None = None
    project_name: str | None = None
    machinery_id: str | None = None
    status: str
    starts_on: str | None = None
    ends_on: str | None = None
    machinery_type: str | None = None
    requested_by: str | None = None
    requested_by_id: str | None = None
    comments: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by_user_id: str | None = None
    provenance: Provenance


class AlertRecord(BaseModel):
    id: str
    code: str
    severity: Literal["info", "warning", "critical"]
    title: str
    description: str
    owner: str
    equipment_id: str | None = None
    request_id: str | None = None
    evidence: list[str]


class HubScope(BaseModel):
    search: str
    bounded: bool = True
    equipment_total: int | None = None
    requests_total: int | None = None
    equipment_returned: int = 0
    requests_returned: int = 0
    complete: bool
    description: str


class HubSummary(BaseModel):
    equipment_count: int | None = None
    administratively_available: int | None = None
    active_failures: int | None = None
    stopped_equipment: int | None = None
    unlinked_equipment: int | None = None
    alerts_count: int | None = None


class OperationEvidenceStatus(BaseModel):
    status: Literal["not_queried", "available", "partial", "disabled", "error"] = "not_queried"
    checked_at: datetime | None = None
    movements_returned: int | None = None
    complete: bool = False
    message: str = "El registro de movimientos no se ha consultado."


class HubResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime
    data_as_of: datetime | None = None
    sources: list[SourceStatus]
    scope: HubScope
    summary: HubSummary
    operation_evidence: OperationEvidenceStatus = Field(default_factory=OperationEvidenceStatus)
    equipment: list[EquipmentRecord]
    requests: list[RequestRecord]
    alerts: list[AlertRecord]
