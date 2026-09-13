"""Next-step decisions preserve evidence scope and do not manufacture physical outcomes."""

from datetime import UTC, date, datetime

import pytest

from app.dashboard.context import QueryContext
from app.dashboard.decision_priorities import decision_items
from app.integrations.fixtures import fixture_records
from app.models.hub import HubResponse, HubScope, HubSummary, SourceStatus
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview


@pytest.fixture
def hub():
    equipment, requests = fixture_records()
    return HubResponse(
        mode="fixture",
        generated_at=datetime(2040, 1, 1, tzinfo=UTC),
        data_as_of=None,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma",
                status="fixture",
                environment="sandbox",
                message="Provided samples",
                observed_on=date(2026, 9, 12),
            )
        ],
        scope=HubScope(search="", complete=False, description="Provided sample scope"),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )


def registry(*movements, available=True):
    return WorkflowOverview(
        available=available, complete=available, message="Test ledger", movements=list(movements)
    )


def approved(hub):
    return next(request for request in hub.requests if request.status == "APROBADA")


def machine(hub):
    return next(item for item in hub.equipment if item.id == approved(hub).machinery_id)


def movement(hub, state="sent", **changes):
    request = approved(hub)
    equipment = machine(hub)
    record = MovementRecord(
        id="test-movement",
        mode=hub.mode,
        environment=request.provenance.environment,
        movement_reference="test-reference",
        request_source_id=request.provenance.source_id,
        machinery_source_id=equipment.provenance.source_id,
        project_source_id=request.project_id,
        mapping={},
        source_request=request.model_dump(mode="json"),
        source_equipment=equipment.model_dump(mode="json"),
        source_request_hash="test-only",
        source_equipment_hash="test-only",
        payload={},
        preparation={},
        state=state,
        job_id="test-job" if state == "sent" else None,
        created_at=datetime(2026, 9, 12, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
        events=[],
    )
    return record.model_copy(update=changes, deep=True)


def approved_item(hub, workflow=None):
    request = next(request for request in hub.requests if request.machinery_id)
    return next(
        item
        for item in decision_items(hub, QueryContext(), workflow)
        if item.request.id == request.id
    )


def receipt():
    return ReceiptRecord(
        receiver="Test receiver",
        reference="TEST-ACTA",
        received_at=datetime(2026, 9, 12, tzinfo=UTC),
        recorded_at=datetime(2026, 9, 12, tzinfo=UTC),
    )


def test_supplied_rows_preserve_obsolete_state_without_inventing_physical_failure(hub):
    rows = decision_items(hub, QueryContext(), registry())
    assert len(rows) == 2
    assert [item.request.id for item in rows] == sorted(request.id for request in hub.requests)
    pending = next(item for item in rows if item.request.status == "PENDIENTE")
    assert pending.title == "Resolver aprobación y asignación"
    assigned = next(item for item in rows if item.request.status == "APROBADA")
    assert assigned.title == "Revisar la asignación"
    assert "CF-03" in assigned.evidence and "OBSOLETA" in assigned.evidence
    assert "correspondencias" in assigned.evidence
    assert "Sin falla activa ni paro registrados" in assigned.evidence
    assert "avería" not in assigned.evidence
    assert "atras" not in " ".join(item.title + item.evidence for item in rows).lower()
    assert assigned.href == QueryContext().request_href(assigned.request.id)


@pytest.mark.parametrize("available", [None, False])
def test_unread_registry_is_explicit_and_cannot_prove_absent_plans(hub, available):
    machine(hub).machinery_status = "OCUPADA"
    record = registry(available=False) if available is False else None
    row = approved_item(hub, record)
    assert row.title == "Consultar el registro del traslado"
    assert "sin consultar" in row.evidence
    assert "no hay" not in row.evidence.lower()
    assert "0 movimientos" not in row.evidence


def test_pending_with_unit_requires_approval_without_asking_to_assign_again(hub):
    target = approved(hub)
    target.status = "PENDIENTE"
    row = next(
        item
        for item in decision_items(hub, QueryContext(), registry())
        if item.request.id == target.id
    )
    assert row.title == "Resolver aprobación"
    assert "asignación" not in row.title


def test_approved_without_id_differs_from_missing_unit_in_bounded_read(hub):
    target = approved(hub)
    original_id = target.machinery_id
    target.machinery_id = None
    row = next(
        item
        for item in decision_items(hub, QueryContext(), registry())
        if item.request.id == target.id
    )
    assert row.title == "Completar asignación"
    target.machinery_id = original_id
    hub.equipment = []
    row = approved_item(hub, registry())
    assert row.title == "Verificar unidad asignada"
    assert "registro no está" in row.evidence


@pytest.mark.parametrize("kind", ["stop", "failure"])
def test_explicit_maintenance_facts_do_not_depend_on_dates_or_obsolete_inference(hub, kind):
    unit = machine(hub)
    unit.machinery_status = "DISPONIBLE"
    if kind == "stop":
        unit.maintenance_is_stopped = True
    else:
        unit.maintenance_failure_id = "test-failure"
    row = approved_item(hub, registry())
    assert "paro" in row.title if kind == "stop" else "falla" in row.title
    if kind == "failure":
        assert "no confirma por sí sola un paro" in row.evidence


@pytest.mark.parametrize("state", ["unknown", "failed", "blocked"])
def test_dispatch_incident_precedes_maintenance_and_general_plan_advice(hub, state):
    unit = machine(hub)
    unit.maintenance_is_stopped = True
    record = movement(hub, state)
    row = approved_item(hub, registry(record))
    assert row.href == QueryContext().movement_href(record.id)
    assert row.action == "Revisar movimiento"
    assert "paro" not in row.title
    if state == "unknown":
        assert "Conciliar" in row.title
        assert "si existe una tarea sin repetir" in row.evidence


@pytest.mark.parametrize("state", ["CANCELADA", "COMPLETADA", "RECHAZADA"])
def test_closed_or_unknown_requests_never_instruct_new_assignment(hub, state):
    target = approved(hub)
    target.status = state
    target.machinery_id = None
    assert all(
        item.request.id != target.id for item in decision_items(hub, QueryContext(), registry())
    )


def test_unknown_request_state_requires_review_without_inventing_approval_or_closure(hub):
    target = approved(hub)
    target.status = "custom-state"
    target.machinery_id = None
    row = next(
        item
        for item in decision_items(hub, QueryContext(), registry())
        if item.request.id == target.id
    )
    assert row.title == "Revisar el estado de la solicitud"
    assert "custom-state" in row.evidence


@pytest.mark.parametrize(
    "state,phrase", [("draft", "plan local"), ("queued", "cola"), ("sending", "curso")]
)
def test_each_unconfirmed_dispatch_state_has_its_own_fact_and_detail_link(hub, state, phrase):
    machine(hub).machinery_status = "OCUPADA"
    record = movement(hub, state)
    row = approved_item(hub, registry(record))
    assert phrase in row.title
    assert row.href == QueryContext().movement_href(record.id)
    assert "recepción registrada" not in row.evidence


def test_sent_completed_task_never_becomes_receipt_or_overdue(hub):
    machine(hub).machinery_status = "OCUPADA"
    record = movement(hub, status="Completada", workflow_role="completed")
    row = approved_item(hub, registry(record))
    assert row.title == "Consultar seguimiento y recepción"
    assert "no se ha registrado una constancia" in row.evidence
    assert "atras" not in (row.title + row.evidence).lower()
    record.events = [
        MovementEventRecord(
            id="test-arrival",
            kind="arrival",
            recorded_at=datetime(2026, 9, 12, tzinfo=UTC),
            event_time=datetime(2026, 9, 12, tzinfo=UTC),
            data={},
        )
    ]
    row = approved_item(hub, registry(record))
    assert row.title == "Revisar la constancia de recepción"
    assert "presencia GPS" in row.evidence and "no se ha registrado" in row.evidence


def test_receipt_on_one_movement_cannot_close_another_movement(hub):
    machine(hub).machinery_status = "OCUPADA"
    received = movement(hub, id="first-test-received", receipt=receipt())
    pending = movement(hub, "queued", id="second-test-queued")
    row = approved_item(hub, registry(received, pending))
    assert "cola" in row.title
    assert row.href == QueryContext().movement_href(pending.id)
    assert "registrada" not in row.evidence


@pytest.mark.parametrize("changed", ["assignment", "period", "approval", "mode", "evidence"])
def test_old_or_incompatible_receipt_cannot_supply_current_execution_evidence(hub, changed):
    machine(hub).machinery_status = "OCUPADA"
    old = movement(hub, receipt=receipt())
    if changed == "assignment":
        replacement = machine(hub).model_copy(deep=True)
        replacement.id = "new-assignment-same-name"
        replacement.provenance.source_id = "new-source-unit"
        hub.equipment.append(replacement)
        approved(hub).machinery_id = replacement.id
    elif changed == "period":
        approved(hub).starts_on = "2026-10-01"
        approved(hub).ends_on = "2026-10-03"
    elif changed == "approval":
        approved(hub).approved_at = datetime(2026, 10, 1, tzinfo=UTC)
    elif changed == "mode":
        old.mode = "live"
    else:
        old.source_equipment["provenance"]["evidence_kind"] = "live_read"
    row = approved_item(hub, registry(old))
    assert row.title == "Preparar correspondencias del traslado"
    assert "recepción" not in row.evidence
    assert row.href == QueryContext().request_href(row.request.id)


def test_exact_receipt_without_an_incident_needs_no_executive_agenda_item(hub):
    machine(hub).machinery_status = "OCUPADA"
    record = movement(hub, receipt=receipt())
    assert all(
        item.request.id != approved(hub).id
        for item in decision_items(hub, QueryContext(), registry(record))
    )


def test_wrong_equipment_provenance_never_supplies_maintenance_claims(hub):
    unit = machine(hub)
    unit.provenance.evidence_kind = "live_read"
    unit.maintenance_is_stopped = True
    row = approved_item(hub, registry())
    assert row.equipment is None
    assert row.title == "Verificar unidad asignada"


def test_unknown_stop_condition_is_not_reported_as_no_stop(hub):
    machine(hub).maintenance_is_stopped = None
    row = approved_item(hub, registry())
    assert "OBSOLETA" in row.evidence
    assert "Sin falla activa ni paro registrados" not in row.evidence


def test_closed_request_keeps_an_unresolved_dispatch_incident_in_the_agenda(hub):
    record = movement(hub, "unknown")
    approved(hub).status = "CANCELADA"
    row = approved_item(hub, registry(record))
    assert row.title == "Conciliar el resultado del envío"
    assert row.href == QueryContext().movement_href(record.id)


def test_scope_and_href_follow_context_without_cross_mode_or_source_fallback(hub):
    context = QueryContext(query="Prisma / Proyecto", filter="unassigned")
    rows = decision_items(hub, context, registry())
    assert len(rows) == 1 and rows[0].request.machinery_id is None
    assert rows[0].href == context.request_href(rows[0].request.id)
    assert decision_items(hub, QueryContext(mode="live"), registry()) == []
    hub.sources[0].status = "error"
    assert decision_items(hub, QueryContext(), registry()) == []
