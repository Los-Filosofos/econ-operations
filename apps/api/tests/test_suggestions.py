"""Candidate suggestions are read-only, rule-based and never an assignment or a location claim."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.suggestions import router
from app.core.config import Settings
from app.integrations.fixtures import fixture_records
from app.main import create_app
from app.models import metadata
from app.models.hub import HubResponse, HubScope, HubSummary, SourceStatus
from app.models.operations import MovementRecord, ReceiptRecord
from app.models.suggestions import AssignmentSuggestion, CandidateUnit
from app.models.workflow import WorkflowOverview
from app.services.suggestions import suggest_assignment

CF01 = "nexus:equipment:2a49b73e-a139-4ef1-866b-d54ef246fb46"
CF02 = "nexus:equipment:7328e8f3-7ada-4f6f-88a1-58cc4ddfd862"
CF03 = "nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"
EXC01 = "nexus:equipment:96519214-2337-4015-8e7c-ab3fdc112f06"
EXC02 = "nexus:equipment:30f98953-96e6-469e-92a5-19cd3431dd5c"
PENDING_ID = "nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"
PENDING_SOURCE_ID = "0cbbbd77-4593-4791-9be5-afd46b06c888"
APPROVED_ID = "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
SUGGESTIONS_PATH = "/api/v1/requests/{request_id}/suggestions"


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


def registry(*movements, available=True, complete=None):
    return WorkflowOverview(
        available=available,
        complete=available if complete is None else complete,
        message="Test ledger",
        movements=list(movements),
    )


def pending(hub):
    return next(request for request in hub.requests if request.id == PENDING_ID)


def unit(hub, equipment_id):
    return next(item for item in hub.equipment if item.id == equipment_id)


def candidate(suggestion: AssignmentSuggestion, equipment_id: str) -> CandidateUnit:
    return next(item for item in suggestion.candidates if item.equipment_id == equipment_id)


def movement(hub, equipment_id=CF01, state="draft", scheduled_date="2026-09-17", **changes):
    request = pending(hub)
    equipment = unit(hub, equipment_id)
    record = MovementRecord(
        id=f"test-movement-{state}-{scheduled_date}",
        mode=hub.mode,
        environment=request.provenance.environment,
        movement_reference=f"test-reference-{state}",
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
        created_at=datetime(2026, 9, 12, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
        events=[],
    )
    return record.model_copy(update=changes, deep=True)


def receipt():
    return ReceiptRecord(
        receiver="Test receiver",
        reference="TEST-ACTA",
        received_at=datetime(2026, 9, 18, tzinfo=UTC),
        recorded_at=datetime(2026, 9, 18, tzinfo=UTC),
    )


def test_fixture_candidates_are_tiered_with_visible_exclusions_and_missing_facts(hub):
    suggestion = suggest_assignment(hub, PENDING_ID)
    assert suggestion is not None and suggestion.applicable is True
    assert suggestion.remote_writes is False
    assert "Prisma" in suggestion.authority_note and "asignar" in suggestion.authority_note
    assert suggestion.request_source_id == PENDING_SOURCE_ID
    assert suggestion.requested_class == "Cargador frontal"
    assert (suggestion.requested_starts_on, suggestion.requested_ends_on) == (
        "2026-09-16",
        "2026-09-18",
    )
    assert suggestion.scope.equipment_returned == 5 and suggestion.scope.equipment_total == 15
    assert suggestion.scope.complete is False
    assert suggestion.registry.status == "not_queried"
    assert "5 de 15" in suggestion.message and "no permite afirmar" in suggestion.message
    tiers = {item.label: item.eligibility for item in suggestion.candidates}
    assert tiers == {
        "CF-01": "eligible",
        "CF-02": "eligible",
        "CF-03": "excluded",
        "EXC-01": "excluded",
        "EXC-02": "excluded",
    }
    cf01 = candidate(suggestion, CF01)
    assert cf01.class_match is True
    assert (cf01.requested_class, cf01.equipment_class) == ("Cargador frontal", "Cargador frontal")
    assert cf01.review_reasons == [] and cf01.exclusion_reasons == []
    assert any("DISPONIBLE" in reason and "no acredita" in reason for reason in cf01.reasons)
    assert cf01.operators_known is False
    assert any("Operadores asociados" in item for item in cf01.missing)
    assert any("Tarifa por proyecto" in item for item in cf01.missing)
    assert any("Ubicación física" in item and "GPS" in item for item in cf01.missing)
    assert any("Registro de movimientos: sin consultar" in item for item in cf01.missing)
    assert not any("Paro de mantenimiento: no verificable" in item for item in cf01.missing)
    assert cf01.provenance.evidence_kind == "provided_sample"
    cf03 = candidate(suggestion, CF03)
    assert any("OBSOLETA" in reason for reason in cf03.exclusion_reasons)
    assert not any(
        "avería" in reason and "afirma avería" not in reason for reason in cf03.exclusion_reasons
    )
    assert cf03.same_project_evidence is not None
    assert "administrativo, no observado" in cf03.same_project_evidence.fact
    assert cf03.same_project_evidence.nature == "administrative"
    assert cf03.same_project_evidence.observed_on == date(2026, 9, 12)
    for label in ("EXC-01", "EXC-02"):
        item = next(c for c in suggestion.candidates if c.label == label)
        assert item.class_match is False
        assert (item.requested_class, item.equipment_class) == ("Cargador frontal", "Excavadora")
        assert any("Clase distinta" in reason for reason in item.exclusion_reasons)
    assert suggestion.similar_classes == []
    assert any("GPS" in rule for rule in suggestion.rules)
    fields = set(AssignmentSuggestion.model_fields) | set(CandidateUnit.model_fields)
    assert not any(
        token in name for name in fields for token in ("eta", "distance", "score", "rank", "gps")
    )


def test_not_applicable_for_approved_or_already_linked_requests(hub):
    approved = suggest_assignment(hub, APPROVED_ID)
    assert approved is not None and approved.applicable is False
    assert approved.candidates == [] and "APROBADA" in approved.message
    assert approved.scope.equipment_total == 15
    linked = pending(hub)
    linked.machinery_id = CF01
    suggestion = suggest_assignment(hub, PENDING_ID)
    assert suggestion.applicable is False and suggestion.candidates == []
    assert "maquinaria_id" in suggestion.message
    assert suggest_assignment(hub, "nexus:request:missing") is None
    assert suggest_assignment(hub, PENDING_SOURCE_ID).request_id == PENDING_ID


@pytest.mark.parametrize(
    ("change", "tier", "needle", "field"),
    [
        ({"machinery_status": "OCUPADA"}, "excluded", "OCUPADA", "exclusion_reasons"),
        ({"machinery_status": "EN_TRANSITO"}, "excluded", "no reconocido", "exclusion_reasons"),
        (
            {"maintenance_is_stopped": True},
            "excluded",
            "Paro de mantenimiento explícito",
            "exclusion_reasons",
        ),
        (
            {"maintenance_is_stopped": None},
            "eligible",
            "Paro de mantenimiento: no verificable",
            "missing",
        ),
        (
            {"maintenance_failure_id": "test:failure", "maintenance_status": "EN_PROCESO"},
            "review_required",
            "Falla activa test:failure (estado: EN_PROCESO)",
            "review_reasons",
        ),
    ],
)
def test_state_stop_and_failure_rules_keep_unknowns_unknown(hub, change, tier, needle, field):
    item = unit(hub, CF01)
    for name, value in change.items():
        setattr(item, name, value)
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == tier
    assert any(needle in line for line in getattr(result, field))


def test_available_unit_with_assignment_dates_is_a_contradiction_to_review(hub):
    item = unit(hub, CF01)
    item.project_id = "test:other-project"
    item.assignment_starts_on, item.assignment_ends_on = "2026-09-15", "2026-09-17"
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "review_required"
    assert any("Contradicción administrativa" in line for line in result.review_reasons)
    assert any("se cruzan del 2026-09-16 al 2026-09-17" in line for line in result.review_reasons)
    assert result.same_project_evidence is None

    item.assignment_ends_on = None
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "review_required"
    assert any(
        "no verificable" in line and "assignment_window.end" in line for line in result.missing
    )
    assert not any("se cruzan" in line for line in result.review_reasons)

    # Same project, ending before the period: administrative continuity, still a contradiction.
    item.project_id = pending(hub).project_id
    item.assignment_starts_on, item.assignment_ends_on = "2026-09-11", "2026-09-14"
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "review_required"
    assert result.same_project_evidence is not None
    assert result.same_project_evidence.field == "project_id, fecha_fin_uso"
    assert "no observado" in result.same_project_evidence.fact


def test_other_request_on_same_unit_with_overlapping_period_requires_review(hub):
    other = next(request for request in hub.requests if request.id == APPROVED_ID)
    other.machinery_id = CF01
    other.starts_on, other.ends_on = "2026-09-17", "2026-09-20"
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "review_required"
    assert result.overlapping_requests == [APPROVED_ID]
    assert any(APPROVED_ID in line and "se cruzan" in line for line in result.review_reasons)

    other.ends_on = None
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "eligible" and result.overlapping_requests == []
    assert any(APPROVED_ID in line and "no verificable" in line for line in result.missing)

    other.ends_on, other.status = "2026-09-20", "CANCELADA"
    result = candidate(suggest_assignment(hub, PENDING_ID), CF01)
    assert result.eligibility == "eligible" and result.overlapping_requests == []


@pytest.mark.parametrize("state", ["draft", "queued", "sending", "unknown", "sent"])
def test_open_movements_of_the_unit_require_review(hub, state):
    record = movement(hub, state=state)
    result = candidate(suggest_assignment(hub, PENDING_ID, registry(record)), CF01)
    assert result.eligibility == "review_required"
    assert result.overlapping_movements == [record.id]
    assert any("dentro del período" in line for line in result.review_reasons)
    assert (
        candidate(suggest_assignment(hub, PENDING_ID, registry(record)), CF02).eligibility
        == "eligible"
    )


def test_closed_later_or_foreign_movements_do_not_flag_and_partial_registry_is_missing(hub):
    received = movement(hub, state="sent", receipt=receipt())
    later = movement(hub, state="queued", scheduled_date="2026-09-25")
    before = movement(hub, state="queued", scheduled_date="2026-09-10")
    elsewhere = movement(hub, state="queued", environment="local")
    undated = movement(hub, state="draft", scheduled_date=None)
    result = candidate(
        suggest_assignment(hub, PENDING_ID, registry(received, later, elsewhere)), CF01
    )
    assert result.eligibility == "eligible" and result.overlapping_movements == []
    assert any("después del período" in line for line in result.reasons)
    result = candidate(suggest_assignment(hub, PENDING_ID, registry(before)), CF01)
    assert result.eligibility == "review_required"
    assert result.overlapping_movements == [before.id]
    assert any("antes del período" in line for line in result.review_reasons)
    result = candidate(suggest_assignment(hub, PENDING_ID, registry(undated)), CF01)
    assert result.eligibility == "eligible"
    assert any("scheduled.start" in line for line in result.missing)
    partial = candidate(suggest_assignment(hub, PENDING_ID, registry(complete=False)), CF01)
    assert any("Registro de movimientos parcial" in line for line in partial.missing)
    unread = candidate(suggest_assignment(hub, PENDING_ID, registry(available=False)), CF01)
    assert any("sin consultar" in line for line in unread.missing)
    complete = candidate(suggest_assignment(hub, PENDING_ID, registry()), CF01)
    assert not any("Registro de movimientos" in line for line in complete.missing)


def test_plural_class_spelling_yields_no_eligible_and_similar_classes_without_changing_tier(hub):
    request = pending(hub)
    request.machinery_type = "Retroexcavadoras"
    unit(hub, CF01).equipment_class = "Retroexcavadora"
    unit(hub, CF02).equipment_class = "RETROEXCAVADORAS "
    suggestion = suggest_assignment(hub, PENDING_ID)
    assert suggestion.similar_classes == ["RETROEXCAVADORAS", "Retroexcavadora"]
    assert all(item.eligibility == "excluded" for item in suggestion.candidates)
    assert "0 unidad(es) elegible(s)" in suggestion.message
    assert "similar_classes" in suggestion.message
    similar = candidate(suggestion, CF01)
    assert (similar.requested_class, similar.equipment_class) == (
        "Retroexcavadoras",
        "Retroexcavadora",
    )
    assert similar.class_match is False
    assert any(
        "«Retroexcavadoras» vs unidad «Retroexcavadora»" in r for r in similar.exclusion_reasons
    )
    exact = unit(hub, EXC01)
    exact.equipment_class = " Retroexcavadoras "
    assert candidate(suggest_assignment(hub, PENDING_ID), EXC01).class_match is True


def test_candidates_from_other_evidence_kind_or_source_never_appear(hub):
    foreign = unit(hub, CF01)
    foreign.provenance.evidence_kind = "live_read"
    foreign.provenance.observed_at = datetime(2026, 9, 12, tzinfo=UTC)
    startrack = unit(hub, CF02)
    startrack.provenance.source = "startrack"
    suggestion = suggest_assignment(hub, PENDING_ID)
    assert {item.equipment_id for item in suggestion.candidates} == {CF03, EXC01, EXC02}
    assert "3 de 15" in suggestion.message


def test_order_is_deterministic_by_tier_evidence_and_id(hub):
    first = suggest_assignment(hub, PENDING_ID)
    assert [item.label for item in first.candidates] == [
        "CF-01",
        "CF-02",
        "CF-03",
        "EXC-02",
        "EXC-01",
    ]
    hub.equipment.reverse()
    second = suggest_assignment(hub, PENDING_ID)
    assert [item.equipment_id for item in second.candidates] == [
        item.equipment_id for item in first.candidates
    ]
    unit(hub, CF01).maintenance_failure_id = "test:failure"
    third = suggest_assignment(hub, PENDING_ID)
    assert [item.label for item in third.candidates] == [
        "CF-02",
        "CF-01",
        "CF-03",
        "EXC-02",
        "EXC-01",
    ]


def test_endpoint_reads_the_bounded_hub_without_assigning(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'suggestions.db'}", _env_file=None)
    app = create_app(settings)
    if SUGGESTIONS_PATH not in app.openapi()["paths"]:
        app.include_router(router)
    operation = app.openapi()["paths"][SUGGESTIONS_PATH]["get"]
    assert operation["summary"] and operation["description"] and "404" in operation["responses"]
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        ok = client.get(f"/api/v1/requests/{PENDING_ID}/suggestions")
        assert ok.status_code == 200, ok.text
        assert ok.headers["cache-control"] == "no-store"
        body = ok.json()
        assert body["schema_version"] == "1.0" and body["mode"] == "fixture"
        assert body["applicable"] is True and body["remote_writes"] is False
        assert body["authority_note"]
        assert body["registry"]["status"] == "available"
        assert body["scope"]["equipment_total"] == 15 and body["scope"]["complete"] is False
        assert [c["label"] for c in body["candidates"] if c["eligibility"] == "eligible"] == [
            "CF-01",
            "CF-02",
        ]
        assert not any("Registro de movimientos" in m for m in body["candidates"][0]["missing"])
        by_source = client.get(f"/api/v1/requests/{PENDING_SOURCE_ID}/suggestions").json()
        assert by_source["request_id"] == PENDING_ID
        approved = client.get(f"/api/v1/requests/{APPROVED_ID}/suggestions").json()
        assert approved["applicable"] is False and approved["candidates"] == []
        missing = client.get("/api/v1/requests/nexus:request:missing/suggestions")
        assert missing.status_code == 404
        assert (
            missing.json()["detail"] == "La solicitud no está en la lectura acotada de este origen."
        )
        assert (
            client.get(f"/api/v1/requests/{PENDING_ID}/suggestions?mode=imaginary").status_code
            == 422
        )
        assert client.get(f"/api/v1/requests/{'x' * 201}/suggestions").status_code == 422
        live = client.get(f"/api/v1/requests/{PENDING_ID}/suggestions?mode=live")
        assert live.status_code == 404
