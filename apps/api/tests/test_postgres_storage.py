"""Storage hygiene that only PostgreSQL accredits: JSON/timestamptz columns, SKIP LOCKED.

The `postgres_engine` fixture migrates and empties the isolated database (skipped when it
is absent, failed when it is configured but down). No EXPLAIN assertions: index usage is
a planner decision; the guarantees checked here are behavioural.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier

from sqlalchemy import event, text
from sqlmodel import Session

from app.models.hub import (
    EquipmentRecord,
    HubResponse,
    HubScope,
    HubSummary,
    OperationEvidenceStatus,
    Provenance,
    RequestRecord,
    SourceStatus,
)
from app.models.operations import Movement, OperationEvent
from app.services.ledger import OperationsLedger, last_read_at, stable_snapshot_hash
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)
WRITES = ("INSERT", "UPDATE", "DELETE")


def _provenance(source_id: str, observed_at: datetime = OBSERVED) -> Provenance:
    return Provenance(
        source="nexus",
        source_id=source_id,
        environment="sandbox",
        observed_at=observed_at,
        evidence_kind="live_read",
        is_synthetic=True,
        source_reference="isolated test inputs, never provider records",
    )


def operation(reference: str = "test-movement-1", machine: str = "test-unit-1"):
    equipment = EquipmentRecord(
        id=f"test:equipment:{machine}",
        code="TEST-01",
        name="Unidad de prueba",
        project_id="test-project",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test inputs only, never served as runtime data.",
        provenance=_provenance(machine),
    )
    request = RequestRecord(
        id="test:request:request-1",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=_provenance("test-request-1"),
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


def hub(observed_at: datetime = OBSERVED, *, machinery_status: str = "OCUPADA") -> HubResponse:
    request, equipment, _ = operation()
    request.provenance.observed_at = observed_at
    equipment.provenance.observed_at = observed_at
    equipment.machinery_status = machinery_status
    return HubResponse(
        mode="live",
        generated_at=observed_at + timedelta(seconds=1),
        data_as_of=observed_at,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma / Nexus",
                status="connected",
                environment="sandbox",
                observed_at=observed_at,
                message="Lectura acotada de prueba.",
            )
        ],
        scope=HubScope(search="", complete=False, description="Prueba acotada"),
        summary=HubSummary(equipment_count=1),
        operation_evidence=OperationEvidenceStatus(
            status="available", checked_at=observed_at + timedelta(seconds=2), complete=True
        ),
        equipment=[equipment],
        requests=[request],
        alerts=[],
    )


def _capture(engine):
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    return statements, capture


def _writes(statements: list[str]) -> list[str]:
    return [item for item in statements if item.lstrip().upper().startswith(WRITES)]


def _snapshot_rows(engine) -> list[tuple]:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT id, recorded_at, last_confirmed_at FROM operation_snapshots "
                "WHERE mode = 'live' ORDER BY recorded_at"
            )
        ).all()


def test_prune_and_dedup_on_json_columns(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    first = ledger.record_snapshot(hub())
    again = ledger.record_snapshot(hub(OBSERVED + timedelta(hours=3)))
    assert again.id == first.id
    assert again.last_confirmed_at is not None and again.last_confirmed_at.tzinfo is UTC
    assert last_read_at(again) == again.last_confirmed_at > first.recorded_at
    assert again.content_hash == stable_snapshot_hash(hub().model_dump(mode="json"))
    rows = _snapshot_rows(postgres_engine)
    assert len(rows) == 1 and rows[0][2] is not None
    with postgres_engine.connect() as connection:
        # The JSON column kept the stamps of the first read; only the confirmation moved.
        stored = connection.execute(
            text(
                "SELECT content -> 'equipment' -> 0 -> 'provenance' ->> 'observed_at' "
                "FROM operation_snapshots"
            )
        ).scalar_one()
    assert stored == "2026-09-12T18:00:00Z"
    changed = ledger.record_snapshot(hub(OBSERVED + timedelta(hours=4), machinery_status="LIBRE"))
    assert changed.id != first.id
    assert [row[0] for row in _snapshot_rows(postgres_engine)] == [first.id, changed.id]
    assert ledger.last_snapshot("live").id == changed.id
    # Retention: the first cut was recorded and confirmed long ago, the latest is protected.
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE operation_snapshots SET recorded_at = now() - interval '40 days', "
                "last_confirmed_at = now() - interval '30 days' WHERE id = :id"
            ),
            {"id": first.id},
        )
    assert ledger.prune_snapshots("live", keep_days=7, keep_latest=1, dry_run=True) == 1
    assert len(_snapshot_rows(postgres_engine)) == 2
    assert ledger.prune_snapshots("live", keep_days=7, keep_latest=1) == 1
    assert [row[0] for row in _snapshot_rows(postgres_engine)] == [changed.id]
    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE operation_snapshots SET recorded_at = now() - interval '40 days'")
        )
    # keep_latest keeps the current read model of the mode even when it is old.
    assert ledger.prune_snapshots("live", keep_days=7, keep_latest=1) == 0
    assert [row[0] for row in _snapshot_rows(postgres_engine)] == [changed.id]
    assert ledger.prune_snapshots("fixture", keep_days=1, keep_latest=1) == 0


def test_revalidate_without_source_change_emits_no_write(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    request, equipment, mapping = operation()
    first = ledger.create("live", request, equipment, mapping)
    reread_request = request.model_copy(deep=True)
    reread_request.provenance.observed_at = OBSERVED + timedelta(hours=3)
    reread_equipment = equipment.model_copy(deep=True)
    reread_equipment.provenance.observed_at = OBSERVED + timedelta(hours=3)
    statements, capture = _capture(postgres_engine)
    try:
        same = ledger.revalidate(first.id, "live", reread_request, reread_equipment)
    finally:
        event.remove(postgres_engine, "before_cursor_execute", capture)
    assert _writes(statements) == []
    assert [item.kind for item in same.events] == ["created"]
    assert same.updated_at == first.updated_at and same.updated_at.tzinfo is UTC
    approved = reread_request.model_copy(deep=True)
    approved.approved_at = OBSERVED + timedelta(days=1)
    changed = ledger.revalidate(first.id, "live", approved, reread_equipment)
    assert [item.kind for item in changed.events] == ["created", "revalidated"]
    assert changed.events[-1].data["previous"]["request_hash"] == first.source_request_hash
    assert changed.events[-1].data["current"]["request_hash"] == changed.source_request_hash
    assert changed.source_request_hash != first.source_request_hash
    with postgres_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM operation_events WHERE kind = 'revalidated'")
            ).scalar_one()
            == 1
        )


def test_listing_events_uses_one_statement_for_all_movements(postgres_engine):
    base = datetime(2026, 9, 1, tzinfo=UTC)
    with Session(postgres_engine) as session:
        for index in range(20):
            movement_id = f"test-mv-{index:03}"
            created_at = base + timedelta(minutes=index)
            session.add(
                Movement(
                    id=movement_id,
                    mode="live",
                    environment="sandbox",
                    movement_reference=movement_id,
                    request_source_id="test-request-1",
                    machinery_source_id=f"test-unit-{index:03}",
                    project_source_id="test-project",
                    mapping={},
                    source_request={"id": "test-request-1"},
                    source_request_hash="test-hash",
                    identity_hash=f"test-identity-{index:03}",
                    preparation={},
                    state="draft",
                    created_at=created_at,
                    updated_at=created_at,
                    next_review_at=created_at,
                )
            )
            for offset in (2, 0, 1):
                session.add(
                    OperationEvent(
                        id=f"test-ev-{index:03}-{offset}",
                        movement_id=movement_id,
                        kind=("created", "queued", "sending")[offset],
                        state="draft",
                        recorded_at=created_at + timedelta(seconds=offset),
                        data={"offset": offset},
                    )
                )
        session.commit()
    ledger = OperationsLedger(postgres_engine)
    statements, capture = _capture(postgres_engine)
    try:
        listed = ledger.list("live", limit=20)
    finally:
        event.remove(postgres_engine, "before_cursor_execute", capture)
    assert len(listed) == 20 and len(statements) <= 3, statements
    assert all(
        [item.id for item in movement.events]
        == [f"test-ev-{movement.id[-3:]}-{offset}" for offset in (0, 1, 2)]
        for movement in listed
    )
    assert [movement.model_dump() for movement in listed] == [
        ledger.get(movement.id, "live").model_dump() for movement in listed
    ]


def test_two_concurrent_claims_take_distinct_rows_with_skip_locked(postgres_engine):
    ledger = OperationsLedger(postgres_engine)
    queued = []
    for index in (1, 2):
        row = ledger.create("live", *operation(f"test-ref-{index}", machine=f"test-unit-{index}"))
        queued.append(ledger.queue(row.id).id)
    barrier = Barrier(2)

    def claim(_worker: int):
        barrier.wait()
        # Each worker has its own session; a head locked by the other one is skipped.
        return OperationsLedger(postgres_engine).claim()

    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(claim, (1, 2)))
    assert all(item is not None for item in claimed)
    assert sorted(item.id for item in claimed) == sorted(queued)
    assert {item.state for item in claimed} == {"sending"}
    assert ledger.claim() is None
    assert {record.state for record in ledger.list("live")} == {"sending"}
