"""Pure graph projection over one hub reading and one ledger page; no I/O and no clock.

`build_graph` follows the `build_trace` pattern: it takes a `HubResponse` and an optional
`WorkflowOverview` and calls no provider, database or clock. Rules it enforces:

- Every machine of the reading is a node, including those without project, request or
  location; missing facts stay visible as «no verificable» instead of hiding the node.
- A movement relates to the reading with an explicit scope: `current` only when the
  stored request and unit match the current source records exactly
  (`matching_current_movements`), `historical` when the request is in the reading but its
  stored copy differs, `unverifiable` when the request or the unit is outside the reading.
  Historical relations are never mixed with current assignments.
- Presence (`observed_at_place`) hangs from the movement's tracked vehicle, never from the
  machine: the device may belong to the transporter and a geofence visit is not receipt.
  Neither a task visit nor `completed_lat/lon` ever produce a machine → place edge.
- Places are identified only by `poi_id`; a name is taken only from a Startrack job observed
  with that same `poi_id`. Records are never joined by names.
- The last observation of each fact (administrative, task, presence, receipt) is chosen with
  `effective_event_sort_key`, never as one global maximum.
- Alerts of the hub are copied as they are; nothing is re-evaluated with the clock.
- No geometry, ETA, distances or proximity are computed or exposed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import ValidationError

from app.models.graph import (
    DECLARED_KIND_NOTE,
    AttributeValue,
    EdgeKind,
    EvidenceRef,
    GraphConflict,
    GraphCoverage,
    GraphEdge,
    GraphGap,
    GraphNode,
    GraphProjection,
    GraphTension,
    IncidentNode,
    MachineNode,
    MovementNode,
    ObservedFact,
    PlaceNode,
    ProjectNode,
    RelationScope,
    RequestNode,
    Verification,
)
from app.models.hub import (
    EquipmentRecord,
    HubResponse,
    Provenance,
    ReceiptSummary,
    RequestRecord,
    SourceStatus,
)
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview
from app.services.evidence import matching_current_movements
from app.services.hub import APPROVED
from app.services.intervals import compare, usage_period_of
from app.services.ledger import effective_event_sort_key
from app.services.transfers import compatible_evidence

# A task exists or may exist in Startrack: a changed source is a contradiction, not a note.
CONFLICTING_STATES = frozenset({"queued", "sending", "sent", "unknown"})
REVALIDATION_STATES = frozenset({"draft", "blocked"})
# Startrack preset role "0" is Pendiente; the sync stores the mapped label when it knows it.
PENDING_ROLES = frozenset({"pending", "0"})
LOCATION_GAP = (
    "ECON no lee la posición GPS de la máquina: el dispositivo rastreado puede ser del "
    "transportador y una visita a geocerca no acredita ubicación ni recepción."
)
LEDGER_NOT_CONSULTED = "El registro de movimientos no se consultó en esta lectura."
NOTES = [
    "Los nodos referenced_only solo están referenciados por ID; no se leyeron del origen.",
    "Las listas vacías describen esta lectura acotada, no la ausencia de registros.",
    "La presencia (observed_at_place) es del vehículo rastreado del movimiento, nunca de la "
    "máquina; no acredita recepción.",
    "Sin geometría, ETA, distancias ni cercanías: las coordenadas visuales las decide el "
    "cliente y no son geográficas.",
    "Las alertas se copian del hub sin reevaluarlas con el reloj.",
]


@dataclass
class _MovementView:
    movement: MovementRecord
    request: RequestRecord | None
    equipment: EquipmentRecord | None
    scope: RelationScope
    latest_task: MovementEventRecord | None
    arrivals: list[MovementEventRecord] = field(default_factory=list)
    receipt: ReceiptRecord | None = None

    @property
    def node_id(self) -> str:
        return f"econ:movement:{self.movement.id}"

    @property
    def latest_arrival(self) -> MovementEventRecord | None:
        return max(self.arrivals, key=effective_event_sort_key, default=None)

    @property
    def workflow_role(self) -> str | None:
        if self.latest_task is not None:
            return self.latest_task.data.get("workflow_role")
        return self.movement.workflow_role

    @property
    def task_pending(self) -> bool:
        return (self.workflow_role or "").strip().lower() in PENDING_ROLES


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _stored_provenance(movement: MovementRecord) -> Provenance | None:
    try:
        return Provenance.model_validate(movement.source_request.get("provenance"))
    except ValidationError:
        return None


def _from_source(movement: MovementRecord, event: MovementEventRecord) -> bool:
    """Same rule as the evidence projection: the event carries its own source proof."""
    provenance, source = event.provenance, _stored_provenance(movement)
    return bool(
        provenance is not None
        and source is not None
        and provenance.source == "startrack"
        and provenance.source_id == event.source_id
        and provenance.observed_at == event.observed_at
        and provenance.environment == movement.environment
        and compatible_evidence(provenance, source, source=False)
        and (movement.mode == "live") == (provenance.evidence_kind == "live_read")
    )


def _nexus_ref(
    provenance: Provenance, reference: str, verification: Verification = "source_observed"
) -> EvidenceRef:
    return EvidenceRef(
        origin="nexus",
        verification=verification,
        provenance=provenance,
        source_id=provenance.source_id,
        environment=provenance.environment,
        evidence_kind=provenance.evidence_kind,
        observed_at=provenance.observed_at,
        observed_on=provenance.observed_on,
        reference=reference,
    )


def _ledger_ref(
    movement: MovementRecord,
    verification: Verification = "ledger_recorded",
    suffix: str = "",
    note: str | None = None,
) -> EvidenceRef:
    stored = _stored_provenance(movement)
    return EvidenceRef(
        origin="econ_ledger",
        verification=verification,
        source_id=movement.id,
        environment=movement.environment,
        evidence_kind=stored.evidence_kind if stored else None,
        recorded_at=movement.created_at,
        reference=f"operation_movements/{movement.id}{suffix}",
        note=note,
    )


def _startrack_ref(event: MovementEventRecord) -> EvidenceRef:
    provenance = event.provenance
    return EvidenceRef(
        origin="startrack",
        verification="source_observed",
        provenance=provenance,
        source_id=event.source_id,
        environment=provenance.environment if provenance else None,
        evidence_kind=provenance.evidence_kind if provenance else None,
        event_time=event.event_time,
        observed_at=event.observed_at,
        recorded_at=event.recorded_at,
        reference=f"operation_events/{event.id}",
    )


def _declaration_ref(receipt: ReceiptRecord) -> EvidenceRef:
    return EvidenceRef(
        origin="econ_declaration",
        verification="declared",
        event_time=receipt.received_at,
        recorded_at=receipt.recorded_at,
        reference=receipt.reference,
        note="Declaración manual de recepción; no verificada contra el proveedor.",
    )


def _receipt(movement: MovementRecord) -> ReceiptRecord | None:
    if isinstance(movement.receipt, ReceiptRecord):
        return movement.receipt
    if isinstance(movement.receipt, dict):
        try:
            return ReceiptRecord.model_validate(movement.receipt)
        except ValidationError:
            return None
    return None


class _GraphBuilder:
    def __init__(self, hub: HubResponse, workflow: WorkflowOverview | None):
        self.hub = hub
        self.workflow = workflow
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.conflicts: list[GraphConflict] = []
        self.tensions: list[GraphTension] = []
        self.gaps: list[GraphGap] = []
        self.equipment_by_id = {item.id: item for item in hub.equipment}
        self.equipment_by_source = {
            item.provenance.source_id: item for item in hub.equipment if item.provenance.source_id
        }
        self.requests_by_source = {
            item.provenance.source_id: item for item in hub.requests if item.provenance.source_id
        }
        self.project_labels: dict[str, str | None] = {}
        self.project_refs: dict[str, list[EvidenceRef]] = {}
        self.views: list[_MovementView] = []
        # Sort key of the latest event chosen per (machine, fact); never a global maximum.
        self.fact_keys: dict[tuple[str, ObservedFact], tuple] = {}

    # ----- collection helpers -----------------------------------------------------------

    def _edge(
        self,
        kind: EdgeKind,
        source: str,
        target: str,
        reference: str,
        *,
        verification: Verification,
        scope: RelationScope,
        evidence: list[EvidenceRef],
        attributes: dict[str, AttributeValue] | None = None,
    ) -> None:
        edge_id = f"{kind}:{source}:{target}:{reference}"
        if edge_id not in self.edges:
            self.edges[edge_id] = GraphEdge(
                id=edge_id,
                kind=kind,
                source=source,
                target=target,
                verification=verification,
                scope=scope,
                evidence=list(evidence),
                attributes=dict(attributes or {}),
            )

    def _conflict(
        self, code: str, key: str, node_ids: list[str], description: str, evidence: list[str]
    ) -> None:
        self.conflicts.append(
            GraphConflict(
                id=f"{code}:{key}",
                code=code,
                node_ids=node_ids,
                description=description,
                evidence=evidence,
            )
        )

    def _tension(
        self, code: str, key: str, node_ids: list[str], description: str, evidence: list[str]
    ) -> None:
        self.tensions.append(
            GraphTension(
                id=f"{code}:{key}",
                code=code,
                node_ids=node_ids,
                description=description,
                evidence=evidence,
            )
        )

    def _gap(self, code: str, key: str, fact: str, description: str, **rest) -> None:
        self.gaps.append(
            GraphGap(id=f"{code}:{key}", code=code, fact=fact, description=description, **rest)
        )

    def _source(self, source_id: str) -> SourceStatus | None:
        return next((item for item in self.hub.sources if item.id == source_id), None)

    # ----- referenced-only nodes --------------------------------------------------------

    def _reference_project(
        self, project_id: str | None, label: str | None, ref: EvidenceRef
    ) -> str | None:
        if not project_id:
            return None
        node_id = f"nexus:project:{project_id}"
        # The label comes from the same record that carries the ID; it is never a join.
        if self.project_labels.get(node_id) is None:
            self.project_labels[node_id] = label
        self.project_refs.setdefault(node_id, []).append(ref)
        return node_id

    def _referenced_machine(self, source_id: str, ref: EvidenceRef) -> str:
        node_id = f"nexus:equipment:{source_id}"
        if node_id not in self.nodes:
            self.nodes[node_id] = MachineNode(
                id=node_id,
                label=source_id,
                verification="referenced_only",
                evidence=[ref],
                missing=["Unidad fuera de la lectura acotada: solo referenciada por ID."],
                source_id=source_id,
            )
            self._gap(
                "record_not_in_reading",
                node_id,
                "unidad",
                "La unidad está referenciada por ID pero no aparece en la lectura acotada.",
                node_id=node_id,
            )
        return node_id

    def _referenced_request(self, source_id: str, ref: EvidenceRef) -> str:
        node_id = f"nexus:request:{source_id}"
        if node_id not in self.nodes:
            self.nodes[node_id] = RequestNode(
                id=node_id,
                label=f"Solicitud {source_id}",
                verification="referenced_only",
                evidence=[ref],
                missing=["Solicitud fuera de la lectura acotada: solo referenciada por ID."],
                source_id=source_id,
            )
            self._gap(
                "record_not_in_reading",
                node_id,
                "solicitud",
                "La solicitud está referenciada por ID pero no aparece en la lectura acotada.",
                node_id=node_id,
            )
        return node_id

    def _place(self, poi_id: str, *, verification: Verification, ref: EvidenceRef) -> str:
        node_id = f"startrack:poi:{poi_id}"
        node = self.nodes.get(node_id)
        if node is None:
            self.nodes[node_id] = PlaceNode(
                id=node_id,
                label=poi_id,
                verification=verification,
                evidence=[ref],
                missing=[
                    "Nombre de la geocerca: solo si Startrack lo informó con este mismo poi_id.",
                    "Geometría de la geocerca: no se incluye.",
                ],
                poi_id=poi_id,
            )
        else:
            node.evidence.append(ref)
            if verification == "source_observed":
                node.verification = "source_observed"
        return node_id

    def _place_name(self, poi_id: str, task: MovementEventRecord) -> None:
        """Only a name observed with this same poi_id; a label never identifies a place."""
        node = self.nodes.get(f"startrack:poi:{poi_id}")
        name = task.data.get("poi_name")
        if isinstance(node, PlaceNode) and node.name is None and name:
            node.name = node.label = name
            node.missing = [item for item in node.missing if not item.startswith("Nombre")]

    # ----- nodes read from the source ---------------------------------------------------

    def add_machines(self) -> None:
        for item in self.hub.equipment:
            provenance = item.provenance
            missing = [f"Ubicación física: {LOCATION_GAP}"]
            if provenance.observed_at is None:
                documented = provenance.observed_on.isoformat() if provenance.observed_on else None
                missing.append(
                    "Hora de observación administrativa: solo se documenta el día "
                    f"{documented or 'ausente'}."
                )
            if item.operators is None:
                missing.append("Operadores: la lectura acotada no los cubre.")
            if item.maintenance_is_stopped is None:
                missing.append("Paro de mantenimiento: sin dato en la lectura.")
            node = MachineNode(
                id=item.id,
                label=item.asset_number or item.code or item.name,
                verification="source_observed",
                evidence=[_nexus_ref(provenance, item.id)],
                missing=missing,
                source_id=provenance.source_id,
                asset_number=item.asset_number,
                code=item.code,
                name=item.name,
                company=item.company,
                equipment_class=item.equipment_class,
                machinery_status=item.machinery_status,
                project_id=item.project_id,
                assignment_starts_on=item.assignment_starts_on,
                assignment_ends_on=item.assignment_ends_on,
                assignment_note=item.assignment_note,
                maintenance_failure_id=item.maintenance_failure_id,
                maintenance_status=item.maintenance_status,
                maintenance_is_stopped=item.maintenance_is_stopped,
                relation_status=item.relation_status,
            )
            node.last_observed["administrative"] = provenance.observed_at
            node.last_read["administrative"] = provenance.observed_at
            self.nodes[item.id] = node
            self._gap(
                "machine_location", item.id, "ubicación física", LOCATION_GAP, node_id=item.id
            )

    def add_requests(self) -> None:
        for item in self.hub.requests:
            missing = []
            if item.project_id is None:
                missing.append("Proyecto de la solicitud: ausente en el origen.")
            if item.machinery_id is None:
                missing.append("Unidad asignada: la solicitud no tiene maquinaria_id.")
            if item.starts_on is None or item.ends_on is None:
                missing.append("Período de uso: fecha de inicio o fin ausente.")
            self.nodes[item.id] = RequestNode(
                id=item.id,
                label=f"Solicitud {item.machinery_type or 'sin tipo'} · {item.status}",
                verification="source_observed",
                evidence=[_nexus_ref(item.provenance, item.id)],
                missing=missing,
                source_id=item.provenance.source_id,
                status=item.status,
                project_id=item.project_id,
                machinery_id=item.machinery_id,
                machinery_type=item.machinery_type,
                starts_on=item.starts_on,
                ends_on=item.ends_on,
                approved_at=item.approved_at,
                requested_by_id=item.requested_by_id,
            )

    def add_incidents(self) -> None:
        for item in self.hub.equipment:
            if not item.maintenance_failure_id:
                continue
            node_id = f"nexus:failure:{item.maintenance_failure_id}"
            ref = _nexus_ref(item.provenance, f"{item.id}.maintenance_failure_id")
            self.nodes[node_id] = IncidentNode(
                id=node_id,
                label=f"Falla {item.maintenance_failure_id}",
                verification="source_observed",
                evidence=[ref],
                missing=[
                    "Detalle de la falla: no se leyó /maquinaria/fallas; solo el ID, estado y "
                    "paro informados en la unidad."
                ],
                failure_id=item.maintenance_failure_id,
                equipment_id=item.id,
                status=item.maintenance_status,
                is_stopped=item.maintenance_is_stopped,
            )
            self._edge(
                "affects",
                node_id,
                item.id,
                item.id,
                verification="source_observed",
                scope="current",
                evidence=[ref],
                attributes={
                    "status": item.maintenance_status,
                    "is_stopped": item.maintenance_is_stopped,
                },
            )

    def add_source_edges(self) -> None:
        for item in self.hub.equipment:
            ref = _nexus_ref(item.provenance, f"{item.id}.project_id")
            project_id = self._reference_project(item.project_id, item.project_name, ref)
            if project_id is not None:
                self._edge(
                    "assigned_to",
                    item.id,
                    project_id,
                    item.id,
                    verification="source_observed",
                    scope="current",
                    evidence=[ref],
                    attributes={
                        "assignment_starts_on": item.assignment_starts_on,
                        "assignment_ends_on": item.assignment_ends_on,
                        "assignment_note": item.assignment_note,
                    },
                )
        for item in self.hub.requests:
            ref = _nexus_ref(item.provenance, f"{item.id}.project_id")
            project_id = self._reference_project(item.project_id, item.project_name, ref)
            if project_id is not None:
                self._edge(
                    "requested_for",
                    item.id,
                    project_id,
                    item.id,
                    verification="source_observed",
                    scope="current",
                    evidence=[ref],
                    attributes={
                        "status": item.status,
                        "starts_on": item.starts_on,
                        "ends_on": item.ends_on,
                        "machinery_type": item.machinery_type,
                    },
                )
            if not item.machinery_id:
                continue
            unit_ref = _nexus_ref(item.provenance, f"{item.id}.machinery_id")
            if item.machinery_id in self.nodes:
                unit_id = item.machinery_id
            else:
                unit_id = self._referenced_machine(
                    item.machinery_id.removeprefix("nexus:equipment:"),
                    _nexus_ref(item.provenance, f"{item.id}.machinery_id", "referenced_only"),
                )
            self._edge(
                "assigned_unit",
                item.id,
                unit_id,
                item.id,
                verification="source_observed",
                scope="current",
                evidence=[unit_ref],
                attributes={
                    "status": item.status,
                    "approved_at": _iso(item.approved_at),
                    "machinery_asset_number": item.machinery_asset_number,
                    "machinery_code": item.machinery_code,
                },
            )

    def add_projects(self) -> None:
        for node_id, refs in self.project_refs.items():
            source_id = node_id.removeprefix("nexus:project:")
            name = self.project_labels.get(node_id)
            self.nodes[node_id] = ProjectNode(
                id=node_id,
                label=name or source_id,
                verification="referenced_only",
                evidence=refs,
                missing=[
                    "Proyecto no leído de Prisma: solo referenciado por ID desde solicitudes, "
                    "unidades o movimientos."
                ],
                source_id=source_id,
                name=name,
            )
            self._gap(
                "project_not_read",
                node_id,
                "proyecto",
                "El proyecto solo está referenciado por ID; su registro no se leyó.",
                node_id=node_id,
            )

    # ----- movements --------------------------------------------------------------------

    def _view(self, movement: MovementRecord) -> _MovementView | None:
        if movement.mode != self.hub.mode:
            return None
        stored = _stored_provenance(movement)
        if stored is None:
            return None

        def compatible(record: RequestRecord | EquipmentRecord | None) -> bool:
            return (
                record is not None
                and movement.environment == record.provenance.environment
                and compatible_evidence(stored, record.provenance)
            )

        request = self.requests_by_source.get(movement.request_source_id)
        equipment = self.equipment_by_source.get(movement.machinery_source_id)
        request = request if compatible(request) else None
        equipment = equipment if compatible(equipment) else None
        if request is None and equipment is None:
            return None
        if request is None or equipment is None:
            scope: RelationScope = "unverifiable"
        elif matching_current_movements(self.hub, request, [movement]):
            scope = "current"
        else:
            scope = "historical"
        task_events = [
            event
            for event in movement.events
            if event.kind == "task_state"
            and event.source_id == movement.job_id
            and event.data.get("job_id") == movement.job_id
            and _from_source(movement, event)
        ]
        arrivals = [
            event
            for event in movement.events
            if event.kind == "arrival"
            and event.data.get("poi_id")
            and event.data.get("poi_id") == movement.mapping.get("poi_id")
            and event.data.get("tracked_asset_id") == movement.tracked_vehicle_id
            and _from_source(movement, event)
        ]
        return _MovementView(
            movement=movement,
            request=request,
            equipment=equipment,
            scope=scope,
            latest_task=max(task_events, key=effective_event_sort_key, default=None),
            arrivals=arrivals,
            receipt=_receipt(movement),
        )

    def add_movements(self) -> None:
        if self.workflow is None or not self.workflow.available:
            return
        for movement in self.workflow.movements:
            view = self._view(movement)
            if view is not None:
                self.views.append(view)
                self._movement_node(view)
        for view in self.views:
            self._movement_edges(view)

    def _movement_node(self, view: _MovementView) -> None:
        movement, arrival = view.movement, view.latest_arrival
        evidence = [_ledger_ref(movement)]
        missing: list[str] = []
        if view.request is None:
            missing.append("Solicitud del movimiento: fuera de la lectura acotada.")
        if view.equipment is None:
            missing.append("Unidad del movimiento: fuera de la lectura acotada.")
        if movement.tracked_vehicle_kind is not None:
            evidence.append(
                _ledger_ref(movement, "declared", ".tracked_vehicle_kind", DECLARED_KIND_NOTE)
            )
        if view.latest_task is not None:
            evidence.append(_startrack_ref(view.latest_task))
        elif movement.job_id:
            missing.append("Estado de la tarea: sin observación registrada de Startrack.")
        if arrival is not None:
            evidence.append(_startrack_ref(arrival))
        else:
            missing.append("Presencia del vehículo rastreado en destino: sin visita registrada.")
        receipt = None
        if view.receipt is not None:
            evidence.append(_declaration_ref(view.receipt))
            receipt = ReceiptSummary(
                receiver=view.receipt.receiver,
                received_at=view.receipt.received_at,
                reference=view.receipt.reference,
                recorded_at=view.receipt.recorded_at,
                note=view.receipt.note,
            )
        else:
            missing.append("Recepción: sin declaración registrada.")
        self.nodes[view.node_id] = MovementNode(
            id=view.node_id,
            label=movement.movement_reference,
            verification="ledger_recorded",
            evidence=evidence,
            missing=missing,
            movement_id=movement.id,
            state=movement.state,
            movement_reference=movement.movement_reference,
            request_source_id=movement.request_source_id,
            machinery_source_id=movement.machinery_source_id,
            project_source_id=movement.project_source_id,
            job_id=movement.job_id,
            task_ref=f"startrack:job:{movement.job_id}" if movement.job_id else None,
            status=view.latest_task.data.get("status") if view.latest_task else movement.status,
            workflow_role=view.workflow_role,
            reason_code=movement.reason_code,
            scheduled_date=movement.mapping.get("scheduled_date"),
            scheduled_time=movement.mapping.get("scheduled_time"),
            poi_id=movement.mapping.get("poi_id"),
            tracked_vehicle_id=movement.tracked_vehicle_id,
            tracked_vehicle_kind=movement.tracked_vehicle_kind,
            tracked_vehicle_kind_verification=(
                "declared" if movement.tracked_vehicle_kind is not None else None
            ),
            arrival_event_time=arrival.event_time if arrival else None,
            arrival_observed_at=arrival.observed_at if arrival else None,
            receipt=receipt,
            relation_scope=view.scope,
            created_at=movement.created_at,
            updated_at=movement.updated_at,
            sent_at=movement.sent_at,
        )

    def _movement_edges(self, view: _MovementView) -> None:
        movement, node_id, scope = view.movement, view.node_id, view.scope
        ledger = _ledger_ref(movement)
        machine_id = (
            view.equipment.id
            if view.equipment is not None
            else self._referenced_machine(
                movement.machinery_source_id,
                _ledger_ref(movement, "referenced_only", ".machinery_source_id"),
            )
        )
        request_id = (
            view.request.id
            if view.request is not None
            else self._referenced_request(
                movement.request_source_id,
                _ledger_ref(movement, "referenced_only", ".request_source_id"),
            )
        )
        self._edge(
            "transfer_of",
            node_id,
            machine_id,
            movement.id,
            verification="ledger_recorded",
            scope=scope,
            evidence=[ledger],
            attributes={
                "state": movement.state,
                "movement_reference": movement.movement_reference,
                "scheduled_date": movement.mapping.get("scheduled_date"),
            },
        )
        self._edge(
            "for_request",
            node_id,
            request_id,
            movement.id,
            verification="ledger_recorded",
            scope=scope,
            evidence=[ledger],
            attributes={"state": movement.state, "request_source_id": movement.request_source_id},
        )
        project_label = (
            view.request.project_name
            if view.request is not None and view.request.project_id == movement.project_source_id
            else None
        )
        project_id = self._reference_project(
            movement.project_source_id,
            project_label,
            _ledger_ref(movement, "referenced_only", ".project_source_id"),
        )
        self._destination_edge(view)
        for event in sorted(view.arrivals, key=effective_event_sort_key):
            self._presence_edge(view, event)
        if view.receipt is not None and project_id is not None:
            receipt = view.receipt
            self._edge(
                "received_by",
                node_id,
                project_id,
                receipt.reference,
                verification="declared",
                scope=scope,
                evidence=[_declaration_ref(receipt)],
                attributes={
                    "receiver": receipt.receiver,
                    "reference": receipt.reference,
                    "received_at": _iso(receipt.received_at),
                    "recorded_at": _iso(receipt.recorded_at),
                    "note": receipt.note,
                    "declared_by_user_id": receipt.declared_by_user_id,
                    "declared_by_email": receipt.declared_by_email,
                    "declared_by_role": receipt.declared_by_role,
                },
            )

    def _destination_edge(self, view: _MovementView) -> None:
        movement, node_id = view.movement, view.node_id
        poi_id = movement.mapping.get("poi_id")
        if not poi_id:
            self._gap(
                "destination_missing",
                movement.id,
                "destino",
                "El plan no declara poi_id de destino.",
                node_id=node_id,
                edge_kind="destination",
            )
            return
        declared = _ledger_ref(
            movement,
            "declared",
            ".mapping.poi_id",
            "Destino declarado en el plan; no observado en Startrack.",
        )
        place_id = self._place(poi_id, verification="referenced_only", ref=declared)
        evidence = [declared]
        task = view.latest_task
        task_poi = task.data.get("poi_id") if task is not None else None
        if task is not None and task_poi is not None:
            if task_poi == poi_id:
                observed = _startrack_ref(task)
                evidence.append(observed)
                self._place(poi_id, verification="source_observed", ref=observed)
                self._place_name(poi_id, task)
            else:
                self._conflict(
                    "task_destination_differs",
                    movement.id,
                    [node_id, place_id],
                    "La tarea observada en Startrack apunta a otra geocerca que la declarada "
                    "en el plan; revisar la correspondencia antes de confiar en el destino.",
                    [
                        f"mapping.poi_id={poi_id}",
                        f"job.poi_id={task_poi}",
                        f"job_id={movement.job_id}",
                        f"observed_at={_iso(task.observed_at)}",
                    ],
                )
        self._edge(
            "destination",
            node_id,
            place_id,
            movement.id,
            verification="declared",
            scope=view.scope,
            evidence=evidence,
            attributes={
                "poi_id": poi_id,
                "scheduled_date": movement.mapping.get("scheduled_date"),
                "scheduled_time": movement.mapping.get("scheduled_time"),
                "task_poi_id": task_poi,
            },
        )

    def _presence_edge(self, view: _MovementView, event: MovementEventRecord) -> None:
        """Presence of the tracked vehicle at the geofence; the machine is never the source."""
        movement = view.movement
        ref = _startrack_ref(event)
        place_id = self._place(event.data["poi_id"], verification="source_observed", ref=ref)
        kind = event.data.get("tracked_asset_kind") or movement.tracked_vehicle_kind
        self._edge(
            "observed_at_place",
            view.node_id,
            place_id,
            event.source_id or event.id,
            verification="source_observed",
            scope=view.scope,
            evidence=[ref],
            attributes={
                "tracked_asset_id": event.data.get("tracked_asset_id"),
                "tracked_asset_kind": kind,
                "tracked_asset_kind_verification": "declared" if kind else None,
                "tracked_asset_kind_note": DECLARED_KIND_NOTE if kind else None,
                "visit_id": event.data.get("visit_id") or event.source_id,
                "event_time": _iso(event.event_time),
                "event_time_raw": event.data.get("event_time_raw"),
                "end_date_raw": event.data.get("end_date_raw"),
                "observed_at": _iso(event.observed_at),
                "label": event.data.get("label"),
            },
        )

    # ----- last observation per fact ----------------------------------------------------

    def add_last_observed(self) -> None:
        for view in self.views:
            if view.scope != "current" or view.equipment is None:
                continue
            node = self.nodes.get(view.equipment.id)
            if not isinstance(node, MachineNode):
                continue
            self._latest(node, "task", view.latest_task)
            self._latest(node, "presence", view.latest_arrival)
            if view.receipt is not None:
                current = node.last_observed["receipt"]
                if current is None or view.receipt.received_at > current:
                    node.last_observed["receipt"] = view.receipt.received_at
                    node.last_read["receipt"] = view.receipt.recorded_at

    def _latest(
        self, node: MachineNode, fact: ObservedFact, event: MovementEventRecord | None
    ) -> None:
        if event is None:
            return
        key = effective_event_sort_key(event)
        previous = self.fact_keys.get((node.id, fact))
        if previous is not None and key <= previous:
            return
        self.fact_keys[(node.id, fact)] = key
        node.last_observed[fact] = event.event_time
        node.last_read[fact] = event.observed_at

    # ----- conflicts, tensions and gaps -------------------------------------------------

    def add_relations(self) -> None:
        approved = sorted(
            (r for r in self.hub.requests if r.status.upper() in APPROVED and r.machinery_id),
            key=lambda r: r.id,
        )
        for request in approved:
            self._assignment_relations(request)
        for index, first in enumerate(approved):
            for second in approved[index + 1 :]:
                if second.machinery_id == first.machinery_id:
                    self._overlap_relation(first, second)
        for view in self.views:
            self._movement_relations(view)

    def _assignment_relations(self, request: RequestRecord) -> None:
        unit = self.equipment_by_id.get(request.machinery_id)
        if unit is None:
            return
        key = f"{unit.id}|{request.id}"
        if unit.machinery_status.upper() == "OBSOLETA":
            self._tension(
                "obsolete_with_approved_request",
                key,
                [unit.id, request.id],
                "La unidad figura OBSOLETA en Prisma y tiene una solicitud aprobada que la "
                "asigna; revisar el estado administrativo antes de trasladar.",
                [f"machinery_status={unit.machinery_status}", f"request.status={request.status}"],
            )
        if unit.project_id and request.project_id and unit.project_id != request.project_id:
            self._conflict(
                "assignment_project_mismatch",
                key,
                [
                    unit.id,
                    request.id,
                    f"nexus:project:{unit.project_id}",
                    f"nexus:project:{request.project_id}",
                ],
                "La asignación vigente de la unidad apunta a un proyecto distinto del de la "
                "solicitud aprobada que la asigna.",
                [
                    f"equipment.project_id={unit.project_id}",
                    f"request.project_id={request.project_id}",
                ],
            )
        elif not unit.project_id:
            self._gap(
                "assignment_not_reported",
                key,
                "asignación vigente",
                "Prisma no informa proyecto vigente en la unidad; no se puede verificar que "
                "coincida con la solicitud aprobada.",
                node_id=unit.id,
                edge_kind="assigned_to",
            )

    def _overlap_relation(self, first: RequestRecord, second: RequestRecord) -> None:
        key = f"{first.id}|{second.id}"
        relation = compare(usage_period_of(first), usage_period_of(second))
        if relation.status == "overlap":
            self._conflict(
                "overlapping_approved_requests",
                key,
                [first.id, second.id, first.machinery_id],
                f"{relation.reason} Prisma admite ambas aprobaciones; ECON solo lo señala.",
                [
                    f"solicitud={first.id}; período={usage_period_of(first).span()}",
                    f"solicitud={second.id}; período={usage_period_of(second).span()}",
                    f"maquinaria_id={first.machinery_id}",
                ],
            )
        elif relation.status == "not_verifiable":
            self._gap(
                "overlap_not_verifiable",
                key,
                "solapamiento de solicitudes aprobadas",
                relation.reason,
                node_id=first.machinery_id,
            )

    def _movement_relations(self, view: _MovementView) -> None:
        movement, node_id = view.movement, view.node_id
        if view.scope == "historical" and view.request is not None:
            if movement.state in CONFLICTING_STATES:
                self._conflict(
                    "movement_source_changed",
                    movement.id,
                    [node_id, view.request.id],
                    "La solicitud o la unidad cambiaron en el origen después de registrar el "
                    "movimiento; la tarea existente ya no describe la asignación vigente.",
                    [
                        f"state={movement.state}",
                        f"request_source_id={movement.request_source_id}",
                        f"source_request_hash={movement.source_request_hash}",
                    ],
                )
            elif movement.state in REVALIDATION_STATES:
                self._gap(
                    "movement_revalidation_pending",
                    movement.id,
                    "vigencia del plan",
                    "El origen cambió desde que se guardó el plan; requiere revalidación antes "
                    "de encolar.",
                    node_id=node_id,
                    edge_kind="for_request",
                )
        elif view.scope == "unverifiable":
            self._gap(
                "movement_counterpart_missing",
                movement.id,
                "relación del movimiento",
                "La solicitud o la unidad del movimiento no están en la lectura acotada; la "
                "relación no se puede verificar.",
                node_id=node_id,
            )
        task = view.latest_task
        if task is not None and task.data.get("status") is not None and view.workflow_role is None:
            self._conflict(
                "status_role_unknown",
                movement.id,
                [node_id],
                "La tarea informa un estado sin rol de flujo conocido (pendiente, completada o "
                "cancelada); no se puede interpretar su avance.",
                [f"job_id={movement.job_id}", f"status={task.data.get('status')}"],
            )
        if view.arrivals and view.receipt is None:
            self._tension(
                "arrival_without_receipt",
                movement.id,
                [node_id],
                "Hay presencia del vehículo rastreado en la geocerca de destino pero ninguna "
                "recepción declarada; la visita no acredita entrega.",
                [f"visits={len(view.arrivals)}", "receipt=ausente"],
            )
        if view.receipt is not None and not view.arrivals:
            self._tension(
                "receipt_without_arrival",
                movement.id,
                [node_id],
                "Hay recepción declarada sin visita registrada del vehículo rastreado en la "
                "geocerca de destino.",
                [f"receipt.reference={view.receipt.reference}", "visits=0"],
            )
        unit = view.equipment
        if unit is None or view.scope != "current":
            return
        key = f"{unit.id}|{movement.id}"
        task_open = movement.state in CONFLICTING_STATES and (
            movement.state != "sent" or view.task_pending
        )
        if unit.maintenance_is_stopped is True and task_open:
            self._tension(
                "stopped_with_pending_task",
                key,
                [unit.id, node_id],
                "La unidad tiene paro de mantenimiento explícito y un traslado pendiente.",
                ["maintenance_is_stopped=true", f"state={movement.state}"],
            )
        if unit.machinery_status.upper() == "DISPONIBLE" and movement.state == "sent":
            self._tension(
                "administrative_status_vs_task",
                key,
                [unit.id, node_id],
                "Prisma informa la unidad DISPONIBLE mientras existe una tarea de traslado "
                "registrada para ella; el estado administrativo no describe el traslado.",
                [f"machinery_status={unit.machinery_status}", f"job_id={movement.job_id}"],
            )

    def add_coverage_gaps(self) -> None:
        workflow = self.workflow
        if workflow is None or not workflow.available:
            self._gap(
                "ledger_not_consulted",
                self.hub.mode,
                "registro de movimientos",
                workflow.message if workflow is not None else LEDGER_NOT_CONSULTED,
            )
        elif not workflow.complete:
            note = workflow.coverage.note if workflow.coverage else ""
            self._gap(
                "ledger_partial",
                self.hub.mode,
                "registro de movimientos",
                f"Registro parcial: {note} Puede existir evidencia fuera de la ventana leída.",
            )
        startrack = self._source("startrack")
        if startrack is not None and startrack.status != "connected":
            self._gap(
                "startrack_not_queried",
                self.hub.mode,
                "seguimiento de Startrack",
                f"{startrack.message} Las tareas y visitas provienen del registro local.",
            )

    # ----- assembly ---------------------------------------------------------------------

    def coverage(self) -> GraphCoverage:
        workflow = self.workflow
        nexus, startrack = self._source("nexus"), self._source("startrack")
        complete = bool(
            self.hub.mode == "live"
            and nexus is not None
            and nexus.status == "connected"
            and startrack is not None
            and startrack.status == "connected"
            and workflow is not None
            and workflow.available
            and workflow.complete
        )
        return GraphCoverage(
            scope=self.hub.scope,
            sources=self.hub.sources,
            operation_evidence=self.hub.operation_evidence,
            ledger=workflow.coverage if workflow is not None else None,
            ledger_available=bool(workflow is not None and workflow.available),
            ledger_message=workflow.message if workflow is not None else LEDGER_NOT_CONSULTED,
            nodes_by_kind=dict(Counter(node.kind for node in self.nodes.values())),
            edges_by_kind=dict(Counter(edge.kind for edge in self.edges.values())),
            referenced_only=sum(
                node.verification == "referenced_only" for node in self.nodes.values()
            ),
            complete=complete,
            description=(
                "Cobertura compuesta de una lectura acotada de Prisma, del registro local de "
                "movimientos y del estado de Startrack. complete solo es true con Prisma y "
                "Startrack consultados en vivo y el registro completo; en fixture y mientras "
                "Startrack no se consulte permanece false. Los nodos y aristas describen esta "
                "lectura, no la flota ni la operación completas."
            ),
        )

    def build(self) -> GraphProjection:
        self.add_machines()
        self.add_requests()
        self.add_incidents()
        self.add_source_edges()
        self.add_movements()
        self.add_projects()
        self.add_last_observed()
        self.add_relations()
        self.add_coverage_gaps()
        return GraphProjection(
            mode=self.hub.mode,
            generated_at=self.hub.generated_at,
            data_as_of=self.hub.data_as_of,
            nodes=list(self.nodes.values()),
            edges=list(self.edges.values()),
            conflicts=self.conflicts,
            tensions=self.tensions,
            gaps=self.gaps,
            alerts=[alert.model_copy(deep=True) for alert in self.hub.alerts],
            coverage=self.coverage(),
            notes=list(NOTES),
        )


def build_graph(hub: HubResponse, workflow: WorkflowOverview | None) -> GraphProjection:
    """Project one hub reading and one ledger page onto typed nodes and evidenced edges."""
    return _GraphBuilder(hub, workflow).build()
