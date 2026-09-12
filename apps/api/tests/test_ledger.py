from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.core.database import build_engine
from app.models import metadata
from app.models.hub import (
    EquipmentRecord,
    HubResponse,
    HubScope,
    HubSummary,
    Provenance,
    RequestRecord,
)
from app.services.ledger import (
    EvidenceMismatch,
    InvalidMovementTransition,
    LedgerError,
    MovementConflict,
    MovementNotFound,
    OperationsLedger,
)
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)


def operation(mode="live", reference="test-movement-1"):
    def provenance(source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read" if mode == "live" else "provided_sample",
            is_synthetic=True,
            source_reference="isolated test inputs, never provider records",
        )

    equipment = EquipmentRecord(
        id="test:equipment:unit-1",
        code="TEST-01",
        name="Unidad de prueba",
        project_id="test-project",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test inputs only, never served as runtime data.",
        provenance=provenance("test-unit-1"),
    )
    request = RequestRecord(
        id="test:request:request-1",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=provenance("test-request-1"),
    )
    mapping = TransferMapping(
        request_source_id="test-request-1",
        machinery_source_id="test-unit-1",
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference=reference,
        scheduled_date=date(2026, 9, 14),
    )
    return request, equipment, mapping


@pytest.fixture
def ledger(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'ledger.db'}")
    metadata.create_all(engine)  # Isolated test schema only; application never does this.
    yield OperationsLedger(engine)
    engine.dispose()


def sent_movement(ledger):
    row = ledger.create("live", *operation(), tracked_vehicle_id="test-vehicle-1")
    ledger.queue(row.id)
    ledger.claim(row.id)
    return ledger.finish_sent(row.id, "test-job-1", status="Pendiente", workflow_role="pending")


def observation(kind="task_state", when=OBSERVED, **data):
    return {
        "kind": kind,
        "source_id": "test-job-1" if kind == "task_state" else "test-visit-1",
        "event_time": when,
        "observed_at": OBSERVED + timedelta(hours=2),
        "data": {"job_id": "test-job-1", **data},
        "provenance": Provenance(
            source="startrack",
            source_id="test-job-1" if kind == "task_state" else "test-visit-1",
            environment="sandbox",
            observed_at=OBSERVED + timedelta(hours=2),
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    }


def test_migration_explicitly_creates_matching_schema_and_reverses(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = build_engine(database_url)
    assert inspect(engine).get_table_names() == []
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), metadata) == []
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "operation_movements",
        "operation_events",
        "operation_snapshots",
    }
    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_identity_is_idempotent_with_conflict_and_multiple_movements_per_request(ledger):
    request, equipment, mapping = operation()
    first = ledger.create("live", request, equipment, mapping)
    request.provenance.observed_at += timedelta(hours=1)
    equipment.provenance.observed_at += timedelta(hours=1)
    assert ledger.create("live", request, equipment, mapping).id == first.id
    assert len(ledger.get(first.id, "live").events) == 1
    changed = mapping.model_copy(update={"poi_id": "another-test-poi"})
    with pytest.raises(MovementConflict):
        ledger.create("live", request, equipment, changed)
    with pytest.raises(MovementConflict):
        ledger.create("live", request, equipment, mapping, tracked_vehicle_id="different")
    other = ledger.create("live", *operation(reference="test-movement-2"))
    assert other.id != first.id
    assert len(ledger.list("live", request_source_id="test-request-1")) == 2
    assert first.source_request["provenance"]["observed_at"] == "2026-09-12T18:00:00Z"
    assert len(first.source_request_hash) == 64
    assert first.source_equipment["machinery_status"] == "OCUPADA"


def test_concurrent_create_reuses_one_identity(ledger):
    barrier = Barrier(4)

    def create(_):
        barrier.wait()
        return OperationsLedger(ledger.engine).create("live", *operation()).id

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(create, range(4)))
    assert len(set(ids)) == 1
    assert len(ledger.list("live")) == 1


@pytest.mark.parametrize("claim_specific", [True, False])
def test_only_one_independent_session_claims_queued_movement(ledger, claim_specific):
    row = ledger.create("live", *operation())
    ledger.queue(row.id)
    barrier = Barrier(6)

    def claim(_):
        barrier.wait()
        return OperationsLedger(ledger.engine).claim(row.id if claim_specific else None)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(claim, range(6)))
    assert sum(item is not None for item in results) == 1
    durable = OperationsLedger(ledger.engine).get(row.id, "live")
    assert durable.state == "sending"
    assert [event.kind for event in durable.events] == ["created", "queued", "sending"]
    assert durable.sending_at.tzinfo is UTC


def test_unknown_timeout_or_crash_never_requeues_or_reposts(ledger):
    row = ledger.create("live", *operation())
    ledger.queue(row.id)
    ledger.claim(row.id)
    unknown = ledger.finish_unknown(row.id, "provider_timeout")
    assert unknown.reason_code == "provider_timeout"
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(row.id)
    assert ledger.claim(row.id) is None
    second = ledger.create("live", *operation(reference="test-crashed-movement"))
    ledger.queue(second.id)
    ledger.claim(second.id)
    assert ledger.recover_stale_sending(datetime.now(UTC) + timedelta(seconds=1)) == 1
    assert ledger.get(second.id, "live").state == "unknown"
    assert ledger.recover_stale_sending(datetime.now(UTC) + timedelta(seconds=1)) == 0
    assert ledger.claim() is None
    # An explicitly verified reconciliation can record the existing remote task.
    assert ledger.finish_sent(row.id, "verified-existing-job").state == "sent"
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(row.id)


def test_provider_failures_store_only_fixed_safe_codes(ledger):
    row = ledger.create("live", *operation())
    ledger.queue(row.id)
    ledger.claim(row.id)
    failed = ledger.finish_failed(row.id, "response body with password or token")
    assert failed.reason_code == "unknown"
    assert "password" not in failed.model_dump_json()
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(row.id)


def test_samples_and_live_records_cannot_cross_modes_or_create_receipts(ledger):
    live = ledger.create("live", *operation())
    sample = ledger.create("fixture", *operation("fixture"))
    assert live.id != sample.id
    assert [row.id for row in ledger.list("fixture")] == [sample.id]
    assert [row.id for row in ledger.list("live")] == [live.id]
    with pytest.raises(MovementNotFound):
        ledger.get(live.id, "fixture")
    with pytest.raises(EvidenceMismatch):
        ledger.queue(sample.id, "fixture")
    with pytest.raises(EvidenceMismatch):
        ledger.create("live", *operation("fixture", "other-sample"))
    with pytest.raises(EvidenceMismatch):
        ledger.create("fixture", *operation())
    with pytest.raises(EvidenceMismatch):
        ledger.record_receipt(
            sample.id,
            "fixture",
            receiver="Test receiver",
            received_at=OBSERVED,
            reference="test-receipt",
        )
    request, equipment, mapping = operation()
    equipment.provenance.evidence_kind = "provided_sample"
    with pytest.raises(EvidenceMismatch):
        ledger.create("live", request, equipment, mapping)


def test_pending_plan_revalidation_preserves_source_history_and_cannot_change_sent(ledger):
    request, equipment, mapping = operation()
    request.status = "PENDIENTE"
    request.machinery_id = None
    blocked = ledger.create("live", request, equipment, mapping)
    assert blocked.state == "blocked"
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(blocked.id)
    request.status = "APROBADA"
    request.machinery_id = equipment.id
    request.provenance.observed_at += timedelta(minutes=30)
    ready = ledger.revalidate(blocked.id, "live", request, equipment)
    assert ready.state == "draft"
    assert ready.source_request_hash != blocked.source_request_hash
    assert ready.events[0].data["request"]["status"] == "PENDIENTE"
    assert ready.events[-1].data["request"]["status"] == "APROBADA"
    ledger.queue(ready.id)
    with pytest.raises(InvalidMovementTransition):
        ledger.revalidate(ready.id, "live", request, equipment)


def test_revalidation_rejects_source_identity_or_evidence_change(ledger):
    request, equipment, mapping = operation()
    row = ledger.create("live", request, equipment, mapping)
    request.provenance.source_id = "unrelated-request"
    with pytest.raises(EvidenceMismatch):
        ledger.revalidate(row.id, "live", request, equipment)
    assert ledger.get(row.id, "live").source_request_hash == row.source_request_hash


def test_task_completion_and_arrival_preserve_event_times_without_inventing_receipt(ledger):
    row = sent_movement(ledger)
    completed = ledger.record_observation(
        row.id, "live", **observation(status="Completada", workflow_role="completed")
    )
    assert completed.status == "Completada"
    assert completed.receipt is None
    arrived = ledger.record_observation(
        row.id,
        "live",
        **observation(
            kind="arrival",
            poi_id="test-poi",
            tracked_asset_id="test-vehicle-1",
            label="Visita observada",
        ),
    )
    assert arrived.receipt is None
    arrival = arrived.events[-1]
    assert arrival.kind == "arrival"
    assert arrival.event_time == OBSERVED
    assert arrival.observed_at == OBSERVED + timedelta(hours=2)
    assert arrival.recorded_at > arrival.event_time
    assert arrived.source_equipment["machinery_status"] == "OCUPADA"
    received = ledger.record_receipt(
        row.id,
        "live",
        receiver="Receptor de prueba",
        received_at=OBSERVED + timedelta(minutes=40),
        reference="ACTA-TEST-1",
    )
    assert received.receipt.source == "manual_declaration"
    assert received.receipt.received_at != arrival.event_time
    assert received.events[-1].kind == "receipt"
    assert received.state == "sent"
    assert received.workflow_role == "completed"
    assert len(
        ledger.record_receipt(
            row.id,
            "live",
            receiver="Receptor de prueba",
            received_at=OBSERVED + timedelta(minutes=40),
            reference="ACTA-TEST-1",
        ).events
    ) == len(received.events)
    with pytest.raises(MovementConflict):
        ledger.record_receipt(
            row.id,
            "live",
            receiver="Otro receptor",
            received_at=OBSERVED,
            reference="OTHER-TEST-ACTA",
        )


def test_receipt_requires_sent_movement_and_zoned_explicit_evidence_but_not_arrival(ledger):
    row = ledger.create("live", *operation())
    with pytest.raises(InvalidMovementTransition):
        ledger.record_receipt(row.id, "live", receiver="Test", received_at=OBSERVED, reference="T")
    ledger.queue(row.id)
    ledger.claim(row.id)
    ledger.finish_sent(row.id, "test-job")
    for changes in [
        {"receiver": "   "},
        {"reference": ""},
        {"received_at": datetime(2026, 9, 12)},
    ]:
        with pytest.raises(LedgerError):
            ledger.record_receipt(
                row.id,
                "live",
                **{
                    "receiver": "Test",
                    "received_at": OBSERVED,
                    "reference": "TEST",
                    **changes,
                },
            )
    result = ledger.record_receipt(
        row.id, "live", receiver="Test", received_at=OBSERVED, reference="TEST"
    )
    assert result.receipt is not None
    assert all(event.kind != "arrival" for event in result.events)


def test_observation_deduplicates_repeated_reads_and_preserves_latest_status(ledger):
    row = sent_movement(ledger)
    event = observation(status="Completada", workflow_role="completed")
    recorded = ledger.record_observation(row.id, "live", **event)
    event["observed_at"] += timedelta(hours=1)
    event["provenance"].observed_at = event["observed_at"]
    repeat = ledger.record_observation(row.id, "live", **event)
    assert len(repeat.events) == len(recorded.events)
    earlier = observation(when=OBSERVED - timedelta(hours=1), status="Pendiente")
    late = ledger.record_observation(row.id, "live", **earlier)
    assert late.status == "Completada"
    assert len(late.events) == len(recorded.events) + 1
    wrong_evidence = observation(status="Completada")
    wrong_evidence["provenance"].evidence_kind = "provided_sample"
    with pytest.raises(EvidenceMismatch):
        ledger.record_observation(row.id, "live", **wrong_evidence)
    with pytest.raises(EvidenceMismatch):
        ledger.record_observation(row.id, "live", **observation(job_id="unrelated-job"))
    with pytest.raises(LedgerError):
        ledger.record_observation(row.id, "live", **observation(error="raw provider error"))


@pytest.mark.parametrize(
    "change",
    [
        {"poi_id": "unrelated-poi"},
        {"tracked_asset_id": "unrelated-vehicle"},
        {"tracked_asset_id": None},
    ],
)
def test_arrival_requires_both_explicit_destination_and_tracked_vehicle(ledger, change):
    row = sent_movement(ledger)
    facts = {"poi_id": "test-poi", "tracked_asset_id": "test-vehicle-1", **change}
    with pytest.raises(EvidenceMismatch):
        ledger.record_observation(row.id, "live", **observation(kind="arrival", **facts))
    assert all(event.kind != "arrival" for event in ledger.get(row.id, "live").events)


def test_task_evidence_requires_exact_source_and_provenance_ids(ledger):
    row = sent_movement(ledger)
    for change in ["source_id", "provenance"]:
        event = observation(status="Completada")
        if change == "source_id":
            event["source_id"] = "another-job"
        else:
            event["provenance"].source_id = "another-job"
        with pytest.raises(EvidenceMismatch):
            ledger.record_observation(row.id, "live", **event)


def test_snapshots_preserve_partial_coverage_and_never_cross_modes(ledger):
    request, equipment, _ = operation("fixture")
    hub = HubResponse(
        mode="fixture",
        generated_at=OBSERVED,
        data_as_of=None,
        sources=[],
        scope=HubScope(
            search="",
            equipment_total=15,
            requests_total=2,
            complete=False,
            description="Partial supplied source examples",
        ),
        summary=HubSummary(),
        requests=[request],
        equipment=[equipment],
        alerts=[],
    )
    snapshot = ledger.record_snapshot(hub)
    assert snapshot.data_as_of is None
    assert snapshot.content["scope"]["complete"] is False
    assert snapshot.content["equipment"][0]["provenance"]["evidence_kind"] == "provided_sample"
    assert ledger.last_snapshot("fixture").id == snapshot.id
    assert ledger.last_snapshot("live") is None
    with pytest.raises(MovementNotFound):
        ledger.get_snapshot(snapshot.id, "live")
    hub.mode = "live"
    with pytest.raises(EvidenceMismatch):
        ledger.record_snapshot(hub)
