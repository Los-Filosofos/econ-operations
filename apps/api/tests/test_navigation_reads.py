"""Route changes reuse the browser's read across the whole application."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.config import Settings
from app.main import create_app
from app.models import metadata


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'navigation.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        metadata.create_all(client.app.state.engine)
        assert client.get("/_dash-layout").status_code == 200
        yield client


def read_store(client, store, *, path="/", search="?mode=fixture", previous=None, registry=None):
    inputs = {
        "url.search": search,
        "registry.data": registry,
        "url.pathname": path,
        "workflow-action-result.data": None,
    }
    # Use the real dependency ordering, including the route and previous browser store.
    dependency = client.app.state.dashboard.callback_map[f"{store}.data"]
    return client.post(
        "/_dash-update-component",
        json={
            "output": f"{store}.data",
            "outputs": {"id": store, "property": "data"},
            "inputs": [
                {**spec, "value": inputs[f"{spec['id']}.{spec['property']}"]}
                for spec in dependency["inputs"]
            ],
            "state": [{"id": store, "property": "data", "value": previous}],
            "changedPropIds": ["registry.data" if registry else "url.pathname"],
        },
    )


def store_data(response, store):
    assert response.status_code == 200, response.text
    return response.json()["response"][store]["data"]


def assert_unchanged(response):
    assert response.status_code in {200, 204}, response.text
    assert response.status_code == 204 or not response.json().get("response")


def test_all_routes_reuse_reads_without_sql_or_provider_calls(client):
    stores = {
        name: store_data(read_store(client, name), name)
        for name in ("snapshot", "workflow-snapshot")
    }
    hub = stores["snapshot"]["hub"]
    paths = [
        "/",
        "/resumen",
        "/decisiones",
        "/solicitudes",
        "/maquinaria",
        "/operaciones",
        "/indicadores",
        "/integracion",
        "/fuentes",
        "/administracion",
        f"/solicitudes/{hub['requests'][0]['id']}",
        f"/maquinaria/{hub['equipment'][0]['id']}",
        "/operaciones/missing-movement",
    ]
    queries = []

    def record_query(*_args):
        queries.append(True)

    event.listen(client.app.state.engine, "before_cursor_execute", record_query)
    try:
        with (
            patch("app.dashboard.application.read_hub") as hub_read,
            patch.object(client.app.state.workflow, "read") as workflow_read,
            patch.object(client.app.state.workflow, "registry_state") as version_read,
        ):
            for path in paths:
                for store, previous in stores.items():
                    assert_unchanged(read_store(client, store, path=path, previous=previous))
            hub_read.assert_not_called()
            workflow_read.assert_not_called()
            version_read.assert_not_called()
        assert not queries
    finally:
        event.remove(client.app.state.engine, "before_cursor_execute", record_query)


def test_mode_and_search_changes_and_forced_refresh_still_read(client):
    store = "snapshot"
    first = store_data(read_store(client, store), store)
    filtered = store_data(
        read_store(
            client, store, path="/maquinaria", search="?mode=fixture&q=CF-03", previous=first
        ),
        store,
    )
    assert filtered["key"] == ["fixture", "CF-03"]
    assert len(filtered["hub"]["equipment"]) == 1
    live = store_data(read_store(client, store, search="?mode=live", previous=first), store)
    assert live["hub"]["mode"] == "live"
    assert live["hub"]["equipment"] == []  # disabled live never falls back to fixtures
    for store in ("snapshot", "workflow-snapshot"):
        previous = store_data(read_store(client, store), store)
        registry = {"mode": "fixture", "version": previous["version"]}
        assert_unchanged(read_store(client, store, previous=previous, registry=registry))
        refreshed = store_data(
            read_store(client, store, previous=previous, registry={**registry, "forced": True}),
            store,
        )
        assert refreshed["mode"] == "fixture"


def test_presentation_navigation_does_not_require_server_callbacks(client):
    dependencies = client.get("/_dash-dependencies").json()
    for output in ("mobile-navigation.opened", "burger.aria-expanded", "data-status.style"):
        dependency = next(item for item in dependencies if item["output"] == output)
        assert dependency["clientside_function"]
    asset = client.get("/assets/navigation.js")
    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]
