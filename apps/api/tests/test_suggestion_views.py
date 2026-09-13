"""Suggestions and date conflicts render the rule services; nothing assigns, ranks or locates."""

import json
from datetime import UTC, datetime

import pytest
from plotly.utils import PlotlyJSONEncoder

from app.dashboard.context import QueryContext
from app.dashboard.suggestion_views import conflicts_section, suggestions_section
from app.integrations.fixtures import fixture_records
from app.models.hub import HubResponse, HubScope, HubSummary, SourceStatus
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview
from app.services.hub import evaluate_alerts

CF01 = "nexus:equipment:2a49b73e-a139-4ef1-866b-d54ef246fb46"
CF02 = "nexus:equipment:7328e8f3-7ada-4f6f-88a1-58cc4ddfd862"
CF03 = "nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"
PENDING_ID = "nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"
APPROVED_ID = "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
AT = datetime(2026, 9, 12, tzinfo=UTC)


def serialized(value) -> str:
    return json.dumps(value, cls=PlotlyJSONEncoder, ensure_ascii=False)


@pytest.fixture
def hub():
    equipment, requests = fixture_records()
    hub = HubResponse(
        mode="fixture",
        generated_at=datetime(2040, 1, 1, tzinfo=UTC),
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma",
                status="fixture",
                environment="sandbox",
                message="Provided samples",
            )
        ],
        scope=HubScope(
            search="",
            equipment_total=15,
            requests_total=2,
            equipment_returned=len(equipment),
            requests_returned=len(requests),
            complete=False,
            description="Provided sample scope",
        ),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )
    hub.alerts = evaluate_alerts(equipment, requests, None)
    return hub


def record(hub, identifier):
    return next(item for item in [*hub.requests, *hub.equipment] if item.id == identifier)


def registry(*movements, available=True, complete=True):
    return WorkflowOverview(
        available=available, complete=complete, message="Test ledger", movements=list(movements)
    )


def movement(
    request, equipment, reference, *, state="draft", scheduled_date="2026-09-17", **changes
):
    row = MovementRecord(
        id=f"test-{reference}",
        mode="fixture",
        environment=request.provenance.environment,
        movement_reference=reference,
        request_source_id=request.provenance.source_id,
        machinery_source_id=equipment.provenance.source_id,
        project_source_id=request.project_id,
        mapping={"scheduled_date": scheduled_date} if scheduled_date else {},
        source_request=request.model_dump(mode="json"),
        source_equipment=equipment.model_dump(mode="json"),
        source_request_hash="test-only",
        source_equipment_hash="test-only",
        payload={},
        preparation={},
        state=state,
        job_id="test-job" if state == "sent" else None,
        created_at=AT,
        updated_at=AT,
        events=[],
    )
    return row.model_copy(update=changes, deep=True)


def test_pending_request_lists_available_loaders_and_discards_obsolete_with_its_reason(hub):
    context = QueryContext()
    content = serialized(suggestions_section(hub, record(hub, PENDING_ID), None, context))
    assert "Unidades que podrían cubrir esta solicitud" in content
    assert "bulb.svg" in content
    for label, identifier in [("CF-01", CF01), ("CF-02", CF02)]:
        assert label in content
        assert context.equipment_href(identifier) in content
    assert content.count("Elegible según la lectura") == 2
    assert "solicitud «Cargador frontal» · unidad «Cargador frontal» · coincide" in content
    assert "Cumple la clase exacta y está DISPONIBLE en Prisma: valorar usarla" in content
    assert "no acredita disponibilidad física" in content
    # CF-03 keeps its same-project evidence but is excluded: no recommendation for it.
    assert "Ya está asignada al mismo proyecto" not in content
    assert "Descartadas y por qué (3)" in content
    assert "CF-03" in content and "OBSOLETA: revisar con Mantenimiento" in content
    assert "EXC-01" in content and "Clase distinta" in content
    assert "Registro de movimientos: sin consultar" in content
    assert "Recomendar no es asignar: la asignación se hace en Prisma." in content
    assert "Sin distancias ni tiempos estimados" in content
    assert "km" not in content and "minutos" not in content


def test_recommendation_phrase_follows_the_service_evidence_only(hub):
    pending = record(hub, PENDING_ID)
    unit = record(hub, CF02)
    unit.project_id, unit.project_name = pending.project_id, pending.project_name
    unit.assignment_starts_on, unit.assignment_ends_on = "2026-09-10", "2026-09-14"
    content = serialized(suggestions_section(hub, pending, None, QueryContext()))
    assert "Ya está asignada al mismo proyecto hasta 2026-09-14 y está DISPONIBLE" in content
    assert "valorar usarla tras revisar los puntos indicados" in content
    assert "no ubicación observada" in content
    assert "Por revisar" in content and "Contradicción administrativa" in content
    assert content.count("Elegible según la lectura") == 1


def test_linked_request_gets_a_note_only_while_its_unit_needs_review(hub):
    approved = record(hub, APPROVED_ID)
    context = QueryContext()
    content = serialized(suggestions_section(hub, approved, None, context))
    assert "CF-03" in content and "requiere revisión (OBSOLETA en Prisma)" in content
    assert "No aplica: la solicitud está en estado APROBADA" in content
    assert "Elegible según la lectura" not in content
    assert context.equipment_href(CF03) in content
    record(hub, CF03).machinery_status = "OCUPADA"
    assert suggestions_section(hub, approved, None, context) is None
    outsider = approved.model_copy(update={"id": "nexus:request:missing"})
    assert suggestions_section(hub, outsider, None, context) is None


def test_conflicts_stay_not_verifiable_when_a_boundary_is_missing(hub):
    approved = record(hub, APPROVED_ID)
    approved.ends_on = None
    for subject in (approved, record(hub, CF03)):
        content = serialized(conflicts_section(hub, subject, None, QueryContext()))
        assert "No verificable" in content and "usage_period.end" in content
        assert "Sin conflicto" not in content
        assert "Asignación vigente de la unidad · CF-03 · 2026-09-11 → 2026-09-14" in content
        assert "Período de uso solicitado · PROY-014 - The Hub - Proyecto Xi - La Unión" in content
        assert "1 no verificable(s) en 1 comparaciones" in content


def test_two_open_requests_on_one_unit_are_a_conflict_with_a_link_to_the_other(hub):
    pending, approved, unit = record(hub, PENDING_ID), record(hub, APPROVED_ID), record(hub, CF03)
    pending.machinery_id, pending.status = unit.id, "APROBADA"
    pending.starts_on, pending.ends_on = "2026-09-13", "2026-09-18"
    hub.alerts = evaluate_alerts(hub.equipment, hub.requests, None)
    context = QueryContext()
    content = serialized(conflicts_section(hub, approved, None, context))
    assert "Cruce" in content and "se cruzan del 2026-09-13 al 2026-09-14" in content
    assert context.request_href(pending.id) in content
    assert "ECON solo lo señala y no modifica la asignación" in content
    assert "Señales de la lectura del hub" in content and "overlapping_approved_requests" in content
    assert "alert-triangle.svg" in content
    # The other request shares the project but not the window: a discrepancy, not a block.
    other = serialized(conflicts_section(hub, pending, None, context))
    assert "Discrepancia" in other and "difiere del período aprobado" in other
    unit_view = serialized(conflicts_section(hub, unit, None, context))
    assert "1 cruce(s), 1 discrepancia(s)" in unit_view
    assert context.request_href(pending.id) in unit_view
    assert context.request_href(approved.id) in unit_view


def test_movement_schedules_and_observed_instants_are_compared_by_day(hub):
    pending, approved, unit = record(hub, PENDING_ID), record(hub, APPROVED_ID), record(hub, CF03)
    pending.machinery_id = unit.id
    late = movement(approved, unit, "late-plan", scheduled_date="2026-09-20")
    undated = movement(approved, unit, "undated-plan", state="queued", scheduled_date=None)
    foreign = movement(pending, unit, "other-request", state="queued", scheduled_date="2026-09-12")
    observed = movement(
        approved,
        unit,
        "sent-plan",
        state="sent",
        scheduled_date="2026-09-10",
        events=[
            MovementEventRecord(
                id="test-arrival",
                kind="arrival",
                event_time=datetime.fromisoformat("2026-09-12T10:00:00-06:00"),
                observed_at=AT,
                recorded_at=AT,
                data={},
            )
        ],
        receipt=ReceiptRecord(
            receiver="Receptor de prueba",
            received_at=datetime.fromisoformat("2026-09-20T10:00:00-06:00"),
            reference="TEST-ACTA",
            recorded_at=AT,
        ),
    )
    context = QueryContext()
    content = serialized(
        conflicts_section(hub, approved, registry(late, undated, foreign, observed), context)
    )
    assert "1 cruce(s), 2 discrepancia(s) y 1 no verificable(s) en 8 comparaciones" in content
    assert "Programado después del fin del período solicitado" in content
    assert "falta day" in content
    assert "traslado sin cerrar de la misma unidad para otra solicitud" in content
    assert "la recepción declarada" in content and "Fuera del período de uso" in content
    assert "Comparaciones sin cruce (4)" in content
    assert "La llegada observada 2026-09-12 cae en" in content
    for reference in ("late-plan", "undated-plan", "other-request", "sent-plan"):
        assert context.movement_href(f"test-{reference}") in content
    # Without the ledger only the window (coincides) and the other request (disjoint) remain.
    assert "Comparaciones sin cruce (2)" in serialized(
        conflicts_section(hub, approved, None, context)
    )


def test_conflicts_section_is_absent_without_comparable_dates(hub):
    assert conflicts_section(hub, record(hub, PENDING_ID), registry(), QueryContext()) is None
    assert conflicts_section(hub, record(hub, CF01), registry(), QueryContext()) is None
