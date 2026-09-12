import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.cli.prepare_transfer import MAX_MAPPING_BYTES, main
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.services.transfers import TransferMapping, prepare_transfer


def operation():
    def provenance(source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="local",
            observed_at=datetime(2026, 9, 12, tzinfo=UTC),
            evidence_kind="test_case",
            is_synthetic=True,
        )

    equipment = EquipmentRecord(
        id="test:equipment:unit-1",
        code="TEST-01",
        name="Unidad de prueba",
        project_id="test-project",
        machinery_status="OCUPADA",
        relation_status="unlinked",
        relation_note="Test-only data, never served by the application.",
        provenance=provenance("unit-1"),
    )
    request = RequestRecord(
        id="test:request:request-1",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=provenance("request-1"),
    )
    mapping = TransferMapping(
        request_source_id="request-1",
        machinery_source_id="unit-1",
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference="test-movement-1",
        scheduled_date=date(2026, 9, 14),
    )
    return request, equipment, mapping


def test_preparation_never_infers_destination_schedule_or_assignee():
    request, equipment, _ = operation()
    result = prepare_transfer(request, equipment)
    assert result.status == "missing_information"
    assert result.draft is None
    assert len(result.missing_fields) == 4
    assert result.remote_writes is False


def test_explicit_mapping_produces_review_draft_without_notifications_or_delivery_claims():
    request, equipment, mapping = operation()
    result = prepare_transfer(request, equipment, mapping)
    assert result.status == "draft_prepared"
    payload = result.draft.payload()
    assert payload["start_date"] == "2026-09-14"  # Not the requested use start.
    assert payload["remote_id"] == "test-movement-1"
    assert payload["poi_id"] == "test-poi"
    assert payload["assigned_user_ids"] == ["test-user"]
    assert payload["notify_contact"] is False
    assert "request-1" in payload["description"]
    assert "status" not in payload
    assert "completed_lat" not in payload
    assert result.remote_writes is False
    assert any("muestra" in note for note in result.notes)


@pytest.mark.parametrize(
    "change",
    ["pending", "missing_assignment", "wrong_unit", "wrong_project", "stopped", "mixed_evidence"],
)
def test_ambiguous_or_blocked_operation_cannot_produce_a_draft(change):
    request, equipment, mapping = operation()
    if change == "pending":
        request.status = "PENDIENTE"
    elif change == "missing_assignment":
        request.machinery_id = None
    elif change == "wrong_unit":
        equipment.id = "test:equipment:different-unit"
    elif change == "wrong_project":
        equipment.project_id = "other-project"
    elif change == "stopped":
        equipment.maintenance_is_stopped = True
    else:
        equipment.provenance.evidence_kind = "live_read"
    result = prepare_transfer(request, equipment, mapping)
    assert result.draft is None
    assert result.blocking_reasons or result.missing_fields


@pytest.mark.parametrize("field", ["request_source_id", "machinery_source_id", "project_source_id"])
def test_mapping_must_match_source_ids_even_if_display_names_match(field):
    request, equipment, mapping = operation()
    mapping = mapping.model_copy(update={field: "unrelated-source-id"})
    result = prepare_transfer(request, equipment, mapping)
    assert result.status == "review_required"
    assert result.draft is None


@pytest.mark.parametrize(
    "value",
    [
        1789344000,
        datetime(2026, 9, 14, tzinfo=UTC),
        "2026-09-14T00:00:00Z",
        "20260914",
        "2026-09-14 ",
    ],
)
def test_mapping_cannot_coerce_an_epoch_or_timestamp_into_a_scheduled_date(value):
    _, _, mapping = operation()
    with pytest.raises(ValidationError):
        TransferMapping.model_validate(mapping.model_dump() | {"scheduled_date": value})


@pytest.mark.parametrize(
    "change",
    [{"scheduled_time": "24:00:00"}, {"assigned_user_ids": ["same-user", "same-user"]}],
)
def test_mapping_rejects_invalid_task_fields_before_preparation(change):
    _, _, mapping = operation()
    with pytest.raises(ValidationError):
        TransferMapping.model_validate(mapping.model_dump() | change)


@pytest.mark.parametrize("mismatch", ["both_startrack", "environment", "synthetic"])
def test_matching_ids_do_not_override_incompatible_provenance(mismatch):
    request, equipment, mapping = operation()
    if mismatch == "both_startrack":
        request.provenance.source = "startrack"
        equipment.provenance.source = "startrack"
    elif mismatch == "environment":
        equipment.provenance.environment = "sandbox"
    else:
        equipment.provenance.is_synthetic = False
    result = prepare_transfer(request, equipment, mapping)
    assert result.status == "review_required"
    assert result.draft is None


def test_preparation_retains_independent_source_provenance_and_unknown_condition():
    request, equipment, mapping = operation()
    equipment.machinery_status = "ESTADO_NUEVO_DEL_PROVEEDOR"
    equipment.maintenance_is_stopped = None
    result = prepare_transfer(request, equipment, mapping)
    assert result.status == "draft_prepared"
    assert result.request_provenance == request.provenance
    assert result.equipment_provenance == equipment.provenance
    assert any("Se desconoce" in note for note in result.notes)
    assert any("no acredita disponibilidad física" in note for note in result.notes)
    assert any("ESTADO_NUEVO_DEL_PROVEEDOR" in note for note in result.notes)
    original_source_id = result.request_provenance.source_id
    request.provenance.source_id = "later-change"
    assert result.request_provenance.source_id == original_source_id
    assert "received_at" not in result.model_dump_json()


def test_local_cli_uses_only_supplied_samples_and_never_constructs_an_http_client(
    monkeypatch, capsys
):
    def forbid_http_client(*args, **kwargs):
        pytest.fail("Local preparation must not create a provider client")

    monkeypatch.setattr("httpx.Client", forbid_http_client)
    result = main(["--request-source-id", "46d2573e-08d3-4855-971d-2fbf9564e135"])
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert result == 0 and not captured.err
    assert output["status"] == "missing_information"
    assert output["draft"] is None and output["remote_writes"] is False
    assert output["request_provenance"]["evidence_kind"] == "provided_sample"
    assert output["request_provenance"]["environment"] == "sandbox"
    assert output["request_provenance"]["observed_at"] is None
    assert output["equipment_provenance"]["source_id"] == "66faacde-728c-4378-8b46-dbfb38254e03"


def test_local_cli_outputs_draft_only_from_explicit_mapping(tmp_path, monkeypatch, capsys):
    def forbid_http_client(*args, **kwargs):
        pytest.fail("Local preparation must not create a provider client")

    monkeypatch.setattr("httpx.Client", forbid_http_client)
    mapping = {
        "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
        "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
        "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
        "poi_id": "test-only-poi",
        "assigned_user_ids": ["test-only-user"],
        "movement_reference": "test-only-movement",
        "scheduled_date": "2026-09-15",
    }
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")
    result = main(["--request-source-id", mapping["request_source_id"], "--mapping", str(path)])
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert result == 0 and not captured.err
    assert output["status"] == "draft_prepared" and output["remote_writes"] is False
    assert output["draft"]["start_date"] == "2026-09-15"
    assert output["draft"]["notify_contact"] is False
    assert any("Estado administrativo de la unidad: OBSOLETA." in note for note in output["notes"])


@pytest.mark.parametrize("kind", ["invalid", "oversized", "missing"])
def test_local_cli_mapping_errors_never_echo_file_contents(kind, tmp_path, capsys):
    path = tmp_path / "mapping.json"
    if kind != "missing":
        content = (
            "private-test-value"
            if kind == "invalid"
            else "private-test-value" + "x" * MAX_MAPPING_BYTES
        )
        path.write_text(content, encoding="utf-8")
    result = main(
        [
            "--request-source-id",
            "46d2573e-08d3-4855-971d-2fbf9564e135",
            "--mapping",
            str(path),
        ]
    )
    captured = capsys.readouterr()
    assert result == 2 and not captured.out
    assert json.loads(captured.err)["remote_writes"] is False
    assert "private-test-value" not in captured.err


def test_local_cli_rejects_names_instead_of_source_ids(capsys):
    result = main(["--request-source-id", "PROY-014"])
    captured = capsys.readouterr()
    assert result == 2 and not captured.out
    assert json.loads(captured.err)["remote_writes"] is False
