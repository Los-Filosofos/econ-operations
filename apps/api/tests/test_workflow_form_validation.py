"""Operator corrections stay actionable without sending invalid form data."""

from unittest.mock import Mock

import pytest

from app.dashboard.workflow_actions import WorkflowInputError, execute_action


def plan_fields():
    return {
        "request_source_id": "test-request",
        "machinery_source_id": "test-equipment",
        "project_source_id": "test-project",
        "poi_id": "test-destination",
        "assigned_user_ids": "test-user-1, test-user-2",
        "movement_reference": "test-movement",
        "scheduled_date": "2026-09-15",
        "scheduled_time": " ",
        "tracked_vehicle_id": " \t ",
    }


def receipt_fields():
    return {
        "receiver": "Persona de prueba",
        "received_date": "2026-09-15",
        "received_time": "10:35",
        "reference": "test-receipt",
        "note": " \t ",
    }


def test_blank_optional_plan_fields_remain_optional():
    service = Mock()
    execute_action(service, "save", "fixture", plan_fields(), "")
    mode, mapping, tracked_vehicle = service.save_plan.call_args.args
    assert mode == "fixture"
    assert mapping.scheduled_time is None
    assert mapping.assigned_user_ids == ("test-user-1", "test-user-2")
    assert tracked_vehicle is None


def test_blank_optional_receipt_note_does_not_discard_valid_receipt():
    service = Mock()
    execute_action(service, "receipt", "live", receipt_fields(), "test-movement")
    args = service.record_receipt.call_args.args
    assert args[0:3] == ("test-movement", "live", "Persona de prueba")
    assert args[3].isoformat() == "2026-09-15T10:35:00-06:00"
    assert args[4:] == ("test-receipt", None)


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("poi_id", " ", "ID de geocerca de destino en Startrack"),
        ("movement_reference", None, "Referencia del movimiento"),
        ("scheduled_date", "2026-02-30", "Fecha no válida"),
        ("scheduled_date", "private-input", "Fecha no válida"),
        ("scheduled_time", "24:00", "Hora no válida"),
        ("scheduled_time", "private-input", "Hora no válida"),
        ("assigned_user_ids", "test-user,", "entradas vacías"),
        ("assigned_user_ids", "test-user,,test-other", "entradas vacías"),
        ("assigned_user_ids", "private input", "sin nombres"),
        ("assigned_user_ids", "test-user, test-user", "no deben repetirse"),
    ],
)
def test_invalid_plan_inputs_explain_correction_before_service_call(field, value, expected):
    service = Mock()
    fields = {**plan_fields(), field: value}
    with pytest.raises(WorkflowInputError, match=expected) as error:
        execute_action(service, "save", "fixture", fields, "")
    assert "private" not in str(error.value)
    service.save_plan.assert_not_called()


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("receiver", " ", "Persona que recibió la maquinaria"),
        ("reference", "", "Referencia de la constancia"),
        ("received_date", "20260230", "Fecha no válida"),
        ("received_time", "12:61", "Hora no válida"),
    ],
)
def test_invalid_receipt_inputs_do_not_reach_recording_service(field, value, expected):
    service = Mock()
    with pytest.raises(WorkflowInputError, match=expected):
        execute_action(service, "receipt", "live", {**receipt_fields(), field: value}, "test-id")
    service.record_receipt.assert_not_called()
