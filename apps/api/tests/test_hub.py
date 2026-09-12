from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.hub import evaluate_alerts
from app.core.config import Settings
from app.integrations.fixtures import FIXTURE_AS_OF, fixture_records
from app.integrations.nexus import NexusEquipment, NexusReadError, NexusRequest, NexusSnapshot
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'hub.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        yield client


def test_fixture_provenance_state_semantics_and_missing_links(client):
    response = client.get("/api/v1/hub")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["mode"] == "fixture"
    assert data["scope"]["complete"] is True
    assert data["summary"]["equipment_count"] == 3
    assert data["summary"]["administratively_available"] == 1
    assert data["summary"]["stopped_equipment"] == 1
    assert data["summary"]["alerts_count"] == 4
    assert all(s["status"] == "fixture" for s in data["sources"])
    assert all(e["id"].startswith("fixture:") for e in data["equipment"])
    assert all(e["provenance"]["environment"] == "local" for e in data["equipment"])
    re03, cf03, ex02 = data["equipment"]
    assert re03["relation_status"] == "unlinked"
    assert re03["transfers"] == []
    assert re03["location"] is None
    assert re03["maintenance_is_stopped"] is None
    assert cf03["machinery_status"] == "OCUPADA"
    assert cf03["transfers"][0]["status"] == "COMPLETADA"
    assert not any(a["equipment_id"] == cf03["id"] for a in data["alerts"])
    assert ex02["maintenance_is_stopped"] is True
    assert {a["code"] for a in data["alerts"]} == {
        "active_failure",
        "maintenance_blocks_transfer",
        "pending_request_started",
        "approved_without_equipment",
    }


def test_fixture_timestamp_stays_fixed_and_filter_preserves_linked_request(client):
    first = client.get("/api/v1/hub?search=CF-03").json()
    second = client.get("/api/v1/hub?search=CF-03").json()
    assert first["data_as_of"] == second["data_as_of"]
    assert first["scope"]["equipment_total"] == 3
    assert first["scope"]["equipment_returned"] == 1
    assert first["requests"][0]["machinery_id"] == first["equipment"][0]["id"]
    assert first["summary"]["alerts_count"] == 0
    assert client.get("/api/v1/hub?search=does-not-exist").json()["summary"]["equipment_count"] == 0


def test_live_cannot_be_enabled_by_caller_and_does_not_return_fixtures(client):
    with patch.object(client.app.state.nexus, "read") as read:
        data = client.get("/api/v1/hub?mode=live").json()
    read.assert_not_called()
    assert data["mode"] == "live"
    assert data["sources"][0]["status"] == "disabled"
    assert data["sources"][1]["status"] == "not_configured"
    assert data["equipment"] == data["requests"] == data["alerts"] == []
    assert all(value is None for value in data["summary"].values())
    assert data["scope"]["complete"] is False
    assert data["scope"]["equipment_total"] is None
    assert data["data_as_of"] is None


def test_query_validation(client):
    assert client.get("/api/v1/hub?mode=production").status_code == 422
    assert client.get("/api/v1/hub", params={"search": "x" * 101}).status_code == 422
    assert client.post("/api/v1/hub").status_code == 405


def test_live_failure_is_explicit_without_reusing_fixture_or_previous_success(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'live.db'}",
        allow_live_reads=True,
        nexus_email="reader@example.test",
        nexus_password="test-secret",
        _env_file=None,
    )
    snapshot = NexusSnapshot(
        equipment=[
            NexusEquipment(
                id="eq-a",
                clave="RE-03",
                nombre="Retroexcavadora",
                estado="DISPONIBLE",
                active_failure_id="failure-a",
                active_failure_is_paro=None,
            )
        ],
        requests=[
            NexusRequest(
                id="request-a",
                status="APPROVED",
                maquinaria_id="eq-a",
            )
        ],
        equipment_total=20,
        requests_total=4,
        complete=False,
    )
    with TestClient(create_app(settings)) as client:
        with patch.object(client.app.state.nexus, "read", return_value=snapshot):
            data = client.get("/api/v1/hub?mode=live&search=RE-03").json()
        assert data["sources"][0]["status"] == "partial"
        assert data["scope"]["equipment_total"] == 20
        assert data["scope"]["equipment_returned"] == 1
        assert data["scope"]["complete"] is False
        item = data["equipment"][0]
        assert item["provenance"]["source_id"] == "eq-a"
        assert item["provenance"]["environment"] == "sandbox"
        assert item["maintenance_is_stopped"] is None
        assert item["request_ids"] == ["nexus:request:request-a"]
        assert item["transfers"] == []
        assert item["relation_status"] == "unlinked"
        with patch.object(
            client.app.state.nexus, "read", side_effect=NexusReadError("Fuente caída")
        ):
            failed = client.get("/api/v1/hub?mode=live").json()
        assert failed["sources"][0]["status"] == "error"
        assert failed["equipment"] == []
        assert failed["data_as_of"] is None
        assert all(value is None for value in failed["summary"].values())


def test_unknown_stop_and_candidate_relation_never_confirm_maintenance_transfer_risk():
    equipment, requests = fixture_records()
    example = equipment[2]
    example.maintenance_is_stopped = None
    assert "maintenance_blocks_transfer" not in {
        a.code for a in evaluate_alerts([example], [], FIXTURE_AS_OF)
    }
    example.maintenance_is_stopped = True
    example.relation_status = "candidate"
    assert "maintenance_blocks_transfer" not in {
        a.code for a in evaluate_alerts([example], [], FIXTURE_AS_OF)
    }
    requests[1].starts_on = "2026-09-11T12:00:00"  # No timezone: unknown, not overdue.
    assert "pending_request_started" not in {
        a.code for a in evaluate_alerts([], requests, FIXTURE_AS_OF)
    }


def test_multiple_transfers_and_business_date_are_evaluated_without_collapsing_tasks():
    equipment, requests = fixture_records()
    example = equipment[2]
    second = example.transfers[0].model_copy(deep=True)
    second.id = "fixture:transfer-03"
    example.transfers.append(second)
    alerts = evaluate_alerts([example], [], FIXTURE_AS_OF)
    assert len([a for a in alerts if a.code == "maintenance_blocks_transfer"]) == 2
    requests[1].starts_on = "2026-09-12"
    # It is still September 11 in El Salvador at 01:00 UTC.
    alerts = evaluate_alerts([], [requests[1]], datetime(2026, 9, 12, 1, tzinfo=UTC))
    assert alerts == []
