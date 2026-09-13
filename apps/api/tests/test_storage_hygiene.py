"""Storage hygiene (ADR 0006): a read that changes nothing writes nothing durable.

SQLite accredits none of the PostgreSQL concurrency guarantees; the deduplication,
pruning and single-statement listing are repeated on the isolated PostgreSQL database
in tests/test_postgres_storage.py.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func
from sqlmodel import Session, select

from app.cli import prune_snapshots as prune_cli
from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.fixtures import fixture_records
from app.main import create_app
from app.models import metadata
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
from app.models.operations import Movement, OperationEvent, SourceSnapshot
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
    """Live cut whose read stamps all derive from `observed_at`; facts stay constant."""
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
                observed_on=observed_at.date(),
                message="Lectura acotada de prueba.",
            ),
            SourceStatus(
                id="startrack",
                label="Startrack",
                status="not_queried",
                environment="sandbox",
                last_evidence_at=observed_at - timedelta(days=1),
                message="No consultado.",
            ),
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


@pytest.fixture
def ledger(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'hygiene.db'}")
    metadata.create_all(engine)  # Isolated test schema only; the application never does this.
    yield OperationsLedger(engine)
    engine.dispose()


def _statements(engine) -> tuple[list[str], object]:
    captured: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        captured.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    return captured, capture


def _writes(statements: list[str]) -> list[str]:
    return [item for item in statements if item.lstrip().upper().startswith(WRITES)]


def _snapshot(
    mode: str, recorded_at: datetime, index: int, *, confirmed_at: datetime | None = None
) -> SourceSnapshot:
    return SourceSnapshot(
        id=f"test-snapshot-{mode}-{index}",
        mode=mode,
        recorded_at=recorded_at,
        generated_at=recorded_at,
        data_as_of=None,
        content_hash=f"test-hash-{index}",
        content={"mode": mode, "index": index},
        last_confirmed_at=confirmed_at,
    )


def test_stable_snapshot_hash_ignores_read_timestamps_but_not_facts():
    first = hub().model_dump(mode="json")
    reread = hub(OBSERVED + timedelta(hours=3)).model_dump(mode="json")
    assert first != reread  # every read stamp moved
    assert stable_snapshot_hash(first) == stable_snapshot_hash(reread)
    changed = hub(OBSERVED + timedelta(hours=3), machinery_status="DISPONIBLE")
    assert stable_snapshot_hash(changed.model_dump(mode="json")) != stable_snapshot_hash(first)
    # The stored content keeps every read stamp; only the fingerprint leaves them out.
    assert reread["generated_at"] != first["generated_at"]
    assert reread["equipment"][0]["provenance"]["observed_at"] == "2026-09-12T21:00:00Z"


def test_unchanged_cut_confirms_the_latest_row_instead_of_inserting(ledger):
    first = ledger.record_snapshot(hub())
    assert first.last_confirmed_at is None
    assert first.content_hash == stable_snapshot_hash(hub().model_dump(mode="json"))
    assert last_read_at(first) == first.recorded_at
    again = ledger.record_snapshot(hub(OBSERVED + timedelta(hours=3)))
    assert again.id == first.id
    assert again.recorded_at == first.recorded_at
    assert again.last_confirmed_at is not None and again.last_confirmed_at >= first.recorded_at
    assert last_read_at(again) == again.last_confirmed_at
    # The stored cut is immutable apart from its confirmation: the first read's stamps stay.
    assert again.content == first.content
    assert again.generated_at == first.generated_at
    changed = ledger.record_snapshot(hub(OBSERVED + timedelta(hours=4), machinery_status="LIBRE"))
    assert changed.id != first.id and changed.last_confirmed_at is None
    with Session(ledger.engine) as session:
        rows = session.exec(
            select(SourceSnapshot)
            .where(SourceSnapshot.mode == "live")
            .order_by(SourceSnapshot.recorded_at)
        ).all()
    assert [row.id for row in rows] == [first.id, changed.id]
    assert ledger.last_snapshot("live").id == changed.id
    # Modes never share a deduplication chain.
    assert ledger.last_snapshot("fixture") is None


def test_unchanged_fixture_sync_stores_one_snapshot(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'sync.db'}",
            allow_local_management=True,
            _env_file=None,
        )
    )
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        first = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert first.status_code == 200, first.text
        second = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert second.status_code == 200, second.text
        with Session(app.state.engine) as session:
            rows = session.exec(
                select(SourceSnapshot).where(SourceSnapshot.mode == "fixture")
            ).all()
        assert len(rows) == 1
        (row,) = rows
        assert row.last_confirmed_at is not None and row.last_confirmed_at >= row.recorded_at
        first_sync = datetime.fromisoformat(first.json()["last_sync_at"])
        second_sync = datetime.fromisoformat(second.json()["last_sync_at"])
        # last_sync_at is the latest read: the cut's record time, then its confirmation.
        assert first_sync == row.recorded_at
        assert second_sync == row.last_confirmed_at >= first_sync
        overview = client.get("/api/v1/operations?mode=fixture").json()
        assert datetime.fromisoformat(overview["last_sync_at"]) == second_sync

        def altered():
            equipment, requests = fixture_records()
            equipment[0].machinery_status = "TEST-CAMBIO"
            return equipment, requests

        with patch("app.services.hub.fixture_records", altered):
            third = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert third.status_code == 200, third.text
        with Session(app.state.engine) as session:
            rows = session.exec(
                select(SourceSnapshot)
                .where(SourceSnapshot.mode == "fixture")
                .order_by(SourceSnapshot.recorded_at)
            ).all()
        assert len(rows) == 2
        assert rows[1].content_hash != rows[0].content_hash
        assert rows[1].last_confirmed_at is None
        assert any(
            item["machinery_status"] == "TEST-CAMBIO" for item in rows[1].content["equipment"]
        )
        assert datetime.fromisoformat(third.json()["last_sync_at"]) == rows[1].recorded_at


def test_revalidate_writes_only_when_source_hashes_change(ledger):
    request, equipment, mapping = operation()
    first = ledger.create("live", request, equipment, mapping)
    reread_request = request.model_copy(deep=True)
    reread_request.provenance.observed_at = OBSERVED + timedelta(hours=3)
    reread_equipment = equipment.model_copy(deep=True)
    reread_equipment.provenance.observed_at = OBSERVED + timedelta(hours=3)
    statements, capture = _statements(ledger.engine)
    try:
        same = ledger.revalidate(first.id, "live", reread_request, reread_equipment)
    finally:
        event.remove(ledger.engine, "before_cursor_execute", capture)
    assert _writes(statements) == []
    assert [item.kind for item in same.events] == ["created"]
    assert same.updated_at == first.updated_at
    assert same.next_review_at == first.next_review_at
    # The row keeps the read time of its last real change, not of the silent re-read.
    assert same.source_request == first.source_request
    assert same.source_request["provenance"]["observed_at"] == "2026-09-12T18:00:00Z"

    approved = reread_request.model_copy(deep=True)
    approved.approved_at = OBSERVED + timedelta(days=1)
    changed = ledger.revalidate(first.id, "live", approved, reread_equipment)
    assert [item.kind for item in changed.events] == ["created", "revalidated"]
    data = changed.events[-1].data
    assert data["previous"] == {
        "request_hash": first.source_request_hash,
        "equipment_hash": first.source_equipment_hash,
    }
    assert data["current"] == {
        "request_hash": changed.source_request_hash,
        "equipment_hash": changed.source_equipment_hash,
    }
    assert data["previous"]["request_hash"] != data["current"]["request_hash"]
    assert data["previous"]["equipment_hash"] == data["current"]["equipment_hash"]
    # Full copies travel only with a real change.
    assert data["request"] == changed.source_request
    assert data["equipment"] == changed.source_equipment
    assert changed.source_request["approved_at"] == "2026-09-13T18:00:00Z"
    assert changed.source_request["provenance"]["observed_at"] == "2026-09-12T21:00:00Z"
    assert changed.updated_at > first.updated_at
    # The same content read once more is silent again.
    third = ledger.revalidate(first.id, "live", approved, reread_equipment)
    assert len(third.events) == 2 and third.updated_at == changed.updated_at


def test_listing_fifty_movements_uses_a_bounded_number_of_statements(ledger):
    base = datetime(2026, 9, 1, tzinfo=UTC)
    with Session(ledger.engine) as session:
        for index in range(50):
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
            # Inserted out of order on purpose: the listing sorts by recorded_at, then id.
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
    expected = {
        f"test-mv-{index:03}": [f"test-ev-{index:03}-{offset}" for offset in (0, 1, 2)]
        for index in range(50)
    }
    statements, capture = _statements(ledger.engine)
    try:
        listed = ledger.list("live", limit=50)
    finally:
        event.remove(ledger.engine, "before_cursor_execute", capture)
    assert len(listed) == 50
    assert len(statements) <= 3, statements
    assert {item.id: [item.id for item in item.events] for item in listed} == expected
    assert [item.id for item in listed] == sorted(expected, reverse=True)
    # Same content as the single-row path (the former one-query-per-movement reading).
    singles = [ledger.get(item.id, "live") for item in listed]
    assert [item.model_dump() for item in singles] == [item.model_dump() for item in listed]
    assert ledger.list("live", limit=10)[0].events[0].kind == "created"


def test_prune_keeps_latest_and_recent_snapshots_and_never_touches_events(ledger):
    now = datetime.now(UTC)
    movement = ledger.create("live", *operation())
    ledger.queue(movement.id)
    with Session(ledger.engine) as session:
        session.add_all(
            [
                _snapshot("fixture", now - timedelta(days=40), 0),
                _snapshot("fixture", now - timedelta(days=30), 1),
                # Confirmed long ago as well: still old.
                _snapshot(
                    "fixture", now - timedelta(days=20), 2, confirmed_at=now - timedelta(days=19)
                ),
                _snapshot("fixture", now - timedelta(days=5), 3),
                _snapshot("fixture", now - timedelta(days=2), 4),
                # Live: every cut was recorded long ago; one was confirmed by a recent read.
                _snapshot("live", now - timedelta(days=60), 5),
                _snapshot(
                    "live", now - timedelta(days=50), 6, confirmed_at=now - timedelta(days=1)
                ),
                _snapshot("live", now - timedelta(days=45), 7),
            ]
        )
        session.commit()

    def counts() -> tuple[int, int]:
        with Session(ledger.engine) as session:
            return (
                session.exec(select(func.count(OperationEvent.id))).one(),
                session.exec(select(func.count(Movement.id))).one(),
            )

    def remaining(mode: str) -> list[str]:
        with Session(ledger.engine) as session:
            return list(
                session.exec(
                    select(SourceSnapshot.id)
                    .where(SourceSnapshot.mode == mode)
                    .order_by(SourceSnapshot.recorded_at)
                ).all()
            )

    before = counts()
    assert before[0] == 2
    assert ledger.prune_snapshots("fixture", keep_days=7, keep_latest=1, dry_run=True) == 3
    assert len(remaining("fixture")) == 5  # a dry run deletes nothing
    assert ledger.prune_snapshots("fixture", keep_days=7, keep_latest=1) == 3
    assert remaining("fixture") == ["test-snapshot-fixture-3", "test-snapshot-fixture-4"]
    assert remaining("live") == [
        "test-snapshot-live-5",
        "test-snapshot-live-6",
        "test-snapshot-live-7",
    ]
    assert ledger.last_snapshot("fixture").id == "test-snapshot-fixture-4"
    # The latest cut by recorded_at is protected; a recently confirmed cut is not old.
    assert ledger.prune_snapshots("live", keep_days=7, keep_latest=1) == 1
    assert remaining("live") == ["test-snapshot-live-6", "test-snapshot-live-7"]
    assert ledger.prune_snapshots("live", keep_days=7, keep_latest=1) == 0
    # keep_latest protects even old cuts.
    assert ledger.prune_snapshots("fixture", keep_days=1, keep_latest=5) == 0
    assert counts() == before
    assert [item.kind for item in ledger.get(movement.id, "live").events] == ["created", "queued"]
    with pytest.raises(Exception, match="al menos un día"):
        ledger.prune_snapshots("fixture", keep_days=0)
    with pytest.raises(Exception, match="al menos un día"):
        ledger.prune_snapshots("fixture", keep_days=7, keep_latest=0)


def test_prune_cli_is_explicit_and_validates_its_arguments(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'prune.db'}"
    engine = build_engine(url)
    metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add_all(
            [
                _snapshot("live", now - timedelta(days=30), 0),
                _snapshot("live", now - timedelta(days=20), 1),
                _snapshot("live", now, 2),
            ]
        )
        session.commit()
    engine.dispose()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    for arguments in (["--keep-days", "0"], ["--keep-days", "7", "--keep-latest", "0"]):
        with pytest.raises(SystemExit) as refused:
            prune_cli.main(arguments)
        assert refused.value.code == 2
    assert prune_cli.main(["--mode", "live", "--keep-days", "7", "--dry-run"]) == 0
    assert "Cortes que se eliminarían (live" in capsys.readouterr().out
    check = build_engine(url)
    with Session(check) as session:
        assert session.exec(select(func.count(SourceSnapshot.id))).one() == 3
    assert prune_cli.main(["--mode", "live", "--keep-days", "7", "--keep-latest", "2"]) == 0
    assert "Cortes eliminados (live, más de 7 días, conservando los 2 más recientes): 1" in (
        capsys.readouterr().out
    )
    with Session(check) as session:
        assert session.exec(
            select(SourceSnapshot.id).order_by(SourceSnapshot.recorded_at)
        ).all() == ["test-snapshot-live-1", "test-snapshot-live-2"]
    check.dispose()
