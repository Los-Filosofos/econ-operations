"""Regression checks for bounded evidence and honest chart populations."""

import json

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder
from sqlmodel import Session
from test_decision_analytics import confirmed_movement, registry
from test_decision_analytics import hub as hub
from test_decision_priorities import receipt

from app.core.config import Settings
from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import has_confirmed_task, states_figure
from app.dashboard.decision_priorities import decision_items
from app.dashboard.views import overview
from app.main import create_app
from app.models import metadata
from app.models.operations import Movement
from app.models.workflow import WorkflowOverview


@pytest.mark.parametrize("count,complete", [(0, True), (100, True), (101, False)])
def test_operations_http_reports_actual_ledger_window_and_narrowed_scope(
    hub, tmp_path, count, complete
):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'coverage.db'}", _env_file=None))
    record = confirmed_movement(hub)
    with TestClient(app) as client:
        metadata.create_all(app.state.engine)
        with Session(app.state.engine) as session:
            for index in range(count):
                data = record.model_dump(exclude={"events"}) | {
                    "id": f"test-coverage-{index:03}",
                    "movement_reference": f"test-coverage-{index:03}",
                    "identity_hash": f"test-{index}",
                    "next_review_at": record.created_at,
                    "request_source_id": "test-narrow-scope" if index == 0 else "test-other",
                }
                session.add(Movement(**data))
            session.commit()
        payload = client.get("/api/v1/operations").json()
        assert payload["available"] is True
        assert payload["complete"] is complete
        assert len(payload["movements"]) == min(count, 100)
        if not complete:
            assert "Registro parcial" in payload["message"]
        narrowed = client.get(
            "/api/v1/operations", params={"request_source_id": "test-narrow-scope"}
        ).json()
        assert narrowed["complete"] is True
        assert len(narrowed["movements"]) == min(count, 1)


def test_partial_registry_does_not_count_absence_or_recommend_another_plan(hub):
    request = next(item for item in hub.requests if item.machinery_id)
    machine = next(item for item in hub.equipment if item.id == request.machinery_id)
    machine.machinery_status = "OCUPADA"
    partial = WorkflowOverview(available=True, message="Partial registry")
    decision = next(
        item for item in decision_items(hub, QueryContext(), partial) if item.request == request
    )
    assert decision.title == "Consultar el registro completo del traslado"
    assert "fuera de esta ventana" in decision.evidence


def test_partial_registry_preserves_known_task_and_does_not_close_unseen_work(hub):
    request = next(item for item in hub.requests if item.machinery_id)
    machine = next(item for item in hub.equipment if item.id == request.machinery_id)
    machine.machinery_status = "OCUPADA"
    movement = confirmed_movement(hub).model_copy(update={"receipt": receipt()})
    partial = registry(movement).model_copy(update={"complete": False})
    assert has_confirmed_task(hub, request, partial)
    decision = next(
        item for item in decision_items(hub, QueryContext(), partial) if item.request == request
    )
    assert "registro completo" in decision.title
    assert "otros movimientos sin resolver" in decision.evidence


def test_chart_population_keeps_local_filter_and_exclusions_visible(hub):
    hub.requests[0].starts_on = "invalid"
    payload = json.dumps(
        overview(hub, QueryContext(), registry()), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "Solicitudes en esta vista: 2; devueltas por la consulta: 2" in payload
    assert "Solicitudes con período representable: 1 de 2" in payload
    assert "antes de la b" in payload and "sin instante com" in payload
    filtered = json.dumps(
        overview(hub, QueryContext(filter="unassigned"), registry()), cls=PlotlyJSONEncoder
    )
    assert "Solicitudes en esta vista: 1; devueltas por la consulta: 2" in filtered


def test_display_label_collisions_do_not_merge_distinct_source_categories():
    states = [("", 1), (" ", 2), ("Sin estado informado", 3)]
    figure = states_figure(states)
    assert len(set(figure.data[0].y)) == 3
    assert list(figure.layout.yaxis.ticktext) == ["Sin estado informado"] * 3
    assert sum(figure.data[0].x) == 6
