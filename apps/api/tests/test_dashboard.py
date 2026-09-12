"""Exercise real Dash HTTP callbacks, not just the component factory."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from plotly.utils import PlotlyJSONEncoder

from app.core.config import Settings
from app.dashboard.analytics import calendar, distribution, exception_groups
from app.dashboard.context import QueryContext, parse_context
from app.dashboard.views import NAVIGATION, render_page
from app.main import create_app
from app.models.hub import HubResponse


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
        response = cold.get("/maquinaria?mode=fixture")
        assert response.status_code == 200
        assert 'rel="stylesheet" href="/assets/style.css' in response.text
        stylesheet = cold.get("/assets/style.css")
        assert stylesheet.headers["content-type"].startswith("text/css")
        assert "--blue: #144f81" in stylesheet.text


def test_one_server_serves_dash_assets_deep_links_and_existing_api(client):
    for path in ["/", "/maquinaria/fixture%3Aeq-ex02?mode=fixture", "/solicitudes"]:
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
    first = data(snapshot(client, "?mode=fixture&q=RE-03"))
    second = data(snapshot(client, "?mode=fixture&q=EX-02"))
    assert first["hub"]["equipment"][0]["code"] == "RE-03"
    assert second["hub"]["equipment"][0]["code"] == "EX-02"
    assert first["hub"]["equipment"][0]["transfers"] == []


def test_every_page_and_details_serialize_and_keep_semantic_evidence(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    paths = [path for path, _ in NAVIGATION] + [
        "/maquinaria/fixture%3Aeq-cf03",
        "/maquinaria/fixture%3Aeq-ex02",
        "/maquinaria/fixture%3Aeq-re03",
        "/maquinaria/missing",
        "/missing",
    ]
    for path in paths:
        content = render_page(path, hub, QueryContext())
        serialized = json.dumps(content, cls=PlotlyJSONEncoder, ensure_ascii=False)
        assert serialized
    detail = json.dumps(
        render_page(paths[6], hub, QueryContext()), cls=PlotlyJSONEncoder, ensure_ascii=False
    )
    assert "OCUPADA" in detail and "COMPLETADA" in detail and "recepción física" in detail


def test_analytics_preserve_counts_missing_dates_and_partial_coverage(client):
    hub = HubResponse.model_validate(client.get("/api/v1/hub").json())
    assert sum(count for _, count in distribution(hub)) == 3
    groups = exception_groups(hub)
    assert len(groups) == 2 and len(groups[0]["alerts"]) == 3
    hub.requests[0].starts_on = "2026-02-30"
    hub.requests[1].starts_on = "2026-09-12T01:00:00+00:00"
    hub.requests[2].starts_on = "2027-01-01"
    result = calendar(hub)
    assert result["undated"] == 1 and result["outside"] == 1
    assert result["days"][datetime(2026, 9, 11, tzinfo=UTC).date()] == 1
    unavailable = HubResponse.model_validate(client.get("/api/v1/hub?mode=live").json())
    assert calendar(unavailable) is None and distribution(unavailable) is None


def test_links_round_trip_search_and_quote_equipment_ids():
    context = QueryContext(mode="live", query="Proyecto Norte & Sur")
    href = context.equipment_href("nexus:equipment:a/b")
    assert "a%2Fb" in href
    parsed = parse_context("?" + href.split("?", 1)[1])
    assert parsed == context
