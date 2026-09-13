"""The primary graph preserves source identities and draws only evidenced relationships."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from plotly.utils import PlotlyJSONEncoder

from app.dashboard.operations_graph import build_operations_graph, operations_graph_view
from app.integrations.fixtures import fixture_records
from app.models.hub import (
    AlertRecord,
    HubResponse,
    HubScope,
    HubSummary,
    Provenance,
    SourceStatus,
    TransferRecord,
)
from app.models.workflow import WorkflowOverview

AT = datetime(2026, 9, 13, 12, tzinfo=UTC)


def hub_fixture() -> HubResponse:
    equipment, requests = fixture_records()
    return HubResponse(
        mode="fixture",
        generated_at=AT,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma / Nexus",
                status="fixture",
                environment="sandbox",
                observed_on=date(2026, 9, 12),
                message="Muestra proporcionada",
            ),
            SourceStatus(
                id="startrack",
                label="Startrack",
                status="fixture",
                environment="sandbox",
                message="Sin tareas proporcionadas",
            ),
        ],
        scope=HubScope(
            search="",
            equipment_total=15,
            requests_total=2,
            equipment_returned=5,
            requests_returned=2,
            complete=False,
            description="Cobertura parcial",
        ),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )


def serialized(value) -> str:
    return json.dumps(value, cls=PlotlyJSONEncoder, ensure_ascii=False)


def test_fixture_graph_has_one_project_five_unique_machines_and_one_exact_assignment():
    graph = build_operations_graph(hub_fixture())
    places = [node for node in graph.nodes if node.kind == "place"]
    machines = [node for node in graph.nodes if node.kind == "machine"]
    assert [(node.subtype, node.source_id) for node in places] == [
        ("project", "39723f32-8bb5-4158-a415-2a3d49b0993b")
    ]
    assert len(machines) == len({node.entity_id for node in machines}) == 5
    assert [node.subtype for node in machines].count("loader") == 3
    assert [node.subtype for node in machines].count("excavator") == 2
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.kind == "assignment" and edge.request_ids == [
        "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
    ]
    assert edge.source.endswith("66faacde-728c-4378-8b46-dbfb38254e03")
    assert edge.target.endswith("39723f32-8bb5-4158-a415-2a3d49b0993b")


def test_unassigned_machines_stay_visible_without_connections_or_invented_places():
    graph = build_operations_graph(hub_fixture())
    connected = {edge.source for edge in graph.edges} | {edge.target for edge in graph.edges}
    unconnected_machines = [
        node for node in graph.nodes if node.kind == "machine" and node.key not in connected
    ]
    assert len(unconnected_machines) == 4
    assert {node.subtype for node in graph.nodes if node.kind == "place"} == {"project"}
    assert all("base" not in node.key and "workshop" not in node.key for node in graph.nodes)
    collection = next(node for node in graph.nodes if node.kind == "collection")
    assert collection.label == "SIN ASIGNACIÓN"
    assert set(collection.member_keys) == {node.key for node in unconnected_machines}
    assert all(
        edge.source != collection.key and edge.target != collection.key for edge in graph.edges
    )


def test_layout_is_stable_when_source_lists_arrive_in_another_order():
    hub = hub_fixture()
    first = build_operations_graph(hub)
    hub.equipment.reverse()
    hub.requests.reverse()
    second = build_operations_graph(hub)
    assert {(node.key, node.x, node.y) for node in first.nodes} == {
        (node.key, node.x, node.y) for node in second.nodes
    }
    assert [(edge.key, edge.source, edge.target) for edge in first.edges] == [
        (edge.key, edge.source, edge.target) for edge in second.edges
    ]


def test_assigned_id_outside_bounded_equipment_read_uses_one_explicit_generic_node():
    hub = hub_fixture()
    request = next(request for request in hub.requests if request.machinery_id)
    hub.equipment = [item for item in hub.equipment if item.id != request.machinery_id]
    graph = build_operations_graph(hub)
    placeholder = next(node for node in graph.nodes if node.entity_id == request.machinery_id)
    assert placeholder.subtype == "machinery"
    assert placeholder.source_id is None
    assert placeholder.status == "Registro fuera de la lectura"
    assert sum(edge.source == placeholder.key for edge in graph.edges) == 1


def test_confirmed_active_transfer_promotes_exact_edge_without_duplicating_machine():
    hub = hub_fixture()
    request = next(request for request in hub.requests if request.machinery_id)
    machine = next(item for item in hub.equipment if item.id == request.machinery_id)
    machine.transfers = [
        TransferRecord(
            id="startrack:job:42",
            code="42",
            status="PENDIENTE",
            request_id=request.id,
            destination_project_id=request.project_id,
            destination_project_name=request.project_name,
            workflow_role="pending",
            evidence_current_assignment=True,
            provenance=Provenance(
                source="startrack",
                source_id="42",
                environment="sandbox",
                observed_at=AT,
                is_synthetic=True,
                evidence_kind="provided_sample",
            ),
        )
    ]
    graph = build_operations_graph(hub)
    assert len([node for node in graph.nodes if node.entity_id == machine.id]) == 1
    assert len(graph.edges) == 1
    assert graph.edges[0].kind == "transfer" and graph.edges[0].active
    payload = serialized(
        operations_graph_view(
            hub,
            WorkflowOverview(available=True, complete=True, message="Registro consultado"),
        )
    )
    assert "graph-edge--transfer graph-edge--active" in payload
    assert "En traslado · tiempo no disponible" in payload
    assert "Sin constancia de recepción" in payload


def test_incident_marker_requires_confirmed_failure_and_keeps_maintenance_separate():
    hub = hub_fixture()
    machine = hub.equipment[0]
    machine.maintenance_failure_id = "failure-source-1"
    machine.maintenance_status = "ABIERTA"
    hub.alerts = [
        AlertRecord(
            id="active_failure:test",
            code="active_failure",
            severity="warning",
            title="Falla activa registrada",
            description="Revisar evidencia de origen.",
            owner="Mantenimiento",
            equipment_id=machine.id,
            evidence=["active_failure_id=failure-source-1"],
        )
    ]
    payload = serialized(operations_graph_view(hub))
    assert "graph-node--incident" in payload
    assert "failure-source-1" in payload
    assert "Incidentes confirmados por reglas" in payload


def test_graph_states_expose_partial_old_empty_and_unavailable_reads_briefly():
    hub = hub_fixture()
    payload = serialized(operations_graph_view(hub))
    assert "Cobertura parcial" in payload and "Fecha documental 12/09/2026" in payload
    hub.equipment = []
    hub.requests = []
    assert "Sin entidades verificables" in serialized(operations_graph_view(hub))
    hub.sources[0].status = "error"
    hub.sources[0].message = "Conexión limitada"
    unavailable = serialized(operations_graph_view(hub))
    assert "Origen no disponible" in unavailable and "Conexión limitada" in unavailable
    assert "operations-graph-world" not in unavailable


def test_full_page_graph_has_local_assets_straight_edges_and_no_tables_or_metric_cards():
    hub = hub_fixture()
    payload = serialized(operations_graph_view(hub))
    assert '"type": "AgGrid"' not in payload and '"type": "Table"' not in payload
    assert "decision-card" not in payload and "query-bar" not in payload
    assert "rotate(" in payload and "graph-edge--assignment" in payload
    assets = Path(__file__).parents[1] / "app" / "dashboard" / "assets"
    for name in [
        "project",
        "base",
        "workshop",
        "excavator",
        "loader",
        "roller",
        "truck",
        "machinery",
        "pool",
    ]:
        svg = (assets / f"graph-{name}.svg").read_text(encoding="utf-8")
        assert svg.startswith("<svg") and "<path" in svg
    css = (assets / "style.css").read_text(encoding="utf-8")
    script = (assets / "operations-graph.js").read_text(encoding="utf-8")
    assert "width: 96px; height: 96px" in css
    assert "width: 58px" in css and "height: 58px" in css
    assert 'font-family: "Roboto Mono"' in css
    assert "RobotoMono-wght.ttf" in css
    assert (assets / "RobotoMono-wght.ttf").stat().st_size > 100_000
    assert "SIL OPEN FONT LICENSE Version 1.1" in (assets / "RobotoMono-OFL.txt").read_text(
        encoding="utf-8"
    )
    assert "prefers-reduced-motion" in css and "graph-edge--active" in css
    assert "pointerdown" in script and "wheel" in script and "keydown" in script
    assert "selectEdge" in script and "data-edge-selection" in script


def test_unassigned_collection_and_connection_expose_context_without_inventing_a_base():
    payload = serialized(operations_graph_view(hub_fixture()))
    assert "Sin asignación verificada" in payload
    assert "Este nodo no representa una base, almacén o taller físico" in payload
    assert "Disponibles" in payload
    assert "graph-edge-label" in payload
    assert "Evidencia de la relación" in payload
    assert "La línea representa correspondencia documental" in payload
