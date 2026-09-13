"""GET /api/v1/status: a cheap registry version the page polls instead of a refresh button."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app
from app.models import metadata

PLAN = {
    "mode": "fixture",
    "mapping": {
        "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
        "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
        "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
        "poi_id": "demo-poi",
        "assigned_user_ids": ["demo-user"],
        "movement_reference": "test-status-001",
        "scheduled_date": "2026-09-14",
        "scheduled_time": "08:00:00",
    },
    "tracked_vehicle_id": None,
}


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'status.db'}",
        allow_local_management=True,
        _env_file=None,
    )
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        yield client


def status(client, mode="fixture"):
    response = client.get(f"/api/v1/status?mode={mode}")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def test_status_is_stable_between_reads_and_never_consults_a_provider(client):
    with patch.object(client.app.state.nexus, "read") as read:
        first = status(client)
        second = status(client)
    read.assert_not_called()
    assert first == second
    assert set(first) == {
        "mode",
        "registry_version",
        "registry_last_read_at",
        "hub_data_as_of",
        "sync",
    }
    assert first["mode"] == "fixture"
    assert len(first["registry_version"]) == 12
    assert first["registry_last_read_at"] is None and first["hub_data_as_of"] is None
    assert first["sync"] == {
        "enabled": False,
        "interval_seconds": 0,
        "last_cycle_at": None,
        "last_cycle_result": None,
        "in_progress": False,
    }
    # Each mode has its own registry and therefore its own version.
    assert status(client, "live")["registry_version"] != first["registry_version"]
    assert client.get("/api/v1/status?mode=production").status_code == 422


def test_version_changes_when_the_registry_changes_and_not_on_an_unchanged_reread(client):
    initial = status(client)["registry_version"]
    live = status(client, "live")["registry_version"]
    assert client.post("/api/v1/operations/plans", json=PLAN).status_code == 201
    after_plan = status(client)["registry_version"]
    assert after_plan != initial
    # A fixture plan does not touch the live registry.
    assert status(client, "live")["registry_version"] == live
    assert client.post("/api/v1/operations/sync", json={"mode": "fixture"}).status_code == 200
    after_cut = status(client)
    assert after_cut["registry_version"] != after_plan
    assert after_cut["registry_last_read_at"] is not None
    # Re-reading an unchanged source confirms the cut (ADR 0006) but is not a change.
    assert client.post("/api/v1/operations/sync", json={"mode": "fixture"}).status_code == 200
    confirmed = status(client)
    assert confirmed["registry_version"] == after_cut["registry_version"]
    assert confirmed["registry_last_read_at"] >= after_cut["registry_last_read_at"]


def test_registry_failure_is_503_without_exposing_details(client):
    error = OperationalError("SELECT 1", {}, Exception("private connection details"))
    with patch.object(client.app.state.workflow.ledger, "last_snapshot", side_effect=error):
        response = client.get("/api/v1/status?mode=fixture")
    assert response.status_code == 503
    assert response.json() == {"detail": "Registro no disponible"}


def test_status_requires_a_session_like_the_rest_of_the_api(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        auth_required=True,
        session_secret="test-only-secret-" + "x" * 32,
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/status?mode=fixture").status_code == 401


def test_sync_block_reflects_the_scheduler_configuration(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'sync.db'}",
        allow_live_reads=True,
        sync_interval_seconds=30,
        _env_file=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        live = client.get("/api/v1/status?mode=live").json()["sync"]
        assert live["enabled"] and live["interval_seconds"] == 30
        # Fixture has no provider to consult: never scheduled, whatever the setting says.
        fixture = client.get("/api/v1/status?mode=fixture").json()["sync"]
        assert not fixture["enabled"] and fixture["interval_seconds"] == 0
    with pytest.raises(ValidationError, match="SYNC_INTERVAL_SECONDS"):
        Settings(database_url="sqlite://", sync_interval_seconds=10, _env_file=None)
