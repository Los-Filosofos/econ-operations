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
    ("host", "client_host", "headers", "expected"),
    [
        ("http://localhost", "198.51.100.10", {}, 409),
        ("http://localhost", "198.51.100.10", {"X-Forwarded-For": "127.0.0.1"}, 409),
        ("http://evil.example", "127.0.0.1", {}, 409),
        # Cross-origin writes are refused before any handler runs.
        ("http://localhost", "127.0.0.1", {"Origin": "https://evil.example"}, 403),
        ("http://localhost", "127.0.0.1", {"Sec-Fetch-Site": "cross-site"}, 403),
    ],
)
def test_request_flags_and_forwarded_headers_cannot_authorize_management(
    app, host, client_host, headers, expected
):
    with TestClient(app, base_url=host, client=(client_host, 5000)) as client:
        metadata.create_all(app.state.engine)
        denied = client.post("/api/v1/operations/plans", json=plan(), headers=headers)
        assert denied.status_code == expected
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


def test_local_dev_mode_records_actor_kind_without_user(app):
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        saved = client.post("/api/v1/operations/plans", json=plan())
        assert saved.status_code == 201, saved.text
        (created,) = saved.json()["events"]
        assert created["kind"] == "created"
        # Loopback development without a login: the kind is recorded, no user is invented.
        assert created["actor_kind"] == "local_dev"
        assert created["actor_user_id"] is None and created["actor_role"] is None
        synced = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert synced.status_code == 200, synced.text


def test_plan_contract_accepts_a_declared_tracked_vehicle_kind(app):
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        declared = {**plan(), "tracked_vehicle_id": "test-vehicle"}
        declared["tracked_vehicle_kind"] = "transporter"
        saved = client.post("/api/v1/operations/plans", json=declared)
        assert saved.status_code == 201, saved.text
        assert saved.json()["tracked_vehicle_kind"] == "transporter"
        assert saved.json()["tracked_vehicle_id"] == "test-vehicle"
        # The same declaration resolves to the same movement; another kind is another identity.
        assert (
            client.post("/api/v1/operations/plans", json=declared).json()["id"]
            == (saved.json()["id"])
        )
        other = {**declared, "tracked_vehicle_kind": "machine_device"}
        assert client.post("/api/v1/operations/plans", json=other).status_code == 409
        # The kind describes a tracked device: without the device it is rejected.
        orphan = {**plan(), "tracked_vehicle_kind": "transporter"}
        orphan["mapping"] = {**orphan["mapping"], "movement_reference": "test-api-orphan"}
        assert client.post("/api/v1/operations/plans", json=orphan).status_code == 409
        invalid = {**declared, "tracked_vehicle_kind": "trailer"}
        assert client.post("/api/v1/operations/plans", json=invalid).status_code == 422
        schema = client.get("/openapi.json").json()
        field = schema["components"]["schemas"]["PlanInput"]["properties"]["tracked_vehicle_kind"]
        assert "no verificado" in field["description"]


def test_resolve_route_is_documented_and_only_acts_on_live_unknown_movements(app):
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        schema = client.get("/openapi.json").json()
        route = schema["paths"]["/api/v1/operations/{movement_id}/resolve"]["post"]
        assert "nunca repite el POST" in route["description"]
        saved = client.post("/api/v1/operations/plans", json=plan()).json()
        assert client.post(f"/api/v1/operations/{saved['id']}/resolve", json={}).status_code == 422
        free_text = {"reason_code": "operator_resolved", "note": "no admitida"}
        assert (
            client.post(f"/api/v1/operations/{saved['id']}/resolve", json=free_text).status_code
            == 422
        )
        # Live is disabled on this server and the movement is a fixture draft anyway.
        refused = client.post(
            f"/api/v1/operations/{saved['id']}/resolve", json={"reason_code": "operator_resolved"}
        )
        assert refused.status_code == 409
        assert client.get("/api/v1/operations").json()["movements"][0]["state"] == "draft"
