"""Provider workflow checks use real adapters and an isolated durable ledger."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from app.core.access import management_scope
from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.models import metadata
from app.services.hub import BUSINESS_TIMEZONE
from app.services.transfers import TransferMapping
from app.services.workflow import WorkflowError, WorkflowService

REQUEST_ID = "10000000-0000-4000-8000-000000000001"
EQUIPMENT_ID = "20000000-0000-4000-8000-000000000001"
PROJECT_ID = "30000000-0000-4000-8000-000000000001"


@pytest.fixture
def workflow(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'provider-workflow.db'}",
        allow_live_reads=True,
        allow_live_writes=True,
        allow_local_management=True,
        nexus_email="workflow@example.test",
        nexus_password="test-only-password",
        _env_file=None,
    )
    state = {
        "request": {
            "id": REQUEST_ID,
            "project_id": PROJECT_ID,
            "status": "APROBADA",
            "maquinaria_id": EQUIPMENT_ID,
            "fecha_inicio": "2026-09-01",
        },
        "equipment": {
            "id": EQUIPMENT_ID,
            "clave": "TEST-UNIT",
            "nombre": "Unidad de prueba",
            "estado": "OCUPADA",
            "project_id": PROJECT_ID,
            "active_failure_is_paro": False,
        },
        "jobs": [],
        "visits": [],
        "create_response": "acknowledged",
        "vehicle_deactivated": "0",
        "posts": 0,
        "calls": [],
    }

    def nexus_handler(request):
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"success": True},
                headers={"Set-Cookie": "auth-token=test-only; Path=/; Secure; HttpOnly"},
            )
        assert request.url.host == "econ-key.maic.ai"
        key = "request" if "/requests/" in request.url.path else "equipment"
        return httpx.Response(200, json=state[key])

    def startrack_handler(request):
        state["calls"].append((request.method, request.url.path))
        assert request.url.host == "staging.gps.gt"
        if request.method == "POST":
            assert request.url.path == "/api/job"
            state["posts"] += 1
            response = state["create_response"]
            if response == "timeout":
                raise httpx.ReadTimeout("test-only-password", request=request)
            if response == "rejected":
                return httpx.Response(422, text="test-only-password")
            data = {"id": "700"}
            if response in {"acknowledged", "contradictory"}:
                data |= {
                    "objective": state["payload"]["objective"],
                    "start_date": state["payload"]["start_date"],
                }
            if response == "contradictory":
                data["poi_id"] = "another-destination"
            return httpx.Response(200, json={"success": True, "data": data})
        path = request.url.path
        if path == "/api/pois":
            data = [{"id": "100", "name": "Destino de prueba"}]
        elif path == "/api/user":
            data = [{"id": "200", "name": "Usuario de prueba"}]
        elif path == "/api/vehicles":
            data = [
                {
                    "id": "300",
                    "description": "Transportador de prueba",
                    "deactivated": state["vehicle_deactivated"],
                }
            ]
        elif path == "/api/job/type":
            data = [{"id": "400", "name": "Traslado"}]
        elif path == "/api/job":
            data = state["jobs"]
        elif path == "/api/visits":
            data = state["visits"]
        else:
            raise AssertionError(f"Unexpected test endpoint: {path}")
        return httpx.Response(200, json={"success": True, "data": data})

    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    nexus = NexusConnector(settings, httpx.MockTransport(nexus_handler))
    startrack = StartrackClient(
        StartrackReadConfig(
            enabled=True, allow_writes=True, api_key="test-key", password="test-only-password"
        ),
        httpx.MockTransport(startrack_handler),
    )
    service = WorkflowService(settings, engine, nexus, startrack)
    yesterday = datetime.now(BUSINESS_TIMEZONE).date() - timedelta(days=1)
    mapping = TransferMapping(
        request_source_id=REQUEST_ID,
        machinery_source_id=EQUIPMENT_ID,
        project_source_id=PROJECT_ID,
        poi_id="100",
        assigned_user_ids=("200",),
        movement_reference="test-provider-workflow",
        scheduled_date=yesterday,
        scheduled_time="01:00:00",
        job_type_id="400",
    )
    with management_scope(True):
        movement = service.save_plan("live", mapping)
    state["payload"] = movement.payload
    yield SimpleNamespace(service=service, state=state, movement=movement, mapping=mapping)
    startrack.close()
    nexus.close()
    engine.dispose()


def dispatch(workflow):
    service = workflow.service
    with management_scope(True):
        service.queue(workflow.movement.id)
        claimed = service.ledger.claim(workflow.movement.id)
        service._dispatch(claimed)
    return service.ledger.get(workflow.movement.id, "live")


def full_job(workflow, **changes):
    return {
        **workflow.state["payload"],
        "id": "700",
        "status": "1",
        "closed_date": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    } | changes


def test_acknowledged_post_is_sent_without_requiring_optional_response_echoes(workflow):
    sent = dispatch(workflow)
    assert sent.state == "sent" and sent.job_id == "700"
    assert workflow.state["posts"] == 1
    assert sent.receipt is None
    assert workflow.service.ledger.claim() is None


def test_acknowledged_post_with_explicit_conflicting_destination_stays_unknown(workflow):
    workflow.state["create_response"] = "contradictory"
    unknown = dispatch(workflow)
    assert unknown.state == "unknown" and unknown.reason_code == "invalid_response"
    assert workflow.state["posts"] == 1
    assert workflow.service.ledger.claim() is None


def test_incomplete_lookup_cannot_authorize_queue(workflow, monkeypatch):
    client = workflow.service.startrack
    result = client.find_jobs_by_remote_id(workflow.movement.movement_reference)
    monkeypatch.setattr(
        client, "find_jobs_by_remote_id", lambda _: result.model_copy(update={"exhausted": False})
    )
    with management_scope(True), pytest.raises(WorkflowError, match="incompleta"):
        workflow.service.queue(workflow.movement.id)
    assert workflow.service.ledger.get(workflow.movement.id, "live").state == "draft"
    assert workflow.state["posts"] == 0


@pytest.mark.parametrize("response", ["id-only", "timeout"])
def test_incomplete_or_lost_post_response_is_unknown_then_reconciled_without_repost(
    workflow, response
):
    workflow.state["create_response"] = response
    unknown = dispatch(workflow)
    assert unknown.state == "unknown" and unknown.job_id is None
    assert workflow.state["posts"] == 1
    assert workflow.service.ledger.claim() is None
    workflow.state["jobs"] = [full_job(workflow)]
    workflow.service._observe(unknown, {"1": "1"})
    reconciled = workflow.service.ledger.get(unknown.id, "live")
    assert reconciled.state == "sent" and reconciled.job_id == "700"
    assert reconciled.receipt is None
    assert workflow.state["posts"] == 1
    task_event = next(event for event in reconciled.events if event.kind == "task_state")
    assert task_event.event_time == datetime.fromisoformat(workflow.state["jobs"][0]["closed_date"])
    assert task_event.data["workflow_role"] == "1"


@pytest.mark.parametrize(
    "change",
    [
        {"poi_id": "101"},
        {"assigned_user_ids": ["201"]},
        {"start_time": None},
        {"description": None},
        {"description": "Another Prisma request with the same labels"},
        {"job_type_id": "401"},
    ],
)
def test_unknown_reconciliation_requires_explicit_original_correspondence(workflow, change):
    workflow.state["create_response"] = "timeout"
    unknown = dispatch(workflow)
    workflow.state["jobs"] = [full_job(workflow, **change)]
    workflow.service._observe(unknown, {})
    assert workflow.service.ledger.get(unknown.id, "live").state == "unknown"
    assert workflow.state["posts"] == 1


def test_multiple_matching_remote_ids_remain_unknown(workflow):
    workflow.state["create_response"] = "timeout"
    unknown = dispatch(workflow)
    workflow.state["jobs"] = [full_job(workflow), full_job(workflow, id="701")]
    workflow.service._observe(unknown, {})
    assert workflow.service.ledger.get(unknown.id, "live").state == "unknown"
    assert workflow.state["posts"] == 1


def test_definite_rejection_becomes_failed_and_never_requeues(workflow):
    workflow.state["create_response"] = "rejected"
    failed = dispatch(workflow)
    assert failed.state == "failed" and failed.reason_code == "provider_rejected"
    assert "test-only-password" not in failed.model_dump_json()
    assert workflow.service.ledger.claim() is None
    with management_scope(True), pytest.raises(WorkflowError):
        workflow.service.queue(failed.id)
    assert workflow.state["posts"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"status": "PENDIENTE"},
        {"maquinaria_id": None},
        {"project_id": "different-project"},
    ],
)
def test_dispatch_rechecks_source_approval_and_assignment_after_queue(workflow, change):
    service = workflow.service
    with management_scope(True):
        service.queue(workflow.movement.id)
        workflow.state["request"].update(change)
        service._dispatch(service.ledger.claim(workflow.movement.id))
    failed = service.ledger.get(workflow.movement.id, "live")
    assert failed.state == "failed" and failed.reason_code == "dispatch_blocked"
    assert workflow.state["posts"] == 0


def test_read_enabled_sdk_without_write_permission_cannot_queue(workflow):
    workflow.service.startrack.config = workflow.service.startrack.config.model_copy(
        update={"allow_writes": False}
    )
    with management_scope(True), pytest.raises(WorkflowError, match="habilitación"):
        workflow.service.queue(workflow.movement.id)
    assert workflow.service.ledger.get(workflow.movement.id, "live").state == "draft"
    assert workflow.state["posts"] == 0


def test_dispatch_rechecks_management_gate_after_claim(workflow):
    service = workflow.service
    with management_scope(True):
        service.queue(workflow.movement.id)
    service._dispatch(service.ledger.claim(workflow.movement.id))
    assert service.ledger.get(workflow.movement.id, "live").state == "failed"
    assert workflow.state["posts"] == 0


def tracked_movement(workflow):
    with management_scope(True):
        return workflow.service.save_plan(
            "live",
            workflow.mapping.model_copy(update={"movement_reference": "tracked-test"}),
            tracked_vehicle_id="300",
        )


def test_deactivated_tracked_vehicle_cannot_be_queued(workflow):
    movement = tracked_movement(workflow)
    workflow.state["vehicle_deactivated"] = "1"
    with management_scope(True), pytest.raises(WorkflowError, match="Vehículo GPS"):
        workflow.service.queue(movement.id)
    assert workflow.state["posts"] == 0


def test_task_completion_and_exact_vehicle_visit_never_create_receipt(workflow):
    service = workflow.service
    workflow.movement = tracked_movement(workflow)
    workflow.state["payload"] = workflow.movement.payload
    sent = dispatch(workflow)
    workflow.state["jobs"] = [full_job(workflow)]
    arrived_at = datetime.now(UTC) - timedelta(hours=1)
    workflow.state["visits"] = [
        {
            "id": 800,
            "poi_id": 100,
            "vehicle_id": 300,
            "start_date": arrived_at.isoformat(),
            "end_date": None,
        }
    ]
    service._observe(sent, {"1": "1"})
    observed = service.ledger.get(sent.id, "live")
    assert observed.status == "1" and observed.workflow_role == "1"
    assert observed.receipt is None
    arrival = next(event for event in observed.events if event.kind == "arrival")
    assert arrival.event_time == arrived_at and arrival.source_id == "800"
    assert arrival.data["tracked_asset_id"] == "300"
    assert "no acredita recepción" in arrival.data["label"]


def test_changed_task_destination_is_recorded_but_not_linked_to_old_destination_visits(workflow):
    service = workflow.service
    workflow.movement = tracked_movement(workflow)
    workflow.state["payload"] = workflow.movement.payload
    sent = dispatch(workflow)
    workflow.state["jobs"] = [full_job(workflow, poi_id="999")]
    with pytest.raises(WorkflowError, match="destino actual"):
        service._observe(sent, {"1": "1"})
    observed = service.ledger.get(sent.id, "live")
    assert observed.events[-1].data["poi_id"] == "999"
    assert observed.receipt is None
    assert all(path != "/api/visits" for _, path in workflow.state["calls"])


@pytest.mark.parametrize("raw_date", ["2026-01-01", "2026-01-01T09:00:00", "not-a-date"])
def test_unzoned_visit_dates_are_not_used_as_arrival(workflow, raw_date):
    service = workflow.service
    workflow.movement = tracked_movement(workflow)
    workflow.state["payload"] = workflow.movement.payload
    sent = dispatch(workflow)
    workflow.state["jobs"] = [full_job(workflow)]
    workflow.state["visits"] = [
        {
            "id": 800,
            "poi_id": 100,
            "vehicle_id": 300,
            "start_date": raw_date,
        }
    ]
    service._observe(sent, {"1": "1"})
    observed = service.ledger.get(sent.id, "live")
    assert all(event.kind != "arrival" for event in observed.events)
    assert observed.receipt is None
