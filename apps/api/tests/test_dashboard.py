"""Exercise real Dash HTTP callbacks, not just the component factory."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder

from app.core.config import Settings
from app.dashboard.analytics import calendar, distribution, request_operation
from app.dashboard.context import QueryContext, parse_context
from app.dashboard.views import NAVIGATION, filter_links, navigation, render_page, scope
from app.main import create_app
from app.models.hub import HubResponse, TransferRecord


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'dash.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        # Dash registers assets and finalizes callbacks when serving its layout.
        assert client.get("/_dash-layout").status_code == 200
        yield client


def snapshot(client, search="?mode=fixture", *, previous=None, changed="url.search"):
    return client.post(
        "/_dash-update-component",
        json={
            "output": "snapshot.data",
            "outputs": {"id": "snapshot", "property": "data"},
            "inputs": [
                {"id": "url", "property": "search", "value": search},
                {"id": "refresh", "property": "n_clicks", "value": 1},
            ],
            "state": [{"id": "snapshot", "property": "data", "value": previous}],
            "changedPropIds": [changed],
        },
    )


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["response"]["snapshot"]["data"]


def test_cold_start_includes_styles_before_any_layout_request(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cold.db'}", _env_file=None)
    with TestClient(create_app(settings)) as cold:
        response = cold.get("/solicitudes?mode=fixture")
        assert response.status_code == 200
        assert 'rel="stylesheet" href="/assets/style.css' in response.text
        stylesheet = cold.get("/assets/style.css")
        assert stylesheet.headers["content-type"].startswith("text/css")
        assert "--blue: #144f81" in stylesheet.text


def test_one_server_serves_dash_assets_deep_links_and_existing_api(client):
    for path in ["/", "/solicitudes/nexus%3Arequest%3Amissing?mode=fixture", "/solicitudes"]:
        response = client.get(path)
        assert response.status_code == 200
        assert '<html lang="es">' in response.text
    for asset in ["style.css", "inter-latin.woff2", "econ-color.png", "econ-icon.png"]:
        assert client.get(f"/assets/{asset}").status_code == 200
    assert client.get("/api/v1/hub").json()["schema_version"] == "1.0"
    assert client.get("/health/ready").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_dash_reads_share_api_contract_and_filter_exactly(client):
    response = snapshot(client, "?mode=fixture&q=CF-03")
    assert response.headers["cache-control"] == "no-store"
    result = data(response)
    api = client.get("/api/v1/hub?mode=fixture&search=CF-03").json()
    assert result["key"] == ["fixture", "CF-03"]
    for field in ["equipment", "requests", "alerts", "summary", "scope", "data_as_of"]:
        assert result["hub"][field] == api[field]


def test_mode_change_never_reuses_fixture_or_enables_live(client):
    previous = data(snapshot(client))
    with patch.object(client.app.state.nexus, "read") as read:
        current = data(snapshot(client, "?mode=live", previous=previous))
    read.assert_not_called()
    assert current["hub"]["mode"] == "live"
    assert current["hub"]["equipment"] == []
    assert current["hub"]["summary"]["equipment_count"] is None
    assert current["hub"]["sources"][0]["status"] == "disabled"


def test_refresh_failure_discards_old_data_and_hides_internal_details(client):
    previous = data(snapshot(client))
    with patch("app.dashboard.application.read_hub", side_effect=RuntimeError("private-password")):
        result = data(snapshot(client, previous=previous, changed="refresh.n_clicks"))
    assert result["hub"] is None
    assert result["error"]
    assert "private-password" not in json.dumps(result)


def test_display_filter_reuses_browser_read_without_calling_provider(client):
    previous = data(snapshot(client))
    with patch("app.dashboard.application.read_hub") as read:
        response = snapshot(client, "?mode=fixture&filter=pending_started", previous=previous)
    read.assert_not_called()
    assert response.status_code in {200, 204}
    if response.status_code == 200:
        assert "snapshot" not in response.json().get("response", {})


@pytest.mark.parametrize(
    "search",
    [
        "?mode=production",
        "?mode=live&mode=fixture",
        "?q=" + "a" * 101,
        "?filter=imaginary",
    ],
)
def test_invalid_url_fails_without_loading_a_source(client, search):
    with patch("app.dashboard.application.read_hub") as read:
        result = data(snapshot(client, search))
    read.assert_not_called()
    assert result["hub"] is None and result["error"]


def test_browser_sessions_keep_separate_queries(client):
    first = data(snapshot(client, "?mode=fixture&q=CF-03"))
    second = data(snapshot(client, "?mode=fixture&q=missing-record"))
    assert first["hub"]["equipment"][0]["asset_number"] == "CF-03"
    assert second["hub"]["equipment"] == []
    assert first["key"] != second["key"]
    assert first["hub"]["equipment"][0]["transfers"] == []


def test_every_page_and_details_serialize_and_keep_semantic_evidence(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    context = QueryContext()
    paths = [path for path, _ in NAVIGATION] + [
        *(context.request_href(item.id).split("?", 1)[0] for item in hub.requests),
        *(context.equipment_href(item.id).split("?", 1)[0] for item in hub.equipment),
        "/solicitudes/missing",
        "/maquinaria/missing",
        "/missing",
    ]
    for path in paths:
        content = render_page(path, hub, QueryContext())
        serialized = json.dumps(content, cls=PlotlyJSONEncoder, ensure_ascii=False)
        assert serialized
    detail = json.dumps(
        render_page(context.request_href(hub.requests[0].id).split("?", 1)[0], hub, context),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert hub.requests[0].provenance.source_id in detail
    assert "Sin constancia de recepción" in detail
    assert "Sin traslado vinculado" in detail
    assert "Muestra del contrato proporcionado" in detail
    assert "Sin lectura fechada" in detail


def test_analytics_preserve_counts_missing_dates_and_partial_coverage(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    assert sum(count for _, count in distribution(hub)) == len(hub.equipment)
    assert calendar(hub) is None
    hub.data_as_of = datetime(2026, 9, 12, 18, tzinfo=UTC)
    hub.requests.append(hub.requests[0].model_copy(deep=True))
    hub.requests[0].starts_on = "2026-02-30"
    hub.requests[1].starts_on = "2026-09-12T01:00:00+00:00"
    hub.requests[2].starts_on = "2027-01-01"
    result = calendar(hub)
    assert result["undated"] == 1 and result["outside"] == 1
    assert result["days"][datetime(2026, 9, 11, tzinfo=UTC).date()] == 1
    unavailable = HubResponse.model_validate(client.get("/api/v1/hub?mode=live").json())
    assert calendar(unavailable) is None and distribution(unavailable) is None


def test_links_round_trip_search_and_quote_record_ids():
    context = QueryContext(mode="live", query="Proyecto Norte & Sur")
    for href in [
        context.equipment_href("nexus:equipment:a/b"),
        context.request_href("nexus:request:a/b"),
    ]:
        assert "a%2Fb" in href
        parsed = parse_context("?" + href.split("?", 1)[1])
        assert parsed == context


def components(value):
    if isinstance(value, list):
        for item in value:
            yield from components(item)
    elif hasattr(value, "to_plotly_json"):
        yield value
        yield from components(getattr(value, "children", None))


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/", "/"),
        ("/resumen", "/"),
        ("/solicitudes", "/solicitudes"),
        ("/solicitudes/source-id", "/solicitudes"),
        ("/maquinaria/unit-id", "/solicitudes"),
        ("/operaciones/movement-id", "/operaciones"),
        ("/fuentes", "/fuentes"),
    ],
)
def test_sidebar_has_one_current_section_and_filters_stay_on_requests(path, expected):
    context = QueryContext(mode="live", query="Proyecto Norte & Sur")
    current = [link for link in navigation(path, context) if " active" in link.className]
    assert len(current) == 1
    assert current[0].href == context.href(expected)
    assert current[0].children.to_plotly_json()["props"]["aria-current"] == "page"
    filters = filter_links(context).children
    assert all(link.href.startswith("/solicitudes?") for link in filters)
    assert any("filter=unassigned" in link.href for link in filters)
    assert parse_context("?mode=fixture&filter=unassigned").filter == "unassigned"


def test_request_table_focuses_on_six_operational_columns_and_preserves_detail_links(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    table = next(
        component
        for component in components(render_page("/solicitudes", hub, QueryContext()))
        if getattr(component, "id", None) == "requests-grid"
    )
    assert len(table.columnDefs) == 6
    assert [column["field"] for column in table.columnDefs] == [
        "project",
        "equipment",
        "period",
        "status",
        "transfer",
        "receipt",
    ]
    assert table.columnDefs[0]["cellRenderer"] == "markdown"
    for row, request in zip(table.rowData, hub.requests, strict=True):
        assert QueryContext().request_href(request.id) in row["project"]
        assert request.status == row["status"]
        assert "Sin constancia" in row["receipt"]


def test_scope_reports_selected_requests_without_changing_source_coverage(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    assert scope(hub).children[1].children == "2 solicitudes"
    current = scope(hub, QueryContext(filter="unassigned"))
    assert current.children[1].children == "1 de 2 solicitudes"
    assert current.children[2].children == "Cobertura parcial"


def test_request_details_keep_source_ids_and_plan_inputs_inside_closed_disclosures(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    request = next(item for item in hub.requests if item.machinery_id)
    content = render_page(f"/solicitudes/{request.id}", hub, QueryContext())
    disclosures = [
        component
        for component in components(content)
        if component.to_plotly_json()["type"] == "Details"
    ]
    titles = {component.children[0].children: component for component in disclosures}
    for title in [
        "Preparar traslado",
        "Referencias de integración",
        "Datos y referencias de la solicitud",
        "Estado y mantenimiento de la unidad",
    ]:
        assert title in titles
        assert not getattr(titles[title], "open", False)
    ids = [
        getattr(component, "id", None)
        for component in components(titles["Referencias de integración"])
    ]
    assert {"type": "workflow-field", "field": "request_source_id"} in ids
    serialized = json.dumps(titles["Datos y referencias de la solicitud"], cls=PlotlyJSONEncoder)
    assert request.provenance.source_id in serialized
    assert request.machinery_id in serialized


def test_missing_assigned_record_is_not_replaced_by_matching_project_or_name(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    request = next(item for item in hub.requests if item.machinery_id)
    expected_id = request.machinery_id
    original = next(item for item in hub.equipment if item.id == expected_id)
    original.id = "test:equipment:different-id"
    original.project_id = request.project_id
    operation = request_operation(hub, request)
    assert operation.equipment is None
    assert operation.transfers == ()
    assert "Registro de la unidad asignada" in operation.missing
    detail = json.dumps(
        render_page(f"/solicitudes/{request.id}", hub, QueryContext()),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert expected_id in detail
    assert "Registro de maquinaria fuera de la consulta" in detail


def test_transfer_needs_exact_request_and_completion_never_creates_receipt(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    request = next(item for item in hub.requests if item.machinery_id)
    equipment = next(item for item in hub.equipment if item.id == request.machinery_id)
    provenance = equipment.provenance.model_copy(
        update={"source": "startrack", "evidence_kind": "test_case", "source_id": "test-task"}
    )
    task = TransferRecord(
        id="test:task:completed",
        code="Tarea de prueba",
        status="COMPLETADA",
        request_id=request.id,
        destination_project_id=request.project_id,
        destination_project_name=request.project_name,
        provenance=provenance,
    )
    equipment.transfers = [
        task,
        task.model_copy(update={"id": "test:task:unrelated", "request_id": "test:other-request"}),
    ]
    equipment.relation_status = "confirmed"
    operation = request_operation(hub, request)
    assert [item.id for item in operation.transfers] == [task.id]
    assert "Evidencia de llegada" in operation.missing
    assert "Recepción física" in operation.missing
    detail = json.dumps(
        render_page(f"/solicitudes/{request.id}", hub, QueryContext()),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "COMPLETADA" in detail
    assert "Sin constancia de recepción" in detail
    assert "Sin evidencia de llegada vinculada" in detail
    equipment.transfers[0].destination_project_id = "test:project:different-destination"
    assert "Conciliación del destino del traslado" in request_operation(hub, request).missing
