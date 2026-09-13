"""Isolated ledger inputs exercise joins; no operational samples or providers are changed."""

import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.fixtures import SAMPLE_PATH
from app.integrations.nexus import NexusEquipment, NexusReadError, NexusRequest, NexusSnapshot
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.main import create_app
from app.models import metadata
from app.models.hub import Provenance
from app.services.evidence import matching_current_movements, project_operation_evidence
from app.services.hub import read_hub
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)
EVENT_TIME = OBSERVED - timedelta(hours=1)


def snapshot():
    return NexusSnapshot(
        equipment=[
            NexusEquipment(
                id="projection-test-unit",
                clave="projection-test-code",
                no_activo="projection-test-asset",
                nombre="Unidad de prueba aislada",
                estado="OCUPADA",
                active_failure_is_paro=False,
            )
        ],
        requests=[
            NexusRequest(
                id="projection-test-request",
                status="APROBADA",
                project_id="projection-test-project",
                project_name="Proyecto de prueba aislada",
                maquinaria_id="projection-test-unit",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                approved_at="2026-09-11T15:00:00Z",
                approved_by_user_id="projection-test-approver",
            )
        ],
        equipment_total=1,
        requests_total=1,
        complete=True,
    )


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'projection.db'}",
        allow_live_reads=True,
        _env_file=None,
    )
    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    connector = Mock(configured=True)
    connector.read.return_value = snapshot()
    yield settings, engine, connector, OperationsLedger(engine)
    engine.dispose()


def sent(store, reference="projection-test-movement"):
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
            poi_id="projection-test-poi",
            assigned_user_ids=("projection-test-driver",),
            movement_reference=reference,
            scheduled_date=date(2026, 9, 12),
        ),
        tracked_vehicle_id="projection-test-vehicle",
    )
    ledger.queue(movement.id)
    ledger.claim(movement.id)
    return ledger.finish_sent(
        movement.id, f"job-{reference}", status="status-pending", workflow_role="pending"
    )


def observe(store, movement, *, kind="task_state", event_time=EVENT_TIME, **values):
    source_id = movement.job_id if kind == "task_state" else "projection-test-visit"
    data = {"job_id": movement.job_id, **values}
    if kind == "arrival":
        data.update(poi_id="projection-test-poi", tracked_asset_id="projection-test-vehicle")
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


def test_projection_preserves_multiple_tasks_latest_source_times_and_separate_receipt(store):
    settings, engine, connector, ledger = store
    first = sent(store)
    second = sent(store, reference="projection-test-second")
    observe(
        store, first, status="provider-closed-7", workflow_role="completed", objective="Entrega"
    )
    # Late ingestion of an older event must not replace the newer source state.
    observe(
        store,
        first,
        event_time=EVENT_TIME - timedelta(hours=1),
        status="provider-pending-1",
        workflow_role="pending",
    )
    observe(store, first, kind="arrival", latitude=13.7, longitude=-89.2)
    ledger.record_receipt(
        first.id,
        "live",
        receiver="Responsable de prueba",
        received_at=OBSERVED,
        reference="constancia-prueba",
    )
    hub = read_hub(settings, connector, "live", engine=engine)
    equipment = hub.equipment[0]
    assert equipment.relation_status == "confirmed"
    assert equipment.machinery_status == "OCUPADA"
    assert equipment.maintenance_is_stopped is False
    assert equipment.location is None
    assert len(equipment.transfers) == 2
    task = next(item for item in equipment.transfers if item.movement_id == first.id)
    assert task.id == f"startrack:job:{first.job_id}"
    assert task.status == "provider-closed-7"
    assert task.workflow_role == "completed"
    assert task.event_time == EVENT_TIME
    assert task.provenance.observed_at == OBSERVED
    assert task.provenance.source_id == first.job_id
    assert task.recorded_at is not None
    assert task.source_data["objective"] == "Entrega"
    assert task.evidence_current_assignment is True
    assert task.evidence_origin == "task_observation"
    assert task.request_id == hub.requests[0].id
    assert task.destination_project_id == hub.requests[0].project_id
    assert hub.operation_evidence.status == "available"
    assert hub.operation_evidence.complete is True
    assert hub.operation_evidence.movements_returned == 2
    assert hub.sources[1].status == "not_configured"
    assert hub.sources[1].last_evidence_at == OBSERVED
    assert hub.sources[1].observed_at is None
    assert hub.scope.complete is False
    assert ledger.get(first.id, "live").receipt.reference == "constancia-prueba"
    assert ledger.get(second.id, "live").receipt is None
    assert "receipt" not in task.model_dump()


def test_creation_acknowledgment_is_not_a_fresh_task_read_or_location(store):
    settings, engine, connector, _ = store
    movement = sent(store)
    observe(store, movement, kind="arrival", latitude=13.7, longitude=-89.2)
    hub = read_hub(settings, connector, "live", engine=engine)
    task = hub.equipment[0].transfers[0]
    assert task.status == "status-pending"
    assert task.event_time is None
    assert task.provenance.observed_at == movement.sent_at
    assert task.recorded_at == movement.sent_at
    assert task.evidence_origin == "creation_acknowledgment"
    assert task.source_data == {}
    assert hub.equipment[0].location is None
    assert store[3].get(movement.id, "live").receipt is None


def test_confirmed_pending_workflow_role_evaluates_raw_status_id_without_collapsing_states(store):
    settings, engine, connector, _ = store
    movement = sent(store)
    observe(store, movement, status="provider-status-42", workflow_role="pending")
    source = snapshot()
    source.equipment[0].active_failure_id = "projection-test-failure"
    source.equipment[0].active_failure_is_paro = True
    connector.read.return_value = source
    hub = read_hub(settings, connector, "live", engine=engine)
    assert hub.equipment[0].transfers[0].status == "provider-status-42"
    alert = next(item for item in hub.alerts if item.code == "maintenance_blocks_transfer")
    assert alert.title.startswith("projection-test-asset:")
    assert "workflow_role=pending" in alert.evidence
    observe(
        store,
        movement,
        event_time=EVENT_TIME + timedelta(minutes=1),
        status="provider-status-77",
        workflow_role="completed",
    )
    completed = read_hub(settings, connector, "live", engine=engine)
    assert "maintenance_blocks_transfer" not in [item.code for item in completed.alerts]
    assert completed.equipment[0].machinery_status == "OCUPADA"


@pytest.mark.parametrize(
    "field,value",
    [
        ("machinery_id", "different-equipment"),
        ("project_id", "different-project"),
        ("starts_on", "2026-09-13"),
        ("ends_on", "2026-09-16"),
        ("approved_at", OBSERVED),
    ],
)
def test_old_assignment_or_period_never_becomes_current_evidence(store, field, value):
    settings, engine, connector, _ = store
    movement = sent(store)
    hub = read_hub(settings, connector, "live")
    setattr(hub.requests[0], field, value)
    assert matching_current_movements(hub, hub.requests[0], [movement]) == []
    project_operation_evidence(hub, engine)
    assert hub.equipment[0].transfers == []
    assert hub.equipment[0].relation_status == "unlinked"
    assert store[3].get(movement.id, "live").job_id == movement.job_id


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("request", "source", "startrack"),
        ("request", "source_id", "same-name-different-id"),
        ("request", "environment", "local"),
        ("request", "evidence_kind", "provided_sample"),
        ("equipment", "source_id", "same-code-different-id"),
        ("equipment", "environment", "local"),
        ("equipment", "is_synthetic", False),
    ],
)
def test_names_never_override_incompatible_source_identities(store, target, field, value):
    settings, _, connector, _ = store
    movement = sent(store)
    hub = read_hub(settings, connector, "live")
    record = hub.requests[0] if target == "request" else hub.equipment[0]
    setattr(record.provenance, field, value)
    assert matching_current_movements(hub, hub.requests[0], [movement]) == []


def test_historical_movement_without_current_equipment_record_does_not_confirm_assignment(store):
    settings, _, connector, _ = store
    movement = sent(store)
    hub = read_hub(settings, connector, "live")
    hub.equipment.clear()
    assert matching_current_movements(hub, hub.requests[0], [movement]) == []


def test_mode_isolation_and_server_disabled_reads_never_query_live_evidence(store):
    settings, engine, connector, ledger = store
    sent(store)
    fixture = read_hub(settings, connector, "fixture", engine=engine)
    assert fixture.operation_evidence.movements_returned == 0
    assert all(not item.transfers for item in fixture.equipment)
    assert ledger.list("live")
    settings.allow_live_reads = False
    with patch.object(OperationsLedger, "list") as query:
        disabled = read_hub(settings, connector, "live", engine=engine)
    query.assert_not_called()
    assert disabled.operation_evidence.status == "disabled"
    assert disabled.sources[1].status == "disabled"
    assert disabled.equipment == disabled.requests == []


def test_failed_source_read_does_not_reuse_equipment_but_retains_dated_evidence_status(store):
    settings, engine, connector, _ = store
    movement = sent(store)
    observe(store, movement, status="provider-pending-1", workflow_role="pending")
    connector.read.side_effect = NexusReadError("Fuente no disponible")
    hub = read_hub(settings, connector, "live", engine=engine)
    assert hub.equipment == hub.requests == []
    assert hub.sources[0].status == "error"
    assert hub.sources[1].last_evidence_at == OBSERVED
    assert hub.sources[1].observed_at is None
    assert hub.data_as_of is None
    assert hub.summary.equipment_count is None


def test_database_error_is_explicit_and_does_not_hide_readable_source_records(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'no-schema.db'}", _env_file=None)
    engine = build_engine(settings.database_url)
    try:
        hub = read_hub(settings, Mock(), "fixture", engine=engine)
    finally:
        engine.dispose()
    assert hub.operation_evidence.status == "error"
    assert hub.operation_evidence.movements_returned is None
    assert "no-schema" not in hub.operation_evidence.message
    assert "SELECT" not in hub.operation_evidence.message
    assert len(hub.requests) == 2
    assert hub.summary.equipment_count == 5


@pytest.mark.parametrize("enabled,expected", [(True, "not_queried"), (False, "disabled")])
def test_configured_sdk_reports_gates_without_claiming_connectivity_or_making_calls(
    store, enabled, expected
):
    settings, engine, connector, _ = store
    client = StartrackClient(
        StartrackReadConfig(enabled=enabled, api_key="isolated-key", password="isolated-password")
    )
    try:
        with patch.object(client, "list_jobs") as jobs, patch.object(client, "get_job") as get:
            hub = read_hub(settings, connector, "live", engine=engine, startrack=client)
        jobs.assert_not_called()
        get.assert_not_called()
    finally:
        client.close()
    assert hub.sources[1].configured is True
    assert hub.sources[1].status == expected
    assert hub.sources[1].observed_at is None
    assert "isolated-key" not in hub.model_dump_json()
    assert "isolated-password" not in hub.model_dump_json()


def test_bounded_operation_window_reports_unknown_coverage(store):
    settings, engine, connector, _ = store
    # Use independent in-memory records to prove truncation without creating runtime fixtures.
    movement = sent(store)
    with patch.object(OperationsLedger, "list", return_value=[movement] * 101) as query:
        hub = read_hub(settings, connector, "live", engine=engine)
    query.assert_called_once_with("live", limit=101)
    assert hub.operation_evidence.status == "partial"
    assert hub.operation_evidence.complete is False
    assert hub.operation_evidence.movements_returned == 100


def test_approval_actor_survives_fixture_live_snapshot_and_public_api(store):
    settings, engine, connector, ledger = store
    supplied = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    fixture = read_hub(settings, connector, "fixture", engine=engine)
    for actual, source in zip(fixture.requests, supplied["requests"]["items"], strict=True):
        assert actual.approved_by_user_id == source["approved_by_user_id"]
    fixture_snapshot = ledger.record_snapshot(fixture)
    assert fixture_snapshot.content["requests"][1]["approved_by_user_id"]
    movement = sent(store)
    assert movement.source_request["approved_by_user_id"] == "projection-test-approver"
    with TestClient(create_app(settings)) as client:
        with (
            patch.object(client.app.state.nexus, "read", return_value=snapshot()),
            patch("app.integrations.nexus.NexusConnector.configured", True),
        ):
            response = client.get("/api/v1/hub?mode=live")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["requests"][0]["approved_by_user_id"] == "projection-test-approver"
    assert data["equipment"][0]["transfers"][0]["movement_id"] == movement.id
    assert data["operation_evidence"]["status"] == "available"
    live = read_hub(settings, connector, "live", engine=engine)
    persisted = ledger.record_snapshot(live)
    assert persisted.content["requests"][0]["approved_by_user_id"] == "projection-test-approver"
