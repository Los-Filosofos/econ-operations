"""Public read models: source states are intentionally not collapsed into one status."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DataMode = Literal["fixture", "live"]
SourceId = Literal["nexus", "startrack"]


class Provenance(BaseModel):
    source: SourceId
    source_id: str
    environment: Literal["local", "sandbox"]
    observed_at: datetime
    is_synthetic: bool


class SourceStatus(BaseModel):
    id: SourceId
    label: str
    status: Literal["fixture", "connected", "partial", "not_configured", "disabled", "error"]
    environment: Literal["local", "sandbox"]
    observed_at: datetime | None = None
    message: str


class TransferRecord(BaseModel):
    id: str
    code: str
    status: str
    request_id: str | None = None
    destination_project_id: str | None = None
    destination_project_name: str | None = None
    driver: str | None = None
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


class RequestRecord(BaseModel):
    id: str
    project_id: str | None = None
    project_name: str | None = None
    machinery_id: str | None = None
    status: str
    starts_on: str | None = None
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


class HubResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime
    data_as_of: datetime | None = None
    sources: list[SourceStatus]
    scope: HubScope
    summary: HubSummary
    equipment: list[EquipmentRecord]
    requests: list[RequestRecord]
    alerts: list[AlertRecord]
