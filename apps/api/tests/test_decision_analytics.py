"""Overview figures count source requests, preserve identity and never infer delivery deadlines."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from plotly.utils import PlotlyJSONEncoder

from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import (
    DAY_MS,
    has_confirmed_task,
    request_counts,
    request_states,
    requests_in_scope,
    states_figure,
    usage_figure,
    usage_timeline,
)
from app.dashboard.decision_views import overview
from app.integrations.fixtures import fixture_records
from app.models.hub import AlertRecord, HubResponse, HubScope, HubSummary, SourceStatus
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview


@pytest.fixture
def hub():
    equipment, requests = fixture_records()
    return HubResponse(
        mode="fixture",
        generated_at=datetime(2030, 1, 1, tzinfo=UTC),
        data_as_of=None,
        sources=[
            SourceStatus(
                id="nexus",
                label="Prisma",
                status="fixture",
                environment="sandbox",
                message="Provided examples",
                observed_on=date(2026, 9, 12),
            )
        ],
        scope=HubScope(
            search="",
            requests_total=2,
            equipment_total=15,
            requests_returned=2,
            equipment_returned=5,
            complete=False,
            description="Supplied contract examples, bounded coverage",
        ),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )


def registry(*movements, available=True):
    return WorkflowOverview(available=available, message="Test registry", movements=list(movements))


def confirmed_movement(hub):
    request = next(request for request in hub.requests if request.machinery_id)
    equipment = next(item for item in hub.equipment if item.id == request.machinery_id)
    return MovementRecord(
        id="test-movement",
        mode=hub.mode,
        environment=request.provenance.environment,
        movement_reference="test-reference",
        request_source_id=request.provenance.source_id,
        machinery_source_id=equipment.provenance.source_id,
        project_source_id=request.project_id,
        mapping={},
        source_request=request.model_dump(mode="json"),
        source_equipment=equipment.model_dump(mode="json"),
        source_request_hash="test-hash",
        source_equipment_hash="test-hash",
        payload={},
        preparation={},
        state="sent",
        job_id="test-startrack-700",
        created_at=datetime(2026, 9, 12, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
        events=[],
    )


def test_provided_requests_support_only_absolute_counts_and_source_periods(hub):
    counts = request_counts(hub, QueryContext(), registry())
    assert (counts.total, counts.unassigned, counts.without_confirmed_task) == (2, 1, 2)
    assert request_states(hub.requests) == [("APROBADA", 1), ("PENDIENTE", 1)]
    timeline = usage_timeline(hub.requests)
    assert [(item.starts_on, item.ends_on) for item in timeline.periods] == [
        (date(2026, 9, 11), date(2026, 9, 14)),
        (date(2026, 9, 16), date(2026, 9, 18)),
    ]
    assert not timeline.excluded
    assert hub.data_as_of is None
    assert counts.total != hub.scope.equipment_total


@pytest.mark.parametrize("field", ["starts_on", "ends_on", "approved_at"])
def test_previous_execution_does_not_remove_current_request_from_unlinked_filter(hub, field):
    movement = confirmed_movement(hub)
    movement.source_request[field] = "2025-01-01"
    workflow = registry(movement)
    request = next(request for request in hub.requests if request.machinery_id)
    assert not has_confirmed_task(hub, request, workflow)
    assert request in requests_in_scope(hub, QueryContext(filter="unlinked"), workflow)


def test_unknown_request_states_remain_distinct_provider_categories(hub):
    first = hub.requests[0]
    rows = [
        first.model_copy(update={"status": status})
        for status in [
            "PENDIENTE",
            "PENDIENTE",
            "PENDING",
            "custom/state:7",
            "",
        ]
    ]
    assert dict(request_states(rows)) == {
        "PENDIENTE": 2,
        "PENDING": 1,
        "custom/state:7": 1,
        "": 1,
    }
    figure = states_figure(request_states(rows))
    assert figure.layout.xaxis.range[0] == 0
    assert figure.layout.xaxis.dtick == 1
    assert sum(figure.data[0].x) == len(rows)


def test_scope_counts_follow_returned_search_population_and_display_filter(hub):
    context = QueryContext(filter="unassigned")
    unassigned = requests_in_scope(hub, context, registry())
    assert len(unassigned) == 1 and unassigned[0].machinery_id is None
    assert request_counts(hub, context, registry()).total == 1
    assert request_counts(hub, context, registry()).unassigned == 1
    assert usage_timeline(unassigned).periods[0].starts_on == date(2026, 9, 16)
    # A backend search has already removed the other source request.
    hub.requests = unassigned
    counts = request_counts(hub, QueryContext(query="selected backend population"), registry())
    assert counts.total == 1
    assert counts.total != hub.scope.requests_total


def test_assignment_count_does_not_require_equipment_record_within_bounded_read(hub):
    hub.equipment = []
    assert request_counts(hub, QueryContext(), registry()).unassigned == 1


def test_pending_filter_uses_backend_alert_ids_without_comparing_source_dates_to_today(hub):
    context = QueryContext(filter="pending_started")
    assert requests_in_scope(hub, context, registry()) == []
    request = hub.requests[0]
    hub.alerts = [
        AlertRecord(
            id="test-alert",
            code="pending_request_started",
            severity="warning",
            title="Test",
            description="Explicit server cohort",
            owner="Test",
            request_id=request.id,
            evidence=[],
        )
    ]
    assert requests_in_scope(hub, context, registry()) == [request]


def test_unavailable_source_and_unavailable_registry_are_not_zero(hub):
    counts = request_counts(hub, QueryContext(), registry(available=False))
    assert counts.total == 2 and counts.without_confirmed_task is None
    assert request_counts(hub, QueryContext()).without_confirmed_task is None
    hub.sources[0].status = "error"
    counts = request_counts(hub, QueryContext(), registry())
    assert counts.total is None and counts.unassigned is None
    assert counts.without_confirmed_task is None
    assert requests_in_scope(hub, QueryContext()) == []


def test_valid_empty_scope_is_zero_but_cross_mode_snapshot_is_unavailable(hub):
    hub.requests = []
    counts = request_counts(hub, QueryContext(), registry())
    assert (counts.total, counts.unassigned, counts.without_confirmed_task) == (0, 0, 0)
    assert request_counts(hub, QueryContext(mode="live"), registry()).total is None


def test_sent_task_links_by_source_request_and_current_assignment_not_names(hub):
    movement = confirmed_movement(hub)
    workflow = registry(movement)
    request = next(request for request in hub.requests if request.machinery_id)
    assert has_confirmed_task(hub, request, workflow)
    assert request_counts(hub, QueryContext(), workflow).without_confirmed_task == 1
    unlinked = requests_in_scope(hub, QueryContext(filter="unlinked"), workflow)
    assert len(unlinked) == 1 and unlinked[0].id != request.id
    # A new assignment, even with the same display name, is not the sent task's assignment.
    request.machinery_id = "another-equipment-with-the-same-name"
    assert not has_confirmed_task(hub, request, workflow)


@pytest.mark.parametrize(
    "change",
    [
        {"request_source_id": "another-source-request"},
        {"source_request": {"id": "another-row"}},
        {"mode": "live"},
        {"environment": "local"},
        {"state": "unknown"},
        {"job_id": None},
        {"project_source_id": "another-project"},
        {"machinery_source_id": "another-machine"},
    ],
)
def test_task_confirmation_rejects_different_ids_mode_environment_or_state(hub, change):
    movement = confirmed_movement(hub).model_copy(update=change)
    request = next(request for request in hub.requests if request.machinery_id)
    assert not has_confirmed_task(hub, request, registry(movement))


def test_task_confirmation_requires_matching_evidence_class(hub):
    movement = confirmed_movement(hub)
    movement.source_request["provenance"]["evidence_kind"] = "live_read"
    request = next(request for request in hub.requests if request.machinery_id)
    assert not has_confirmed_task(hub, request, registry(movement))


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ("2026-09-12", "2026-09-12", (date(2026, 9, 12), date(2026, 9, 12))),
        ("2026-09-12T01:00:00Z", "2026-09-13T01:00:00Z", (date(2026, 9, 11), date(2026, 9, 12))),
        (
            "2026-09-12T00:00:00-06:00",
            "2026-09-12T23:00:00-06:00",
            (date(2026, 9, 12), date(2026, 9, 12)),
        ),
        ("2024-02-29", "2024-03-01", (date(2024, 2, 29), date(2024, 3, 1))),
    ],
)
def test_usage_calendar_preserves_date_only_and_converts_only_zoned_instants(
    hub, start, end, expected
):
    request = hub.requests[0].model_copy(update={"starts_on": start, "ends_on": end})
    timeline = usage_timeline([request])
    assert len(timeline.periods) == 1 and not timeline.excluded
    period = timeline.periods[0]
    assert (period.starts_on, period.ends_on) == expected
    assert period.request.starts_on == start and period.request.ends_on == end


@pytest.mark.parametrize(
    "start,end",
    [
        (None, "2026-09-12"),
        ("2026-09-12", None),
        ("2026-02-29", "2026-03-01"),
        ("20260912", "2026-09-13"),
        ("2026-09-12T00:00:00", "2026-09-13"),
        ("2026-09-12", "2026-09-11"),
        ("2026-09-12T12:00:00-06:00", "2026-09-12T11:00:00-06:00"),
        ("2026-09-12", "9999-12-31"),
    ],
)
def test_invalid_missing_ambiguous_or_inverted_usage_periods_are_counted_explicitly(
    hub, start, end
):
    request = hub.requests[0].model_copy(update={"starts_on": start, "ends_on": end})
    timeline = usage_timeline([request])
    assert not timeline.periods and len(timeline.excluded) == 1
    assert timeline.excluded[0].request.id == request.id and timeline.excluded[0].reason


def test_timeline_axis_comes_from_source_periods_and_includes_end_calendar_day(hub):
    timeline = usage_timeline(hub.requests)
    figure = usage_figure(timeline)
    assert list(figure.data[0].base) == ["2026-09-11", "2026-09-16"]
    assert list(figure.data[0].x) == [4 * DAY_MS, 3 * DAY_MS]
    assert list(figure.layout.xaxis.range) == ["2026-09-11", "2026-09-19"]
    assert figure.data[0].customdata[0][3] == "14 sep 2026"
    assert not figure.layout.shapes and not figure.layout.annotations
    original = figure.to_json()
    hub.generated_at += timedelta(days=3650)
    hub.data_as_of = datetime(2040, 1, 1, tzinfo=UTC)
    assert usage_figure(usage_timeline(hub.requests)).to_json() == original


def test_repeated_display_names_remain_separate_exact_request_rows(hub):
    first = hub.requests[0]
    second = first.model_copy(deep=True, update={"id": "a-second-source-request"})
    second.provenance.source_id = "another-original-id"
    figure = usage_figure(usage_timeline([first, second]))
    assert set(figure.data[0].y) == {first.id, second.id}
    assert len(figure.data[0].y) == 2
    assert {row[0] for row in figure.data[0].customdata} == {
        first.provenance.source_id,
        second.provenance.source_id,
    }


def test_overview_serializes_two_charts_and_accessible_original_data_without_fake_kpis(hub):
    component = overview(hub, QueryContext(), registry())
    payload = json.dumps(component, cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert "decision-request-states" in payload and "decision-request-usage" in payload
    assert "Ver datos de estados" in payload and "Ver datos de períodos" in payload
    assert "Inicio y fin incluidos; no son plazos de entrega" in payload
    assert "Qué requiere atención" in payload and "Qué requiere revisión" in payload
    assert "decision-count" not in payload and "Solicitudes en vista" not in payload
    assert "Ver distribución por estado de solicitud" in payload
    for request in hub.requests:
        assert request.provenance.source_id in payload
    assert "porcentaje" not in payload and "utilización" not in payload


def test_unavailable_registry_and_excluded_dates_remain_visible_in_overview(hub):
    hub.requests[0].starts_on = "ambiguous"
    payload = json.dumps(overview(hub, QueryContext()), cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert "Registro de tareas sin confirmar" in payload
    assert "1 solicitud(es) no representadas" in payload
    assert "Fecha no válida o con hora sin zona" in payload
    assert "ambiguous" in payload
