"""Typed graph projection of one operative reading: nodes, edges, evidence, conflicts, gaps.

Every node and edge carries the evidence it rests on (`EvidenceRef`) and the scope of the
relation. A fact the bounded reading did not cover stays visible as «no verificable»; a
record only referenced by ID (a project, a unit outside the read page) is a
`referenced_only` node, never a guess. Presence edges hang from the movement's tracked
vehicle, never from the machine: the GPS device may belong to the transporter. The graph
has no geometry, ETA nor proximity; visual coordinates are a client decision.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.hub import (
    AlertRecord,
    DataMode,
    HubScope,
    OperationEvidenceStatus,
    Provenance,
    ReceiptSummary,
    SourceStatus,
)
from app.models.operations import MovementState, TrackedVehicleKind
from app.models.workflow import OperationsCoverage

NodeKind = Literal["machine", "project", "place", "request", "movement", "incident"]
EdgeKind = Literal[
    "assigned_to",
    "requested_for",
    "assigned_unit",
    "transfer_of",
    "for_request",
    "destination",
    "observed_at_place",
    "received_by",
    "affects",
]
Verification = Literal["source_observed", "ledger_recorded", "declared", "referenced_only"]
RelationScope = Literal["current", "historical", "unverifiable", "not_applicable"]
EvidenceOrigin = Literal["nexus", "startrack", "econ_ledger", "econ_declaration"]
ObservedFact = Literal["administrative", "task", "presence", "receipt"]
ConflictCode = Literal[
    "assignment_project_mismatch",
    "movement_source_changed",
    "task_destination_differs",
    "overlapping_approved_requests",
    "status_role_unknown",
]
TensionCode = Literal[
    "administrative_status_vs_task",
    "obsolete_with_approved_request",
    "stopped_with_pending_task",
    "arrival_without_receipt",
    "receipt_without_arrival",
]
AttributeValue = str | int | float | bool | None
NOT_VERIFIABLE: Literal["no verificable"] = "no verificable"
DECLARED_KIND_NOTE = "Declarado por el operador; no verificado."


class EvidenceRef(BaseModel):
    """Where a fact comes from; the source provenance travels intact when there is one."""

    model_config = ConfigDict(frozen=True)

    origin: EvidenceOrigin
    verification: Verification
    provenance: Provenance | None = None
    source_id: str | None = None
    environment: str | None = None
    evidence_kind: Literal["live_read", "provided_sample", "test_case"] | None = None
    # Fact instant in the source (visit, status change, declared reception).
    event_time: datetime | None = None
    # Read instant of the source; it never stands in for the fact instant.
    observed_at: datetime | None = None
    observed_on: date | None = None
    # Instant the local ledger stored the row or event.
    recorded_at: datetime | None = None
    reference: str | None = None
    note: str | None = None


def _facts() -> dict[ObservedFact, datetime | None]:
    return {"administrative": None, "task": None, "presence": None, "receipt": None}


class NodeBase(BaseModel):
    id: str
    kind: NodeKind
    label: str
    verification: Verification
    evidence: list[EvidenceRef] = Field(default_factory=list)
    missing: list[str] = Field(
        default_factory=list,
        description="Hechos que esta lectura no cubre para el nodo; cada uno es «no verificable».",
    )


class MachineNode(NodeBase):
    kind: Literal["machine"] = "machine"
    source_id: str | None = None
    asset_number: str | None = None
    code: str | None = None
    name: str | None = None
    company: str | None = None
    equipment_class: str | None = None
    machinery_status: str | None = None
    project_id: str | None = None
    assignment_starts_on: str | None = None
    assignment_ends_on: str | None = None
    assignment_note: str | None = None
    maintenance_failure_id: str | None = None
    maintenance_status: str | None = None
    maintenance_is_stopped: bool | None = None
    relation_status: str | None = None
    last_observed: dict[ObservedFact, datetime | None] = Field(
        default_factory=_facts,
        description=(
            "Instante del hecho por tipo, cada uno con su propia última observación (nunca un "
            "máximo global): administrative es la lectura de Prisma; task y presence son la "
            "fecha del hecho en Startrack de los movimientos vigentes; presence corresponde al "
            "vehículo rastreado del movimiento (puede ser el transportador), no a la máquina; "
            "receipt es el instante declarado de recepción."
        ),
    )
    last_read: dict[ObservedFact, datetime | None] = Field(
        default_factory=_facts,
        description="Instante de lectura o registro de cada hecho; no sustituye al del hecho.",
    )


class ProjectNode(NodeBase):
    kind: Literal["project"] = "project"
    source_id: str | None = None
    name: str | None = None
    presence: Literal["referenced_only"] = "referenced_only"


class PlaceNode(NodeBase):
    kind: Literal["place"] = "place"
    poi_id: str
    # Only a name observed in Startrack for this same poi_id; never a name join.
    name: str | None = None
    geometry: Literal[None] = None


class RequestNode(NodeBase):
    kind: Literal["request"] = "request"
    source_id: str | None = None
    status: str | None = None
    project_id: str | None = None
    machinery_id: str | None = None
    machinery_type: str | None = None
    starts_on: str | None = None
    ends_on: str | None = None
    approved_at: datetime | None = None
    requested_by_id: str | None = None


class MovementNode(NodeBase):
    kind: Literal["movement"] = "movement"
    movement_id: str
    state: MovementState
    movement_reference: str
    request_source_id: str
    machinery_source_id: str
    project_source_id: str
    job_id: str | None = None
    task_ref: str | None = Field(default=None, description="startrack:job:{job_id} cuando existe.")
    status: str | None = None
    workflow_role: str | None = None
    reason_code: str | None = None
    scheduled_date: str | None = None
    scheduled_time: str | None = None
    poi_id: str | None = None
    tracked_vehicle_id: str | None = None
    tracked_vehicle_kind: TrackedVehicleKind | None = None
    tracked_vehicle_kind_verification: Literal["declared"] | None = None
    arrival_event_time: datetime | None = None
    arrival_observed_at: datetime | None = None
    receipt: ReceiptSummary | None = None
    relation_scope: RelationScope
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None


class IncidentNode(NodeBase):
    kind: Literal["incident"] = "incident"
    failure_id: str
    equipment_id: str
    status: str | None = None
    is_stopped: bool | None = None


GraphNode = Annotated[
    MachineNode | ProjectNode | PlaceNode | RequestNode | MovementNode | IncidentNode,
    Field(discriminator="kind"),
]


class GraphEdge(BaseModel):
    id: str = Field(description="Determinista: {kind}:{source}:{target}:{reference}.")
    kind: EdgeKind
    source: str
    target: str
    verification: Verification
    scope: RelationScope
    evidence: list[EvidenceRef] = Field(min_length=1)
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)


class GraphConflict(BaseModel):
    """Two documented facts that cannot both describe the current operation."""

    id: str
    code: ConflictCode
    node_ids: list[str]
    edge_ids: list[str] = Field(default_factory=list)
    description: str
    evidence: list[str]


class GraphTension(BaseModel):
    """Facts that coexist in the sources but call for review; not a contradiction."""

    id: str
    code: TensionCode
    node_ids: list[str]
    description: str
    evidence: list[str]


class GraphGap(BaseModel):
    """A fact the reading does not cover; it is never reported as absent or as fine."""

    id: str
    code: str
    node_id: str | None = None
    edge_kind: EdgeKind | None = None
    fact: str
    description: str
    status: Literal["no verificable"] = NOT_VERIFIABLE


class GraphCoverage(BaseModel):
    scope: HubScope
    sources: list[SourceStatus]
    operation_evidence: OperationEvidenceStatus
    ledger: OperationsCoverage | None = None
    ledger_available: bool
    ledger_message: str
    nodes_by_kind: dict[NodeKind, int]
    edges_by_kind: dict[EdgeKind, int]
    referenced_only: int = Field(description="Nodos solo referenciados por ID, no leídos.")
    complete: bool
    description: str


class GraphProjection(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime
    data_as_of: datetime | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    conflicts: list[GraphConflict]
    tensions: list[GraphTension]
    gaps: list[GraphGap]
    alerts: list[AlertRecord] = Field(
        description="Alertas del hub copiadas tal cual; no se reevalúan con el reloj."
    )
    coverage: GraphCoverage
    notes: list[str]
    remote_writes: Literal[False] = False
