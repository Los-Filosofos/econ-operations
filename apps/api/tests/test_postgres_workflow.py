"""Cross-process cycle exclusion and actor persistence that only PostgreSQL accredits.

SQLite runs `cycle_lock` as a documented no-op; these tests need the `postgres_engine`
fixture (skipped when the database is absent, failed when it is configured but down).
"""

import threading
import time
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.core.access import management_scope
from app.core.config import Settings
from app.core.database import build_engine, cycle_lock
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import Actor
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping
from app.services.workflow import SyncInProgress, WorkflowService

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)


def operation(reference: str):
    def provenance(source_id: str) -> Provenance:
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
        id="test:equipment:pg-1",
        code="TEST-PG-01",
        name="Unidad de prueba",
        project_id="test-project",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test inputs only, never served as runtime data.",
        provenance=provenance("test-unit-pg-1"),
    )
    request = RequestRecord(
        id="test:request:pg-1",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=provenance("test-request-pg-1"),
    )
    mapping = TransferMapping(
        request_source_id="test-request-pg-1",
        machinery_source_id="test-unit-pg-1",
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference=reference,
        scheduled_date=date(2026, 9, 14),
    )
    return request, equipment, mapping


def advisory_locks(engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'")
        ).scalar_one()


def service_for(postgres_url: str, engine) -> WorkflowService:
    settings = Settings(database_url=postgres_url, allow_local_management=True, _env_file=None)
    offline = SimpleNamespace(configured=False)
    return WorkflowService(settings, engine, offline, offline)


def test_cycle_lock_is_exclusive_per_key_and_released_after_an_exception(postgres_engine):
    with cycle_lock(postgres_engine, "econ:test:a") as owned:
        assert owned is True
        assert advisory_locks(postgres_engine) == 1
        # Another pooled connection is another session: it does not wait, it is refused.
        with cycle_lock(postgres_engine, "econ:test:a") as again:
            assert again is False
        with cycle_lock(postgres_engine, "econ:test:b") as other:
            assert other is True
    assert advisory_locks(postgres_engine) == 0
    with pytest.raises(ValueError, match="test-only"), cycle_lock(postgres_engine, "econ:test:a"):
        assert advisory_locks(postgres_engine) == 1
        raise ValueError("test-only failure inside the cycle")
    # The failing holder's connection was invalidated, so the lock left with it.
    assert advisory_locks(postgres_engine) == 0
    with cycle_lock(postgres_engine, "econ:test:a") as owned:
        assert owned is True


def test_second_process_cannot_sync_while_advisory_lock_is_held(postgres_engine, postgres_url):
    # A second engine has its own pool, exactly like another worker process would.
    other_engine = build_engine(postgres_url)
    first = service_for(postgres_url, postgres_engine)
    second = service_for(postgres_url, other_engine)
    entered, release = threading.Event(), threading.Event()
    outcome: dict = {}
    from app.services import workflow as workflow_module

    original = workflow_module.read_hub

    def blocking_read_hub(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=20)
        return original(*args, **kwargs)

    def run_first():
        with management_scope(True):
            try:
                outcome["result"] = first.sync("fixture")
            except Exception as error:  # noqa: BLE001 - reported by the assertions below
                outcome["error"] = error

    try:
        with patch("app.services.workflow.read_hub", blocking_read_hub):
            worker = threading.Thread(target=run_first)
            worker.start()
            try:
                assert entered.wait(timeout=20)
                assert advisory_locks(other_engine) == 1
                started = time.monotonic()
                with management_scope(True), pytest.raises(SyncInProgress, match="otro proceso"):
                    second.sync("fixture")
                assert time.monotonic() - started < 2
            finally:
                release.set()
                worker.join(timeout=30)
        assert "error" not in outcome, outcome
        assert outcome["result"].available and outcome["result"].last_sync_at is not None
        assert advisory_locks(postgres_engine) == 0
        with management_scope(True):
            assert second.sync("fixture").available
        assert advisory_locks(postgres_engine) == 0
    finally:
        other_engine.dispose()


def test_lock_is_released_when_the_cycle_fails(postgres_engine, postgres_url):
    service = service_for(postgres_url, postgres_engine)
    with (
        patch("app.services.workflow.read_hub", side_effect=RuntimeError("test-only failure")),
        management_scope(True),
        pytest.raises(RuntimeError, match="test-only"),
    ):
        service.sync("fixture")
    assert advisory_locks(postgres_engine) == 0
    with management_scope(True):
        assert service.sync("fixture").available


def test_actor_columns_roundtrip(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    session_actor = Actor(
        user_id="42", email="logistica@example.test", role="logistica", kind="session"
    )
    row = ledger.create("live", *operation("test-actor-1"), actor=session_actor)
    ledger.queue(row.id, actor=Actor(kind="cli_worker"))
    ledger.claim(row.id, actor=Actor(kind="local_dev"))
    record = ledger.get(row.id, "live")
    created, queued, sending = record.events
    assert (created.actor_user_id, created.actor_role, created.actor_kind) == (
        "42",
        "logistica",
        "session",
    )
    assert isinstance(created.actor_user_id, str) and int(created.actor_user_id) == 42
    assert (queued.actor_user_id, queued.actor_role, queued.actor_kind) == (
        None,
        None,
        "cli_worker",
    )
    assert (sending.actor_user_id, sending.actor_role, sending.actor_kind) == (
        None,
        None,
        "local_dev",
    )
    with postgres_engine.connect() as connection:
        raw = connection.execute(
            text(
                "SELECT actor_user_id, actor_role, actor_kind FROM operation_events "
                "WHERE kind = 'created'"
            )
        ).one()
        columns = dict(
            connection.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'operation_events' AND column_name LIKE 'actor_%'"
                )
            ).all()
        )
    assert tuple(raw) == ("42", "logistica", "session")
    assert columns == {
        "actor_user_id": "character varying",
        "actor_role": "character varying",
        "actor_kind": "character varying",
    }
