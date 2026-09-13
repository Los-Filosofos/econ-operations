"""Missing source coverage must never turn into zero missing records."""

from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.dashboard.coverage_analytics import coverage_figure, coverage_rows
from app.services.hub import read_hub


@pytest.fixture
def hub():
    return read_hub(Settings(database_url="sqlite://", _env_file=None), Mock(), "fixture")


def test_fixture_distinguishes_read_records_from_the_unread_population(hub):
    chart = coverage_figure(hub)
    assert coverage_rows(hub) == [("Solicitudes", 2, 2), ("Maquinaria", 5, 15)]
    assert list(chart.data[0].x) == pytest.approx([100, 100 / 3])
    assert list(chart.data[1].x) == pytest.approx([0, 200 / 3])
    assert list(chart.data[0].customdata) == [[2, 2], [5, 15]]
    assert list(chart.data[1].customdata) == [0, 10]
    assert list(chart.layout.xaxis.range) == [0, 100]
    assert chart.data[1].marker.pattern.shape == "/"
    assert [item.text for item in chart.layout.annotations] == [
        "2 de 2 · 100 %",
        "5 de 15 · 33,3 %",
    ]


@pytest.mark.parametrize("total", [None, 3])
def test_unknown_or_inconsistent_total_has_no_invented_remainder(hub, total):
    hub.scope.equipment_total = total
    chart = coverage_figure(hub)
    assert chart.data[0].x[1] is None
    assert chart.data[0].customdata[1][0] == 5
    assert chart.data[1].x[1] is None
    assert ("desconocido" if total is None else "inconsistente") in chart.layout.annotations[1].text


def test_empty_collection_is_not_zero_or_full_coverage(hub):
    hub.scope.equipment_returned = 0
    hub.scope.equipment_total = 0
    chart = coverage_figure(hub)
    assert chart.data[0].x[1] is None
    assert chart.data[1].x[1] is None
    assert "colección vacía; sin porcentaje" in chart.layout.annotations[1].text


def test_known_population_without_read_records_has_zero_coverage(hub):
    hub.scope.equipment_returned = 0
    chart = coverage_figure(hub)
    assert chart.data[0].x[1] == 0
    assert chart.data[1].x[1] == 100
    assert chart.layout.annotations[1].text == "0 de 15 · 0 %"


def test_failed_source_never_looks_like_a_zero_coverage_measurement(hub):
    hub.sources[0].status = "error"
    assert coverage_rows(hub) == []
    assert coverage_figure(hub) is None
