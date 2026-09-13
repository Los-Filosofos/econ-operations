"""Guarantees that only PostgreSQL accredits; SQLite runs cannot stand in for them."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session

from app.core.database import build_engine
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import Actor, Movement
from app.services.ledger import MovementConflict, OperationsLedger
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)
NEW_INDEXES = {
    "uq_operation_movements_job_identity",
    "uq_operation_movements_inflight_machine",
    "ix_operation_snapshots_mode_recorded",
}
OLD_INDEXES = {
    "ix_operation_movements_mode",
    "ix_operation_movements_dispatch",
    "ix_operation_snapshots_mode",
}
TRUNCATE = "TRUNCATE operation_events, operation_movements, operation_snapshots, users"


def _movement(reference: str, **values):
    now = datetime.now(UTC)
    base = {
        "id": f"mv-{reference}",
        "mode": "live",
        "environment": "sandbox",
        "movement_reference": reference,
        "request_source_id": "req-1",
        "machinery_source_id": "eq-1",
        "project_source_id": "proj-1",
        "mapping": {},
        "source_request": {"id": "req-1"},
        "source_request_hash": "h1",
        "identity_hash": "i1",
        "preparation": {},
        "state": "draft",
        "created_at": now,
        "updated_at": now,
        "next_review_at": now,
    }
    base.update(values)
    return Movement(**base)


def _insert(engine, *rows) -> None:
    with Session(engine) as session:
        session.add_all(rows)
        session.commit()


def operation(reference: str, machine: str = "test-unit-1"):
    def provenance(source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
            source_reference="isolated test inputs, never provider records",
        )

    equipment = EquipmentRecord(
        id=f"test:equipment:{machine}",
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


def sent_movement(ledger: OperationsLedger, reference: str = "test-movement-1", job_id="job-1"):
    row = ledger.create("live", *operation(reference), tracked_vehicle_id="test-vehicle-1")
    ledger.queue(row.id)
    ledger.claim(row.id)
    return ledger.finish_sent(row.id, job_id, status="Pendiente", workflow_role="pending")


def task_observation(job_id: str, status: str, event_time: datetime, observed_at: datetime):
    return {
        "kind": "task_state",
        "source_id": job_id,
        "event_time": event_time,
        "observed_at": observed_at,
        "data": {"job_id": job_id, "status": status, "workflow_role": "pending"},
        "provenance": Provenance(
            source="startrack",
            source_id=job_id,
            environment="sandbox",
            observed_at=observed_at,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    }


def _indexes(connection, table: str) -> dict[str, str]:
    return dict(
        connection.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = :table"),
            {"table": table},
        ).all()
    )


def _trigger_present(connection) -> bool:
    return bool(
        connection.execute(
            text(
                "SELECT 1 FROM pg_trigger WHERE tgname = 'operation_events_append_only' "
                "AND NOT tgisinternal"
            )
        ).first()
    )


def test_movement_identity_is_unique_per_mode_and_environment(postgres_engine):
    _insert(postgres_engine, _movement("traslado-1"))
    with Session(postgres_engine) as session:
        session.add(_movement("traslado-1", id="mv-other"))
        with pytest.raises(IntegrityError):
            session.commit()
    _insert(postgres_engine, _movement("traslado-1", id="mv-fixture", mode="fixture"))


def test_inflight_machine_exclusivity_is_enforced_by_postgres(postgres_engine):
    _insert(postgres_engine, _movement("a", state="queued"))
    for state in ["unknown", "sending", "queued"]:
        with Session(postgres_engine) as session:
            session.add(_movement("b", id="mv-b", state=state))
            with pytest.raises(IntegrityError):
                session.commit()
    _insert(postgres_engine, _movement("b", id="mv-b", state="draft"))
    _insert(postgres_engine, _movement("c", id="mv-c", mode="fixture", state="queued"))
    _insert(postgres_engine, _movement("d", id="mv-d", environment="local", state="queued"))
    _insert(postgres_engine, _movement("e", id="mv-e", machinery_source_id="eq-2", state="queued"))
    # Leaving the in-flight states frees the slot for the next movement of the machine.
    with postgres_engine.begin() as connection:
        connection.execute(text("UPDATE operation_movements SET state = 'sent' WHERE id = 'mv-a'"))
    _insert(postgres_engine, _movement("f", id="mv-f", state="queued"))


def test_job_identity_is_unique_per_environment(postgres_engine):
    _insert(postgres_engine, _movement("a", state="sent", job_id="J1"))
    with Session(postgres_engine) as session:
        session.add(_movement("b", id="mv-b", state="sent", job_id="J1"))
        with pytest.raises(IntegrityError):
            session.commit()
    _insert(
        postgres_engine,
        _movement("b", id="mv-b", state="draft"),
        _movement("c", id="mv-c", state="failed"),
        _movement("d", id="mv-d", state="sent", job_id="J1", environment="local"),
        _movement("e", id="mv-e", state="sent", job_id="J1", mode="fixture"),
    )


def test_partial_unique_indexes_and_trigger_are_defined_as_expected(postgres_engine):
    with postgres_engine.connect() as connection:
        movements = _indexes(connection, "operation_movements")
        snapshots = _indexes(connection, "operation_snapshots")
        assert _trigger_present(connection)
    job = movements["uq_operation_movements_job_identity"]
    assert job.startswith("CREATE UNIQUE INDEX")
    assert "(mode, environment, job_id)" in job and job.endswith("WHERE (job_id IS NOT NULL)")
    inflight = movements["uq_operation_movements_inflight_machine"]
    assert inflight.startswith("CREATE UNIQUE INDEX")
    assert "(mode, environment, machinery_source_id)" in inflight
    predicate = inflight.split(" WHERE ", 1)[1]
    assert all(f"'{state}'" in predicate for state in ("queued", "sending", "unknown"))
    assert "'sent'" not in predicate and "'draft'" not in predicate
    assert "ix_operation_movements_review" in movements
    assert not OLD_INDEXES & (set(movements) | set(snapshots))
    assert "(mode, recorded_at)" in snapshots["ix_operation_snapshots_mode_recorded"]


def test_two_sessions_claim_different_queued_movements_with_skip_locked(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    first = ledger.create("live", *operation("test-ref-1"))
    ledger.queue(first.id)
    second = ledger.create("live", *operation("test-ref-2", machine="test-unit-2"))
    ledger.queue(second.id)
    holder = postgres_engine.connect()
    holder.begin()
    try:
        head = holder.execute(
            text(
                "SELECT id FROM operation_movements WHERE mode = 'live' AND state = 'queued' "
                "ORDER BY queued_at, id LIMIT 1 FOR UPDATE"
            )
        ).scalar_one()
        assert head == first.id
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=1) as pool:
            # Without SKIP LOCKED this would wait for the holder's transaction.
            claimed = pool.submit(OperationsLedger(postgres_engine).claim).result(timeout=10)
        assert time.monotonic() - started < 2
    finally:
        holder.rollback()
        holder.close()
    assert claimed is not None and claimed.id == second.id
    assert ledger.get(first.id, "live").state == "queued"
    assert ledger.claim().id == first.id
    assert ledger.claim() is None


def test_concurrent_queue_for_same_machine_lets_exactly_one_win(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    candidates = [
        ledger.create("live", *operation("test-ref-b")).id,
        ledger.create("live", *operation("test-ref-c")).id,
    ]
    barrier = Barrier(2)

    def queue(movement_id: str):
        barrier.wait()
        try:
            return OperationsLedger(postgres_engine).queue(movement_id)
        except MovementConflict as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(queue, candidates))
    winners = [item for item in results if not isinstance(item, MovementConflict)]
    losers = [item for item in results if isinstance(item, MovementConflict)]
    assert len(winners) == 1 and len(losers) == 1
    # The conflict names the movement that holds the slot and its state.
    assert winners[0].id in str(losers[0]) and "estado queued" in str(losers[0])
    states = {record.id: record.state for record in ledger.list("live")}
    assert sorted(states.values()) == ["draft", "queued"]
    loser_id = next(item for item in candidates if states[item] == "draft")
    # The loser's session rolled back cleanly: its history is untouched and it still works.
    assert [item.kind for item in ledger.get(loser_id, "live").events] == ["created"]
    with pytest.raises(MovementConflict):
        ledger.queue(loser_id)
    claimed = ledger.claim()
    assert claimed.id == winners[0].id
    ledger.finish_failed(claimed.id, "provider_rejected")
    assert ledger.queue(loser_id).state == "queued"


def test_record_observation_row_lock_serializes_concurrent_writers(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    row = sent_movement(ledger)
    times = [OBSERVED + timedelta(minutes=10 * index) for index in range(8)]

    def record(index: int) -> None:
        OperationsLedger(postgres_engine).record_observation(
            row.id,
            "live",
            **task_observation(
                "job-1", f"Status_{index}", times[index], times[index] + timedelta(minutes=1)
            ),
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in [pool.submit(record, index) for index in range(8)]:
            future.result()
    final = ledger.get(row.id, "live")
    assert len([item for item in final.events if item.kind == "task_state"]) == 8
    assert final.status == "Status_7"


def test_operation_events_are_append_only(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    row = sent_movement(ledger)
    for statement in [
        "UPDATE operation_events SET kind = 'edited' WHERE movement_id = :id",
        "DELETE FROM operation_events WHERE movement_id = :id",
    ]:
        with pytest.raises(DBAPIError) as rejected, postgres_engine.begin() as connection:
            connection.execute(text(statement), {"id": row.id})
        assert "append-only" in str(rejected.value)
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(postgres_engine, "before_cursor_execute", capture)
    try:
        ledger.record_observation(
            row.id,
            "live",
            **task_observation("job-1", "Completada", OBSERVED, OBSERVED + timedelta(hours=1)),
            actor=Actor(kind="cli_worker"),
        )
    finally:
        event.remove(postgres_engine, "before_cursor_execute", capture)
    assert any(item.upper().startswith("INSERT INTO OPERATION_EVENTS") for item in statements)
    assert not any("UPDATE OPERATION_EVENTS" in item.upper() for item in statements)
    kinds = [item.kind for item in ledger.get(row.id, "live").events]
    assert kinds == ["created", "queued", "sending", "sent", "task_state"]
    assert ledger.get(row.id, "live").events[-1].actor_kind == "cli_worker"
    # The fixture's TRUNCATE stays possible: the trigger is row-level UPDATE/DELETE only.
    with postgres_engine.begin() as connection:
        connection.execute(text(TRUNCATE))


def test_timestamptz_roundtrip_and_stale_recovery(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    row = ledger.create("live", *operation("test-ref-1"))
    ledger.queue(row.id)
    claimed = ledger.claim(row.id)
    assert claimed.sending_at.tzinfo is UTC
    assert abs(claimed.sending_at - datetime.now(UTC)) < timedelta(minutes=1)
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE operation_movements SET sending_at = now() - interval '11 minutes' "
                "WHERE id = :id"
            ),
            {"id": row.id},
        )
    assert ledger.recover_stale_sending(datetime.now(UTC) - timedelta(minutes=10)) == 1
    assert ledger.recover_stale_sending(datetime.now(UTC) - timedelta(minutes=10)) == 0
    recovered = ledger.get(row.id, "live")
    assert recovered.state == "unknown" and recovered.reason_code == "worker_interrupted"
    assert recovered.sending_at.tzinfo is UTC
    assert datetime.now(UTC) - recovered.sending_at > timedelta(minutes=10)
    sent = ledger.finish_sent(row.id, "job-1")
    assert sent.sent_at.tzinfo is UTC and sent.queued_at.tzinfo is UTC
    assert sent.events[-1].recorded_at.tzinfo is UTC


def test_receipt_json_null_guard_on_postgres(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    row = sent_movement(ledger)
    declaration = {"receiver": "Receptor de prueba", "received_at": OBSERVED, "reference": "ACTA-1"}
    first = ledger.record_receipt(
        row.id,
        "live",
        **declaration,
        declared_by=Actor(user_id="7", email="x@y", role="logistica", kind="session"),
    )
    assert first.receipt.declared_by_email == "x@y"
    again = ledger.record_receipt(
        row.id,
        "live",
        **declaration,
        declared_by=Actor(user_id="8", email="z@y", role="gerencia_proyecto", kind="session"),
    )
    assert again.receipt == first.receipt
    assert len(again.events) == len(first.events)
    with pytest.raises(MovementConflict):
        ledger.record_receipt(row.id, "live", **{**declaration, "reference": "ACTA-2"})
    with postgres_engine.connect() as connection:
        stored = connection.execute(
            text("SELECT receipt ->> 'reference' FROM operation_movements WHERE id = :id"),
            {"id": row.id},
        ).scalar_one()
    assert stored == "ACTA-1"


def _legacy_rows(connection) -> None:
    now = datetime.now(UTC)
    for movement_id, state, job_id in [("mv-1", "sent", "J1"), ("mv-2", "queued", None)]:
        connection.execute(
            text(
                "INSERT INTO operation_movements (id, mode, environment, movement_reference, "
                "request_source_id, machinery_source_id, project_source_id, mapping, "
                "source_request, source_request_hash, identity_hash, preparation, state, "
                "job_id, created_at, updated_at, next_review_at) VALUES (:id, 'live', "
                "'sandbox', :id, 'req-1', 'eq-1', 'proj-1', '{}', '{}', 'h', :id, '{}', "
                ":state, :job_id, :at, :at, :at)"
            ),
            {"id": movement_id, "state": state, "job_id": job_id, "at": now},
        )
    connection.execute(
        text(
            "INSERT INTO operation_events (id, movement_id, kind, recorded_at, data) "
            "VALUES ('ev-1', 'mv-1', 'created', :at, '{}')"
        ),
        {"at": now},
    )


def test_upgrade_0004_preserves_existing_rows(postgres_migrations_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_migrations_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0003_users")
    engine = build_engine(postgres_migrations_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(TRUNCATE))
            _legacy_rows(connection)
            assert set(_indexes(connection, "operation_movements")) & OLD_INDEXES
            assert not _trigger_present(connection)
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT id, state, job_id, tracked_vehicle_kind FROM operation_movements "
                    "ORDER BY id"
                )
            ).all() == [("mv-1", "sent", "J1", None), ("mv-2", "queued", None, None)]
            assert connection.execute(
                text("SELECT id, actor_user_id, actor_role, actor_kind FROM operation_events")
            ).all() == [("ev-1", None, None, None)]
            assert (
                connection.execute(
                    text("SELECT last_confirmed_at FROM operation_snapshots LIMIT 1")
                ).all()
                == []
            )
            present = set(_indexes(connection, "operation_movements")) | set(
                _indexes(connection, "operation_snapshots")
            )
            assert NEW_INDEXES <= present and not OLD_INDEXES & present
            assert _trigger_present(connection)
            assert connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conname = 'ck_operation_movements_tracked_vehicle_kind'"
                )
            ).first()
        command.downgrade(config, "0003_users")
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT id, state, job_id FROM operation_movements ORDER BY id")
            ).all() == [("mv-1", "sent", "J1"), ("mv-2", "queued", None)]
            assert connection.execute(text("SELECT id FROM operation_events")).all() == [("ev-1",)]
            present = set(_indexes(connection, "operation_movements")) | set(
                _indexes(connection, "operation_snapshots")
            )
            assert OLD_INDEXES <= present and not NEW_INDEXES & present
            assert not _trigger_present(connection)
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_upgrade_0004_fails_on_existing_violations_without_touching_rows(
    postgres_migrations_url, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", postgres_migrations_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0003_users")
    engine = build_engine(postgres_migrations_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(TRUNCATE))
            _legacy_rows(connection)
            # A second movement already linked to J1: the documented pre-check would list it.
            connection.execute(
                text(
                    "UPDATE operation_movements SET state = 'sent', job_id = 'J1' WHERE id = 'mv-2'"
                )
            )
        with pytest.raises(IntegrityError):
            command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0003_users")
            assert connection.execute(
                text("SELECT id, job_id FROM operation_movements ORDER BY id")
            ).all() == [("mv-1", "J1"), ("mv-2", "J1")]
            assert (
                connection.execute(text("SELECT count(*) FROM operation_events")).scalar_one() == 1
            )
            assert not _trigger_present(connection)
        # Reconciled by hand (never by the migration): the upgrade then applies.
        with engine.begin() as connection:
            connection.execute(text(TRUNCATE))
        command.upgrade(config, "head")
    finally:
        engine.dispose()
