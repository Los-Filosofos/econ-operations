"""The indicators page turns published rows into plain-language insights; nothing is invented.

Every expected sentence below is traced to a documented field of the fixture (created_at,
approved_at, fecha_fin_uso, estado) or to a synthetic row whose values are spelled out here.
"""

import json
from collections import Counter
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from plotly.utils import PlotlyJSONEncoder

from app.core.config import Settings
from app.dashboard.context import QueryContext
from app.dashboard.indicator_views import (
    COLUMNS,
    INDICATOR_SLAS,
    SLAS,
    duration_text,
    hours_figure,
    indicator_rows,
    indicator_table,
    insight_of,
    status_label,
    top_insights,
    when_text,
)
from app.dashboard.theme import MEASURE
from app.dashboard.views import PAGES, render_page
from app.models.indicators import IndicatorResult, IndicatorRow
from app.models.workflow import WorkflowOverview
from app.services.hub import read_hub
from app.services.indicators import SHEETS, compute_indicators

APPROVED_ID = "nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"
PENDING_ID = "nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"
CF01_ID = "nexus:equipment:2a49b73e-a139-4ef1-866b-d54ef246fb46"
CF03_ID = "nexus:equipment:66faacde-728c-4378-8b46-dbfb38254e03"
APPROVAL_INSIGHT = (
    "La solicitud de Cargador frontal para PROY-014 se aprobó en 42 s: creada el "
    "11/09/2026 · 18:59, aprobada el 11/09/2026 · 19:00. 1 solicitud sin tiempo de aprobación: "
    "la solicitud de Cargador frontal para PROY-014, creada el 12/09/2026 · 10:02. Motivo: sin "
    "approved_at: la solicitud sigue PENDIENTE."
)


@pytest.fixture
def hub():
    return read_hub(Settings(database_url="sqlite://", _env_file=None), Mock(), "fixture")


def registry():
    return WorkflowOverview(available=True, complete=True, message="Registro local consultado")


def serialized(component) -> str:
    return json.dumps(component, cls=PlotlyJSONEncoder, ensure_ascii=False)


def components(value):
    if isinstance(value, list | tuple):
        for item in value:
            yield from components(item)
    elif hasattr(value, "to_plotly_json"):
        yield value
        yield from components(getattr(value, "children", None))


def kinds(content) -> Counter:
    return Counter(component.to_plotly_json()["type"] for component in components(content))


def row(subject_id: str, label: str, status: str = "evaluable", reason=None, **values):
    return IndicatorRow(
        subject_id=subject_id,
        source_id=subject_id.rsplit(":", 1)[-1],
        label=label,
        values=values,
        evidence=[f"{key}={value}" for key, value in values.items()],
        status=status,
        reason=reason,
    )


def result_for(identifier: str, rows: list[IndicatorRow], status="evaluable", reason=None):
    counts = Counter(item.status for item in rows)
    return IndicatorResult(
        sheet=SHEETS[identifier],
        status=status,
        reason=reason,
        rows=rows,
        evaluable_count=counts["evaluable"],
        partial_count=counts["partial"],
        not_evaluable_count=counts["not_evaluable"],
        coverage_note="Filas de prueba.",
    )


def result_of(report, identifier: str):
    return next(item for item in report.indicators if item.sheet.id == identifier)


# ----- fixture page ------------------------------------------------------------------------


def test_fixture_page_shows_eight_questions_one_observed_chart_and_visible_records(hub):
    content = render_page("/indicadores", hub, QueryContext(), registry())
    page = serialized(content)
    report = compute_indicators(hub, registry())

    assert next(page for page in PAGES if page["path"] == "/indicadores")["icon"] == "chart-bar"
    for index, sheet in enumerate(SHEETS.values(), start=1):
        assert f"I{index} · {sheet.name}" in page
        assert sheet.question in page
    expected = {
        "approval_time": "Parcial",
        "open_request_age": "No evaluable",
        "approved_with_unit_without_sent_task": "No evaluable",
        "occupied_without_project": "Sin casos evaluables",
        "assignment_ended": "No evaluable",
        "completed_task_without_receipt": "No evaluable",
        "active_failure_registered": "Sin casos evaluables",
        "evidence_age": "No evaluable",
    }
    assert {item.sheet.id: status_label(item)[0] for item in report.indicators} == expected
    assert "Sin corte; antigüedades no evaluables" in page
    assert "Modo fixture: muestras documentales sin corte de observación" in page
    assert "5 de 15 unidades · 2 de 2 solicitudes" in page
    assert '"aria-label": "Pregunta de análisis"' in page
    assert "Definición y datos de origen" in page
    # A single measured approval is a dated interval, never a trend or SLA result.
    counts = kinds(content)
    assert counts["Graph"] == 1
    assert "indicator-sla-" not in page and "sla-overview-" not in page
    tables = [
        item
        for item in components(content)
        if str(getattr(item, "id", "")).startswith("indicator-rows-")
    ]
    for table in tables:
        assert table.dashGridOptions["paginationPageSize"] == 10
        assert [column["field"] for column in table.columnDefs] == [key for key, _ in COLUMNS]
    assert "/api/v1/indicators?mode=fixture" in page


def test_insights_are_derived_from_fixture_rows_and_cite_their_dates(hub):
    report = compute_indicators(hub, None)
    texts = {item.sheet.id: insight_of(item, hub, report).text for item in report.indicators}

    assert texts["approval_time"] == APPROVAL_INSIGHT
    assert texts["open_request_age"] == (
        "1 solicitud abierta sin antigüedad evaluable: la solicitud de Cargador frontal para "
        "PROY-014 (pendiente desde 12/09/2026 · 10:02). Motivo: sin corte de observación (fixture)."
    )
    assert texts["approved_with_unit_without_sent_task"].startswith(
        "1 solicitud aprobada con unidad sin evaluar: la solicitud de Cargador frontal para "
        "PROY-014 con CF-03, aprobada el 11/09/2026 · 19:00. Motivo: no evaluable en fixture"
    )
    assert texts["occupied_without_project"] == (
        "Sin casos: ninguna de las 5 unidades leídas figura OCUPADA (4 DISPONIBLE, 1 OBSOLETA)."
    )
    assert texts["assignment_ended"] == (
        "1 unidad asignada sin evaluar: CF-03 asignada a PROY-014 hasta 14/09/2026. "
        "Motivo: sin corte de observación (fixture)."
    )
    assert texts["active_failure_registered"] == (
        "Sin casos: ninguna de las 5 unidades leídas tiene active_failure_id en Prisma."
    )
    assert texts["completed_task_without_receipt"].startswith("No evaluable en fixture")
    assert texts["evidence_age"].startswith("No evaluable en fixture")
    assert "atras" not in " ".join(texts.values()).lower()
    assert [item.id for item in top_insights(report, hub)] == ["approval_time"]


def test_page_is_readable_in_the_fixture_without_a_ledger_and_guards_a_failed_source(hub):
    assert "I1 · " in serialized(render_page("/indicadores", hub, QueryContext()))
    hub.sources[0].status = "error"
    page = serialized(render_page("/indicadores", hub, QueryContext()))
    assert "Indicadores: origen no disponible" in page
    assert "I1 · " not in page
    assert "Indicadores: origen no disponible" in serialized(
        render_page("/indicadores", hub, QueryContext(mode="live"))
    )


# ----- text helpers ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (42.209783, "42 s"),
        (8100, "2 h 15 min"),
        (36 * 3600, "36 h"),
        (47 * 3600 + 300, "47 h 5 min"),
        (49.5 * 3600, "2 días 1 h"),
        (72 * 3600, "3 días"),
    ],
)
def test_durations_read_in_plain_language(seconds, expected):
    assert duration_text(seconds) == expected


def test_single_approval_keeps_source_instants_and_elapsed_time(hub):
    result = result_of(compute_indicators(hub, registry()), "approval_time")
    chart = hours_figure(result, hub)
    approved = next(row for row in result.rows if row.status == "evaluable")
    assert chart.layout.meta["kind"] == "interval"
    start, end = [datetime.fromisoformat(value) for value in chart.data[0].x]
    assert (end - start).total_seconds() == approved.values["seconds"]
    assert chart.data[0].type == "scatter"
    assert chart.data[0].mode == "lines+markers"
    assert chart.layout.annotations[2].text == "42 s"
    assert "Creada 18:59:19" == chart.layout.annotations[0].text
    assert "Aprobada 19:00:01" == chart.layout.annotations[1].text


def test_only_zoned_instants_become_dates_in_el_salvador_time():
    assert when_text("2026-09-12T14:00:00Z") == "12/09/2026 · 08:00"
    assert when_text(datetime(2026, 9, 12, 14, tzinfo=UTC)) == "12/09/2026 · 08:00"
    assert when_text("2026-09-12T14:00:00") == "sin fecha"
    assert when_text(None) == "sin fecha"
    assert when_text("no es una fecha") == "sin fecha"


# ----- live-like rows -----------------------------------------------------------------------


def test_live_like_rows_read_as_actions_with_their_source_instants(hub):
    report = compute_indicators(hub, None).model_copy(
        update={
            "data_as_of": datetime(2026, 9, 17, 12, tzinfo=UTC),
            "generated_at": datetime(2026, 9, 12, 21, tzinfo=UTC),
        }
    )
    project_id = hub.requests[0].project_id
    waiting = result_for(
        "open_request_age",
        [
            row(
                PENDING_ID,
                "APROBADA 2026-09-16 → 2026-09-18",
                variant="aprobada_sin_unidad",
                since_field="approved_at",
                since="2026-09-12T20:00:00+00:00",
                hours=2.25,
                starts_on="2026-09-16",
                start_reached=False,
                days_since_start=None,
            )
        ],
    )
    ended = result_for(
        "assignment_ended",
        [
            row(
                CF03_ID,
                "CF-03",
                machinery_status="OBSOLETA",
                project_id=project_id,
                assignment_ends_on="2026-09-14",
                ended=True,
                days_since_end=3,
            )
        ],
    )
    failure = result_for(
        "active_failure_registered",
        [
            row(
                CF01_ID,
                "CF-01",
                machinery_status="MANTENIMIENTO",
                active_failure_id="falla-prueba",
                active_failure_status="EN_PROCESO",
                active_failure_is_paro=True,
                failure_age=None,
            )
        ],
    )
    completed = result_for(
        "completed_task_without_receipt",
        [
            row(
                "econ:movement:movimiento-prueba",
                "job-prueba",
                job_id="job-prueba",
                completed_event_time="2026-09-12T16:00:00+00:00",
                receipt_declared=False,
                hours_since_completion=10.0,
            )
        ],
    )
    evidence = result_for(
        "evidence_age",
        [
            row(
                "econ:movement:movimiento-prueba",
                "job-prueba",
                last_registry_read_at="2026-09-12T19:00:00+00:00",
                evidence_age_hours=2.0,
                movement_last_observed_at="2026-09-12T18:00:00+00:00",
            )
        ],
    )
    occupied = result_for(
        "occupied_without_project",
        [row(CF01_ID, "CF-01", machinery_status="OCUPADA", project_id=None, without_project=True)],
    )

    texts = {
        item.sheet.id: insight_of(item, hub, report)
        for item in (waiting, ended, failure, completed, evidence, occupied)
    }
    assert texts["open_request_age"].text == (
        "La solicitud de Cargador frontal para PROY-014 lleva 2 h 15 min aprobada sin unidad "
        "asignada desde 12/09/2026 · 14:00; su inicio solicitado (16/09/2026) aún no llega."
    )
    assert texts["assignment_ended"].text == (
        "CF-03 sigue asignada a PROY-014 con fecha_fin_uso 14/09/2026, vencida hace 3 días al "
        "corte (17/09/2026 · 06:00)."
    )
    assert texts["active_failure_registered"].text == (
        "1 unidad con falla activa registrada: CF-01 (EN_PROCESO, con paro); la antigüedad de la "
        "falla no se lee."
    )
    assert texts["completed_task_without_receipt"].text == (
        "La tarea job-prueba completada el 12/09/2026 · 10:00 lleva 10 h sin recepción "
        "declarada al corte."
    )
    assert texts["evidence_age"].text == (
        "La última lectura del registro fue el 12/09/2026 · 13:00, hace 2 h respecto a la "
        "consulta (12/09/2026 · 15:00); 1 traslado enviado en el registro, el más reciente "
        "observado el 12/09/2026 · 12:00."
    )
    assert texts["occupied_without_project"].text == "1 unidad OCUPADA sin proyecto: CF-01."
    assert {name: item.actionable for name, item in texts.items()} == {
        "open_request_age": 1,
        "assignment_ended": 1,
        "active_failure_registered": 1,
        "completed_task_without_receipt": 1,
        "evidence_age": 0,
        "occupied_without_project": 1,
    }
    assert all(item.status == "Evaluable" and item.family == "active" for item in texts.values())


def test_top_insights_prefer_actionable_rows_then_the_fixed_priority(hub):
    report = compute_indicators(hub, None)
    approval = result_of(report, "approval_time")
    occupied = result_for(
        "occupied_without_project",
        [row(CF01_ID, "CF-01", machinery_status="OCUPADA", project_id=None, without_project=True)],
    )
    evidence = result_for(
        "evidence_age",
        [
            row(
                "econ:movement:m",
                "job",
                last_registry_read_at="2026-09-12T19:00:00+00:00",
                evidence_age_hours=1.0,
                movement_last_observed_at=None,
            )
        ],
    )
    absent = result_for("active_failure_registered", [], "not_evaluable", "sin casos evaluables")
    mixed = report.model_copy(update={"indicators": [approval, absent, evidence, occupied]})

    assert [item.id for item in top_insights(mixed, hub)] == [
        "occupied_without_project",
        "evidence_age",
        "approval_time",
    ]
    assert [item.id for item in top_insights(mixed, hub, limit=1)] == ["occupied_without_project"]


# ----- chart, SLA cards and table -----------------------------------------------------------


def test_chart_uses_only_evaluable_magnitudes_and_orders_them():
    rows = [
        row(PENDING_ID, "PENDIENTE", hours=2.25),
        row(APPROVED_ID, "APROBADA", hours=36.0),
        row("nexus:request:tercera", "PENDIENTE", hours=12.0),
    ]
    assert len(hours_figure(result_for("open_request_age", rows[:2])).data[0].x) == 2
    unevaluable = row("nexus:request:x", "P", "not_evaluable", "sin corte")
    assert (
        len(hours_figure(result_for("open_request_age", [*rows[:2], unevaluable])).data[0].x) == 2
    )
    occupied = [
        row(f"nexus:equipment:{index}", f"U-{index}", without_project=True) for index in range(4)
    ]
    assert hours_figure(result_for("occupied_without_project", occupied)) is None

    chart = hours_figure(result_for("open_request_age", rows))
    assert chart is not None
    assert list(chart.data[0].x) == [36.0, 12.0, 2.25]
    assert list(chart.data[0].y) == [APPROVED_ID, "nexus:request:tercera", PENDING_ID]
    assert list(chart.data[0].text) == ["36 h", "12 h", "2.25 h"]
    assert chart.data[0].marker.color == MEASURE
    assert chart.layout.xaxis.title.text == "Tiempo abierta al corte (horas corridas)"
    assert chart.layout.xaxis.range[0] == 0
    assert len(chart.layout.yaxis.ticktext) == 3
    seconds = [
        row(f"nexus:request:{index}", f"S-{index}", seconds=3600.0 * index) for index in range(1, 4)
    ]
    assert list(hours_figure(result_for("approval_time", seconds)).data[0].x) == [3.0, 2.0, 1.0]


def test_sla_cards_are_the_documented_table_and_stay_to_be_validated(hub):
    assert [sla.id for sla in SLAS] == ["S1", "S2", "S3", "S4", "S5", "S6"]
    assert all(indicator in SHEETS for sla in SLAS for indicator in sla.indicators)
    assert {key: [sla.id for sla in value] for key, value in INDICATOR_SLAS.items()} == {
        "approval_time": ["S1"],
        "open_request_age": ["S1", "S2"],
        "approved_with_unit_without_sent_task": ["S3"],
        "occupied_without_project": [],
        "assignment_ended": [],
        "completed_task_without_receipt": ["S4"],
        "active_failure_registered": ["S5"],
        "evidence_age": ["S6"],
    }
    page = serialized(render_page("/indicadores", hub, QueryContext()))
    for sla in SLAS:
        assert sla.name in page and sla.threshold in page
    assert "a validar con ECON" in page
    assert "No calculable: /fallas no se lee" in page
    assert "no se calcula cumplimiento" in page
    assert "cumple" not in page.replace("cumplimiento", "")


def test_table_keeps_the_contract_columns_links_each_subject_and_folds_past_five_rows(hub):
    report = compute_indicators(hub, None)
    context = QueryContext()
    rows = indicator_rows(result_of(report, "approval_time"), context)
    assert [list(item) for item in rows] == [[key for key, _ in COLUMNS]] * 2
    approved = next(item for item in rows if item["subject_id"] == APPROVED_ID)
    assert context.request_href(APPROVED_ID) in approved["subject"]
    assert approved["status"] == "Evaluable" and approved["reason"] == "Fila evaluable"
    assert "seconds: 42.21" in approved["values"]
    assert "created_at=2026-09-12T00:59:19.326175+00:00" in approved["evidence"]
    pending = next(item for item in rows if item["subject_id"] == PENDING_ID)
    assert pending["status"] == "No evaluable" and "sin approved_at" in pending["reason"]
    unit = indicator_rows(result_of(report, "assignment_ended"), context)[0]
    assert context.equipment_href(CF03_ID) in unit["subject"]

    table = indicator_table(result_of(report, "approval_time"), context, folded=False)
    assert table.to_plotly_json()["type"] == "Div"
    many = result_for(
        "open_request_age",
        [row(f"nexus:request:{index}", f"S-{index}", hours=float(index)) for index in range(6)],
    )
    folded = indicator_table(many, context)
    assert folded.to_plotly_json()["type"] == "Accordion"
    assert "Ver las 6 filas" in serialized(folded)
    assert kinds(folded)["AgGrid"] == 1


# ----- decisions page ---------------------------------------------------------------------


def test_decisions_alias_uses_the_same_agenda_and_actions_as_home(hub):
    context = QueryContext()
    content = render_page("/decisiones", hub, context, registry())
    page = serialized(content)

    assert all(item["path"] != "/decisiones" for item in PAGES)
    assert page == serialized(render_page("/", hub, context, registry()))
    assert "Agenda de uso y asignación" in page
    for title in ("Resolver aprobación y asignación", "Revisar la asignación"):
        assert title in page
    assert "CF-03" in page and "OBSOLETA" in page
    assert "2026-09-11" in page and "2026-09-14" in page
    for request in hub.requests:
        assert context.request_href(request.id) in page
    assert "Lo que dicen los indicadores" not in page
    assert kinds(content)["Graph"] == 1

    unassigned = QueryContext(filter="unassigned")
    narrowed = serialized(render_page("/decisiones", hub, unassigned, registry()))
    assert "Revisar la asignación" in narrowed
    assert narrowed == page  # Overview ignores list filters.
    hub.requests = []
    empty = serialized(render_page("/decisiones", hub, context, registry()))
    assert "Sin solicitudes en esta lectura" in empty
