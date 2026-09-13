"""Exercise the Dash action boundary and evidence semantics through real callbacks."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder
from sqlmodel import SQLModel

from app.core.config import Settings
from app.dashboard.context import QueryContext
from app.dashboard.views import render_page
from app.dashboard.workflow_actions import execute_action
from app.dashboard.workflow_forms import action_id, field_id
from app.dashboard.workflow_views import (
    matching_movements,
    movement_detail,
    remaining_evidence,
)
from app.integrations.fixtures import fixture_records
from app.main import create_app
from app.models.hub import HubResponse
from app.models.operations import MovementEventRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'workflow-ui.db'}",
        allow_local_management=True,
        _env_file=None,
    )
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1", client=("127.0.0.1", 50001)
    ) as client:
        SQLModel.metadata.create_all(client.app.state.engine)
        assert client.get("/_dash-layout").status_code == 200
        yield client


def fields():
    equipment, requests = fixture_records()
    request = next(item for item in requests if item.machinery_id)
    machine = next(item for item in equipment if item.id == request.machinery_id)
    return {
        "request_source_id": request.provenance.source_id,
        "machinery_source_id": machine.provenance.source_id,
        "project_source_id": request.project_id,
        "poi_id": "test-destination",
        "assigned_user_ids": "test-user-1, test-user-2",
        "movement_reference": "test-ui-movement",
        "scheduled_date": "2026-09-15",
        "scheduled_time": "09:30",
        "tracked_vehicle_id": "test-vehicle",
    }


def pattern(identifier):
    return json.dumps(identifier, sort_keys=True, separators=(",", ":"))


def action(client, name, values=None, *, movement="", mode="fixture"):
    values = values or {}
    response = client.post(
        "/_dash-update-component",
        json={
            "output": "workflow-action-result.data",
            "outputs": {"id": "workflow-action-result", "property": "data"},
            "inputs": [
                {
                    "id": pattern(
                        {"type": "workflow-action", "action": ["ALL"], "movement": ["ALL"]}
                    ),
                    "property": "n_clicks",
                    "value": [1],
                }
            ],
            "state": [
                {
                    "id": pattern({"type": "workflow-field", "field": ["ALL"]}),
                    "property": "value",
                    "value": list(values.values()),
                },
                {
                    "id": pattern({"type": "workflow-field", "field": ["ALL"]}),
                    "property": "id",
                    "value": [field_id(name) for name in values],
                },
                {"id": "url", "property": "search", "value": f"?mode={mode}"},
                {"id": "url", "property": "pathname", "value": "/operaciones"},
            ],
            "changedPropIds": [pattern(action_id(name, movement)) + ".n_clicks"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["response"]["workflow-action-result"]["data"]


def overview(client, mode="fixture"):
    response = client.post(
        "/_dash-update-component",
        json={
            "output": "workflow-snapshot.data",
            "outputs": {"id": "workflow-snapshot", "property": "data"},
            "inputs": [
                {"id": "url", "property": "search", "value": f"?mode={mode}"},
                {"id": "refresh", "property": "n_clicks", "value": 1},
                {"id": "workflow-action-result", "property": "data", "value": None},
            ],
            "state": [],
            "changedPropIds": ["refresh.n_clicks"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["response"]["workflow-snapshot"]["data"]


def test_save_callback_persists_explicit_plan_and_never_sends_fixture(client):
    result = action(client, "save", fields())
    assert result["ok"], result
    assert "/operaciones/" in result["href"]
    current = overview(client)
    assert current["mode"] == "fixture"
    stored = current["overview"]["movements"]
    assert len(stored) == 1
    assert stored[0]["mode"] == "fixture"
    assert stored[0]["mapping"]["scheduled_time"] == "09:30:00"
    assert stored[0]["mapping"]["assigned_user_ids"] == ["test-user-1", "test-user-2"]
    assert stored[0]["tracked_vehicle_id"] == "test-vehicle"
    assert stored[0]["job_id"] is None and stored[0]["receipt"] is None
    assert not current["overview"]["sending_enabled"]
    rejected = action(client, "queue", movement=stored[0]["id"])
    assert not rejected["ok"]
    assert overview(client)["overview"]["movements"][0]["job_id"] is None


@pytest.mark.parametrize(
    "headers",
    [
        {"origin": "https://unrelated.example"},
        {"sec-fetch-site": "cross-site"},
    ],
)
def test_browser_inputs_do_not_grant_local_management(client, headers):
    # Cross-origin callbacks are refused before Dash runs them.
    response = client.post("/_dash-update-component", headers=headers, json={})
    assert response.status_code == 403
    assert overview(client)["overview"]["movements"] == []


def test_server_disable_is_enforced_on_action_after_form_was_loaded(client):
    assert overview(client)["overview"]["management_enabled"]
    client.app.state.settings.allow_local_management = False
    result = action(client, "save", fields())
    assert not result["ok"]
    assert overview(client)["overview"]["movements"] == []


def test_action_errors_never_return_internal_exception_text(client):
    with patch.object(
        client.app.state.workflow, "save_plan", side_effect=RuntimeError("test-private-password")
    ):
        result = action(client, "save", fields())
    assert not result["ok"]
    assert "test-private-password" not in json.dumps(result)


def test_fixture_arrival_and_receipt_cannot_be_created_from_ui(client):
    assert action(client, "save", fields())["ok"]
    movement = overview(client)["overview"]["movements"][0]
    result = action(
        client,
        "receipt",
        {
            "receiver": "Persona de prueba",
            "received_date": "2026-09-15",
            "received_time": "10:00",
            "reference": "test-receipt",
            "note": "",
        },
        movement=movement["id"],
    )
    assert not result["ok"]
    stored = overview(client)["overview"]["movements"][0]
    assert stored["receipt"] is None
    assert not any(event["kind"] in {"arrival", "receipt"} for event in stored["events"])


def test_receipt_input_uses_explicit_el_salvador_time():
    service = Mock()
    _, _ = execute_action(
        service,
        "receipt",
        "live",
        {
            "receiver": "Persona de prueba",
            "received_date": "2026-09-15",
            "received_time": "10:35",
            "reference": "test-evidence",
            "note": "",
        },
        "test-movement",
    )
    received_at = service.record_receipt.call_args.args[3]
    assert received_at.isoformat() == "2026-09-15T10:35:00-06:00"
    assert received_at.utcoffset() == timedelta(hours=-6)
    service.reset_mock()
    with pytest.raises(ValueError):
        execute_action(
            service,
            "receipt",
            "live",
            {
                "receiver": "Persona de prueba",
                "received_date": "20260915",
                "received_time": "10:35",
                "reference": "test-evidence",
            },
            "test-movement",
        )
    service.record_receipt.assert_not_called()


def test_task_completion_and_arrival_stay_distinct_from_receipt(client):
    assert action(client, "save", fields())["ok"]
    record = WorkflowOverview.model_validate(overview(client)["overview"]).movements[0]
    event = MovementEventRecord(
        id="test-arrival",
        kind="arrival",
        source_id="test-visit",
        event_time=datetime(2026, 9, 15, 16, tzinfo=UTC),
        observed_at=datetime(2026, 9, 15, 17, tzinfo=UTC),
        recorded_at=datetime(2026, 9, 15, 17, tzinfo=UTC),
        data={},
    )
    record = record.model_copy(
        update={
            "mode": "live",
            "state": "sent",
            "job_id": "test-job",
            "status": "COMPLETADA",
            "events": [event],
        }
    )
    current = WorkflowOverview(available=True, message="Registro de prueba", movements=[record])
    rendered = json.dumps(
        movement_detail(current, QueryContext(mode="live"), record.id),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "COMPLETADA" in rendered and "Llegada observada" in rendered
    assert "Sin constancia de recepción" in rendered
    assert remaining_evidence(
        ["Traslado vinculado", "Evidencia de llegada", "Recepción física"], [record]
    ) == ["Recepción física"]
    _, requests = fixture_records()
    request = next(
        item for item in requests if item.provenance.source_id == record.request_source_id
    )
    assert matching_movements(current, request) == [record]
    changed = record.model_copy(update={"source_request": {"id": "test-other-request"}})
    current.movements = [changed]
    assert matching_movements(current, request) == []


def test_saved_evidence_replaces_missing_text_in_primary_request_views(client):
    assert action(client, "save", fields())["ok"]
    current = WorkflowOverview.model_validate(overview(client)["overview"])
    record = current.movements[0]
    instant = datetime(2026, 9, 15, 17, tzinfo=UTC)
    record.job_id = "test-observed-job"
    record.state = "sent"
    record.status = "COMPLETADA"
    record.events.append(
        MovementEventRecord(
            id="test-arrival",
            kind="arrival",
            source_id="test-visit",
            event_time=instant,
            observed_at=instant,
            recorded_at=instant,
            data={},
        )
    )
    record.receipt = ReceiptRecord(
        receiver="Persona de prueba",
        received_at=instant,
        reference="test-receipt",
        recorded_at=instant,
    )
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    hub.requests = [
        item for item in hub.requests if item.provenance.source_id == record.request_source_id
    ]
    context = QueryContext()
    for path in ["/solicitudes", f"/solicitudes/{hub.requests[0].id}"]:
        content = json.dumps(
            render_page(path, hub, context, current), cls=PlotlyJSONEncoder, ensure_ascii=False
        )
        assert "COMPLETADA" in content and "Llegada observada" in content
        assert "Recibida" in content
        assert "Sin traslado vinculado" not in content
        assert "Sin constancia" not in content
        assert "Sin evidencia de llegada" not in content
    filtered = json.dumps(
        render_page("/solicitudes", hub, QueryContext(filter="unlinked"), current),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "Sin solicitudes en esta consulta" in filtered
    hub.requests[0].machinery_id = "test-new-assignment"
    updated_grid = json.dumps(
        render_page("/solicitudes", hub, context, current),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "Sin constancia" in updated_grid
    assert "COMPLETADA" not in updated_grid and "Recibida" not in updated_grid
    updated_detail = json.dumps(
        render_page(f"/solicitudes/{hub.requests[0].id}", hub, context, current),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "no coinciden con la asignación actual" in updated_detail
    assert "Recibida" in updated_detail  # The historical movement remains inspectable.
