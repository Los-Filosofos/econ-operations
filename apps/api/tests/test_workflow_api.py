from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.config import Settings
from app.integrations.fixtures import fixture_records
from app.main import create_app
from app.models import metadata


def plan():
    machines, requests = fixture_records()
    request = next(item for item in requests if item.status == "APROBADA")
    machine = next(item for item in machines if item.id == request.machinery_id)
    return {
        "mode": "fixture",
        "mapping": {
            "request_source_id": request.provenance.source_id,
            "machinery_source_id": machine.provenance.source_id,
            "project_source_id": request.project_id,
            "poi_id": "test-poi",
            "assigned_user_ids": ["test-user"],
            "movement_reference": "test-api-plan",
            "scheduled_date": "2026-09-14",
        },
    }


@pytest.fixture
def app(tmp_path):
    return create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'operations.db'}",
            allow_local_management=True,
            _env_file=None,
        )
    )


def test_missing_schema_remains_visible_and_startup_does_not_create_tables(app):
    with TestClient(app) as client:
        result = client.get("/api/v1/operations")
        assert result.status_code == 200
        assert result.headers["cache-control"] == "no-store"
        assert result.json()["available"] is False
        assert inspect(app.state.engine).get_table_names() == []


def test_local_sample_plan_is_persistent_idempotent_and_cannot_be_sent(app):
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        with patch.object(app.state.startrack, "create_job") as create_job:
            result = client.post("/api/v1/operations/plans", json=plan())
            assert result.status_code == 201, result.text
            row = result.json()
            assert row["mode"] == "fixture"
            assert row["state"] == "draft"
            assert row["receipt"] is None
            assert row["job_id"] is None
            repeated = client.post("/api/v1/operations/plans", json=plan())
            assert repeated.json()["id"] == row["id"]
            queued = client.post(f"/api/v1/operations/{row['id']}/queue")
            assert queued.status_code == 409
            forged = client.post(
                f"/api/v1/operations/{row['id']}/receipt",
                json={
                    "mode": "fixture",
                    "receiver": "Test receiver",
                    "received_at": "2026-09-14T14:00:00-06:00",
                    "reference": "test-receipt",
                },
            )
            assert forged.status_code == 409
            create_job.assert_not_called()
        sync = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert sync.status_code == 200
        assert sync.json()["last_sync_at"] is not None
    # A new lifespan/engine reads the same durable record.
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5501)) as client:
        overview = client.get("/api/v1/operations").json()
        assert overview["management_enabled"] is True
        assert overview["sending_enabled"] is False
        assert overview["movements"][0]["id"] == row["id"]
        assert overview["last_sync_at"] is not None


@pytest.mark.parametrize(
    ("host", "client_host", "headers"),
    [
        ("http://localhost", "198.51.100.10", {}),
        ("http://localhost", "198.51.100.10", {"X-Forwarded-For": "127.0.0.1"}),
        ("http://evil.example", "127.0.0.1", {}),
        ("http://localhost", "127.0.0.1", {"Origin": "https://evil.example"}),
        ("http://localhost", "127.0.0.1", {"Sec-Fetch-Site": "cross-site"}),
    ],
)
def test_request_flags_and_forwarded_headers_cannot_authorize_management(
    app, host, client_host, headers
):
    with TestClient(app, base_url=host, client=(client_host, 5000)) as client:
        metadata.create_all(app.state.engine)
        denied = client.post("/api/v1/operations/plans", json=plan(), headers=headers)
        assert denied.status_code == 409
        assert app.state.workflow.ledger.list("fixture") == []


def test_server_default_disables_management_and_live_without_sample_fallback(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'readonly.db'}", _env_file=None))
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5000)) as client:
        metadata.create_all(app.state.engine)
        assert client.post("/api/v1/operations/plans", json=plan()).status_code == 409
        live = client.get("/api/v1/operations?mode=live").json()
        assert live["available"] is False
        assert live["movements"] == []
        assert client.get("/api/v1/operations/catalogs").status_code == 409
        assert client.post("/api/v1/operations/sync", json={"mode": "live"}).status_code == 409
