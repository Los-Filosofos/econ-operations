"""Day intervals of the domain: inclusive comparison, no clock, and no conversion between kinds."""

import inspect
from datetime import UTC, date, datetime

import pytest

from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.services import intervals
from app.services.intervals import (
    DayInterval,
    assignment_window_of,
    compare,
    covers,
    parse_day,
    scheduled_day,
    usage_period_of,
)


@pytest.fixture(autouse=True)
def forbid_clock(monkeypatch):
    """The module compares documented dates only; reading the clock is an error."""

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("intervals must never read the clock")

        @classmethod
        def today(cls):
            raise AssertionError("intervals must never read the clock")

    monkeypatch.setattr(intervals, "datetime", Frozen)


def usage(start, end):
    return DayInterval(kind="usage_period", start=start, end=end, source="test")


def window(start, end):
    return DayInterval(kind="assignment_window", start=start, end=end, source="test")


def test_module_has_no_io_and_never_reads_the_clock():
    source = inspect.getsource(intervals)
    assert "now(" not in source and "today(" not in source
    assert "import os" not in source and "httpx" not in source and "sqlalchemy" not in source


def test_sharing_one_day_is_an_inclusive_overlap():
    relation = compare(
        usage(date(2026, 9, 11), date(2026, 9, 14)), window(date(2026, 9, 14), date(2026, 9, 18))
    )
    assert relation.status == "overlap"
    assert relation.missing == []
    assert "del 2026-09-14 al 2026-09-14" in relation.reason


def test_adjacent_days_are_disjoint():
    relation = compare(
        usage(date(2026, 9, 11), date(2026, 9, 13)), window(date(2026, 9, 14), date(2026, 9, 18))
    )
    assert relation.status == "disjoint"
    assert relation.missing == []


def test_missing_boundary_is_not_verifiable_and_never_disjoint():
    relation = compare(usage(date(2026, 9, 11), None), window(date(2026, 9, 14), date(2026, 9, 18)))
    assert relation.status == "not_verifiable"
    assert relation.missing == ["usage_period.end"]
    assert "falta usage_period.end" in relation.reason
    both = compare(usage(None, None), window(None, date(2026, 9, 18)))
    assert both.missing == ["usage_period.start", "usage_period.end", "assignment_window.start"]


def test_partial_coverage_and_inverted_boundaries_are_not_verifiable():
    observed = DayInterval(
        kind="observed", start=date(2026, 9, 11), end=date(2026, 9, 12), source="test", partial=True
    )
    partial = compare(observed, usage(date(2026, 9, 11), date(2026, 9, 14)))
    assert partial.status == "not_verifiable"
    assert partial.missing == ["observed.coverage"]
    inverted = compare(
        usage(date(2026, 9, 14), date(2026, 9, 11)), window(date(2026, 9, 11), date(2026, 9, 14))
    )
    assert inverted.status == "not_verifiable"
    assert inverted.missing == ["usage_period.order"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-12", date(2026, 9, 12)),
        ("2026-09-12 10:00:00", None),
        ("2026-09-12T10:00:00", None),
        ("2026-09-13T03:00:00+00:00", date(2026, 9, 12)),
        ("2026-09-12T23:30:00-06:00", date(2026, 9, 12)),
        ("not a date", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_day_keeps_days_reads_zoned_instants_locally_and_rejects_unzoned(value, expected):
    assert parse_day(value) == expected


def test_unzoned_instant_makes_the_comparison_not_verifiable():
    interval = usage(parse_day("2026-09-12 10:00:00"), parse_day("2026-09-14"))
    relation = compare(interval, window(date(2026, 9, 11), date(2026, 9, 14)))
    assert relation.status == "not_verifiable"
    assert relation.missing == ["usage_period.start"]


def test_covers_is_inclusive_and_requires_every_date():
    period = usage(date(2026, 9, 11), date(2026, 9, 14))
    assert covers(period, date(2026, 9, 14)).status == "overlap"
    assert covers(period, date(2026, 9, 11)).status == "overlap"
    assert covers(period, date(2026, 9, 15)).status == "disjoint"
    unknown = covers(period, None)
    assert unknown.status == "not_verifiable" and unknown.missing == ["day"]
    incomplete = covers(usage(date(2026, 9, 11), None), date(2026, 9, 12))
    assert incomplete.status == "not_verifiable" and incomplete.missing == ["usage_period.end"]


def test_kinds_are_built_from_their_own_source_fields_and_never_converted():
    provenance = Provenance(
        source="nexus",
        source_id="test:request",
        environment="local",
        observed_at=datetime(2026, 9, 12, tzinfo=UTC),
        is_synthetic=True,
        evidence_kind="test_case",
    )
    request = RequestRecord(
        id="test:request",
        status="PENDIENTE",
        starts_on="2026-09-16",
        ends_on="2026-09-18",
        provenance=provenance,
    )
    equipment = EquipmentRecord(
        id="test:equipment",
        code="TEST-01",
        name="Unidad",
        machinery_status="DISPONIBLE",
        assignment_starts_on="2026-09-11",
        assignment_ends_on="2026-09-14",
        relation_status="unlinked",
        relation_note="test",
        provenance=provenance.model_copy(update={"source_id": "test:equipment"}),
    )
    period, assignment = usage_period_of(request), assignment_window_of(equipment)
    scheduled = scheduled_day(date(2026, 9, 15))
    assert (period.kind, assignment.kind, scheduled.kind) == (
        "usage_period",
        "assignment_window",
        "scheduled",
    )
    assert "fecha_inicio/fecha_fin" in period.source
    assert "fecha_inicio_uso/fecha_fin_uso" in assignment.source
    assert scheduled.start == scheduled.end == date(2026, 9, 15)
    assert compare(period, assignment).status == "disjoint"
    assert compare(scheduled, period).status == "disjoint"
    assert compare(scheduled, assignment).status == "disjoint"
    assert period.span() == "2026-09-16 → 2026-09-18"
    assert usage(date(2026, 9, 16), None).span() == "2026-09-16 → ausente"
