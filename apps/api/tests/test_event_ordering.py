"""Tests for deterministic event ordering and atomic status updates (Issue #2).

Verifies the single ordering policy:
1. Fact date (event_time) takes absolute precedence over observation-only dates (observed_at).
2. Late events are preserved in history without regressing current projection.
3. Observation-only reads cannot assert actuality over known fact dates.
4. Ties in event_time are broken deterministically by recorded_at.
5. Entity row locking ensures consistent atomic updates under concurrent writers.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from app.core.database import build_engine
from app.models import metadata
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import Actor
from app.services.evidence import _transfer
from app.services.ledger import (
    MovementRecord,
    OperationsLedger,
    effective_event_sort_key,
)
from app.services.transfers import TransferMapping

T0 = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)


def _provenance(source_id: str, observed_at: datetime = T0) -> Provenance:
    return Provenance(
        source="nexus",
        source_id=source_id,
        environment="sandbox",
        observed_at=observed_at,
        evidence_kind="live_read",
        is_synthetic=True,
        source_reference="isolated test fixture",
    )


def _operation(reference: str = "test-movement-ord"):
    equipment = EquipmentRecord(
        id="test:equipment:unit-ord",
        code="ORD-01",
        name="Unidad Orden",
        project_id="test-proj-ord",
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test only",
        provenance=_provenance("test-unit-ord"),
    )
    request = RequestRecord(
        id="test:request:req-ord",
        status="APROBADA",
        machinery_id="test:equipment:unit-ord",
        project_id="test-proj-ord",
        project_name="Proyecto Orden",
        starts_on="2026-09-01",
        provenance=_provenance("test-req-ord"),
    )
    mapping = TransferMapping(
        request_source_id="test-req-ord",
        machinery_source_id="test-unit-ord",
        project_source_id="test-proj-ord",
        poi_id="test-poi-ord",
        assigned_user_ids=("test-user-ord",),
        movement_reference=reference,
        scheduled_date="2026-09-14",
    )
    return request, equipment, mapping


@pytest.fixture
def ledger(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'event_ordering.db'}")
    metadata.create_all(engine)
    yield OperationsLedger(engine)
    engine.dispose()


def _sent_movement(ledger: OperationsLedger, job_id: str = "test-job-ord") -> MovementRecord:
    row = ledger.create("live", *_operation(), tracked_vehicle_id="test-veh-ord")
    ledger.queue(row.id)
    ledger.claim(row.id)
    return ledger.finish_sent(row.id, job_id, status="Pendiente", workflow_role="pending")


def _task_obs(
    job_id: str = "test-job-ord",
    status: str = "En camino",
    workflow_role: str = "in_transit",
    event_time: datetime | None = None,
    observed_at: datetime | None = None,
) -> dict:
    obs_time = observed_at or T0
    return {
        "kind": "task_state",
        "source_id": job_id,
        "event_time": event_time,
        "observed_at": obs_time,
        "data": {
            "job_id": job_id,
            "status": status,
            "workflow_role": workflow_role,
        },
        "provenance": Provenance(
            source="startrack",
            source_id=job_id,
            environment="sandbox",
            observed_at=obs_time,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    }


def test_null_event_time_does_not_overwrite_explicit_earlier_fact_event(ledger):
    """Event A (18:00) -> Event B (None, 20:00) -> Event C (19:00) -> Event D (17:00).

    Expected projection:
    - After A: status is "StatusA" (18:00 fact)
    - After B: status remains "StatusA" (reading date 20:00 cannot assert actuality over 18:00 fact)
    - After C: status becomes "StatusC" (19:00 fact beats 18:00 fact)
    - After D: status remains "StatusC" (17:00 fact is older than 19:00 fact)
    All 4 events are preserved in the ledger history.
    """
    row = _sent_movement(ledger)

    # Event A: explicit fact at 18:00
    time_a = T0 + timedelta(hours=6)
    rec_a = ledger.record_observation(
        row.id, "live", **_task_obs(status="StatusA", event_time=time_a, observed_at=time_a)
    )
    assert rec_a.status == "StatusA"

    # Event B: event_time=None, observed at 20:00
    time_b = T0 + timedelta(hours=8)
    rec_b = ledger.record_observation(
        row.id, "live", **_task_obs(status="StatusB", event_time=None, observed_at=time_b)
    )
    assert rec_b.status == "StatusA"  # Does NOT overwrite!
    assert len([e for e in rec_b.events if e.kind == "task_state"]) == 2

    # Event C: explicit fact at 19:00 (after A, but before B's observed time)
    time_c = T0 + timedelta(hours=7)
    rec_c = ledger.record_observation(
        row.id, "live", **_task_obs(status="StatusC", event_time=time_c, observed_at=time_c)
    )
    assert rec_c.status == "StatusC"  # 19:00 fact beats 18:00 fact
    assert len([e for e in rec_c.events if e.kind == "task_state"]) == 3

    # Event D: late arriving event with older fact time 17:00
    time_d = T0 + timedelta(hours=5)
    rec_d = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(status="StatusD", event_time=time_d, observed_at=T0 + timedelta(hours=9)),
    )
    assert rec_d.status == "StatusC"  # 17:00 does not overwrite 19:00
    assert len([e for e in rec_d.events if e.kind == "task_state"]) == 4


def test_first_event_without_event_time_sets_initial_status_and_is_overwritten_by_fact_time(
    ledger,
):
    """Observation-only events set state when no fact dates exist, but yield to fact dates."""
    row = _sent_movement(ledger)

    # Event 1: observation-only at 10:00
    t1 = T0 - timedelta(hours=2)
    rec1 = ledger.record_observation(
        row.id, "live", **_task_obs(status="Obs10", event_time=None, observed_at=t1)
    )
    assert rec1.status == "Obs10"

    # Event 2: observation-only at 12:00 -> newer observation wins over older observation
    t2 = T0
    rec2 = ledger.record_observation(
        row.id, "live", **_task_obs(status="Obs12", event_time=None, observed_at=t2)
    )
    assert rec2.status == "Obs12"

    # Event 3: observation-only at 11:00 -> older observation does not overwrite
    t3 = T0 - timedelta(hours=1)
    rec3 = ledger.record_observation(
        row.id, "live", **_task_obs(status="Obs11", event_time=None, observed_at=t3)
    )
    assert rec3.status == "Obs12"

    # Event 4: fact date at 09:00 -> fact date beats observation-only even if observed later
    t4_fact = T0 - timedelta(hours=3)
    rec4 = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(status="Fact09", event_time=t4_fact, observed_at=T0 + timedelta(hours=1)),
    )
    assert rec4.status == "Fact09"

    # Event 5: observation-only at 14:00 -> cannot overwrite established fact date
    t5 = T0 + timedelta(hours=2)
    rec5 = ledger.record_observation(
        row.id, "live", **_task_obs(status="Obs14", event_time=None, observed_at=t5)
    )
    assert rec5.status == "Fact09"
    assert len([e for e in rec5.events if e.kind == "task_state"]) == 5


def test_tied_event_times_use_recorded_at_as_tiebreaker(ledger):
    """Two events with identical event_time: the one recorded later in the ledger wins."""
    row = _sent_movement(ledger)
    same_time = T0 + timedelta(hours=2)

    rec1 = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(
            status="FirstWrite",
            workflow_role="pending",
            event_time=same_time,
            observed_at=same_time,
        ),
    )
    assert rec1.status == "FirstWrite"

    rec2 = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(
            status="SecondWrite",
            workflow_role="completed",
            event_time=same_time,
            observed_at=same_time + timedelta(minutes=1),
        ),
    )
    assert rec2.status == "SecondWrite"
    assert rec2.workflow_role == "completed"


def test_effective_event_sort_key_total_ordering():
    """Verify effective_event_sort_key ordering rules directly."""
    from app.models.operations import MovementEventRecord

    def make_event(
        event_id: str,
        event_time: datetime | None,
        observed_at: datetime | None,
        recorded_at: datetime,
    ) -> MovementEventRecord:
        return MovementEventRecord(
            id=event_id,
            kind="task_state",
            event_time=event_time,
            observed_at=observed_at,
            recorded_at=recorded_at,
            data={},
        )

    t18 = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)
    t19 = datetime(2026, 9, 12, 19, 0, tzinfo=UTC)
    t20 = datetime(2026, 9, 12, 20, 0, tzinfo=UTC)

    ev_fact18 = make_event("1", t18, t18, t18)
    ev_obs20 = make_event("2", None, t20, t20)
    ev_fact19 = make_event("3", t19, t19, t19)

    # Fact beats observation-only
    assert effective_event_sort_key(ev_fact18) > effective_event_sort_key(ev_obs20)
    # Later fact beats earlier fact
    assert effective_event_sort_key(ev_fact19) > effective_event_sort_key(ev_fact18)
    # max() selects the 19:00 fact event
    assert max([ev_fact18, ev_obs20, ev_fact19], key=effective_event_sort_key).id == "3"


def test_evidence_projection_matches_ledger_status(ledger):
    """Verify that evidence._transfer matches ledger deterministic state."""
    request, _, _ = _operation()
    row = _sent_movement(ledger)

    time_18 = T0 + timedelta(hours=6)
    time_20 = T0 + timedelta(hours=8)
    time_19 = T0 + timedelta(hours=7)

    # 18:00 fact -> None @ 20:00 reading -> 19:00 fact
    ledger.record_observation(
        row.id, "live", **_task_obs(status="Status18", event_time=time_18, observed_at=time_18)
    )
    ledger.record_observation(
        row.id, "live", **_task_obs(status="Status20Obs", event_time=None, observed_at=time_20)
    )
    ledger.record_observation(
        row.id, "live", **_task_obs(status="Status19", event_time=time_19, observed_at=time_19)
    )

    movement = ledger.get(row.id, "live")
    transfer = _transfer(movement, request)
    assert transfer.status == "Status19"
    assert movement.status == "Status19"


def test_concurrent_observations_with_lock(ledger):
    """Concurrent writers serialize cleanly and produce deterministic status."""
    row = _sent_movement(ledger)
    times = [T0 + timedelta(minutes=10 * i) for i in range(8)]
    statuses = [f"Status_{i}" for i in range(8)]

    def record_one(idx: int):
        obs = _task_obs(
            status=statuses[idx],
            event_time=times[idx],
            observed_at=times[idx] + timedelta(minutes=1),
        )
        ledger.record_observation(row.id, "live", **obs)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(record_one, i) for i in range(8)]
        for f in futures:
            f.result()

    final = ledger.get(row.id, "live")
    # All 8 observations recorded
    assert len([e for e in final.events if e.kind == "task_state"]) == 8
    # Status is Status_7 (latest event_time)
    assert final.status == "Status_7"


def test_observation_actor_is_recorded_without_changing_the_ordering_policy(ledger):
    """The worker only states its kind; fact dates still decide the projected status."""
    row = _sent_movement(ledger)
    worker = Actor(kind="cli_worker")
    fact = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(status="Fact", event_time=T0 + timedelta(hours=1), observed_at=T0),
        actor=worker,
    )
    assert fact.events[-1].actor_kind == "cli_worker"
    assert fact.events[-1].actor_user_id is None and fact.events[-1].actor_role is None
    later_read = ledger.record_observation(
        row.id,
        "live",
        **_task_obs(status="ReadOnly", event_time=None, observed_at=T0 + timedelta(hours=3)),
    )
    assert later_read.status == "Fact"
    assert later_read.events[-1].actor_kind is None
