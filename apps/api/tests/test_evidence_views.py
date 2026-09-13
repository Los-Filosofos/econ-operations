"""Evidence detail regressions use isolated records, never runtime sample additions."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from plotly.utils import PlotlyJSONEncoder

from app.dashboard.analytics import equipment_label
from app.dashboard.context import QueryContext
from app.dashboard.evidence_views import equipment_movements
from app.dashboard.views import equipment_detail, request_detail, requests
from app.dashboard.workflow_views import movement_detail
from app.integrations.fixtures import fixture_records
from app.models.hub import HubResponse, HubScope, HubSummary, SourceStatus
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview

AT = datetime(2026, 9, 15, 16, tzinfo=UTC)


def serialized(value):
    return json.dumps(value, cls=PlotlyJSONEncoder, ensure_ascii=False)


@pytest.fixture
def evidence():
    machines, source_requests = fixture_records()
    request = next(item for item in source_requests if item.machinery_id)
    machine = next(item for item in machines if item.id == request.machinery_id)
    machine.asset_number = "ASSET-PRIORITARIO"
    machine.code = "RAW-CLAVE"
    machine.machinery_status = "OCUPADA"
    hub = HubResponse(
        mode="fixture",
        generated_at=AT,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma",
                status="fixture",
                environment="sandbox",
                message="Test sample",
            )
        ],
        scope=HubScope(
            search="",
            requests_returned=1,
            equipment_returned=1,
            complete=False,
            description="Isolated test sample",
        ),
        summary=HubSummary(),
        equipment=[machine],
        requests=[request],
        alerts=[],
    )
    movement = MovementRecord(
        id="test-movement",
        mode="fixture",
        environment=request.provenance.environment,
        movement_reference="Movimiento de prueba",
        request_source_id=request.provenance.source_id,
        machinery_source_id=machine.provenance.source_id,
        project_source_id=request.project_id,
        tracked_vehicle_id="test-transporter",
        mapping={},
        source_request=request.model_dump(mode="json"),
        source_equipment=machine.model_dump(mode="json"),
        source_request_hash="test-hash",
        source_equipment_hash="test-hash",
        payload={},
        preparation={},
        state="sent",
        job_id="test-task",
        status="COMPLETADA",
        workflow_role="completed",
        created_at=AT,
        updated_at=AT,
        events=[],
    )
    return hub, request, machine, movement


def registry(*movements, available=True, complete=True):
    return WorkflowOverview(
        available=available,
        complete=complete,
        message="Registro de prueba",
        movements=list(movements),
    )


@pytest.mark.parametrize(
    "workflow,label",
    [
        (None, "Operaciones por consultar"),
        (registry(available=False), "Operaciones no disponibles"),
        (registry(complete=False), "Operaciones consultadas parcialmente"),
    ],
)
def test_unknown_registry_never_becomes_missing_transfer_or_receipt(evidence, workflow, label):
    hub, request, machine, _ = evidence
    for content in [
        requests(hub, QueryContext(), workflow),
        request_detail(hub, QueryContext(), request.id, workflow),
        equipment_detail(hub, QueryContext(), machine.id, workflow),
    ]:
        result = serialized(content)
        assert label in result
        assert "Sin constancia" not in result
        assert "Sin traslado vinculado" not in result


def test_available_empty_registry_keeps_bounded_absence_and_both_sources_visible(evidence):
    hub, _, machine, _ = evidence
    result = serialized(equipment_detail(hub, QueryContext(), machine.id, registry()))
    assert "Prisma / Nexus" in result and "Startrack" in result
    assert "Sin traslado vinculado en los registros consultados" in result
    assert "Sin observación disponible" in result and "Sin constancia de recepción" in result
    assert "Fecha documental" in result


def test_machine_display_prefers_asset_number_and_preserves_original_code(evidence):
    hub, request, machine, movement = evidence
    assert equipment_label(machine) == "ASSET-PRIORITARIO"
    for content in [
        equipment_detail(hub, QueryContext(), machine.id, registry()),
        request_detail(hub, QueryContext(), request.id, registry()),
        movement_detail(registry(movement), QueryContext(), movement.id),
    ]:
        result = serialized(content)
        assert "ASSET-PRIORITARIO" in result
    detail = serialized(equipment_detail(hub, QueryContext(), machine.id, registry()))
    assert "RAW-CLAVE" in detail
    assert "Número de activo · no_activo" in detail and "Clave original · clave" in detail
    machine.asset_number = None
    assert equipment_label(machine) == "RAW-CLAVE"
    machine.code = None
    assert equipment_label(machine) == machine.name


def test_occupied_and_completed_are_compatible_without_assuming_receipt(evidence):
    hub, _, machine, movement = evidence
    result = serialized(equipment_detail(hub, QueryContext(), machine.id, registry(movement)))
    assert "Ocupada y tarea completada son estados compatibles" in result
    assert "no libera automáticamente" in result
    assert "Sin constancia de recepción" in result
    assert "Recibida" not in result


def test_maintenance_and_pending_task_need_human_review_without_remote_resolution(evidence):
    hub, _, machine, movement = evidence
    machine.maintenance_is_stopped = True
    movement.status = "PENDIENTE"
    movement.workflow_role = "pending"
    result = serialized(equipment_detail(hub, QueryContext(), machine.id, registry(movement)))
    assert "Mantenimiento y traslado pendiente requieren revisión" in result
    assert "Mantenimiento debe confirmar" in result
    assert "no modifica los proveedores" in result


def test_several_movements_keep_independent_receipts_and_transporter_arrival(evidence):
    hub, _, machine, movement = evidence
    movement.events = [
        MovementEventRecord(
            id="test-arrival",
            kind="arrival",
            source_id="test-visit",
            event_time=AT,
            observed_at=AT + timedelta(hours=1),
            recorded_at=AT + timedelta(hours=2),
            data={"vehicle_id": "test-transporter"},
        )
    ]
    movement.receipt = ReceiptRecord(
        receiver="Receptor de prueba", received_at=AT, reference="test-constancia", recorded_at=AT
    )
    second = movement.model_copy(
        deep=True,
        update={
            "id": "test-second",
            "movement_reference": "Segundo movimiento",
            "job_id": "test-other-task",
            "receipt": None,
            "events": [],
        },
    )
    result = serialized(
        equipment_detail(hub, QueryContext(), machine.id, registry(movement, second))
    )
    assert "Movimiento de prueba" in result and "Segundo movimiento" in result
    assert "Recibida" in result and "Sin constancia de recepción" in result
    assert "test-constancia" in result and "Receptor de prueba" in result
    assert "Llegada observada" in result
    assert "Sin observación disponible" in result
    assert "puede corresponder al transportador" in result
    assert machine.location is None


@pytest.mark.parametrize("changed", ["assignment", "period", "environment", "source_id"])
def test_machine_detail_excludes_incompatible_receipts_from_current_assignment(evidence, changed):
    hub, request, machine, movement = evidence
    movement.receipt = ReceiptRecord(
        receiver="Old receiver", received_at=AT, reference="incompatible-receipt", recorded_at=AT
    )
    if changed == "assignment":
        movement.source_request["machinery_id"] = "different-machine"
    elif changed == "period":
        movement.source_request["ends_on"] = "2025-01-01"
    elif changed == "environment":
        movement.environment = "local"
    else:
        movement.machinery_source_id = "different-source-id"
    workflow = registry(movement)
    assert not equipment_movements(hub, machine, workflow)
    result = serialized(equipment_detail(hub, QueryContext(), machine.id, workflow))
    assert "incompatible-receipt" not in result
    assert "Ocupada y tarea completada son estados compatibles" not in result
    assert request.machinery_id == machine.id


def test_movement_timeline_keeps_task_event_read_and_registration_times(evidence):
    _, _, _, movement = evidence
    movement.events = [
        MovementEventRecord(
            id="test-task-event",
            kind="task_state",
            source_id="test-task",
            event_time=AT,
            observed_at=AT + timedelta(hours=1),
            recorded_at=AT + timedelta(hours=2),
            data={"status": "COMPLETADA", "workflow_role": "completed"},
        )
    ]
    result = serialized(movement_detail(registry(movement), QueryContext(), movement.id))
    assert "Estado de tarea: COMPLETADA" in result
    for time in ["10:00", "11:00", "12:00"]:
        assert time in result
    assert "corte de Prisma conservado" in result


def test_movement_unavailable_is_distinct_from_unknown_identifier(evidence):
    _, _, _, movement = evidence
    result = serialized(movement_detail(registry(available=False), QueryContext(), movement.id))
    assert "Registro de operaciones no disponible" in result
    assert "Movimiento fuera de este origen" not in result
