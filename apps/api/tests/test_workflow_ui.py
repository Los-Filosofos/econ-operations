"""Exercise the Dash action boundary and evidence semantics through real callbacks."""

import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder
from sqlmodel import SQLModel

from app.core.config import Settings
from app.dashboard.context import QueryContext
from app.dashboard.views import render_page
from app.dashboard.workflow_actions import execute_action
from app.dashboard.workflow_forms import action_id, field_id, resolve_id
from app.dashboard.workflow_views import (
    PAGE_ID,
    SIZE_ID,
    TABLE_ID,
    WINDOW_ID,
    events_panel,
    matching_movements,
    movement_detail,
    movement_id,
    operations,
    register_workflow_callbacks,
    remaining_evidence,
)
from app.integrations.fixtures import fixture_records
from app.main import create_app
from app.models.hub import EquipmentRecord, HubResponse, Provenance, RequestRecord
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview
from app.services.transfers import TransferMapping


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


def test_dash_save_in_development_records_the_local_developer_not_a_user(client):
    assert action(client, "save", fields())["ok"]
    (stored,) = client.app.state.workflow.ledger.list("fixture")
    (created,) = stored.events
    assert created.kind == "created"
    # Anonymous loopback callback with AUTH_REQUIRED=false: the kind is recorded, no user.
    assert created.actor_kind == "local_dev"
    assert created.actor_user_id is None and created.actor_role is None
    # The form does not collect the device kind, so it stays undeclared.
    assert stored.tracked_vehicle_id == "test-vehicle" and stored.tracked_vehicle_kind is None


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
    received_at = service.record_receipt.call_args.kwargs["received_at"]
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


# --- Pagination, timeline slicing, out-of-page fetch and explicit resolution ---------------


def registered(client):
    """Callbacks the application wires once; registering again is a no-op."""
    register_workflow_callbacks(client.app.state.dashboard, client.app)
    register_workflow_callbacks(client.app.state.dashboard, client.app)
    return client.app.state.dashboard.callback_map


def callback_key(client, needle: str) -> str:
    return next(key for key in registered(client) if needle in key)


def fixture_plans(client, count: int) -> list[str]:
    """Persist `count` fixture plans straight into the ledger; newest first when listed."""
    equipment, requests = fixture_records()
    request = next(item for item in requests if item.machinery_id)
    machine = next(item for item in equipment if item.id == request.machinery_id)
    ledger = client.app.state.workflow.ledger
    identifiers = []
    for index in range(count):
        mapping = TransferMapping(
            request_source_id=request.provenance.source_id,
            machinery_source_id=machine.provenance.source_id,
            project_source_id=request.project_id,
            poi_id="test-destination",
            assigned_user_ids=("test-user",),
            movement_reference=f"test-page-{index:03d}",
            scheduled_date=date(2026, 9, 15),
        )
        identifiers.append(ledger.create("fixture", request, machine, mapping).id)
    return identifiers


def dispatch(client, key, outputs, inputs, state, changed):
    """Post one callback the way the renderer does: a single pattern output is a flat list
    of resolved ids; a multi-output is a list with one entry (dict or list) per output."""
    response = client.post(
        "/_dash-update-component",
        json={
            "output": key,
            "outputs": outputs,
            "inputs": inputs,
            "state": state,
            "changedPropIds": [changed],
        },
    )
    assert response.status_code in {200, 204}, response.text
    # Dash answers an all-no_update callback with an empty response: nothing changed.
    return (response.json()["response"] or None) if response.status_code == 200 else None


def page_request(client, page, size, previous, search="?mode=fixture"):
    return dispatch(
        client,
        callback_key(client, "operations-table"),
        [
            [{"id": TABLE_ID, "property": "children"}],
            [{"id": PAGE_ID, "property": "total"}],
            [{"id": PAGE_ID, "property": "value"}],
            [{"id": WINDOW_ID, "property": "data"}],
        ],
        [
            [{"id": PAGE_ID, "property": "value", "value": page}],
            [{"id": SIZE_ID, "property": "value", "value": size}],
        ],
        [
            [{"id": WINDOW_ID, "property": "data", "value": previous}],
            {"id": "url", "property": "search", "value": search},
        ],
        pattern(PAGE_ID if previous.get("size") == int(size) else SIZE_ID) + ".value",
    )


def test_operations_are_paginated_in_pages_of_fifty_from_the_ledger(client):
    identifiers = fixture_plans(client, 101)
    workflow = WorkflowOverview.model_validate(overview(client)["overview"])
    assert workflow.total == 101 and workflow.page_size == 100 and not workflow.complete
    page = json.dumps(
        operations(workflow, QueryContext()), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "Movimientos 1–50 de 101 · página 1 de 3." in page
    assert "Registro paginado" in page and "Movimientos por página" in page
    assert page.count('"reference": "[test') == 50
    assert '"pagination": false' in page
    # Page 3 of 50 holds the single remaining (oldest) movement.
    third = page_request(client, 3, "50", {"page": 1, "size": 50})
    table = json.dumps(third[pattern(TABLE_ID)]["children"], ensure_ascii=False)
    assert "Movimientos 101–101 de 101 · página 3 de 3." in table
    assert identifiers[0] in table and identifiers[1] not in table
    assert third[pattern(PAGE_ID)] == {"total": 3, "value": 3}
    assert third[pattern(WINDOW_ID)]["data"] == {"page": 3, "size": 50}
    # A new page size starts again at page 1 and recomputes the number of pages.
    resized = page_request(client, 3, "100", {"page": 3, "size": 50})
    assert resized[pattern(PAGE_ID)] == {"total": 2, "value": 1}
    assert "Movimientos 1–100 de 101 · página 1 de 2." in json.dumps(
        resized[pattern(TABLE_ID)]["children"], ensure_ascii=False
    )
    # The echo that fires when the controls mount reads nothing.
    assert page_request(client, 1, "50", {"page": 1, "size": 50}) is None
    # The search only filters the loaded page and says so.
    filtered = page_request(client, 2, "50", {"page": 1, "size": 50}, "?mode=fixture&q=page-05")
    filtered_table = json.dumps(filtered[pattern(TABLE_ID)]["children"], ensure_ascii=False)
    assert "coincidencia(s) con «page-05» en esta página" in filtered_table
    assert "La búsqueda no consulta otras páginas" in filtered_table


def test_a_movement_beyond_the_first_page_is_fetched_by_id(client):
    oldest = fixture_plans(client, 101)[0]
    workflow = WorkflowOverview.model_validate(overview(client)["overview"])
    assert all(item.id != oldest for item in workflow.movements)
    placeholder = json.dumps(
        movement_detail(workflow, QueryContext(), oldest), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "fuera de la primera página" in placeholder and "movement-fetch" in placeholder
    fetched = dispatch(
        client,
        callback_key(client, "movement-detail"),
        [{"id": movement_id("detail", oldest), "property": "children"}],
        [[{"id": movement_id("fetch", oldest), "property": "data", "value": "fixture"}]],
        [{"id": "url", "property": "search", "value": "?mode=fixture"}],
        pattern(movement_id("fetch", oldest)) + ".data",
    )
    detail = json.dumps(fetched[pattern(movement_id("detail", oldest))], ensure_ascii=False)
    assert "test-page-000" in detail and "Evidencia y acciones de este traslado" in detail
    assert "movement-fetch" not in detail
    missing = dispatch(
        client,
        callback_key(client, "movement-detail"),
        [{"id": movement_id("detail", "test-missing"), "property": "children"}],
        [[{"id": movement_id("fetch", "test-missing"), "property": "data", "value": "fixture"}]],
        [{"id": "url", "property": "search", "value": "?mode=fixture"}],
        pattern(movement_id("fetch", "test-missing")) + ".data",
    )
    assert missing is None


def live_unknown_movement(app, reference="test-unknown") -> MovementRecord:
    """A synthetic live movement whose creation outcome is uncertain, without providers."""
    observed = datetime(2026, 9, 12, tzinfo=UTC)

    def provenance(source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=observed,
            evidence_kind="live_read",
            is_synthetic=True,
        )

    equipment = EquipmentRecord(
        id="test:equipment:unknown-1",
        code="TEST-UNK-01",
        name="Unidad de prueba",
        project_id="test-project",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test inputs only.",
        provenance=provenance("test-unit-unknown-1"),
    )
    request = RequestRecord(
        id="test:request:unknown-1",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=provenance("test-request-unknown-1"),
    )
    mapping = TransferMapping(
        request_source_id="test-request-unknown-1",
        machinery_source_id="test-unit-unknown-1",
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference=reference,
        scheduled_date=date(2026, 9, 14),
    )
    ledger = app.state.workflow.ledger
    row = ledger.create("live", request, equipment, mapping)
    ledger.queue(row.id)
    ledger.claim(row.id)
    return ledger.finish_unknown(row.id, "ambiguous_response")


def resolve_request(client, movement, step, reason="operator_resolved"):
    return dispatch(
        client,
        callback_key(client, "workflow-resolve"),
        [
            [{"id": resolve_id("modal", movement), "property": "opened"}],
            {"id": "workflow-action-result", "property": "data"},
        ],
        [
            [{"id": resolve_id("open", movement), "property": "n_clicks", "value": 1}],
            [{"id": resolve_id("cancel", movement), "property": "n_clicks", "value": 0}],
            [{"id": resolve_id("confirm", movement), "property": "n_clicks", "value": 1}],
        ],
        [
            [{"id": resolve_id("reason", movement), "property": "value", "value": reason}],
            {"id": "url", "property": "search", "value": "?mode=live"},
            {"id": "url", "property": "pathname", "value": f"/operaciones/{movement}"},
        ],
        pattern(resolve_id(step, movement)) + ".n_clicks",
    )


def test_resolution_is_offered_only_to_a_role_that_manages_transfers():
    unknown = live_record(state="unknown")
    workflow = WorkflowOverview(
        available=True,
        complete=True,
        message="Registro",
        management_enabled=True,
        movements=[unknown],
    )
    context = QueryContext(mode="live")
    offered = json.dumps(
        movement_detail(workflow, context, unknown.id), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "Resolver como fallido" in offered and "Confirmar cierre como fallido" in offered
    assert "operator_resolved" in offered and "Motivo del cierre" in offered
    assert "Tu rol no permite esta acción" not in offered
    with patch("app.dashboard.workflow_views.permitted", return_value=False):
        refused = json.dumps(
            movement_detail(workflow, context, unknown.id),
            cls=PlotlyJSONEncoder,
            ensure_ascii=False,
        )
    assert "Resolver como fallido" not in refused
    assert "Tu rol no permite esta acción" in refused
    sent = unknown.model_copy(update={"state": "sent", "job_id": "test-job"})
    workflow.movements = [sent]
    assert "Resolver como fallido" not in json.dumps(
        movement_detail(workflow, context, sent.id), cls=PlotlyJSONEncoder, ensure_ascii=False
    )


def test_resolve_callback_closes_an_unknown_movement_with_a_permitted_code(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'resolve-ui.db'}",
        allow_local_management=True,
        allow_live_reads=True,
        _env_file=None,
    )
    with TestClient(
        create_app(settings), base_url="http://127.0.0.1", client=("127.0.0.1", 50001)
    ) as client:
        SQLModel.metadata.create_all(client.app.state.engine)
        assert client.get("/_dash-layout").status_code == 200
        unknown = live_unknown_movement(client.app)
        ledger = client.app.state.workflow.ledger
        assert resolve_request(client, unknown.id, "open") == {
            pattern(resolve_id("modal", unknown.id)): {"opened": True}
        }
        assert resolve_request(client, unknown.id, "cancel") == {
            pattern(resolve_id("modal", unknown.id)): {"opened": False}
        }
        refused = resolve_request(client, unknown.id, "confirm", reason="free text")
        assert refused["workflow-action-result"]["data"]["ok"] is False
        assert "motivo permitido" in refused["workflow-action-result"]["data"]["message"]
        assert ledger.get(unknown.id, "live").state == "unknown"
        resolved = resolve_request(client, unknown.id, "confirm")
        assert resolved[pattern(resolve_id("modal", unknown.id))] == {"opened": False}
        result = resolved["workflow-action-result"]["data"]
        assert result["ok"] is True and result["path"] == f"/operaciones/{unknown.id}"
        assert "cerrado como fallido" in result["message"] and unknown.id in result["href"]
        stored = ledger.get(unknown.id, "live")
        assert stored.state == "failed" and stored.reason_code == "operator_resolved"
        resolution = stored.events[-1]
        assert resolution.kind == "resolved" and resolution.actor_kind == "local_dev"
        assert resolution.actor_user_id is None
        again = resolve_request(client, unknown.id, "confirm")
        assert again["workflow-action-result"]["data"]["ok"] is False
        assert "private" not in json.dumps(again)
        detail = json.dumps(
            movement_detail(
                client.app.state.workflow.read("live"), QueryContext(mode="live"), unknown.id
            ),
            cls=PlotlyJSONEncoder,
            ensure_ascii=False,
        )
        assert "Cerrado como fallido por el operador" in detail
        assert "Motivo operator_resolved: Comprobado a mano" in detail
        assert "registrado por desarrollo local sin sesión" in detail


def live_record(*, state="unknown") -> MovementRecord:
    _, requests = fixture_records()
    request = next(item for item in requests if item.machinery_id)
    return MovementRecord(
        id="test-live-record",
        mode="live",
        environment="sandbox",
        movement_reference="Movimiento live de prueba",
        request_source_id=request.provenance.source_id,
        machinery_source_id="test-unit",
        project_source_id=request.project_id or "test-project",
        mapping={"scheduled_date": "2026-09-15"},
        source_request=request.model_dump(mode="json"),
        source_equipment=None,
        source_request_hash="test-hash",
        source_equipment_hash=None,
        payload={"objective": "test"},
        preparation={},
        state=state,
        created_at=datetime(2026, 9, 12, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
        events=[],
    )


def event(identifier, kind, when, **fields) -> MovementEventRecord:
    return MovementEventRecord(
        id=identifier,
        kind=kind,
        event_time=when,
        observed_at=when,
        recorded_at=when,
        data={},
        **fields,
    )


def test_timeline_names_who_recorded_and_who_declared_each_fact():
    when = datetime(2026, 9, 15, 17, tzinfo=UTC)
    record = live_record(state="sent")
    record.job_id = "test-job"
    record.events = [
        event("test-created", "created", when, actor_kind="session", actor_user_id="7"),
        event("test-task", "task_state", when, actor_kind="cli_worker"),
        event("test-receipt", "receipt", when, actor_kind="session", actor_user_id="9"),
        event("test-unknown-actor", "arrival", when),
    ]
    record.receipt = ReceiptRecord(
        receiver="Persona que recibe",
        received_at=when,
        reference="test-receipt",
        recorded_at=when,
        declared_by_user_id="9",
        declared_by_email="gerencia@example.com",
        declared_by_role="gerencia_proyecto",
    )
    record.events[0].actor_role = "logistica"
    record.events[2].actor_role = "gerencia_proyecto"
    workflow = WorkflowOverview(
        available=True, complete=True, message="Registro", movements=[record]
    )
    detail = json.dumps(
        movement_detail(workflow, QueryContext(mode="live"), record.id),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "registrado por usuario 7 · Logística y Equipo" in detail
    assert "registrado por el worker de sincronización" in detail
    assert "declarado por gerencia@example.com · Gerencia de Proyecto" in detail
    assert "Declarada por" in detail and "actor no registrado" in detail
    assert "Persona que recibe" in detail  # The declared receiver stays a separate fact.


def test_long_timelines_are_sliced_in_pages_of_fifty(client):
    base = datetime(2026, 9, 1, tzinfo=UTC)
    record = live_record(state="sent")
    record.mode = "fixture"
    record.events = [
        event(f"test-event-{index:03d}", "task_state", base + timedelta(minutes=index))
        for index in range(120)
    ]
    workflow = WorkflowOverview(
        available=True, complete=True, message="Registro", movements=[record]
    )
    detail = json.dumps(
        movement_detail(workflow, QueryContext(), record.id),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "Eventos 1–50 de 120 · página 1 de 3." in detail
    # Event 49 is recorded at 18:49 El Salvador; event 50 (18:50) belongs to the next page.
    assert "18:49" in detail and "18:50" not in detail
    assert '"total": 3' in detail and "Páginas del historial del movimiento" in detail
    last = json.dumps(events_panel(record, 3), cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert "Eventos 101–120 de 120 · página 3 de 3." in last and "19:59" in last
    sliced = dispatch(
        client,
        callback_key(client, "movement-events"),
        [{"id": movement_id("events", record.id), "property": "children"}],
        [[{"id": movement_id("events-page", record.id), "property": "value", "value": 2}]],
        [
            {
                "id": "workflow-snapshot",
                "property": "data",
                "value": {"mode": "fixture", "overview": workflow.model_dump(mode="json")},
            },
            {"id": "url", "property": "search", "value": "?mode=fixture"},
        ],
        pattern(movement_id("events-page", record.id)) + ".value",
    )
    page = json.dumps(sliced[pattern(movement_id("events", record.id))], ensure_ascii=False)
    assert "Eventos 51–100 de 120 · página 2 de 3." in page and "19:39" in page
    short = live_record()
    short.events = record.events[:50]
    assert "Páginas del historial" not in json.dumps(
        movement_detail(
            WorkflowOverview(available=True, complete=True, message="Registro", movements=[short]),
            QueryContext(mode="live"),
            short.id,
        ),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )


def test_operations_and_movement_show_a_skeleton_while_the_ledger_loads():
    for content in (operations(None, QueryContext()), movement_detail(None, QueryContext(), "x")):
        rendered = json.dumps(content, cls=PlotlyJSONEncoder, ensure_ascii=False)
        assert "Consultando la operación…" in rendered and "Skeleton" in rendered
        assert '"role": "status"' in rendered
