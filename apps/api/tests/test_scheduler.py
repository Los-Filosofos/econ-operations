"""In-process live scheduler (ADR 0006): bounded cycles under the cycle lock, never in fixture."""

import asyncio
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.main import create_app
from app.models import metadata
from app.services.workflow import (
    INTERNAL_ERROR,
    SyncInProgress,
    SyncScheduler,
    WorkflowError,
    WorkflowService,
)

REQUEST_ID = "10000000-0000-4000-8000-000000000001"
EQUIPMENT_ID = "20000000-0000-4000-8000-000000000001"
PROJECT_ID = "30000000-0000-4000-8000-000000000001"


@pytest.fixture
def service(tmp_path):
    """Live workflow over mocked transports: Nexus answers one request and one machine."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'scheduler.db'}",
        allow_live_reads=True,
        nexus_email="scheduler@example.test",
        nexus_password="test-only-password",
        _env_file=None,
    )
    calls = []
    records = {
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
    }

    def nexus_handler(request):
        calls.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"success": True},
                headers={"Set-Cookie": "auth-token=test-only; Path=/; Secure; HttpOnly"},
            )
        key = "request" if request.url.path.endswith("/requests") else "equipment"
        page = {"items": [records[key]], "total": 1, "page": 1, "limit": 25}
        return httpx.Response(200, json=page)

    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    nexus = NexusConnector(settings, httpx.MockTransport(nexus_handler))
    startrack = StartrackClient(StartrackReadConfig(enabled=False))
    workflow = WorkflowService(settings, engine, nexus, startrack)
    workflow.calls = calls
    yield workflow
    nexus.close()
    startrack.close()
    engine.dispose()


def run(coroutine):
    return asyncio.run(coroutine)


def test_scheduler_runs_live_cycles_with_a_short_interval_and_stops_cleanly(service):
    scheduler = SyncScheduler(service, interval_seconds=0.01)

    async def scenario():
        scheduler.start()
        assert scheduler.running
        for _ in range(100):
            await asyncio.sleep(0.02)
            if service.sync_status("live").last_cycle_at is not None:
                break
        await scheduler.stop()
        assert not scheduler.running

    run(scenario())
    assert service.calls, "the cycle read Prisma through the mocked transport"
    outcome = service.sync_status("live")
    assert outcome.last_cycle_result == "ok"
    assert outcome.last_cycle_at is not None and not outcome.in_progress
    registry = service.registry_state("live")
    assert registry.last_read_at is not None, "the cycle recorded a cut of the live source"
    # Nothing was scheduled for fixture: its registry and outcome stay untouched.
    assert service.sync_status("fixture").last_cycle_at is None
    assert service.registry_state("fixture").last_read_at is None
    # Stopping twice is harmless and a stopped scheduler runs no more cycles.
    run(scheduler.stop())
    before = len(service.calls)
    run(asyncio.sleep(0.05))
    assert len(service.calls) == before


def test_skipped_cycles_and_failures_are_recorded_without_stopping_the_loop(service):
    scheduler = SyncScheduler(service, interval_seconds=30)
    outcomes = [
        SyncInProgress("Ya hay una sincronización en curso en otro proceso."),
        WorkflowError("Prisma no respondió; consulta el estado de fuentes."),
        RuntimeError("private provider body"),
        None,
    ]
    with patch.object(service, "run_cycle", side_effect=outcomes) as run_cycle:
        results = [run(scheduler.run_once()) for _ in outcomes]
    assert run_cycle.call_count == 4
    assert results == [
        "skipped",
        "error: Prisma no respondió; consulta el estado de fuentes.",
        f"error: {INTERNAL_ERROR}",
        "ok",
    ]
    assert "private provider body" not in " ".join(results)
    assert service.sync_status("live").last_cycle_result == "ok"


def test_the_lock_held_by_another_cycle_makes_the_scheduler_skip_not_wait(service):
    scheduler = SyncScheduler(service, interval_seconds=30)
    with service._sync_lock:
        assert service.sync_status("live").in_progress
        assert run(scheduler.run_once()) == "skipped"
    assert not service.sync_status("live").in_progress


@pytest.mark.parametrize(
    "interval, live, expected",
    [(30, True, True), (30, False, False), (0, True, False), (0, False, False)],
)
def test_create_app_starts_the_scheduler_only_for_live_with_an_interval(
    tmp_path, interval, live, expected
):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        allow_live_reads=live,
        sync_interval_seconds=interval,
        _env_file=None,
    )
    assert settings.sync_enabled is expected
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        scheduler = app.state.scheduler
        assert (scheduler is not None) is expected
        if scheduler is not None:
            assert scheduler.running
    if scheduler is not None:
        assert not scheduler.running, "shutdown cancels the task"


def test_an_active_interval_below_thirty_seconds_is_rejected():
    with pytest.raises(ValidationError, match="SYNC_INTERVAL_SECONDS"):
        Settings(database_url="sqlite://", sync_interval_seconds=5, _env_file=None)
    off = Settings(database_url="sqlite://", sync_interval_seconds=0, _env_file=None)
    assert off.sync_enabled is False
