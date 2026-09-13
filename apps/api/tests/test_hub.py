import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.integrations.fixtures import SAMPLE_PATH, fixture_records
from app.integrations.nexus import NexusEquipment, NexusReadError, NexusRequest, NexusSnapshot
from app.main import create_app
from app.models.hub import EquipmentRecord, Provenance, RequestRecord, TransferRecord
from app.services.hub import evaluate_alerts

TEST_AS_OF = datetime(2026, 9, 12, 15, tzinfo=UTC)


def rule_records() -> tuple[EquipmentRecord, RequestRecord]:
    """Business-rule inputs belong to tests, never the supplied-data dashboard."""
    provenance = Provenance(
        source="nexus",
        source_id="test:equipment:stopped",
        environment="local",
        observed_at=TEST_AS_OF,
        is_synthetic=True,
        evidence_kind="test_case",
    )
    equipment = EquipmentRecord(
        id="test:equipment:stopped",
        code="TEST-01",
        name="Equipo para prueba de reglas",
        machinery_status="MANTENIMIENTO",
        maintenance_failure_id="test:failure:open",
        maintenance_is_stopped=True,
        relation_status="confirmed",
        relation_note="Relación definida exclusivamente en esta prueba.",
        transfers=[
            TransferRecord(
                id="test:transfer:pending",
                code="TEST-TR-01",
                status="PENDIENTE",
                provenance=provenance.model_copy(
                    update={"source": "startrack", "source_id": "test:transfer:pending"}
                ),
            )
        ],
        provenance=provenance,
    )
    request = RequestRecord(
        id="test:request:pending",
        status="PENDIENTE",
        starts_on="2026-09-11",
        provenance=provenance.model_copy(update={"source_id": "test:request:pending"}),
    )
    return equipment, request


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'hub.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        yield client


def test_supplied_samples_preserve_source_states_provenance_and_missing_links(client):
    response = client.get("/api/v1/hub")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["mode"] == "fixture"
    assert data["scope"]["complete"] is False
    assert data["scope"]["equipment_total"] == 15
    assert data["scope"]["requests_total"] == 2
    assert data["summary"]["equipment_count"] == 5
    assert data["summary"]["administratively_available"] == 4
    assert data["summary"]["stopped_equipment"] == 0
    assert data["summary"]["alerts_count"] == 0
    assert data["data_as_of"] is None
    for item in data["equipment"] + data["requests"]:
        evidence = item["provenance"]
        assert item["id"].endswith(evidence["source_id"])
        assert evidence["environment"] == "sandbox"
        assert evidence["evidence_kind"] == "provided_sample"
        assert evidence["observed_at"] is None
        assert evidence["observed_on"] == "2026-09-12"
        assert evidence["source_reference"].startswith("econ-hackathon-openapi.json#/")
    assert all(item["transfers"] == [] for item in data["equipment"])
    assert all(item["location"] is None for item in data["equipment"])
    assert all(item["relation_status"] == "unlinked" for item in data["equipment"])
    cf03 = next(item for item in data["equipment"] if item["asset_number"] == "CF-03")
    assert cf03["code"] is None
    assert cf03["machinery_status"] == "OBSOLETA"
    assert cf03["maintenance_failure_id"] is None
    assert cf03["maintenance_is_stopped"] is False
    assert cf03["request_ids"] == ["nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"]
    assert {item["asset_number"] for item in data["equipment"]} == {
        "CF-01",
        "CF-02",
        "CF-03",
        "EXC-01",
        "EXC-02",
    }


def test_bundled_samples_are_exact_subsets_of_the_supplied_openapi():
    supplied = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    source_path = Path(__file__).parents[3] / supplied["source_document"]
    spec = json.loads(source_path.read_text(encoding="utf-8"))
    for collection, endpoint in [
        ("equipment", "/api/maquinaria/equipos"),
        ("requests", "/api/maquinaria/requests"),
        ("projects", "/api/projects"),
    ]:
        example = spec["paths"][endpoint]["get"]["responses"]["200"]["content"]["application/json"][
            "example"
        ]
        assert supplied[collection]["reported_total"] == example.get("total")
        assert len(supplied[collection]["items"]) == len(example["items"])
        for actual, original in zip(supplied[collection]["items"], example["items"], strict=True):
            assert actual == {field: original[field] for field in actual}


def test_sample_filter_preserves_exact_link_and_the_documented_period(client):
    first = client.get("/api/v1/hub?search=CF-03").json()
    second = client.get("/api/v1/hub?search=CF-03").json()
    assert first["data_as_of"] is second["data_as_of"] is None
    assert first["scope"]["equipment_total"] == 15
    assert first["scope"]["equipment_returned"] == 1
    assert first["requests"][0]["machinery_id"] == first["equipment"][0]["id"]
    assert first["requests"][0]["machinery_type"] == "Cargador frontal"
    assert first["requests"][0]["starts_on"] == "2026-09-11"
    assert first["requests"][0]["ends_on"] == "2026-09-14"
    assert first["requests"][0]["requested_by_id"] == "98bf9d4d-fb00-4680-9883-6a72cf0bae0e"
    assert first["requests"][0]["requested_by"] == "María José López Ramírez"
    assert first["requests"][0]["approved_at"] == "2026-09-12T01:00:01.535958Z"
    assert first["summary"]["alerts_count"] == 0
    assert client.get("/api/v1/hub?search=does-not-exist").json()["summary"]["equipment_count"] == 0
    own_team = client.get("/api/v1/hub?search=PROY-006").json()
    assert own_team["equipment"] == own_team["requests"] == []
    assert own_team["scope"]["complete"] is False


def test_live_cannot_be_enabled_by_caller_and_does_not_return_fixtures(client):
    with patch.object(client.app.state.nexus, "read") as read:
        data = client.get("/api/v1/hub?mode=live").json()
    read.assert_not_called()
    assert data["mode"] == "live"
    assert data["sources"][0]["status"] == "disabled"
    assert data["sources"][1]["status"] == "disabled"
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
                no_activo="source-asset-a",
                nombre="Retroexcavadora",
                clase_equipo="Retroexcavadora",
                estado="DISPONIBLE",
                project_id="project-a",
                project_name="Proyecto de prueba",
                active_failure_id="failure-a",
                active_failure_is_paro=None,
                created_at="2025-01-02T03:04:05+00:00",
                updated_at="2025-01-03T09:10:11-06:00",
            )
        ],
        requests=[
            NexusRequest(
                id="request-a",
                status="APPROVED",
                maquinaria_id="eq-a",
                project_id="project-a",
                project_name="Proyecto de prueba",
                tipo="Retroexcavadora",
                fecha_inicio="2026-09-11",
                fecha_fin="2026-09-26",
                requested_by_user_id="requester-a",
                requested_by_name="Solicitante de prueba",
                comentarios="Comentario conservado de la fuente.",
                created_at="2025-01-01T12:00:00+00:00",
                updated_at="2025-01-02T14:00:00-06:00",
                approved_at="2025-01-02T13:00:00-06:00",
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
        assert item["provenance"]["evidence_kind"] == "live_read"
        assert item["provenance"]["observed_at"] == data["data_as_of"]
        assert item["provenance"]["observed_on"] is None
        assert item["code"] == "RE-03"
        assert item["asset_number"] == "source-asset-a"
        assert item["equipment_class"] == "Retroexcavadora"
        assert item["project_id"] == "project-a"
        assert item["created_at"] == "2025-01-02T03:04:05Z"
        assert item["updated_at"] == "2025-01-03T09:10:11-06:00"
        assert item["maintenance_is_stopped"] is None
        assert item["request_ids"] == ["nexus:request:request-a"]
        assert item["transfers"] == []
        assert item["relation_status"] == "unlinked"
        request = data["requests"][0]
        assert request["provenance"]["source_id"] == "request-a"
        assert request["provenance"]["evidence_kind"] == "live_read"
        assert request["provenance"]["observed_at"] == data["data_as_of"]
        assert request["machinery_id"] == item["id"]
        assert request["project_id"] == "project-a"
        assert request["project_name"] == "Proyecto de prueba"
        assert request["machinery_type"] == "Retroexcavadora"
        assert request["starts_on"] == "2026-09-11"
        assert request["ends_on"] == "2026-09-26"
        assert request["requested_by_id"] == "requester-a"
        assert request["requested_by"] == "Solicitante de prueba"
        assert request["comments"] == "Comentario conservado de la fuente."
        assert request["created_at"] == "2025-01-01T12:00:00Z"
        assert request["updated_at"] == "2025-01-02T14:00:00-06:00"
        assert request["approved_at"] == "2025-01-02T13:00:00-06:00"
        with patch.object(
            client.app.state.nexus, "read", side_effect=NexusReadError("Fuente caída")
        ):
            failed = client.get("/api/v1/hub?mode=live").json()
        assert failed["sources"][0]["status"] == "error"
        assert failed["equipment"] == []
        assert failed["data_as_of"] is None
        assert all(value is None for value in failed["summary"].values())


def test_unknown_stop_and_candidate_relation_never_confirm_maintenance_transfer_risk():
    example, request = rule_records()
    example.maintenance_is_stopped = None
    assert "maintenance_blocks_transfer" not in {
        a.code for a in evaluate_alerts([example], [], TEST_AS_OF)
    }
    example.maintenance_is_stopped = True
    example.relation_status = "candidate"
    assert "maintenance_blocks_transfer" not in {
        a.code for a in evaluate_alerts([example], [], TEST_AS_OF)
    }
    request.starts_on = "2026-09-11T12:00:00"  # No timezone: unknown, not overdue.
    assert "pending_request_started" not in {
        a.code for a in evaluate_alerts([], [request], TEST_AS_OF)
    }


def test_multiple_transfers_and_business_date_are_evaluated_without_collapsing_tasks():
    example, request = rule_records()
    second = example.transfers[0].model_copy(deep=True)
    second.id = "test:transfer:second"
    example.transfers.append(second)
    alerts = evaluate_alerts([example], [], TEST_AS_OF)
    assert len([a for a in alerts if a.code == "maintenance_blocks_transfer"]) == 2
    request.starts_on = "2026-09-12"
    # It is still September 11 in El Salvador at 01:00 UTC.
    alerts = evaluate_alerts([], [request], datetime(2026, 9, 12, 1, tzinfo=UTC))
    assert alerts == []


def test_occupied_equipment_and_completed_transfer_are_not_conflicting_states():
    equipment, _ = rule_records()
    equipment.machinery_status = "OCUPADA"
    equipment.maintenance_failure_id = None
    equipment.maintenance_is_stopped = None
    equipment.transfers[0].status = "COMPLETADA"
    assert evaluate_alerts([equipment], [], TEST_AS_OF) == []


def test_missing_observation_cut_does_not_turn_sample_dates_into_current_alerts():
    _, request = rule_records()
    request.starts_on = "2000-01-01"
    assert evaluate_alerts([], [request], None) == []


def approved_pair(first_period, second_period, machinery_id="test:equipment:unit"):
    """Two approved requests on the same unit; business-rule inputs live only in tests."""
    provenance = Provenance(
        source="nexus",
        source_id="test:request:a",
        environment="local",
        observed_at=TEST_AS_OF,
        is_synthetic=True,
        evidence_kind="test_case",
    )
    first = RequestRecord(
        id="test:request:a",
        status="APROBADA",
        machinery_id=machinery_id,
        project_id="test-project",
        starts_on=first_period[0],
        ends_on=first_period[1],
        provenance=provenance,
    )
    second = first.model_copy(
        update={
            "id": "test:request:b",
            "starts_on": second_period[0],
            "ends_on": second_period[1],
            "provenance": provenance.model_copy(update={"source_id": "test:request:b"}),
        }
    )
    return first, second


def codes(alerts):
    return [alert.code for alert in alerts]


def test_fixture_has_no_overlap_alert_but_reports_not_verifiable_when_dates_missing():
    equipment, requests = fixture_records()
    fixture_alerts = evaluate_alerts(equipment, requests, None)
    assert "overlapping_approved_requests" not in codes(fixture_alerts)
    assert "overlap_not_verifiable" not in codes(fixture_alerts)

    first, second = approved_pair(("2026-09-11", "2026-09-14"), ("2026-09-13", "2026-09-16"))
    alerts = evaluate_alerts([], [first, second], None)
    assert codes(alerts) == ["overlapping_approved_requests"]
    alert = alerts[0]
    assert alert.severity == "warning" and alert.owner == "Logística"
    assert alert.equipment_id == "test:equipment:unit"
    assert any(
        "test:request:a" in line and "2026-09-11 → 2026-09-14" in line for line in alert.evidence
    )
    assert any(
        "test:request:b" in line and "2026-09-13 → 2026-09-16" in line for line in alert.evidence
    )
    assert "del 2026-09-13 al 2026-09-14" in alert.description
    assert "no modifica" in alert.description
    # Same result with an observation cut: only source dates are compared.
    assert codes(evaluate_alerts([], [first, second], TEST_AS_OF)) == codes(alerts)

    # Adjacent periods are disjoint; a pending request is not part of the pair rule.
    _, adjacent = approved_pair(("2026-09-11", "2026-09-14"), ("2026-09-15", "2026-09-16"))
    assert evaluate_alerts([], [first, adjacent], None) == []
    pending = second.model_copy(update={"status": "PENDIENTE"})
    assert "overlapping_approved_requests" not in codes(evaluate_alerts([], [first, pending], None))

    second.ends_on = None
    unknown = evaluate_alerts([], [first, second], None)
    assert codes(unknown) == ["overlap_not_verifiable"]
    assert unknown[0].severity == "info"
    assert "missing=usage_period.end" in unknown[0].evidence
    assert any("2026-09-13 → ausente" in line for line in unknown[0].evidence)


def test_assignment_window_mismatch_is_signalled_not_blocked():
    equipment, requests = fixture_records()
    cf03 = next(item for item in equipment if item.asset_number == "CF-03")
    request = next(item for item in requests if item.machinery_id == cf03.id)
    assert (cf03.assignment_starts_on, cf03.assignment_ends_on) == ("2026-09-11", "2026-09-14")
    assert (request.starts_on, request.ends_on) == ("2026-09-11", "2026-09-14")
    assert evaluate_alerts([cf03], [request], None) == []

    request.starts_on, request.ends_on = "2026-09-12", "2026-09-15"
    for as_of in (None, TEST_AS_OF):
        alerts = evaluate_alerts([cf03], [request], as_of)
        assert codes(alerts) == ["assignment_window_differs_from_request"]
        alert = alerts[0]
        assert alert.severity == "info" and alert.owner == "Logística"
        assert alert.request_id == request.id and alert.equipment_id == cf03.id
        assert "vigencia" in alert.description
        assert any("2026-09-12 → 2026-09-15" in line for line in alert.evidence)
        assert any("asignación vigente=2026-09-11 → 2026-09-14" in line for line in alert.evidence)

    # Only comparable when the request and the unit refer to the same Prisma project.
    other_project = request.model_copy(update={"project_id": "test:other-project"})
    assert evaluate_alerts([cf03], [other_project], None) == []

    cf03.assignment_ends_on = None
    unknown = evaluate_alerts([cf03], [request], None)
    assert codes(unknown) == ["overlap_not_verifiable"]
    assert "missing=assignment_window.end" in unknown[0].evidence


def test_supplied_records_do_not_share_mutable_state():
    equipment, requests = fixture_records()
    equipment[2].request_ids.clear()
    requests[0].status = "TEST-ONLY"
    fresh_equipment, fresh_requests = fixture_records()
    assert fresh_equipment[2].request_ids
    assert fresh_requests[0].status == "PENDIENTE"
