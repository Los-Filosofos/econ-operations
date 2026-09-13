"""The Prisma → ECON → Startrack trace, its HTTP route and its page."""

import json

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder
from sqlmodel import Session, SQLModel

from app.api.users import new_user
from app.core.auth import Role
from app.core.config import Settings
from app.dashboard.context import QueryContext
from app.dashboard.integration_views import PANEL_ID, SELECT_ID, request_options
from app.dashboard.views import render_page
from app.main import create_app
from app.models import metadata
from app.models.hub import HubResponse
from app.models.workflow import WorkflowOverview
from app.services.integration_trace import TREATMENTS, build_trace, default_request_id

ASSIGNED = "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
UNASSIGNED = "nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"
MAPPING = {
    "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
    "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
    "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
    "poi_id": "test-poi",
    "assigned_user_ids": ["test-user"],
    "movement_reference": "test-integration-001",
    "scheduled_date": "2026-09-15",
    "scheduled_time": "07:30:00",
}


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'integration.db'}",
        allow_local_management=True,
        _env_file=None,
    )
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1", client=("127.0.0.1", 50001)
    ) as client:
        SQLModel.metadata.create_all(client.app.state.engine)
        assert client.get("/_dash-layout").status_code == 200
        yield client


def hub_of(client) -> HubResponse:
    return HubResponse.model_validate(client.get("/api/v1/hub").json())


def save_plan(client) -> dict:
    response = client.post("/api/v1/operations/plans", json={"mode": "fixture", "mapping": MAPPING})
    assert response.status_code == 201, response.text
    return response.json()


def overview(client) -> WorkflowOverview:
    return WorkflowOverview.model_validate(
        client.get("/api/v1/operations", params={"mode": "fixture"}).json()
    )


def test_trace_without_movement_reports_missing_preparation_and_no_payload(client):
    trace = build_trace(hub_of(client), ASSIGNED, overview(client))
    assert trace is not None
    assert trace.movement_id is None and trace.payload is None
    assert trace.message == "Sin envío registrado para esta solicitud"
    assert trace.preparation.status == "missing_information"
    assert trace.preparation.missing_fields
    assert not trace.preparation.blocking_reasons
    request_stage = next(stage for stage in trace.stages if stage.key == "startrack_request")
    assert request_stage.state == "pending"
    assert all(entry.value is None for entry in request_stage.entries)
    assert set(trace.preparation.missing_fields) <= set(request_stage.rules)
    response_stage = next(stage for stage in trace.stages if stage.key == "startrack_response")
    assert response_stage.state == "pending" and response_stage.entries == []
    # No end of a duration is registered, so no duration is shown.
    assert trace.timeline.durations == []
    assert trace.timeline.expected_duration_seconds is None
    assert all(moment.at is None for moment in trace.timeline.instants)


def test_trace_with_saved_movement_shows_payload_and_scheduled_instant(client):
    movement = save_plan(client)
    trace = build_trace(hub_of(client), ASSIGNED, overview(client))
    assert trace.movement_id == movement["id"]
    assert trace.movement_reference == "test-integration-001"
    assert trace.payload["remote_id"] == "test-integration-001"
    assert trace.payload["poi_id"] == "test-poi"
    assert trace.payload["assigned_user_ids"] == ["test-user"]
    assert trace.payload["start_date"] == "2026-09-15"
    request_stage = next(stage for stage in trace.stages if stage.key == "startrack_request")
    assert request_stage.state == "done"
    assert {entry.field for entry in request_stage.entries} == {
        "objective",
        "description",
        "start_date",
        "start_time",
        "remote_id",
        "poi_id",
        "assigned_user_ids",
        "job_type_id",
    }
    scheduled = next(moment for moment in trace.timeline.instants if moment.key == "scheduled")
    assert scheduled.at is not None and scheduled.at.isoformat() == "2026-09-15T07:30:00-06:00"
    # A saved plan is not a sent task: nothing later than the schedule is registered.
    assert [moment.key for moment in trace.timeline.instants if moment.at] == ["scheduled"]
    assert trace.timeline.durations == []
    assert trace.job_id is None


def test_field_map_keeps_prisma_fields_that_never_reach_the_job(client):
    save_plan(client)
    trace = build_trace(hub_of(client), ASSIGNED, overview(client))
    rows = {row.concept: row for row in trace.field_map}
    assert rows["Tarifa por hora del proyecto"].treatment == "absent"
    assert rows["Tarifa por hora del proyecto"].startrack.field is None
    assert rows["Período de uso solicitado"].treatment == "absent"
    assert rows["Comentarios de la solicitud"].treatment == "absent"
    assert rows["Paro de mantenimiento"].treatment == "absent"
    assert rows["Operador ↔ conductor"].treatment == "manual"
    assert "assigned_user_remote_ids" in rows["Operador ↔ conductor"].note
    assert rows["Programación del traslado"].startrack.value == "2026-09-15, 07:30:00"
    assert rows["Referencia del movimiento"].startrack.value == "test-integration-001"
    # The real Startrack form fields ECON never sends stay visible as such.
    for concept in [
        "Completar antes de (fecha límite)",
        "Origen (geocerca)",
        "Ventana horaria de entrega",
        "Duración esperada",
        "Formularios de la tarea",
        "Artículos de la tarea",
        "Contacto de la tarea",
    ]:
        row = rows[concept]
        assert row.prisma.field is None and row.econ.field is None
        assert row.treatment in {"absent", "manual"}
    assert {row.treatment for row in trace.field_map} <= set(TREATMENTS)


def test_trace_of_a_request_without_a_unit_blocks_nothing_and_keeps_gaps_visible(client):
    trace = build_trace(hub_of(client), UNASSIGNED, overview(client))
    assert trace.equipment_label is None
    assert "Unidad asignada a la solicitud" in trace.preparation.missing_fields
    assert trace.preparation.blocking_reasons  # PENDIENTE is not an approval
    prisma = next(stage for stage in trace.stages if stage.key == "prisma")
    assert {entry.field for entry in prisma.entries} == {
        "id",
        "tipo",
        "status",
        "fecha_inicio",
        "fecha_fin",
        "project_id",
        "project_name",
        "maquinaria_id",
        "maquinaria_no_activo",
        "requested_by_name",
        "approved_by_name",
        "comentarios",
    }
    assert next(stage for stage in trace.stages if stage.key == "startrack_request").state == (
        "blocked"
    )


def test_http_route_answers_200_404_and_422(client):
    ok = client.get(f"/api/v1/integration/{ASSIGNED}")
    assert ok.status_code == 200
    assert ok.headers["cache-control"] == "no-store"
    body = ok.json()
    assert body["schema_version"] == "1.0" and body["mode"] == "fixture"
    assert [stage["key"] for stage in body["stages"]] == [
        "prisma",
        "econ",
        "startrack_request",
        "startrack_response",
    ]
    assert body["timeline"]["note"].startswith("ECON no estima tiempos de ruta")
    # The original Prisma id addresses the same trace as the normalized one.
    by_source = client.get("/api/v1/integration/46d2573e-08d3-4855-971d-2fbf9564e135").json()
    assert {key: value for key, value in by_source.items() if key != "generated_at"} == {
        key: value for key, value in body.items() if key != "generated_at"
    }
    assert client.get("/api/v1/integration/nexus:request:missing").status_code == 404
    assert client.get(f"/api/v1/integration/{ASSIGNED}?mode=imaginary").status_code == 422
    assert client.get(f"/api/v1/integration/{'x' * 201}").status_code == 422


def test_route_and_page_derive_the_same_trace(client):
    save_plan(client)
    body = client.get(f"/api/v1/integration/{ASSIGNED}").json()
    trace = build_trace(hub_of(client), ASSIGNED, overview(client))
    assert json.loads(trace.model_dump_json())["field_map"] == body["field_map"]
    assert json.loads(trace.model_dump_json())["timeline"] == body["timeline"]


def test_page_renders_with_and_without_a_movement(client):
    hub = hub_of(client)
    context = QueryContext()
    empty_page = json.dumps(
        render_page("/integracion", hub, context, overview(client)),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "Sin envío registrado para esta solicitud" in empty_page
    assert "Sin duración esperada informada" in empty_page
    assert "ECON no estima tiempos de ruta" in empty_page
    for label in TREATMENTS.values():
        assert label in empty_page
    save_plan(client)
    with_movement = json.dumps(
        render_page("/integracion", hub, context, overview(client)),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "test-integration-001" in with_movement
    assert "Sin envío registrado para esta solicitud" not in with_movement
    assert SELECT_ID["type"] in with_movement and PANEL_ID["type"] in with_movement


def test_select_lists_the_requests_of_the_read_and_prefers_an_assigned_one(client):
    hub = hub_of(client)
    options = request_options(hub)
    assert {option["value"] for option in options} == {item.id for item in hub.requests}
    assert default_request_id(hub) == ASSIGNED
    assert any("CF-03" in option["label"] for option in options)
    assert any("sin unidad asignada" in option["label"] for option in options)


def test_trace_is_none_outside_the_read(client):
    assert build_trace(hub_of(client), "nexus:request:not-here", overview(client)) is None


def test_the_route_needs_a_session_and_every_read_role_may_use_it(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'integration-auth.db'}",
        auth_required=True,
        session_secret="unit-test-secret",
        _env_file=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        anonymous = client.get(f"/api/v1/integration/{ASSIGNED}")
        assert anonymous.status_code == 401
        assert anonymous.json() == {"detail": "Autenticación requerida"}
        with Session(app.state.engine) as db:
            db.add(new_user("lectura@example.com", "lectura", Role.lectura, "correct-horse-b"))
            db.commit()
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "lectura@example.com", "password": "correct-horse-b"},
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/integration/{ASSIGNED}").status_code == 200
        assert client.get("/integracion", follow_redirects=False).status_code == 200
