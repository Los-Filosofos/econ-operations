"""Provider workflow checks use real adapters and an isolated durable ledger."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import event as sqlalchemy_event

from app.core.access import management_scope
from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.models import metadata
from app.models.operations import Actor
from app.services.hub import BUSINESS_TIMEZONE
from app.services.transfers import TransferMapping
from app.services.workflow import JOB_CONFLICT_REASON, WorkflowError, WorkflowService

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
        # When set, an acknowledged POST also registers the job (payload + these facts) so
        # that later bounded reads of the same cycle find it, as the sandbox would.
        "created_job": None,
        # Called at the start of every provider request; tests assert on SQL state there.
        "probe": lambda: None,
    }

    def nexus_handler(request):
        state["probe"]()
        state["calls"].append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"success": True},
                headers={"Set-Cookie": "auth-token=test-only; Path=/; Secure; HttpOnly"},
            )
        assert request.url.host == "econ-key.maic.ai"
        path = request.url.path
        if path.endswith(("/equipos", "/requests")):
            key = "request" if path.endswith("/requests") else "equipment"
            page = {
                "items": [state[key]],
                "total": 1,
                "page": int(request.url.params.get("page", "1")),
                "limit": int(request.url.params.get("limit", "25")),
            }
            return httpx.Response(200, json=page)
        key = "request" if "/requests/" in path else "equipment"
        return httpx.Response(200, json=state[key])

    def startrack_handler(request):
        state["probe"]()
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
            if state["created_job"] is not None:
                state["jobs"].append({**state["payload"], "id": "700", **state["created_job"]})
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
            # The bounded reads filter by exact id or remote_id, as the client requests.
            field = request.url.params.get("filter_by")
            value = request.url.params.get("filter_values")
            data = [job for job in state["jobs"] if field is None or str(job.get(field)) == value]
        elif path == "/api/job/status":
            data = [
                {"id": "0", "name": "Pendiente", "workflow_role": "0"},
                {"id": "1", "name": "Completada", "workflow_role": "1"},
                {"id": "2", "name": "Cancelada", "workflow_role": "2"},
            ]
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
    # The visit precedes the task closure, so it falls inside the movement's window.
    closed_at = datetime.fromisoformat(workflow.state["jobs"][0]["closed_date"])
    arrived_at = closed_at - timedelta(minutes=30)
    workflow.state["visits"] = [
        {
            "id": 800,
            "poi_id": 100,
            "vehicle_id": 300,
            "start_date": arrived_at.isoformat(),
            "end_date": None,
        }
    ]
    assert service._observe(sent, {"1": "1"}) == 0
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


def visit(identifier: int, start: datetime, end: str | None = None) -> dict:
    return {
        "id": identifier,
        "poi_id": 100,
        "vehicle_id": 300,
        "start_date": start.isoformat(),
        "end_date": end,
    }


def closed_job(workflow, closed_at: datetime, **changes) -> dict:
    return full_job(
        workflow,
        closed_date=closed_at.isoformat(),
        last_status_change_date=closed_at.isoformat(),
        **changes,
    )


def sent_with_vehicle(workflow, kind: str | None = None):
    with management_scope(True):
        movement = workflow.service.save_plan(
            "live",
            workflow.mapping.model_copy(update={"movement_reference": "tracked-test"}),
            tracked_vehicle_id="300",
            tracked_vehicle_kind=kind,
        )
    workflow.movement = movement
    workflow.state["payload"] = movement.payload
    return dispatch(workflow)


def arrivals(workflow, movement_id: str) -> list:
    record = workflow.service.ledger.get(movement_id, "live")
    return [event for event in record.events if event.kind == "arrival"]


SESSION_ACTOR = Actor(user_id="7", email="logistica@example.test", role="logistica", kind="session")


def test_receipt_keeps_declared_receiver_separate_from_actor(workflow):
    sent = dispatch(workflow)
    with management_scope(True):
        received = workflow.service.record_receipt(
            sent.id,
            "live",
            receiver="Persona X",
            received_at=datetime.now(UTC),
            reference="ACTA-TEST-1",
            actor=SESSION_ACTOR,
        )
    assert received.receipt.receiver == "Persona X"
    assert received.receipt.declared_by_user_id == SESSION_ACTOR.user_id
    assert received.receipt.declared_by_email == SESSION_ACTOR.email
    assert received.receipt.declared_by_role == SESSION_ACTOR.role
    receipt_event = next(event for event in received.events if event.kind == "receipt")
    assert receipt_event.data["receiver"] == "Persona X"
    assert (receipt_event.actor_user_id, receipt_event.actor_role, receipt_event.actor_kind) == (
        "7",
        "logistica",
        "session",
    )


@pytest.mark.parametrize(
    ("kind", "expected_label"),
    [
        ("transporter", "vehículo del transportador"),
        ("machine_device", "vehículo GPS"),
        (None, "vehículo GPS"),
    ],
)
def test_tracked_vehicle_kind_travels_to_arrival_evidence(workflow, kind, expected_label):
    sent = sent_with_vehicle(workflow, kind)
    assert sent.tracked_vehicle_kind == kind
    closed_at = datetime.now(UTC) - timedelta(hours=1)
    workflow.state["jobs"] = [closed_job(workflow, closed_at)]
    workflow.state["visits"] = [visit(800, closed_at - timedelta(minutes=30))]
    assert workflow.service._observe(sent, {"1": "1"}) == 0
    (arrival,) = arrivals(workflow, sent.id)
    assert arrival.data.get("tracked_asset_kind") == kind
    assert expected_label in arrival.data["label"]
    assert "no acredita recepción" in arrival.data["label"]
    if kind == "transporter":
        assert "transportador" in arrival.data["label"]
    assert workflow.service.ledger.get(sent.id, "live").receipt is None


def test_visits_after_task_closure_are_not_attributed(workflow):
    sent = sent_with_vehicle(workflow)
    closed_at = datetime.now(UTC) - timedelta(hours=2)
    workflow.state["jobs"] = [closed_job(workflow, closed_at)]
    workflow.state["visits"] = [
        visit(800, closed_at + timedelta(hours=1)),
        visit(801, closed_at - timedelta(hours=1)),
    ]
    # One visit falls after the closure: it is counted, not attributed.
    assert workflow.service._observe(sent, {"1": "1"}) == 1
    assert [event.source_id for event in arrivals(workflow, sent.id)] == ["801"]
    # Repeating the read attributes nothing new and keeps reporting the excluded visit.
    assert workflow.service._observe(sent, {"1": "1"}) == 1
    assert [event.source_id for event in arrivals(workflow, sent.id)] == ["801"]


def test_cancelled_task_also_closes_the_window(workflow):
    sent = sent_with_vehicle(workflow)
    cancelled_at = datetime.now(UTC) - timedelta(hours=2)
    workflow.state["jobs"] = [closed_job(workflow, cancelled_at, status="2")]
    workflow.state["visits"] = [visit(800, cancelled_at + timedelta(minutes=5))]
    assert workflow.service._observe(sent, {"2": "2"}) == 1
    assert arrivals(workflow, sent.id) == []


def test_reopened_task_reopens_the_attribution_window(workflow):
    sent = sent_with_vehicle(workflow)
    closed_at = datetime.now(UTC) - timedelta(hours=3)
    later_visit = visit(800, closed_at + timedelta(hours=1))
    workflow.state["jobs"] = [closed_job(workflow, closed_at)]
    workflow.state["visits"] = [later_visit]
    assert workflow.service._observe(sent, {"1": "1", "0": "0"}) == 1
    assert arrivals(workflow, sent.id) == []
    # The task goes back to pending after the closure: the window is open again and the
    # old closure is not kept, so the same visit is now within the movement's window.
    reopened_at = closed_at + timedelta(minutes=30)
    workflow.state["jobs"] = [
        full_job(
            workflow,
            status="0",
            closed_date=None,
            last_status_change_date=reopened_at.isoformat(),
        )
    ]
    assert workflow.service._observe(sent, {"1": "1", "0": "0"}) == 0
    assert [event.source_id for event in arrivals(workflow, sent.id)] == ["800"]
    record = workflow.service.ledger.get(sent.id, "live")
    assert record.workflow_role == "0"
    assert record.receipt is None


def test_undated_closure_never_uses_the_reading_time_as_closure(workflow):
    sent = sent_with_vehicle(workflow)
    # A closing state whose provider dates are unzoned yields no closure instant.
    workflow.state["jobs"] = [
        full_job(workflow, closed_date="2026-09-12 10:00:00", last_status_change_date=None)
    ]
    inside = datetime.now(UTC) - timedelta(hours=1)
    workflow.state["visits"] = [visit(800, inside)]
    assert workflow.service._observe(sent, {"1": "1"}) == 0
    task_state = next(
        event
        for event in workflow.service.ledger.get(sent.id, "live").events
        if event.kind == "task_state"
    )
    assert task_state.event_time is None
    assert [event.source_id for event in arrivals(workflow, sent.id)] == ["800"]


def test_creation_date_and_visit_end_are_persisted(workflow):
    sent = sent_with_vehicle(workflow)
    closed_at = datetime.now(UTC) - timedelta(hours=1)
    workflow.state["jobs"] = [
        closed_job(workflow, closed_at, creation_date="2026-09-12 08:00:00-06:00")
    ]
    workflow.state["visits"] = [
        visit(800, closed_at - timedelta(minutes=30), end="2026-09-13 10:15:00-06:00")
    ]
    assert workflow.service._observe(sent, {"1": "1"}) == 0
    record = workflow.service.ledger.get(sent.id, "live")
    task_state = next(event for event in record.events if event.kind == "task_state")
    assert task_state.data["creation_date"] == "2026-09-12 08:00:00-06:00"
    (arrival,) = arrivals(workflow, sent.id)
    assert arrival.data["end_date_raw"] == "2026-09-13 10:15:00-06:00"
    assert arrival.data["event_time_raw"] == (closed_at - timedelta(minutes=30)).isoformat()


def test_post_answered_with_a_job_linked_elsewhere_fails_without_repost(workflow):
    service = workflow.service
    first = dispatch(workflow)
    assert first.state == "sent" and first.job_id == "700"
    with management_scope(True):
        second = service.save_plan(
            "live", workflow.mapping.model_copy(update={"movement_reference": "second-attempt"})
        )
    workflow.movement = second
    workflow.state["payload"] = second.payload
    # The provider answers with the job that already belongs to the first movement.
    failed = dispatch(workflow)
    assert failed.state == "failed" and failed.reason_code == JOB_CONFLICT_REASON
    assert failed.job_id is None
    assert workflow.state["posts"] == 2
    assert service.ledger.get(first.id, "live").job_id == "700"
    assert service.ledger.claim() is None
    with management_scope(True), pytest.raises(WorkflowError):
        service.queue(failed.id)
    assert workflow.state["posts"] == 2
    finished = [event for event in failed.events if event.kind == "failed"]
    assert finished and finished[-1].data["reason_code"] == JOB_CONFLICT_REASON


def test_resolve_closes_unknown_without_repost_and_records_actor(workflow):
    service = workflow.service
    workflow.state["create_response"] = "timeout"
    unknown = dispatch(workflow)
    assert unknown.state == "unknown"
    with management_scope(True):
        with pytest.raises(WorkflowError, match="código permitido"):
            service.resolve(unknown.id, reason_code="free text", actor=SESSION_ACTOR)
        resolved = service.resolve(unknown.id, reason_code="operator_resolved", actor=SESSION_ACTOR)
    assert resolved.state == "failed" and resolved.reason_code == "operator_resolved"
    resolution = resolved.events[-1]
    assert resolution.kind == "resolved"
    assert resolution.data == {"reason_code": "operator_resolved", "previous_state": "unknown"}
    assert (resolution.actor_user_id, resolution.actor_role, resolution.actor_kind) == (
        "7",
        "logistica",
        "session",
    )
    assert workflow.state["posts"] == 1
    with management_scope(True), pytest.raises(WorkflowError):
        service.resolve(resolved.id, reason_code="operator_resolved", actor=SESSION_ACTOR)
    # The machine's in-flight slot is free again for an explicit new plan.
    with management_scope(True):
        again = service.save_plan(
            "live", workflow.mapping.model_copy(update={"movement_reference": "after-resolve"})
        )
        assert service.queue(again.id).state == "queued"
    assert workflow.state["posts"] == 1


def test_explicit_actor_never_bypasses_the_management_gate(workflow):
    service = workflow.service
    with management_scope(False):
        with pytest.raises(WorkflowError, match="sesión con permiso"):
            service.save_plan("live", workflow.mapping, actor=SESSION_ACTOR)
        with pytest.raises(WorkflowError, match="sesión con permiso"):
            service.queue(workflow.movement.id, actor=SESSION_ACTOR)
        with pytest.raises(WorkflowError, match="sesión con permiso"):
            service.sync("live", actor=SESSION_ACTOR)
        with pytest.raises(WorkflowError, match="sesión con permiso"):
            service.resolve(workflow.movement.id, reason_code="unknown", actor=SESSION_ACTOR)
        with pytest.raises(WorkflowError, match="sesión con permiso"):
            service.record_receipt(
                workflow.movement.id,
                "live",
                receiver="Persona X",
                received_at=datetime.now(UTC),
                reference="ACTA-TEST-1",
                actor=SESSION_ACTOR,
            )
    assert service.ledger.get(workflow.movement.id, "live").state == "draft"
    assert workflow.state["posts"] == 0


def test_no_sql_connection_is_held_during_provider_calls(workflow):
    service = workflow.service
    engine = service.ledger.engine
    held = {"count": 0}
    violations = []

    @sqlalchemy_event.listens_for(engine, "checkout")
    def _checked_out(_dbapi_connection, _record, _proxy):
        held["count"] += 1

    @sqlalchemy_event.listens_for(engine, "checkin")
    def _checked_in(_dbapi_connection, _record):
        held["count"] -= 1

    def probe():
        if held["count"] or engine.pool.checkedout():
            violations.append((held["count"], engine.pool.checkedout()))

    workflow.state["probe"] = probe
    closed_at = datetime.now(UTC) - timedelta(hours=1)
    workflow.state["created_job"] = {
        "status": "1",
        "closed_date": closed_at.isoformat(),
        "last_status_change_date": closed_at.isoformat(),
    }
    workflow.state["visits"] = [visit(800, closed_at - timedelta(minutes=30))]
    with management_scope(True):
        movement = service.save_plan(
            "live",
            workflow.mapping.model_copy(update={"movement_reference": "tracked-test"}),
            tracked_vehicle_id="300",
        )
        workflow.state["payload"] = movement.payload
        service.queue(movement.id)
        result = service.sync("live")
    assert result.available
    paths = [path for _, path in workflow.state["calls"]]
    # Every phase talked to a provider: hub read, revalidation, dispatch and follow-up.
    assert "/api/maquinaria/requests" in paths
    assert f"/api/maquinaria/requests/{REQUEST_ID}" in paths
    assert "/api/job/status" in paths and "/api/visits" in paths
    assert workflow.state["posts"] == 1
    assert violations == []
    assert held["count"] == 0 and engine.pool.checkedout() == 0
    record = service.ledger.get(movement.id, "live")
    assert record.state == "sent" and record.job_id == "700"
    assert [event.source_id for event in arrivals(workflow, movement.id)] == ["800"]


def test_run_cycle_records_the_cli_worker_and_reports_visits_outside_the_window(workflow):
    service = workflow.service
    with management_scope(True):
        movement = service.save_plan(
            "live",
            workflow.mapping.model_copy(update={"movement_reference": "tracked-test"}),
            tracked_vehicle_id="300",
            tracked_vehicle_kind="transporter",
        )
        workflow.state["payload"] = movement.payload
        service.queue(movement.id)
    closed_at = datetime.now(UTC) - timedelta(hours=2)
    workflow.state["created_job"] = {
        "status": "1",
        "closed_date": closed_at.isoformat(),
        "last_status_change_date": closed_at.isoformat(),
    }
    workflow.state["visits"] = [
        visit(800, closed_at + timedelta(hours=1)),
        visit(801, closed_at - timedelta(hours=1)),
    ]
    result = service.run_cycle("live")
    assert "1 no atribuidas" in result.message
    record = service.ledger.get(movement.id, "live")
    assert record.state == "sent" and record.job_id == "700"
    assert workflow.state["posts"] == 1
    worker_kinds = {"sending", "sent", "task_state", "arrival"}
    worker_events = [event for event in record.events if event.kind in worker_kinds]
    assert {event.kind for event in worker_events} == worker_kinds
    for event in worker_events:
        assert event.actor_kind == "cli_worker"
        assert event.actor_user_id is None and event.actor_role is None
    (arrival,) = arrivals(workflow, movement.id)
    assert arrival.source_id == "801"
    assert arrival.data["tracked_asset_kind"] == "transporter"
    assert record.receipt is None
