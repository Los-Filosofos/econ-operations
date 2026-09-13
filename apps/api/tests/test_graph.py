"""The typed graph: evidence-backed nodes and edges, explicit scopes, conflicts apart from gaps.

Fixtures here are minimal local copies (a fixture-mode client, an isolated live store, one
mapping) so this module never imports another test module.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.fixtures import fixture_records
from app.integrations.nexus import NexusEquipment, NexusRequest, NexusSnapshot
from app.main import create_app
from app.models import metadata
from app.models.graph import GraphProjection, MachineNode, MovementNode, PlaceNode, ProjectNode
from app.models.hub import (
    HubResponse,
    HubScope,
    HubSummary,
    Provenance,
    RequestRecord,
    SourceStatus,
)
from app.models.workflow import WorkflowOverview
from app.services.graph import build_graph
from app.services.hub import read_hub
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping

CF01 = "nexus:equipment:2a49b73e-a139-4ef1-866b-d54ef246fb46"
CF03 = "nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"
PROJECT = "nexus:project:39723f32-8bb5-4158-a415-2a3d49b0993b"
APPROVED_ID = "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
PENDING_ID = "nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"
MAPPING = {
    "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
    "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
    "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
    "poi_id": "test-poi",
    "assigned_user_ids": ["test-user"],
    "movement_reference": "test-graph-001",
    "scheduled_date": "2026-09-15",
    "scheduled_time": "07:30:00",
}
OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)
EVENT_TIME = OBSERVED - timedelta(hours=1)
LIVE_UNIT = "nexus:equipment:graph-test-unit"
LIVE_PROJECT = "nexus:project:graph-test-project"
LIVE_POI = "startrack:poi:graph-test-poi"


# ----- minimal constructors ---------------------------------------------------------------


def registry(*movements, available=True, complete=True, message="Registro de prueba"):
    return WorkflowOverview(
        available=available, complete=complete, message=message, movements=list(movements)
    )


def fixture_hub(**changes) -> HubResponse:
    equipment, requests = fixture_records()
    hub = HubResponse(
        mode="fixture",
        generated_at=datetime(2040, 1, 1, tzinfo=UTC),
        data_as_of=None,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma",
                status="fixture",
                environment="sandbox",
                message="Muestras",
                observed_on=date(2026, 9, 12),
            ),
            SourceStatus(
                id="startrack",
                label="Startrack",
                status="fixture",
                environment="sandbox",
                message="Sin tareas en las muestras.",
            ),
        ],
        scope=HubScope(
            search="",
            equipment_total=15,
            requests_total=2,
            equipment_returned=len(equipment),
            requests_returned=len(requests),
            complete=False,
            description="Muestras",
        ),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )
    return hub.model_copy(update=changes)


def approved_request(request_id: str, machinery_id: str, starts_on, ends_on) -> RequestRecord:
    provenance = Provenance(
        source="nexus",
        source_id=request_id,
        environment="sandbox",
        observed_at=None,
        observed_on=date(2026, 9, 12),
        is_synthetic=True,
        evidence_kind="provided_sample",
    )
    return RequestRecord(
        id=f"nexus:request:{request_id}",
        project_id="39723f32-8bb5-4158-a415-2a3d49b0993b",
        machinery_id=machinery_id,
        status="APROBADA",
        starts_on=starts_on,
        ends_on=ends_on,
        approved_at=datetime(2026, 9, 12, 1, tzinfo=UTC),
        provenance=provenance,
    )


def snapshot(approved_at="2026-09-11T15:00:00Z") -> NexusSnapshot:
    return NexusSnapshot(
        equipment=[
            NexusEquipment(
                id="graph-test-unit",
                clave="graph-test-code",
                no_activo="graph-test-asset",
                nombre="Unidad de prueba del grafo",
                estado="OCUPADA",
                active_failure_is_paro=False,
            )
        ],
        requests=[
            NexusRequest(
                id="graph-test-request",
                status="APROBADA",
                project_id="graph-test-project",
                project_name="Proyecto de prueba del grafo",
                maquinaria_id="graph-test-unit",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                approved_at=approved_at,
                approved_by_user_id="graph-test-approver",
            )
        ],
        equipment_total=1,
        requests_total=1,
        complete=True,
    )


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'graph.db'}",
        allow_local_management=True,
        _env_file=None,
    )
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1", client=("127.0.0.1", 50002)
    ) as client:
        SQLModel.metadata.create_all(client.app.state.engine)
        yield client


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'graph-live.db'}",
        allow_live_reads=True,
        _env_file=None,
    )
    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    connector = Mock(configured=True)
    connector.read.return_value = snapshot()
    yield settings, engine, connector, OperationsLedger(engine)
    engine.dispose()


def sent(store, reference="graph-test-movement", tracked_vehicle_kind=None):
    settings, _, connector, ledger = store
    hub = read_hub(settings, connector, "live")
    request, equipment = hub.requests[0], hub.equipment[0]
    movement = ledger.create(
        "live",
        request,
        equipment,
        TransferMapping(
            request_source_id=request.provenance.source_id,
            machinery_source_id=equipment.provenance.source_id,
            project_source_id=request.project_id,
            poi_id="graph-test-poi",
            assigned_user_ids=("graph-test-driver",),
            movement_reference=reference,
            scheduled_date=date(2026, 9, 12),
        ),
        tracked_vehicle_id="graph-test-vehicle",
        tracked_vehicle_kind=tracked_vehicle_kind,
    )
    ledger.queue(movement.id)
    ledger.claim(movement.id)
    return ledger.finish_sent(
        movement.id, f"job-{reference}", status="status-pending", workflow_role="pending"
    )


def observe(store, movement, *, kind="task_state", event_time=EVENT_TIME, **values):
    source_id = movement.job_id if kind == "task_state" else "graph-test-visit"
    data = {"job_id": movement.job_id, **values}
    if kind == "arrival":
        data.update(poi_id="graph-test-poi", tracked_asset_id="graph-test-vehicle")
    return store[3].record_observation(
        movement.id,
        "live",
        kind=kind,
        source_id=source_id,
        event_time=event_time,
        observed_at=OBSERVED,
        data=data,
        provenance=Provenance(
            source="startrack",
            source_id=source_id,
            environment="sandbox",
            observed_at=OBSERVED,
            is_synthetic=True,
            evidence_kind="live_read",
        ),
    )


def live_graph(store) -> GraphProjection:
    settings, engine, connector, ledger = store
    hub = read_hub(settings, connector, "live", engine=engine)
    return build_graph(hub, registry(*ledger.list("live")))


def nodes_of(graph: GraphProjection, kind: str):
    return [node for node in graph.nodes if node.kind == kind]


def edges_of(graph: GraphProjection, kind: str):
    return [edge for edge in graph.edges if edge.kind == kind]


def touching(graph: GraphProjection, node_id: str):
    return [edge for edge in graph.edges if node_id in (edge.source, edge.target)]


# ----- (a) fixture reading ----------------------------------------------------------------


def test_fixture_graph_keeps_every_machine_and_backs_each_edge_with_evidence():
    graph = build_graph(fixture_hub(), registry())

    machines = nodes_of(graph, "machine")
    assert len(machines) == 5
    assert all(node.verification == "source_observed" for node in machines)
    isolated = [node for node in machines if not touching(graph, node.id)]
    assert len(isolated) == 4 and CF03 not in {node.id for node in isolated}
    for node in machines:
        assert isinstance(node, MachineNode)
        assert all(value is None for value in node.last_observed.values())
        assert any(item.startswith("Ubicación física") for item in node.missing)
        assert any(gap.code == "machine_location" and gap.node_id == node.id for gap in graph.gaps)

    projects = nodes_of(graph, "project")
    assert len(projects) == 1
    project = projects[0]
    assert isinstance(project, ProjectNode)
    assert project.id == PROJECT and project.verification == "referenced_only"
    assert project.label.startswith("PROY-014") and project.presence == "referenced_only"
    assert len(nodes_of(graph, "request")) == 2
    assert not nodes_of(graph, "movement") and not nodes_of(graph, "place")
    assert not nodes_of(graph, "incident")

    [assigned] = edges_of(graph, "assigned_to")
    assert (assigned.source, assigned.target) == (CF03, PROJECT)
    assert assigned.scope == "current" and assigned.verification == "source_observed"
    assert assigned.attributes["assignment_starts_on"] == "2026-09-11"
    assert assigned.attributes["assignment_ends_on"] == "2026-09-14"
    [evidence] = assigned.evidence
    assert evidence.origin == "nexus" and evidence.verification == "source_observed"
    assert evidence.provenance.evidence_kind == "provided_sample"
    assert evidence.observed_on == date(2026, 9, 12) and evidence.observed_at is None
    assert len(edges_of(graph, "requested_for")) == 2
    [assigned_unit] = edges_of(graph, "assigned_unit")
    assert (assigned_unit.source, assigned_unit.target) == (APPROVED_ID, CF03)
    assert all(edge.evidence for edge in graph.edges)

    assert graph.conflicts == []
    assert [tension.code for tension in graph.tensions] == ["obsolete_with_approved_request"]
    assert set(graph.tensions[0].node_ids) == {CF03, APPROVED_ID}
    assert graph.coverage.complete is False and graph.data_as_of is None
    assert graph.coverage.referenced_only == 1
    assert graph.coverage.nodes_by_kind == {"machine": 5, "request": 2, "project": 1}
    assert graph.alerts == [] and graph.remote_writes is False


# ----- (b) saved fixture plan -------------------------------------------------------------


def test_saved_fixture_plan_is_a_draft_movement_with_declared_destination(client):
    saved = client.post("/api/v1/operations/plans", json={"mode": "fixture", "mapping": MAPPING})
    assert saved.status_code == 201, saved.text
    movement_id = saved.json()["id"]

    response = client.get("/api/v1/graph", params={"mode": "fixture"})
    assert response.status_code == 200
    graph = GraphProjection.model_validate(response.json())

    [movement] = nodes_of(graph, "movement")
    assert isinstance(movement, MovementNode)
    assert movement.id == f"econ:movement:{movement_id}"
    assert movement.state == "draft" and movement.relation_scope == "current"
    assert movement.verification == "ledger_recorded"
    assert movement.task_ref is None and movement.job_id is None
    assert movement.arrival_event_time is None and movement.receipt is None
    assert movement.tracked_vehicle_kind is None
    assert movement.tracked_vehicle_kind_verification is None

    [transfer] = edges_of(graph, "transfer_of")
    assert (transfer.source, transfer.target) == (movement.id, CF03)
    assert transfer.verification == "ledger_recorded" and transfer.scope == "current"
    assert transfer.evidence[0].origin == "econ_ledger"
    [for_request] = edges_of(graph, "for_request")
    assert (for_request.source, for_request.target) == (movement.id, APPROVED_ID)
    assert for_request.verification == "ledger_recorded"
    [destination] = edges_of(graph, "destination")
    assert (destination.source, destination.target) == (movement.id, "startrack:poi:test-poi")
    assert destination.verification == "declared"
    assert [ref.verification for ref in destination.evidence] == ["declared"]
    [place] = nodes_of(graph, "place")
    assert isinstance(place, PlaceNode)
    assert place.poi_id == "test-poi" and place.name is None and place.geometry is None
    assert place.verification == "referenced_only"
    assert not edges_of(graph, "observed_at_place") and not edges_of(graph, "received_by")
    assert graph.conflicts == []
    assert graph.coverage.ledger_available is True
    assert graph.coverage.nodes_by_kind["movement"] == 1
    assert graph.coverage.complete is False


def test_movement_whose_request_is_outside_the_reading_is_unverifiable(client):
    assert client.post("/api/v1/operations/plans", json={"mode": "fixture", "mapping": MAPPING})
    movements = OperationsLedger(client.app.state.engine).list("fixture")
    hub = fixture_hub(requests=[])

    graph = build_graph(hub, registry(*movements))

    [movement] = nodes_of(graph, "movement")
    assert movement.relation_scope == "unverifiable"
    referenced = next(node for node in graph.nodes if node.id == APPROVED_ID)
    assert referenced.kind == "request" and referenced.verification == "referenced_only"
    assert all(edge.scope == "unverifiable" for edge in touching(graph, movement.id))
    assert {gap.code for gap in graph.gaps} >= {
        "movement_counterpart_missing",
        "record_not_in_reading",
    }
    assert graph.conflicts == []


# ----- (c) live evidence ------------------------------------------------------------------


def test_presence_hangs_from_the_movement_and_receipt_is_a_declared_edge(store):
    settings, engine, connector, ledger = store
    movement = sent(store, tracked_vehicle_kind="transporter")
    observe(
        store,
        movement,
        status="status-pending",
        workflow_role="pending",
        poi_id="graph-test-poi",
        poi_name="Patio de prueba",
    )
    observe(store, movement, kind="arrival", visit_id="graph-test-visit", label="Presencia GPS")
    ledger.record_receipt(
        movement.id,
        "live",
        receiver="Responsable de prueba",
        received_at=OBSERVED,
        reference="constancia-prueba",
    )

    graph = live_graph(store)
    hub_observed_at = graph.data_as_of
    assert hub_observed_at is not None

    [node] = nodes_of(graph, "movement")
    assert isinstance(node, MovementNode)
    assert node.relation_scope == "current"
    assert node.task_ref == f"startrack:job:{movement.job_id}"
    assert node.tracked_vehicle_id == "graph-test-vehicle"
    assert node.tracked_vehicle_kind == "transporter"
    assert node.tracked_vehicle_kind_verification == "declared"
    assert node.arrival_event_time == EVENT_TIME and node.arrival_observed_at == OBSERVED
    assert node.receipt is not None and node.receipt.receiver == "Responsable de prueba"

    [presence] = edges_of(graph, "observed_at_place")
    assert presence.source == node.id and presence.target == LIVE_POI
    assert presence.verification == "source_observed" and presence.scope == "current"
    assert presence.attributes["tracked_asset_id"] == "graph-test-vehicle"
    assert presence.attributes["tracked_asset_kind"] == "transporter"
    assert presence.attributes["tracked_asset_kind_verification"] == "declared"
    assert presence.attributes["visit_id"] == "graph-test-visit"
    assert presence.evidence[0].event_time == EVENT_TIME
    assert presence.evidence[0].observed_at == OBSERVED
    assert presence.evidence[0].provenance.source == "startrack"
    # Presence never hangs from the machine: no machine → place edge of any kind.
    assert not [
        edge for edge in graph.edges if edge.source == LIVE_UNIT and edge.target == LIVE_POI
    ]
    assert not [edge for edge in edges_of(graph, "observed_at_place") if edge.source == LIVE_UNIT]

    [received] = edges_of(graph, "received_by")
    assert (received.source, received.target) == (node.id, LIVE_PROJECT)
    assert received.verification == "declared"
    assert received.attributes["receiver"] == "Responsable de prueba"
    assert received.attributes["reference"] == "constancia-prueba"
    assert received.evidence[0].origin == "econ_declaration"
    assert not nodes_of(graph, "incident")
    assert all(node.kind != "person" for node in graph.nodes)

    [place] = nodes_of(graph, "place")
    assert place.name == "Patio de prueba" and place.verification == "source_observed"
    assert place.geometry is None
    [destination] = edges_of(graph, "destination")
    assert [ref.verification for ref in destination.evidence] == ["declared", "source_observed"]
    assert destination.attributes["task_poi_id"] == "graph-test-poi"

    machine = next(node for node in nodes_of(graph, "machine") if node.id == LIVE_UNIT)
    assert machine.last_observed["presence"] == EVENT_TIME
    assert machine.last_observed["administrative"] == hub_observed_at
    assert machine.last_observed["task"] == EVENT_TIME
    assert machine.last_observed["receipt"] == OBSERVED
    assert machine.last_read["presence"] == OBSERVED
    assert graph.conflicts == []
    assert not {tension.code for tension in graph.tensions} & {
        "arrival_without_receipt",
        "receipt_without_arrival",
    }


def test_arrival_without_receipt_is_a_tension_not_a_receipt(store):
    movement = sent(store)
    observe(store, movement, kind="arrival")

    graph = live_graph(store)

    [node] = nodes_of(graph, "movement")
    assert node.receipt is None and node.arrival_event_time == EVENT_TIME
    assert [tension.code for tension in graph.tensions] == ["arrival_without_receipt"]
    assert not edges_of(graph, "received_by")
    assert "Recepción: sin declaración registrada." in node.missing
    # The vehicle kind was not declared: nothing is invented for it.
    [presence] = edges_of(graph, "observed_at_place")
    assert presence.attributes["tracked_asset_kind"] is None
    assert presence.attributes["tracked_asset_kind_verification"] is None


# ----- (d) changed source -----------------------------------------------------------------


def test_changed_source_request_makes_the_relation_historical_with_a_conflict(store):
    settings, engine, connector, ledger = store
    movement = sent(store)
    connector.read.return_value = snapshot(approved_at="2026-09-11T16:00:00Z")

    graph = live_graph(store)

    [node] = nodes_of(graph, "movement")
    assert node.relation_scope == "historical"
    movement_edges = touching(graph, node.id)
    assert movement_edges and all(edge.scope == "historical" for edge in movement_edges)
    assert not [edge for edge in movement_edges if edge.scope == "current"]
    [conflict] = graph.conflicts
    assert conflict.code == "movement_source_changed"
    assert set(conflict.node_ids) == {node.id, "nexus:request:graph-test-request"}
    assert f"state={movement.state}" in conflict.evidence
    # The current assignment edges of the source stay current; the stale relation does not.
    [assigned_unit] = edges_of(graph, "assigned_unit")
    assert assigned_unit.scope == "current"
    machine = next(item for item in nodes_of(graph, "machine") if item.id == LIVE_UNIT)
    assert machine.last_observed["task"] is None


# ----- (e) live disabled ------------------------------------------------------------------


def test_disabled_live_reads_give_an_empty_graph_without_fixture_fallback(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'disabled.db'}",
            allow_live_reads=False,
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        response = client.get("/api/v1/graph", params={"mode": "live"})
    assert response.status_code == 200
    graph = GraphProjection.model_validate(response.json())
    assert graph.mode == "live"
    assert graph.nodes == [] and graph.edges == []
    assert all(source.status == "disabled" for source in graph.coverage.sources)
    assert graph.coverage.ledger_available is False
    assert graph.coverage.complete is False
    assert graph.coverage.nodes_by_kind == {}
    assert "ledger_not_consulted" in {gap.code for gap in graph.gaps}


# ----- (f) overlapping approved requests ---------------------------------------------------


def test_overlapping_approved_requests_conflict_and_missing_dates_stay_a_gap():
    first = approved_request("graph-overlap-a", CF01, "2026-09-10", "2026-09-12")
    second = approved_request("graph-overlap-b", CF01, "2026-09-12", "2026-09-14")
    hub = fixture_hub()
    hub.requests = [*hub.requests, first, second]

    graph = build_graph(hub, None)

    [conflict] = [c for c in graph.conflicts if c.code == "overlapping_approved_requests"]
    assert {first.id, second.id} <= set(conflict.node_ids)
    assert CF01 in conflict.node_ids
    assert graph.coverage.ledger_available is False
    assert "ledger_not_consulted" in {gap.code for gap in graph.gaps}
    # CF-01 reports no project: not verifiable, never a mismatch.
    assert not [c for c in graph.conflicts if c.code == "assignment_project_mismatch"]
    assert [gap for gap in graph.gaps if gap.code == "assignment_not_reported"]

    hub.requests = [
        *fixture_hub().requests,
        first,
        approved_request("graph-overlap-c", CF01, "2026-09-12", None),
    ]
    graph = build_graph(hub, None)
    assert not [c for c in graph.conflicts if c.code == "overlapping_approved_requests"]
    [gap] = [gap for gap in graph.gaps if gap.code == "overlap_not_verifiable"]
    assert gap.status == "no verificable" and "usage_period.end" in gap.description


# ----- (g) OpenAPI and HTTP contract -------------------------------------------------------


def test_openapi_documents_graph_and_suggestions_and_the_route_validates(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'schema.db'}", _env_file=None))
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        schema = client.get("/openapi.json").json()
        for path in ("/api/v1/graph", "/api/v1/requests/{request_id}/suggestions"):
            operation = schema["paths"][path]["get"]
            assert operation["summary"] and operation["description"]
        tags = {tag["name"] for tag in schema["tags"]}
        assert {"Grafo operativo", "Sugerencias"} <= tags
        assert schema["paths"]["/api/v1/graph"]["get"]["tags"] == ["Grafo operativo"]

        response = client.get("/api/v1/graph", params={"mode": "fixture"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        graph = GraphProjection.model_validate(response.json())
        assert graph.mode == "fixture" and graph.coverage.complete is False
        assert client.get("/api/v1/graph", params={"mode": "production"}).status_code == 422
        assert client.get("/api/v1/graph", params={"search": "x" * 101}).status_code == 422
        filtered = client.get("/api/v1/graph", params={"search": "CF-01"}).json()
        assert [node["label"] for node in filtered["nodes"] if node["kind"] == "machine"] == [
            "CF-01"
        ]
