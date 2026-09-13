from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.access import management_scope
from app.core.config import Settings
from app.core.database import build_engine
from app.main import create_app
from app.models import metadata
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import Movement
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping
from app.services.workflow import WorkflowService

OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)


def make_operation(index: int, mode: str = "live"):
    def provenance(source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read" if mode == "live" else "provided_sample",
            is_synthetic=True,
            source_reference="test-input",
        )

    equipment = EquipmentRecord(
        id=f"test:equipment:{index}",
        code=f"EQ-{index:04d}",
        name=f"Unidad {index}",
        project_id="test-project",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test only.",
        provenance=provenance(f"unit-{index}"),
    )
    request = RequestRecord(
        id=f"test:request:{index}",
        status="APROBADA",
        machinery_id=equipment.id,
        project_id="test-project",
        starts_on="2026-09-01",
        provenance=provenance(f"req-{index}"),
    )
    mapping = TransferMapping(
        request_source_id=f"req-{index}",
        machinery_source_id=f"unit-{index}",
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference=f"MOV-{index:05d}",
        scheduled_date=date(2026, 9, 14),
    )
    return request, equipment, mapping


def test_selection_with_over_100_movements_new_inserts_and_restart(tmp_path):
    db_path = tmp_path / "worker_selection.db"
    engine = build_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)
    ledger = OperationsLedger(engine)

    # 1. Create 120 movements; movement 1 is the oldest.
    created_ids = []
    base_time = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    for i in range(1, 121):
        req, eq, mp = make_operation(i, "live")
        mov = ledger.create("live", req, eq, mp)
        # Give deterministic distinct initial timestamps so order is strictly monotonic
        mov_time = base_time + timedelta(minutes=i)
        with ledger.engine.begin() as conn:
            conn.execute(
                update(Movement)
                .where(Movement.id == mov.id)
                .values(created_at=mov_time, next_review_at=mov_time)
            )
        created_ids.append(mov.id)

    # Verify oldest movement is created_ids[0]
    first_mov_id = created_ids[0]

    # Cycle 1: budget 25 selects movements 1..25
    c1 = ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c1) == 25
    assert [m.id for m in c1] == created_ids[0:25]
    for m in c1:
        ledger.advance_review(m.id, "live")

    # Cycle 2: budget 25 selects movements 26..50
    c2 = ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c2) == 25
    assert [m.id for m in c2] == created_ids[25:50]
    for m in c2:
        ledger.advance_review(m.id, "live")

    # 2. Insert 30 NEW movements (121..150) between cycles
    new_ids = []
    for i in range(121, 151):
        req, eq, mp = make_operation(i, "live")
        mov = ledger.create("live", req, eq, mp)
        new_ids.append(mov.id)

    # Cycle 3: Older pending movements (51..75) MUST be selected before the newly created ones!
    c3 = ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c3) == 25
    assert [m.id for m in c3] == created_ids[50:75]
    for m in c3:
        ledger.advance_review(m.id, "live")

    # 3. Simulate process restart: re-instantiate OperationsLedger on the same database
    engine.dispose()
    restarted_engine = build_engine(f"sqlite:///{db_path}")
    restarted_ledger = OperationsLedger(restarted_engine)

    # Cycle 4 on restarted ledger: progress was persisted in DB, picks up at 76..100!
    c4 = restarted_ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c4) == 25
    assert [m.id for m in c4] == created_ids[75:100]
    for m in c4:
        restarted_ledger.advance_review(m.id, "live")

    # Cycle 5: selects remaining original movements 101..120 (20 items) plus the least recently
    # reviewed movements returning to review (movements 1..5)!
    c5 = restarted_ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c5) == 25
    assert [m.id for m in c5[:20]] == created_ids[100:120]
    # Movement 1 (first_mov_id) returns to review within a bounded number of cycles (5 cycles)!
    assert [m.id for m in c5[20:]] == created_ids[0:5]
    assert c5[20].id == first_mov_id
    for m in c5:
        restarted_ledger.advance_review(m.id, "live")

    # Cycle 6: selects next least recently reviewed movements (created_ids[5:30])
    c6 = restarted_ledger.select_for_review("live", ("draft", "blocked"), limit=25)
    assert len(c6) == 25
    assert [m.id for m in c6] == created_ids[5:30]
    for m in c6:
        restarted_ledger.advance_review(m.id, "live")

    # All movements continue to be reviewed fairly and durably without starvation
    restarted_engine.dispose()


def test_operations_pagination_total_and_coverage(tmp_path):
    db_path = tmp_path / "pagination.db"
    engine = build_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)
    ledger = OperationsLedger(engine)

    # Create 120 movements
    for i in range(1, 121):
        req, eq, mp = make_operation(i, "live")
        ledger.create("live", req, eq, mp)

    assert ledger.count("live") == 120

    # Test list_page directly
    p1_items, total1 = ledger.list_page("live", offset=0, limit=100)
    assert total1 == 120
    assert len(p1_items) == 100

    p2_items, total2 = ledger.list_page("live", offset=100, limit=100)
    assert total2 == 120
    assert len(p2_items) == 20

    # Test via WorkflowService.read
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        allow_live_reads=True,
        allow_local_management=True,
        _env_file=None,
    )
    service = WorkflowService(
        settings, engine, SimpleNamespace(), SimpleNamespace(configured=False)
    )

    overview_p1 = service.read("live", page=1, page_size=100)
    assert overview_p1.total == 120
    assert overview_p1.page == 1
    assert overview_p1.page_size == 100
    assert overview_p1.total_pages == 2
    assert len(overview_p1.movements) == 100
    assert overview_p1.coverage is not None
    assert overview_p1.coverage.is_complete is False
    assert overview_p1.complete is False
    assert overview_p1.coverage.has_more is True
    assert overview_p1.coverage.displayed == 100
    assert "Mostrando 100 de 120" in overview_p1.coverage.note
    assert "página 1 de 2" in overview_p1.coverage.note

    overview_p2 = service.read("live", page=2, page_size=100)
    assert overview_p2.total == 120
    assert overview_p2.page == 2
    assert overview_p2.total_pages == 2
    assert len(overview_p2.movements) == 20
    assert overview_p2.coverage is not None
    assert overview_p2.coverage.has_more is False
    assert overview_p2.coverage.displayed == 20
    assert overview_p2.complete is overview_p2.coverage.is_complete is False
    assert "100 movimientos más recientes" not in overview_p2.message
    assert "Mostrando 20 de 120" in overview_p2.message

    # Test complete population note when total <= limit
    overview_all = service.read("live", page=1, page_size=200)
    assert overview_all.total == 120
    assert len(overview_all.movements) == 120
    assert overview_all.coverage.is_complete is True
    assert overview_all.complete is True
    assert "Población completa: 120" in overview_all.coverage.note

    filtered = service.read("live", request_source_id="req-1", page_size=1)
    assert filtered.total == 1
    assert filtered.complete is filtered.coverage.is_complete is True
    assert filtered.movements[0].request_source_id == "req-1"

    empty = service.read("live", request_source_id="missing")
    assert empty.total == 0
    assert empty.complete is empty.coverage.is_complete is True
    beyond = service.read("live", request_source_id="missing", page=2)
    assert beyond.complete is beyond.coverage.is_complete is False
    assert "Población completa" not in beyond.coverage.note

    # Test via FastAPI HTTP endpoint
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 5000)) as client:
        with management_scope(True):
            resp = client.get("/api/v1/operations?mode=live&page=1&page_size=50")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 120
            assert data["page"] == 1
            assert data["page_size"] == 50
            assert data["total_pages"] == 3
            assert len(data["movements"]) == 50
            assert data["coverage"]["is_complete"] is False
            assert data["complete"] is False
            assert data["coverage"]["has_more"] is True

            for query in ("page=0", "page_size=0", "page_size=501"):
                assert client.get(f"/api/v1/operations?{query}").status_code == 422

    engine.dispose()


def test_mode_isolation_and_safe_claim(tmp_path):
    db_path = tmp_path / "modes.db"
    engine = build_engine(f"sqlite:///{db_path}")
    metadata.create_all(engine)
    ledger = OperationsLedger(engine)

    for i in range(1, 11):
        ledger.create("live", *make_operation(i, "live"))
        ledger.create("fixture", *make_operation(i, "fixture"))

    assert ledger.count("live") == 10
    assert ledger.count("fixture") == 10

    # select_for_review strictly isolates modes
    live_review = ledger.select_for_review("live", ("draft", "blocked"), limit=50)
    assert len(live_review) == 10
    assert all(m.mode == "live" for m in live_review)

    fixture_review = ledger.select_for_review("fixture", ("draft", "blocked"), limit=50)
    assert len(fixture_review) == 10
    assert all(m.mode == "fixture" for m in fixture_review)

    # Safe claim: queue one live movement
    target = live_review[0]
    ledger.queue(target.id, "live")
    claimed = ledger.claim()
    assert claimed is not None
    assert claimed.id == target.id
    assert claimed.state == "sending"

    # Verify that select_for_review does not include queued or sending movements in draft/blocked
    remaining_drafts = ledger.select_for_review("live", ("draft", "blocked"), limit=50)
    assert len(remaining_drafts) == 9
    assert target.id not in [m.id for m in remaining_drafts]

    # After transition to sent, it appears in sent/unknown review selection for observation
    ledger.finish_sent(target.id, "job-xyz")
    obs = ledger.select_for_review("live", ("sent", "unknown"), limit=50)
    assert len(obs) == 1
    assert obs[0].id == target.id

    engine.dispose()
