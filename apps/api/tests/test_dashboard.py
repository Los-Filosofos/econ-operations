"""Exercise real Dash HTTP callbacks, not just the component factory."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder

from app.core.config import Settings
from app.dashboard.analytics import request_operation
from app.dashboard.application import STATUS_POLL_SECONDS, app_shell
from app.dashboard.context import QueryContext, parse_context
from app.dashboard.views import (
    PAGES,
    REQUEST_FILTERS,
    filter_tabs,
    navigation,
    origin_line,
    render_page,
    scope,
    searchable,
)
from app.main import create_app
from app.models import metadata
from app.models.hub import HubResponse, TransferRecord
from app.models.workflow import WorkflowOverview
from app.services.hub import read_hub


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'dash.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        # Dash registers assets and finalizes callbacks when serving its layout.
        assert client.get("/_dash-layout").status_code == 200
        yield client


def snapshot(
    client,
    search="?mode=fixture",
    *,
    previous=None,
    changed="url.search",
    path="/",
    action=None,
    registry=None,
):
    return client.post(
        "/_dash-update-component",
        json={
            "output": "snapshot.data",
            "outputs": {"id": "snapshot", "property": "data"},
            "inputs": [
                {"id": "url", "property": "search", "value": search},
                {"id": "registry", "property": "data", "value": registry},
                {"id": "url", "property": "pathname", "value": path},
                {"id": "workflow-action-result", "property": "data", "value": action},
            ],
            "state": [{"id": "snapshot", "property": "data", "value": previous}],
            "changedPropIds": [changed],
        },
    )


def workflow_snapshot(client, search="?mode=fixture", *, registry=None, changed="url.search"):
    return client.post(
        "/_dash-update-component",
        json={
            "output": "workflow-snapshot.data",
            "outputs": {"id": "workflow-snapshot", "property": "data"},
            "inputs": [
                {"id": "url", "property": "search", "value": search},
                {"id": "registry", "property": "data", "value": registry},
                {"id": "workflow-action-result", "property": "data", "value": None},
            ],
            "state": [],
            "changedPropIds": [changed],
        },
    )


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["response"]["snapshot"]["data"]


def unchanged(response) -> bool:
    """A callback that returned no_update answers 204 or an empty multi-output response."""
    assert response.status_code in {200, 204}, response.text
    return response.status_code == 204 or not response.json().get("response")


def version(client, mode="fixture") -> str:
    return client.get(f"/api/v1/status?mode={mode}").json()["registry_version"]


def test_cold_start_includes_styles_before_any_layout_request(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'cold.db'}", _env_file=None)
    with TestClient(create_app(settings)) as cold:
        response = cold.get("/solicitudes?mode=fixture")
        assert response.status_code == 200
        assert 'rel="stylesheet" href="/assets/style.css' in response.text
        stylesheet = cold.get("/assets/style.css")
        assert stylesheet.headers["content-type"].startswith("text/css")
        assert "--econ-brand: #144f81" in stylesheet.text


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


def test_reread_failure_discards_old_data_and_hides_internal_details(client):
    previous = data(snapshot(client))
    changed = {"mode": "fixture", "version": "another-version", "at": 1}
    with patch("app.dashboard.application.read_hub", side_effect=RuntimeError("private-password")):
        result = data(
            snapshot(client, previous=previous, changed="registry.data", registry=changed)
        )
    assert result["hub"] is None
    assert result["error"]
    assert "private-password" not in json.dumps(result)


def test_header_polls_the_registry_instead_of_a_refresh_button():
    shell = list(components(app_shell(False)))
    kinds = {component.to_plotly_json()["type"] for component in shell}
    buttons = [
        component
        for component in shell
        if component.to_plotly_json()["type"] == "Button"
        and "Actualizar" in json.dumps(component.children, cls=PlotlyJSONEncoder)
    ]
    assert not buttons, "the manual refresh button is gone"
    poll = next(component for component in shell if getattr(component, "id", None) == "status-poll")
    assert poll.to_plotly_json()["type"] == "Interval"
    assert poll.interval == STATUS_POLL_SECONDS * 1000 == 15000
    stores = {component.id for component in shell if component.to_plotly_json()["type"] == "Store"}
    assert {"status", "registry", "snapshot", "workflow-snapshot"} <= stores
    fallback = next(component for component in shell if getattr(component, "id", None) == "refresh")
    assert fallback.to_plotly_json()["type"] == "MenuItem"
    assert fallback.children == "Volver a leer ahora"
    assert "Menu" in kinds
    indicator = next(
        component for component in shell if getattr(component, "id", None) == "refresh-indicator"
    )
    assert indicator.to_plotly_json()["props"]["aria-live"] == "polite"
    status_text = next(
        component for component in shell if getattr(component, "id", None) == "read-status-text"
    )
    assert status_text.children == "Leyendo el origen…"


def test_load_callbacks_show_a_polite_indicator_while_they_run(client):
    dependencies = client.get("/_dash-dependencies").json()
    loads = {
        dependency["output"]: dependency
        for dependency in dependencies
        if dependency["output"] in {"snapshot.data", "workflow-snapshot.data"}
    }
    assert set(loads) == {"snapshot.data", "workflow-snapshot.data"}
    for dependency in loads.values():
        assert dependency["running"]["running"] == {"refresh-indicator.children": "Actualizando…"}
        assert "refresh.n_clicks" not in [
            f"{item['id']}.{item['property']}" for item in dependency["inputs"]
        ]
        assert "registry.data" in [
            f"{item['id']}.{item['property']}" for item in dependency["inputs"]
        ]
    clientside = [
        dependency["output"] for dependency in dependencies if dependency.get("clientside_function")
    ]
    assert any("status.data" in output and "registry.data" in output for output in clientside)
    assert any(output.startswith("registry.data@") for output in clientside), "manual re-read"


def test_every_read_carries_the_registry_version_it_was_taken_at(client):
    metadata.create_all(client.app.state.engine)
    current = version(client)
    assert data(snapshot(client))["version"] == current
    workflow = workflow_snapshot(client).json()["response"]["workflow-snapshot"]["data"]
    assert workflow["version"] == current and workflow["mode"] == "fixture"


def test_an_unchanged_registry_version_never_reloads_and_a_changed_one_does(client):
    metadata.create_all(client.app.state.engine)
    previous = data(snapshot(client))
    same = {"mode": "fixture", "version": previous["version"], "at": 1}
    with patch("app.dashboard.application.read_hub") as read:
        assert unchanged(
            snapshot(client, previous=previous, changed="registry.data", registry=same)
        )
        # A poll for another mode says nothing about this page.
        other_mode = {"mode": "live", "version": "different", "at": 2}
        assert unchanged(
            snapshot(client, previous=previous, changed="registry.data", registry=other_mode)
        )
        assert unchanged(workflow_snapshot(client, registry=other_mode, changed="registry.data"))
    read.assert_not_called()
    changed = {"mode": "fixture", "version": "different", "at": 3}
    result = data(snapshot(client, previous=previous, changed="registry.data", registry=changed))
    assert result["hub"] is not None and result["version"] == previous["version"]
    reloaded = workflow_snapshot(client, registry=changed, changed="registry.data")
    assert reloaded.json()["response"]["workflow-snapshot"]["data"]["mode"] == "fixture"
    # "Volver a leer ahora" forces the read even when nothing changed.
    forced = {"mode": "fixture", "version": None, "forced": True, "at": 4}
    with patch("app.dashboard.application.read_hub", wraps=read_hub) as read:
        assert data(snapshot(client, previous=previous, changed="registry.data", registry=forced))
    read.assert_called_once()


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
    paths = [page["path"] for page in PAGES] + [
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
        render_page(
            context.request_href(hub.requests[0].id).split("?", 1)[0],
            hub,
            context,
            WorkflowOverview(available=True, complete=True, message="Registro local consultado"),
        ),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert hub.requests[0].provenance.source_id in detail
    assert "Sin constancia de recepción" in detail
    assert "Sin traslado vinculado" in detail
    assert "Muestra del contrato proporcionado" in detail
    assert "Sin lectura fechada" in detail


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
        ("/decisiones", "/decisiones"),
        ("/indicadores", "/indicadores"),
        ("/solicitudes", "/solicitudes"),
        ("/solicitudes/source-id", "/solicitudes"),
        ("/maquinaria/unit-id", "/maquinaria"),
        ("/maquinaria", "/maquinaria"),
        ("/operaciones/movement-id", "/operaciones"),
        ("/fuentes", "/fuentes"),
    ],
)
def test_sidebar_has_one_current_section_and_filters_stay_on_requests(path, expected):
    context = QueryContext(mode="live", query="Proyecto Norte & Sur")
    current = [link for link in navigation(path, context) if link.active]
    assert len(current) == 1
    assert current[0].href == context.href(expected)
    assert current[0].to_plotly_json()["props"]["aria-current"] == "page"
    tabs = filter_tabs(QueryContext(filter="unassigned"), REQUEST_FILTERS, "Filtros")
    assert tabs.value == "unassigned"
    assert "unassigned" in [tab.value for tab in tabs.children.children]
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
        assert row["receipt"] == "Operaciones por consultar"


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
    accordions = [
        component
        for component in components(content)
        if component.to_plotly_json()["type"] == "Accordion"
    ]
    assert accordions and all(getattr(accordion, "value", None) is None for accordion in accordions)
    titles = {
        component.children[0].children: component
        for component in components(content)
        if component.to_plotly_json()["type"] == "AccordionItem"
    }
    for title in [
        "Preparar traslado",
        "Referencias de integración",
        "Datos y referencias de la solicitud",
        "Estado y mantenimiento de la unidad",
    ]:
        assert title in titles
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
        render_page(
            f"/solicitudes/{request.id}",
            hub,
            QueryContext(),
            WorkflowOverview(available=True, complete=True, message="Registro local consultado"),
        ),
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
        render_page(
            f"/solicitudes/{request.id}",
            hub,
            QueryContext(),
            WorkflowOverview(available=True, complete=True, message="Registro local consultado"),
        ),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "COMPLETADA" in detail
    assert "Sin constancia de recepción" in detail
    assert "Sin evidencia de llegada vinculada" in detail
    equipment.transfers[0].destination_project_id = "test:project:different-destination"
    assert "Conciliación del destino del traslado" in request_operation(hub, request).missing


def wire(identifier):
    """Dash serializes a pattern id as sorted JSON; ALL travels as ["ALL"]."""
    return json.dumps(identifier, sort_keys=True, separators=(",", ":"))


ALL_MARK = ["ALL"]
APPLY_WIRE = wire({"field": ALL_MARK, "type": "query-apply"})
SEARCH_WIRE = wire({"field": ALL_MARK, "type": "query-search"})
MODE_WIRE = wire({"field": ALL_MARK, "type": "query-mode"})
TABS_WIRE = wire({"page": ALL_MARK, "type": "filter-tabs"})


def query_bar(client, path, search="?mode=fixture"):
    response = client.post(
        "/_dash-update-component",
        json={
            "output": "query-controls.children",
            "outputs": {"id": "query-controls", "property": "children"},
            "inputs": [{"id": "url", "property": "pathname", "value": path}],
            "state": [{"id": "url", "property": "search", "value": search}],
            "changedPropIds": ["url.pathname"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["response"]["query-controls"]["children"]


def apply_query(client, *, clicks, submits=None, tabs=None, mode="fixture", query="", search=""):
    response = client.post(
        "/_dash-update-component",
        json={
            "output": "url.search",
            "outputs": {"id": "url", "property": "search"},
            "inputs": [
                {"id": APPLY_WIRE, "property": "n_clicks", "value": clicks},
                {"id": SEARCH_WIRE, "property": "n_submit", "value": submits or []},
                {"id": TABS_WIRE, "property": "value", "value": tabs or []},
            ],
            "state": [
                {"id": MODE_WIRE, "property": "value", "value": [mode] if mode else []},
                {"id": SEARCH_WIRE, "property": "value", "value": [query] if mode else []},
                {"id": "url", "property": "search", "value": search},
            ],
            "changedPropIds": [wire({"field": "apply", "type": "query-apply"}) + ".n_clicks"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json().get("response", {}).get("url", {}).get("search")


LIST_PAGES = ["/", "/resumen", "/decisiones", "/solicitudes", "/maquinaria", "/operaciones"]
QUIET_PAGES = [
    "/solicitudes/nexus%3Arequest%3Aany",
    "/maquinaria/nexus%3Aequipment%3Aany",
    "/operaciones/movement-id",
    "/fuentes",
    "/administracion",
    "/integracion",
    "/indicadores",
]
RENDER_OUTPUTS = [
    ("content", "children"),
    ("navigation", "children"),
    ("mobile-navigation-links", "children"),
    ("scope", "children"),
]


def rendered(client, path, hub, search="?mode=fixture"):
    """The real render callback with the browser's stores, as the page receives them."""
    names = [f"{identifier}.{prop}" for identifier, prop in RENDER_OUTPUTS]
    targets = [{"id": identifier, "property": prop} for identifier, prop in RENDER_OUTPUTS]
    response = client.post(
        "/_dash-update-component",
        json={
            "output": ".." + "...".join(names) + "..",
            "outputs": targets,
            "inputs": [
                {"id": "url", "property": "pathname", "value": path},
                {"id": "url", "property": "search", "value": search},
                {
                    "id": "snapshot",
                    "property": "data",
                    "value": {"key": ["fixture", ""], "hub": hub, "error": None},
                },
                {"id": "workflow-snapshot", "property": "data", "value": None},
            ],
            "state": [],
            "changedPropIds": ["url.pathname"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["response"]


def test_decisions_and_indicators_render_through_the_dash_callback(client):
    hub = client.get("/api/v1/hub?mode=fixture").json()
    decisions = rendered(client, "/decisiones", hub)
    page = json.dumps(decisions["content"]["children"], ensure_ascii=False)
    assert "Qué requiere atención" in page and "Lo que dicen los indicadores" in page
    assert "Resolver aprobación y asignación" in page
    navigation = json.dumps(decisions["navigation"]["children"], ensure_ascii=False)
    assert "/decisiones?mode=fixture" in navigation and "/indicadores?mode=fixture" in navigation
    assert "checklist.svg" in navigation and "chart-bar.svg" in navigation
    assert decisions["scope"]["children"] is not None

    indicators = rendered(client, "/indicadores", hub)
    page = json.dumps(indicators["content"]["children"], ensure_ascii=False)
    assert "I1 · Tiempo de aprobación de la solicitud" in page
    assert "Sin corte; antigüedades no evaluables" in page
    assert "a validar con ECON" in page
    assert indicators["scope"]["children"] is not None


@pytest.mark.parametrize("path", LIST_PAGES)
def test_the_query_bar_only_mounts_where_the_search_narrows_a_list(client, path):
    bar = query_bar(client, path)
    assert bar is not None
    assert "query-search" in json.dumps(bar)
    assert "query-mode" in json.dumps(bar) and "query-apply" in json.dumps(bar)


@pytest.mark.parametrize("path", QUIET_PAGES)
def test_details_sources_administration_and_integration_have_no_search(client, path):
    assert query_bar(client, path) is None


def test_the_mounted_bar_carries_the_url_state_it_will_reapply(client):
    bar = query_bar(client, "/solicitudes", "?mode=live&q=CF-03&filter=unassigned")
    controls = {
        control["props"]["id"]["type"]: control["props"].get("value")
        for control in bar["props"]["children"]
    }
    assert controls["query-search"] == "CF-03"
    assert controls["query-mode"] == "live"
    # An unreadable address never seeds the controls with an invented value.
    fallback = query_bar(client, "/solicitudes", "?mode=production")
    values = {
        control["props"]["id"]["type"]: control["props"].get("value")
        for control in fallback["props"]["children"]
    }
    assert values == {"query-search": "", "query-mode": "fixture", "query-apply": None}


def test_applying_the_bar_keeps_the_current_filter_and_ignores_a_bare_mount(client):
    assert (
        apply_query(client, clicks=[1], mode="live", query=" CF-03 ", search="?filter=unassigned")
        == "?mode=live&q=CF-03&filter=unassigned"
    )
    assert apply_query(client, clicks=[1], mode="fixture", query="", search="?mode=live") == (
        "?mode=fixture&q="
    )
    # Wildcard callbacks re-run when the bar mounts; that is not an applied query.
    assert apply_query(client, clicks=[0], mode="live", query="CF-03", search="?mode=fixture") is (
        None
    )
    assert apply_query(client, clicks=[], submits=[], mode=None, search="?mode=fixture") is None


def test_a_page_without_the_bar_keeps_the_origin_and_a_way_to_change_it(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    context = QueryContext(mode="fixture", query="CF-03", filter="unassigned")
    detail = json.dumps(
        scope(hub, context, None, "/solicitudes/x"), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "Cambiar a sandbox actual (sintético)" in detail
    assert "mode=live" in detail and "q=CF-03" in detail and "filter=unassigned" in detail
    listing = json.dumps(
        scope(hub, context, None, "/solicitudes"), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "Cambiar a" not in listing
    line = json.dumps(
        origin_line(QueryContext(mode="live"), "/administracion"),
        cls=PlotlyJSONEncoder,
        ensure_ascii=False,
    )
    assert "Sandbox actual (sintético)" in line
    assert "Cambiar a muestras proporcionadas" in line
    assert "/administracion?mode=fixture" in line
    assert searchable("/operaciones") and not searchable("/operaciones/movement")
