from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlmodel import Session

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
from app.models.operations import TRACKED_VEHICLE_KIND_CHECK, Actor, Movement
from app.services.ledger import (
    EvidenceMismatch,
    InvalidMovementTransition,
    LedgerError,
    MovementConflict,
    MovementNotFound,
    OperationsLedger,
    _hash,
    stable_fingerprint,
)
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)


def operation(mode="live", reference="test-movement-1", machine="test-unit-1"):
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
        provenance=provenance(machine),
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
        machinery_source_id=machine,
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


LEGACY_MOVEMENT_SQL = (
    "INSERT INTO operation_movements (id, mode, environment, movement_reference, "
    "request_source_id, machinery_source_id, project_source_id, mapping, source_request, "
    "source_request_hash, identity_hash, preparation, state, job_id, created_at, updated_at, "
    "next_review_at) VALUES (:id, 'live', 'sandbox', :id, 'req-1', 'eq-1', 'proj-1', '{}', "
    "'{}', 'h', 'i', '{}', :state, :job_id, :at, :at, :at)"
)
# Stored the way SQLite keeps UTCDateTime: naive text read back as UTC.
LEGACY_AT = "2026-09-12 18:00:00.000000"
LEGACY_EVENT_SQL = (
    "INSERT INTO operation_events (id, movement_id, kind, recorded_at, data) "
    "VALUES (:id, :movement_id, 'created', :at, '{}')"
)


def test_migration_explicitly_creates_matching_schema_and_reverses(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = build_engine(database_url)
    assert inspect(engine).get_table_names() == []
    config = Config("alembic.ini")
    # Rows written before 0004 survive the table rebuild that adds the CHECK constraint.
    command.upgrade(config, "0003_users")
    with engine.begin() as connection:
        connection.execute(
            text(LEGACY_MOVEMENT_SQL),
            {"id": "legacy-1", "state": "sent", "job_id": "job-1", "at": LEGACY_AT},
        )
        connection.execute(
            text(LEGACY_EVENT_SQL), {"id": "event-1", "movement_id": "legacy-1", "at": LEGACY_AT}
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), metadata) == []
        # compare_metadata ignores index predicates on SQLite; read the rendered DDL instead.
        indexes = dict(
            connection.execute(
                text("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL")
            ).all()
        )
        assert indexes["uq_operation_movements_job_identity"].startswith("CREATE UNIQUE INDEX")
        assert indexes["uq_operation_movements_job_identity"].endswith("WHERE job_id IS NOT NULL")
        assert indexes["uq_operation_movements_inflight_machine"].startswith("CREATE UNIQUE INDEX")
        assert indexes["uq_operation_movements_inflight_machine"].endswith(
            "WHERE state IN ('queued', 'sending', 'unknown')"
        )
        assert "ix_operation_snapshots_mode_recorded" in indexes
        assert not {"ix_operation_movements_mode", "ix_operation_movements_dispatch"} & set(indexes)
        assert "ix_operation_snapshots_mode" not in indexes
        table_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE name = 'operation_movements'")
        ).scalar_one()
        assert f"CONSTRAINT {TRACKED_VEHICLE_KIND_CHECK} CHECK" in table_sql
        assert connection.execute(
            text("SELECT id, job_id, tracked_vehicle_kind FROM operation_movements")
        ).all() == [("legacy-1", "job-1", None)]
        assert connection.execute(
            text("SELECT id, actor_user_id, actor_role, actor_kind FROM operation_events")
        ).all() == [("event-1", None, None, None)]
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "operation_movements",
        "operation_events",
        "operation_snapshots",
        "users",
    }
    command.downgrade(config, "0003_users")
    with engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("operation_events")}
        assert not columns & {"actor_user_id", "actor_role", "actor_kind"}
        assert connection.execute(text("SELECT id FROM operation_events")).all() == [("event-1",)]
        assert connection.execute(text("SELECT id FROM operation_movements")).all() == [
            ("legacy-1",)
        ]
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
    # An unknown outcome keeps the machine's single in-flight slot until it is reconciled.
    second = ledger.create("live", *operation(reference="test-crashed-movement"))
    with pytest.raises(MovementConflict):
        ledger.queue(second.id)
    # An explicitly verified reconciliation can record the existing remote task.
    assert ledger.finish_sent(row.id, "verified-existing-job").state == "sent"
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(row.id)
    ledger.queue(second.id)
    ledger.claim(second.id)
    assert ledger.recover_stale_sending(datetime.now(UTC) + timedelta(seconds=1)) == 1
    assert ledger.get(second.id, "live").state == "unknown"
    assert ledger.recover_stale_sending(datetime.now(UTC) + timedelta(seconds=1)) == 0
    assert ledger.claim() is None


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
    hub.mode = "live"
    with pytest.raises(EvidenceMismatch):
        ledger.record_snapshot(hub)


def test_second_inflight_movement_for_same_machine_is_rejected_until_reconciled(ledger):
    first = ledger.create("live", *operation(reference="test-ref-1"))
    ledger.queue(first.id)
    ledger.claim(first.id)
    second = ledger.create("live", *operation(reference="test-ref-2"))
    assert second.state == "draft"
    with pytest.raises(MovementConflict) as blocked:
        ledger.queue(second.id)
    assert first.id in str(blocked.value) and "estado sending" in str(blocked.value)
    ledger.finish_unknown(first.id, "provider_timeout")
    with pytest.raises(MovementConflict) as blocked:
        ledger.queue(second.id)
    assert first.id in str(blocked.value) and "estado unknown" in str(blocked.value)
    assert ledger.get(second.id, "live").state == "draft"
    # Another machine, the sample mode or another environment never share the slot.
    third = ledger.create("live", *operation(reference="test-ref-3", machine="test-unit-2"))
    assert ledger.queue(third.id).state == "queued"
    with Session(ledger.engine) as session:
        for index, values in enumerate([{"mode": "fixture"}, {"environment": "local"}]):
            columns = ledger.get(second.id, "live").model_dump(exclude={"events"})
            columns.update(
                id=f"test-other-slot-{index}",
                identity_hash="test",
                state="queued",
                **values,
            )
            session.add(Movement(**columns))
            session.commit()
    # Leaving unknown is an explicit operator decision, never an automatic retry.
    with pytest.raises(LedgerError):
        ledger.resolve_unknown(first.id, "live", reason_code="free text is not a code")
    with pytest.raises(InvalidMovementTransition):
        ledger.resolve_unknown(second.id, "live", reason_code="operator_resolved")
    with pytest.raises(EvidenceMismatch):
        ledger.resolve_unknown(first.id, "fixture", reason_code="operator_resolved")
    operator = Actor(user_id="7", email="x@y", role="logistica", kind="session")
    resolved = ledger.resolve_unknown(
        first.id, "live", reason_code="operator_resolved", actor=operator
    )
    assert resolved.state == "failed" and resolved.reason_code == "operator_resolved"
    assert resolved.events[-1].kind == "resolved"
    assert resolved.events[-1].state == "failed"
    assert resolved.events[-1].data == {
        "reason_code": "operator_resolved",
        "previous_state": "unknown",
    }
    assert resolved.events[-1].actor_kind == "session"
    assert resolved.events[-1].actor_user_id == "7"
    assert ledger.queue(second.id).state == "queued"
    with pytest.raises(InvalidMovementTransition):
        ledger.resolve_unknown(first.id, "live", reason_code="operator_resolved")
    with pytest.raises(InvalidMovementTransition):
        ledger.queue(first.id)


def test_verified_finish_sent_frees_the_machine_slot(ledger):
    first = ledger.create("live", *operation(reference="test-ref-1"))
    ledger.queue(first.id)
    ledger.claim(first.id)
    ledger.finish_unknown(first.id)
    second = ledger.create("live", *operation(reference="test-ref-2"))
    with pytest.raises(MovementConflict):
        ledger.queue(second.id)
    assert ledger.finish_sent(first.id, "job-1").state == "sent"
    assert ledger.queue(second.id).state == "queued"


def test_inflight_guard_is_the_index_even_when_the_python_precheck_misses(ledger):
    first = ledger.create("live", *operation(reference="test-ref-1"))
    ledger.queue(first.id)
    second = ledger.create("live", *operation(reference="test-ref-2"))
    with patch.object(OperationsLedger, "_inflight_blocker", return_value=None):
        with pytest.raises(MovementConflict) as blocked:
            ledger.queue(second.id)
    assert "en vuelo" in str(blocked.value)
    # The loser's transaction rolled back: the row and the ledger stay usable.
    assert ledger.get(second.id, "live").state == "draft"
    assert [event.kind for event in ledger.get(second.id, "live").events] == ["created"]
    assert ledger.claim() is not None


def test_job_id_cannot_link_two_movements(ledger):
    first = ledger.create("live", *operation(reference="test-ref-1"))
    ledger.queue(first.id)
    ledger.claim(first.id)
    ledger.finish_sent(first.id, "job-1")
    second = ledger.create("live", *operation(reference="test-ref-2"))
    ledger.queue(second.id)
    ledger.claim(second.id)
    with pytest.raises(MovementConflict) as conflict:
        ledger.finish_sent(second.id, "job-1")
    assert first.id in str(conflict.value) and "estado sent" in str(conflict.value)
    assert ledger.get(second.id, "live").state == "sending"
    with patch.object(OperationsLedger, "_job_holder", return_value=None):
        with pytest.raises(MovementConflict):
            ledger.finish_sent(second.id, "job-1")
    assert ledger.get(second.id, "live").state == "sending"
    assert [event.kind for event in ledger.get(second.id, "live").events][-1] == "sending"
    assert ledger.finish_sent(second.id, "job-2").state == "sent"
    with pytest.raises(MovementNotFound):
        ledger.finish_sent("missing", "job-3")


def test_receipt_and_transitions_record_actor_without_fabrication(ledger):
    row = sent_movement(ledger)
    declarant = Actor(user_id="7", email="x@y", role="logistica", kind="session")
    declaration = {"receiver": "Receptor declarado", "received_at": OBSERVED, "reference": "ACTA-1"}
    received = ledger.record_receipt(row.id, "live", **declaration, declared_by=declarant)
    assert received.receipt.receiver == "Receptor declarado"
    assert received.receipt.declared_by_user_id == "7"
    assert received.receipt.declared_by_email == "x@y"
    assert received.receipt.declared_by_role == "logistica"
    event = received.events[-1]
    assert (event.kind, event.actor_kind, event.actor_user_id, event.actor_role) == (
        "receipt",
        "session",
        "7",
        "logistica",
    )
    # The same declaration repeated by another user is idempotent, not a conflict.
    other = Actor(user_id="8", email="z@y", role="gerencia_proyecto", kind="session")
    again = ledger.record_receipt(row.id, "live", **declaration, declared_by=other)
    assert again.receipt.declared_by_email == "x@y"
    assert len(again.events) == len(received.events)
    with pytest.raises(MovementConflict):
        ledger.record_receipt(
            row.id, "live", **{**declaration, "reference": "ACTA-2"}, declared_by=other
        )
    # Without an actor nothing is invented.
    second = ledger.create("live", *operation(reference="test-ref-2"))
    ledger.queue(second.id)
    ledger.claim(second.id)
    ledger.finish_sent(second.id, "job-2")
    plain = ledger.record_receipt(second.id, "live", **declaration)
    assert (
        plain.receipt.declared_by_user_id,
        plain.receipt.declared_by_email,
        plain.receipt.declared_by_role,
    ) == (None, None, None)
    assert all(
        (event.actor_kind, event.actor_user_id, event.actor_role) == (None, None, None)
        for event in plain.events
    )
    # Local development and the worker only state their kind; no user is fabricated.
    local = Actor(kind="local_dev")
    worker = Actor(kind="cli_worker")
    third = ledger.create("live", *operation(reference="test-ref-3"), actor=local)
    assert (third.events[0].actor_kind, third.events[0].actor_user_id) == ("local_dev", None)
    ledger.queue(third.id, actor=local)
    claimed = ledger.claim(third.id, actor=worker)
    assert (claimed.events[-1].actor_kind, claimed.events[-1].actor_user_id) == (
        "cli_worker",
        None,
    )
    assert ledger.finish_unknown(third.id, actor=worker).events[-1].actor_kind == "cli_worker"
    sent = ledger.finish_sent(third.id, "job-3", actor=worker)
    assert sent.events[-1].actor_kind == "cli_worker" and sent.events[-1].actor_role is None
    receipt = ledger.record_receipt(third.id, "live", **declaration, declared_by=local)
    assert receipt.receipt.declared_by_user_id is None
    assert receipt.events[-1].actor_kind == "local_dev"
    with pytest.raises(ValidationError):
        Actor(kind="session")
    with pytest.raises(ValidationError):
        Actor(kind="cli_worker", user_id="7")
    with pytest.raises(ValidationError):
        Actor(kind="local_dev", email="x@y")


def test_identity_hash_includes_tracked_vehicle_kind_only_when_declared(ledger):
    request, equipment, mapping = operation()
    first = ledger.create(
        "live",
        request,
        equipment,
        mapping,
        tracked_vehicle_id="test-vehicle-1",
        tracked_vehicle_kind="transporter",
    )
    assert first.tracked_vehicle_kind == "transporter"
    repeated = ledger.create(
        "live",
        request,
        equipment,
        mapping,
        tracked_vehicle_id="test-vehicle-1",
        tracked_vehicle_kind="transporter",
    )
    assert repeated.id == first.id
    for kind in ["machine_device", None]:
        with pytest.raises(MovementConflict):
            ledger.create(
                "live",
                request,
                equipment,
                mapping,
                tracked_vehicle_id="test-vehicle-1",
                tracked_vehicle_kind=kind,
            )
    with pytest.raises(LedgerError):
        ledger.create(
            "live",
            *operation(reference="test-ref-x"),
            tracked_vehicle_id="test-vehicle-1",
            tracked_vehicle_kind="drone",
        )
    with pytest.raises(LedgerError):
        ledger.create(
            "live", *operation(reference="test-ref-x"), tracked_vehicle_kind="transporter"
        )
    # Movements created before migration 0004 keep exactly their hash: a repeated plan
    # without a kind still resolves to the same movement instead of conflicting.
    legacy = ledger.create(
        "live", *operation(reference="test-legacy"), tracked_vehicle_id="test-vehicle-1"
    )
    with Session(ledger.engine) as session:
        assert session.get(Movement, legacy.id).identity_hash == _hash(
            {
                "mapping": legacy.mapping,
                "payload": legacy.payload,
                "tracked_vehicle_id": "test-vehicle-1",
            }
        )
    assert (
        ledger.create(
            "live", *operation(reference="test-legacy"), tracked_vehicle_id="test-vehicle-1"
        ).id
        == legacy.id
    )
    ledger.queue(first.id)
    ledger.claim(first.id)
    ledger.finish_sent(first.id, "job-1")
    assert ledger.get(first.id, "live").tracked_vehicle_kind == "transporter"


def test_stable_fingerprint_ignores_read_timestamps_and_skips_unchanged_rewrites(ledger):
    request, equipment, mapping = operation()
    reread = request.model_copy(deep=True)
    reread.provenance.observed_at += timedelta(hours=3)
    reread.provenance.observed_on = date(2026, 9, 13)
    assert stable_fingerprint(request) == stable_fingerprint(reread)
    changed = request.model_copy(deep=True)
    changed.status = "PENDIENTE"
    assert stable_fingerprint(changed) != stable_fingerprint(request)
    first = ledger.create("live", request, equipment, mapping)
    assert first.source_request_hash == stable_fingerprint(request)
    assert first.source_request_hash == stable_fingerprint(first.source_request)
    assert first.source_equipment_hash == stable_fingerprint(equipment)
    assert first.source_request["provenance"]["observed_at"] == "2026-09-12T18:00:00Z"
    equipment_reread = equipment.model_copy(deep=True)
    equipment_reread.provenance.observed_at += timedelta(hours=3)
    again = ledger.revalidate(first.id, "live", reread, equipment_reread)
    assert again.source_request_hash == first.source_request_hash
    assert again.source_equipment_hash == first.source_equipment_hash
    # An unchanged re-read is not rewritten: the row keeps the read time of its last
    # real change and no "revalidated" event is appended (ADR 0006).
    assert again.source_request["provenance"]["observed_at"] == "2026-09-12T18:00:00Z"
    assert again.source_request["provenance"]["observed_on"] is None
    assert [event.kind for event in again.events].count("revalidated") == 0


def test_arrival_observation_requires_event_time(ledger):
    row = sent_movement(ledger)
    visit = observation(kind="arrival", poi_id="test-poi", tracked_asset_id="test-vehicle-1")
    visit["event_time"] = None
    with pytest.raises(LedgerError):
        ledger.record_observation(row.id, "live", **visit)
    assert all(event.kind != "arrival" for event in ledger.get(row.id, "live").events)
    # A task read without a fact date remains an observation-only event.
    task = observation(status="Pendiente")
    task["event_time"] = None
    assert ledger.record_observation(row.id, "live", **task).events[-1].event_time is None


def test_optional_observation_keys_only_change_evidence_when_present(ledger):
    row = sent_movement(ledger)
    first = ledger.record_observation(row.id, "live", **observation(status="Completada"))
    with_none = observation(
        status="Completada", creation_date=None, end_date_raw=None, tracked_asset_kind=None
    )
    assert len(ledger.record_observation(row.id, "live", **with_none).events) == len(first.events)
    explicit = observation(status="Completada", creation_date="2026-09-12 10:00:00-06:00")
    stored = ledger.record_observation(row.id, "live", **explicit)
    assert len(stored.events) == len(first.events) + 1
    assert stored.events[-1].data["creation_date"] == "2026-09-12 10:00:00-06:00"
    assert "tracked_asset_kind" not in stored.events[-1].data
    visit = observation(
        kind="arrival",
        poi_id="test-poi",
        tracked_asset_id="test-vehicle-1",
        tracked_asset_kind="transporter",
        end_date_raw="2026-09-12 13:00:00-06:00",
    )
    arrival = ledger.record_observation(row.id, "live", **visit).events[-1]
    assert arrival.data["tracked_asset_kind"] == "transporter"
    assert arrival.data["end_date_raw"] == "2026-09-12 13:00:00-06:00"
    with pytest.raises(LedgerError):
        ledger.record_observation(
            row.id,
            "live",
            **observation(
                kind="arrival",
                poi_id="test-poi",
                tracked_asset_id="test-vehicle-1",
                tracked_asset_kind="drone",
            ),
        )
