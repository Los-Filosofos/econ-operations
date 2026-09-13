"""Indicators are per-row differences between documented instants; never means, never clock.

Constructors are minimal local copies (fixture hub through `read_hub`, an isolated live
store with a Mock connector) so this module never imports another test module.
"""

import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusEquipment, NexusRequest, NexusSnapshot
from app.main import create_app
from app.models import metadata
from app.models.hub import HubResponse, Provenance
from app.models.indicators import IndicatorsReport
from app.models.workflow import OperationsCoverage, WorkflowOverview
from app.services import indicators
from app.services.hub import read_hub
from app.services.indicators import SHEETS, compute_indicators
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping

APPROVED_ID = "46d2573e-08d3-4855-971d-2fbf9564e135"
PENDING_ID = "0cbbbd77-4593-4791-9be5-afd46b06c888"
CF03_ID = "66faacde-728c-4378-8b46-dbfb38254e03"
OBSERVED = datetime(2026, 9, 12, 18, tzinfo=UTC)
EVENT_TIME = OBSERVED - timedelta(hours=2)
# 12:00Z is 06:00 in El Salvador (UTC−6): the business day of the cut is 2026-09-13.
CUTOFF = datetime(2026, 9, 13, 12, tzinfo=UTC)
# Matched against the "_"-separated tokens of every JSON key of the report.
FORBIDDEN_TOKENS = {
    "mean",
    "avg",
    "average",
    "percent",
    "percentage",
    "pct",
    "p50",
    "p90",
    "median",
    "rate",
    "ratio",
}


# ----- minimal constructors ---------------------------------------------------------------


def fixture_hub() -> HubResponse:
    settings = Settings(database_url="sqlite://", _env_file=None)
    return read_hub(settings, Mock(), "fixture")


def registry(*movements, complete=True, last_sync_at=None, available=True) -> WorkflowOverview:
    coverage = OperationsCoverage(
        total=len(movements) if complete else len(movements) + 1,
        displayed=len(movements),
        is_complete=complete,
        note="Registro de prueba",
    )
    return WorkflowOverview(
        available=available,
        complete=complete,
        message="Registro de prueba" if complete else "Registro parcial de prueba",
        movements=list(movements),
        last_sync_at=last_sync_at,
        coverage=coverage,
    )


def unit(identifier: str, estado: str, **fields) -> NexusEquipment:
    fields.setdefault("active_failure_is_paro", False)
    return NexusEquipment(
        id=identifier,
        clave=None,
        no_activo=identifier.upper(),
        nombre=f"Unidad {identifier}",
        estado=estado,
        **fields,
    )


def request(identifier: str, status: str, **fields) -> NexusRequest:
    return NexusRequest(
        id=identifier,
        status=status,
        project_id="indicators-test-project",
        project_name="Proyecto de prueba de indicadores",
        **fields,
    )


def snapshot(equipment=None, requests=None) -> NexusSnapshot:
    equipment = (
        equipment
        if equipment is not None
        else [
            unit(
                "indicators-test-unit",
                "OCUPADA",
                project_id="indicators-test-project",
                fecha_inicio_uso="2026-09-10",
                fecha_fin_uso="2026-09-12",
            )
        ]
    )
    requests = (
        requests
        if requests is not None
        else [
            request(
                "indicators-test-request",
                "APROBADA",
                maquinaria_id="indicators-test-unit",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                created_at="2026-09-11T14:00:00Z",
                approved_at="2026-09-11T15:00:00Z",
                approved_by_user_id="indicators-test-approver",
            )
        ]
    )
    return NexusSnapshot(
        equipment=equipment,
        requests=requests,
        equipment_total=len(equipment),
        requests_total=len(requests),
        complete=True,
    )


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'indicators-live.db'}",
        allow_live_reads=True,
        _env_file=None,
    )
    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    connector = Mock(configured=True)
    connector.read.return_value = snapshot()
    yield settings, engine, connector, OperationsLedger(engine)
    engine.dispose()


def live_hub(store, *, data_as_of=CUTOFF) -> HubResponse:
    settings, engine, connector, _ = store
    hub = read_hub(settings, connector, "live", engine=engine)
    # The cut of the reading is fixed explicitly; the wall clock never decides an age.
    hub.data_as_of = data_as_of
    return hub


def sent(store, reference="indicators-test-movement"):
    settings, _, connector, ledger = store
    hub = read_hub(settings, connector, "live")
    request, equipment = hub.requests[0], hub.equipment[0]
    movement = ledger.create(
        "live",
        request,
        equipment,
        TransferMapping(
            request_source_id=request.provenance.source_id,
            machinery_source_id=equipment.provenance.source_id,
            project_source_id=request.project_id,
            poi_id="indicators-test-poi",
            assigned_user_ids=("indicators-test-driver",),
            movement_reference=reference,
            scheduled_date=date(2026, 9, 12),
        ),
        tracked_vehicle_id="indicators-test-vehicle",
    )
    ledger.queue(movement.id)
    ledger.claim(movement.id)
    return ledger.finish_sent(
        movement.id, f"job-{reference}", status="status-pending", workflow_role="0"
    )


def observe(store, movement, *, kind="task_state", event_time=EVENT_TIME, **values):
    source_id = movement.job_id if kind == "task_state" else "indicators-test-visit"
    data = {"job_id": movement.job_id, **values}
    if kind == "arrival":
        data.update(poi_id="indicators-test-poi", tracked_asset_id="indicators-test-vehicle")
    return store[3].record_observation(
        movement.id,
        "live",
        kind=kind,
        source_id=source_id,
        event_time=event_time,
        observed_at=OBSERVED,
        data=data,
        provenance=Provenance(
            source="startrack",
            source_id=source_id,
            environment="sandbox",
            observed_at=OBSERVED,
            is_synthetic=True,
            evidence_kind="live_read",
        ),
    )


def result_of(report: IndicatorsReport, indicator_id: str):
    return next(item for item in report.indicators if item.sheet.id == indicator_id)


def row_of(result, source_id: str):
    return next(row for row in result.rows if row.source_id == source_id)


def walk_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


# ----- fixture ---------------------------------------------------------------------------


def test_fixture_computes_only_source_to_source_differences():
    report = compute_indicators(fixture_hub(), None)

    assert report.mode == "fixture" and report.data_as_of is None
    assert report.scope.equipment_returned == 5 and report.scope.equipment_total == 15
    assert [item.sheet.id for item in report.indicators] == list(SHEETS)

    approval = result_of(report, "approval_time")
    assert approval.status == "partial"
    approved = row_of(approval, APPROVED_ID)
    assert approved.status == "evaluable"
    assert approved.values["seconds"] == pytest.approx(42.209783, abs=1e-6)
    assert approved.values["minutes"] is None
    assert approved.values["created_at"] == "2026-09-12T00:59:19.326175+00:00"
    assert approved.values["approved_at"] == "2026-09-12T01:00:01.535958+00:00"
    pending = row_of(approval, PENDING_ID)
    assert pending.status == "not_evaluable" and "sin approved_at" in pending.reason
    assert approval.evaluable_count == 1 and approval.not_evaluable_count == 1

    age = result_of(report, "open_request_age")
    assert age.status == "not_evaluable" and "sin corte" in age.reason
    assert [row.source_id for row in age.rows] == [PENDING_ID]
    assert age.rows[0].status == "not_evaluable" and "sin corte" in age.rows[0].reason
    assert "hours" not in age.rows[0].values

    # (a) Fixture never sends tasks: absence in the archive is not zero, so the indicator is
    # not evaluable there; the approved request is still listed with that reason.
    without_task = result_of(report, "approved_with_unit_without_sent_task")
    assert without_task.status == "not_evaluable"
    assert "ausencia en el archivo no es cero" in without_task.reason
    assert [row.source_id for row in without_task.rows] == [APPROVED_ID]
    assert without_task.rows[0].status == "not_evaluable"
    assert "sent_task" not in without_task.rows[0].values
    assert "5 de 15 unidades" in without_task.coverage_note

    occupied = result_of(report, "occupied_without_project")
    assert occupied.status == "not_evaluable" and occupied.rows == []
    assert occupied.reason.startswith("sin casos evaluables")
    assert "ninguna unidad OCUPADA entre las 5 filas leídas" in occupied.reason

    ended = result_of(report, "assignment_ended")
    assert ended.status == "not_evaluable" and "sin corte" in ended.reason
    assert [row.source_id for row in ended.rows] == [CF03_ID]
    assert "ended" not in ended.rows[0].values

    for indicator_id in ("completed_task_without_receipt", "evidence_age"):
        result = result_of(report, indicator_id)
        assert result.status == "not_evaluable" and result.rows == []
        assert "fixture" in result.reason
    failures = result_of(report, "active_failure_registered")
    assert failures.status == "not_evaluable" and failures.rows == []
    assert "ninguna falla activa entre las 5 filas leídas" in failures.reason
    assert report.last_registry_read_at is None and report.ledger_available is False
    assert any("fixture" in note and "sin corte" in note for note in report.notes)


def test_fixture_never_uses_the_clock_for_source_facts(monkeypatch):
    class Clockless(datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("compute_indicators consultó el reloj")

        @classmethod
        def utcnow(cls):
            raise AssertionError("compute_indicators consultó el reloj")

    hub = fixture_hub()
    monkeypatch.setattr(indicators, "datetime", Clockless)

    report = compute_indicators(hub, None)

    assert report.generated_at == hub.generated_at
    assert result_of(report, "approval_time").evaluable_count == 1
    assert result_of(report, "occupied_without_project").status == "not_evaluable"
    assert all(item.status == "not_evaluable" for item in report.indicators[1:])


def test_no_percentages_or_means_are_published(store):
    movement = sent(store)
    observe(store, movement, status="provider-closed", workflow_role="1")
    fixture = compute_indicators(fixture_hub(), None)
    live = compute_indicators(
        live_hub(store), registry(*store[3].list("live"), last_sync_at=OBSERVED)
    )

    for report in (fixture, live):
        payload = json.loads(report.model_dump_json())
        tokens = {token for key in walk_keys(payload) for token in key.lower().split("_")}
        assert not tokens & FORBIDDEN_TOKENS
        for item in report.indicators:
            assert item.evaluable_count + item.partial_count + item.not_evaluable_count == len(
                item.rows
            )
            assert item.sheet.denominator.startswith("No aplica")
            assert item.sheet.question and item.sheet.decision and item.sheet.status_rule
    assert all(item.partial_count == 0 for item in fixture.indicators)
    assert all(
        item.evaluable_count + item.not_evaluable_count == len(item.rows)
        for item in fixture.indicators
    )


# ----- live with an explicit cut ---------------------------------------------------------


def test_live_snapshot_with_cutoff_computes_ages(store):
    settings, engine, connector, _ = store
    connector.read.return_value = snapshot(
        equipment=[
            unit(
                "indicators-ended-unit",
                "OCUPADA",
                project_id="indicators-test-project",
                fecha_fin_uso="2026-09-12",
            ),
            unit("indicators-orphan-unit", "OCUPADA"),
            unit("indicators-undated-unit", "DISPONIBLE", project_id="indicators-test-project"),
        ],
        requests=[
            request(
                "indicators-started",
                "PENDIENTE",
                fecha_inicio="2026-09-11",
                fecha_fin="2026-09-20",
                created_at="2026-09-10T12:00:00Z",
            ),
            request(
                "indicators-future",
                "PENDIENTE",
                fecha_inicio="2026-09-20",
                fecha_fin="2026-09-25",
                created_at="2026-09-13T00:00:00Z",
            ),
            request(
                "indicators-approved-no-unit",
                "APROBADA",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                created_at="2026-09-11T00:00:00Z",
                approved_at="2026-09-12T00:00:00Z",
            ),
        ],
    )

    report = compute_indicators(live_hub(store), registry(last_sync_at=OBSERVED))

    assert report.mode == "live" and report.data_as_of == CUTOFF
    age = result_of(report, "open_request_age")
    assert age.status == "evaluable" and age.evaluable_count == 3
    started = row_of(age, "indicators-started")
    assert started.values["variant"] == "pendiente" and started.values["hours"] == 72.0
    assert started.values["start_reached"] is True and started.values["days_since_start"] == 2
    future = row_of(age, "indicators-future")
    assert future.values["hours"] == 12.0
    assert future.values["start_reached"] is False and future.values["days_since_start"] is None
    assert "atraso" not in json.dumps(future.model_dump(mode="json"), ensure_ascii=False)
    no_unit = row_of(age, "indicators-approved-no-unit")
    assert no_unit.values["variant"] == "aprobada_sin_unidad"
    assert no_unit.values["since_field"] == "approved_at" and no_unit.values["hours"] == 36.0
    assert all(
        value >= 0
        for row in age.rows
        for value in row.values.values()
        if isinstance(value, int | float) and not isinstance(value, bool)
    )

    occupied = result_of(report, "occupied_without_project")
    assert occupied.status == "evaluable" and occupied.evaluable_count == 2
    assert row_of(occupied, "indicators-orphan-unit").values["without_project"] is True
    assert row_of(occupied, "indicators-ended-unit").values["without_project"] is False

    ended = result_of(report, "assignment_ended")
    assert ended.status == "partial"
    assert row_of(ended, "indicators-ended-unit").values == {
        "machinery_status": "OCUPADA",
        "project_id": "indicators-test-project",
        "assignment_ends_on": "2026-09-12",
        "ended": True,
        "days_since_end": 1,
    }
    undated = row_of(ended, "indicators-undated-unit")
    assert undated.status == "not_evaluable" and "sin fecha_fin_uso" in undated.reason
    assert "indicators-orphan-unit" not in {row.source_id for row in ended.rows}

    # Without a cut the very same live rows are not evaluable: the wall clock never stands in.
    uncut = compute_indicators(live_hub(store, data_as_of=None), registry(last_sync_at=OBSERVED))
    assert result_of(uncut, "open_request_age").status == "not_evaluable"
    assert result_of(uncut, "assignment_ended").status == "not_evaluable"
    assert result_of(uncut, "occupied_without_project").evaluable_count == 2


def test_approved_with_unit_without_sent_task_is_a_list_that_depends_on_registry_coverage(store):
    settings, engine, connector, ledger = store
    movement = sent(store)
    connector.read.return_value = snapshot(
        equipment=[
            unit("indicators-test-unit", "OCUPADA", project_id="indicators-test-project"),
            unit("indicators-idle-unit", "DISPONIBLE"),
        ],
        requests=[
            snapshot().requests[0],
            request(
                "indicators-without-task",
                "APROBADA",
                maquinaria_id="indicators-idle-unit",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                approved_at="2026-09-11T15:00:00Z",
            ),
            request(
                "indicators-unit-outside",
                "APROBADA",
                maquinaria_id="indicators-unit-not-in-page",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                approved_at="2026-09-11T15:00:00Z",
            ),
        ],
    )
    movements = ledger.list("live")

    complete = compute_indicators(live_hub(store), registry(*movements, last_sync_at=OBSERVED))
    result = result_of(complete, "approved_with_unit_without_sent_task")
    assert result.status == "partial" and result.partial_count == 0
    with_task = row_of(result, "indicators-test-request")
    assert with_task.status == "evaluable" and with_task.values["sent_task"] is True
    assert with_task.values["job_ids"] == movement.job_id
    assert with_task.values["movement_ids"] == movement.id
    assert with_task.values["hours_approved_to_sent"] == pytest.approx(
        (movement.sent_at - datetime(2026, 9, 11, 15, tzinfo=UTC)).total_seconds() / 3600, abs=0.01
    )
    without = row_of(result, "indicators-without-task")
    assert without.status == "evaluable" and without.values["sent_task"] is False
    outside = row_of(result, "indicators-unit-outside")
    assert outside.status == "not_evaluable" and "fuera de la lectura" in outside.reason

    partial = compute_indicators(
        live_hub(store), registry(*movements, complete=False, last_sync_at=OBSERVED)
    )
    result = result_of(partial, "approved_with_unit_without_sent_task")
    assert row_of(result, "indicators-test-request").status == "evaluable"
    absent = row_of(result, "indicators-without-task")
    assert absent.status == "partial" and absent.values["sent_task"] is None
    assert "no es verificable" in absent.reason and result.partial_count == 1
    assert "Registro parcial" in result.coverage_note

    # A stale stored copy of the request is never a current task for it.
    changed = live_hub(store)
    changed.requests[0].approved_at = OBSERVED
    result = result_of(
        compute_indicators(changed, registry(*movements, last_sync_at=OBSERVED)),
        "approved_with_unit_without_sent_task",
    )
    assert row_of(result, "indicators-test-request").values["sent_task"] is False

    unavailable = compute_indicators(live_hub(store), registry(available=False))
    result = result_of(unavailable, "approved_with_unit_without_sent_task")
    assert result.status == "not_evaluable" and "no disponible" in result.reason
    assert all(row.status == "not_evaluable" for row in result.rows) and len(result.rows) == 3


def test_completed_task_without_receipt_uses_event_time_not_observed_at(store):
    settings, engine, connector, ledger = store
    movement = sent(store)
    # The task closed at EVENT_TIME; Startrack was read two hours later (OBSERVED).
    observe(store, movement, status="provider-closed", workflow_role="1")
    hub = live_hub(store, data_as_of=EVENT_TIME + timedelta(hours=10))

    report = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=OBSERVED))

    result = result_of(report, "completed_task_without_receipt")
    assert result.status == "evaluable" and len(result.rows) == 1
    [row] = result.rows
    assert row.subject_id == f"econ:movement:{movement.id}" and row.label == movement.job_id
    assert row.values["receipt_declared"] is False
    assert row.values["completed_event_time"] == EVENT_TIME.isoformat()
    assert row.values["hours_since_completion"] == 10.0
    assert f"observed_at={OBSERVED.isoformat()}" in row.evidence

    # A newer pending state reopens the task: it leaves the population.
    observe(
        store,
        movement,
        event_time=EVENT_TIME + timedelta(hours=1),
        status="provider-reopened",
        workflow_role="0",
    )
    reopened = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=OBSERVED))
    assert result_of(reopened, "completed_task_without_receipt").rows == []

    # A completed state without its own date is not evaluable: the read time never stands in.
    second = sent(store, reference="indicators-undated-movement")
    observe(store, second, event_time=None, status="provider-closed", workflow_role="1")
    undated = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=OBSERVED))
    result = result_of(undated, "completed_task_without_receipt")
    [row] = result.rows
    assert row.subject_id == f"econ:movement:{second.id}"
    assert row.status == "not_evaluable" and "sin event_time" in row.reason
    assert "hours_since_completion" not in row.values

    # A declared receipt keeps the row evaluable without an age; it is not derived from GPS.
    ledger.record_receipt(
        second.id,
        "live",
        receiver="Responsable de prueba",
        received_at=OBSERVED,
        reference="constancia-prueba",
    )
    received = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=OBSERVED))
    [row] = result_of(received, "completed_task_without_receipt").rows
    assert row.status == "evaluable" and row.values["receipt_declared"] is True
    assert row.values["receipt_reference"] == "constancia-prueba"
    assert "hours_since_completion" not in row.values


def test_evidence_age_uses_the_last_registry_reading_and_generated_at(store):
    settings, engine, connector, ledger = store
    movement = sent(store)
    observe(store, movement, status="provider-pending", workflow_role="0")
    hub = live_hub(store)
    hub.generated_at = OBSERVED + timedelta(hours=3)
    # recorded_at of the last cut is older; a later confirmation without changes is the reading.
    last_read = OBSERVED + timedelta(hours=1)

    report = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=last_read))

    assert report.last_registry_read_at == last_read
    result = result_of(report, "evidence_age")
    assert result.status == "evaluable"
    [row] = result.rows
    assert row.values["last_registry_read_at"] == last_read.isoformat()
    assert row.values["evidence_age_hours"] == 2.0
    assert row.values["movement_last_observed_at"] == OBSERVED.isoformat()

    without_read = compute_indicators(hub, registry(*ledger.list("live"), last_sync_at=None))
    assert result_of(without_read, "evidence_age").status == "not_evaluable"
    assert "sin lectura del registro" in result_of(without_read, "evidence_age").reason


def test_active_failure_rows_copy_prisma_fields_and_never_invent_an_age(store):
    settings, engine, connector, _ = store
    connector.read.return_value = snapshot(
        equipment=[
            unit(
                "indicators-failed-unit",
                "MANTENIMIENTO",
                active_failure_id="indicators-test-failure",
                active_failure_status="EN_PROCESO",
                active_failure_is_paro=True,
            ),
            unit("indicators-healthy-unit", "DISPONIBLE"),
        ],
        requests=[],
    )

    result = result_of(compute_indicators(live_hub(store), registry()), "active_failure_registered")

    assert result.status == "evaluable" and len(result.rows) == 1
    [row] = result.rows
    assert row.source_id == "indicators-failed-unit"
    assert row.values["active_failure_id"] == "indicators-test-failure"
    assert row.values["active_failure_status"] == "EN_PROCESO"
    assert row.values["active_failure_is_paro"] is True
    assert row.values["failure_age"] is None
    assert any("no verificable" in item for item in row.evidence)


# ----- HTTP contract ---------------------------------------------------------------------


def test_endpoint_publishes_fixture_report_and_openapi_tag(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'schema.db'}", _env_file=None))
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        schema = client.get("/openapi.json").json()
        operation = schema["paths"]["/api/v1/indicators"]["get"]
        assert operation["tags"] == ["Indicadores"]
        assert "sin promedios" in operation["summary"]
        assert "ausencia no es cero" in operation["summary"]
        assert "fixture sin corte" in operation["summary"]
        assert "Indicadores" in {tag["name"] for tag in schema["tags"]}

        response = client.get("/api/v1/indicators", params={"mode": "fixture"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        report = IndicatorsReport.model_validate(response.json())
        assert report.mode == "fixture" and report.data_as_of is None
        assert report.ledger_available is True and report.registry.status == "available"
        assert result_of(report, "approval_time").evaluable_count == 1
        assert result_of(report, "open_request_age").status == "not_evaluable"
        assert client.get("/api/v1/indicators", params={"mode": "production"}).status_code == 422
        assert client.get("/api/v1/indicators", params={"search": "x" * 101}).status_code == 422
        filtered = client.get("/api/v1/indicators", params={"search": "CF-01"}).json()
        assert filtered["scope"]["equipment_returned"] == 1
        assert filtered["scope"]["equipment_total"] == 15


def test_endpoint_with_live_disabled_explains_and_never_falls_back(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'disabled.db'}",
            allow_live_reads=False,
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        response = client.get("/api/v1/indicators", params={"mode": "live"})
    assert response.status_code == 200
    report = IndicatorsReport.model_validate(response.json())
    assert report.mode == "live" and report.data_as_of is None
    assert report.scope.equipment_returned == 0 and report.scope.requests_returned == 0
    assert report.scope.equipment_total is None
    assert report.registry.status == "disabled" and report.ledger_available is False
    assert all(item.rows == [] for item in report.indicators)
    assert all(item.status == "not_evaluable" for item in report.indicators)
    assert any("deshabilitadas" in note for note in report.notes)
    assert any("no hay fallback" in note for note in report.notes)
