"""Keep the documented walkthrough executable without provider access."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models import metadata


def test_swagger_describes_public_operations_and_actual_errors(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'schema.db'}", _env_file=None))
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        schema = client.get("/openapi.json").json()
        for path, methods in schema["paths"].items():
            if not path.startswith(("/api/v1/", "/health/")):
                continue
            for operation in methods.values():
                assert operation["summary"]
                assert operation["description"]
        assert "503" in schema["paths"]["/health/ready"]["get"]["responses"]
        for path, methods in schema["paths"].items():
            if not path.startswith("/api/v1/operations"):
                continue
            if "post" in methods:
                responses = methods["post"]["responses"]
                assert responses["409"]["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/ErrorResponse"
                }
                assert "422" in responses
        assert schema["components"]["schemas"]["WorkflowOverview"]["properties"]["complete"]
        assert "securitySchemes" not in schema["components"]


def test_documented_fixture_plan_and_sync_work_without_remote_calls(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'walkthrough.db'}",
            allow_local_management=True,
            allow_live_reads=False,
            allow_live_writes=False,
            _env_file=None,
        )
    )
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 5500)) as client:
        metadata.create_all(app.state.engine)
        schema = client.get("/openapi.json").json()
        example = schema["paths"]["/api/v1/operations/plans"]["post"]["requestBody"]["content"][
            "application/json"
        ]["examples"]["local_sample"]["value"]
        with (
            patch.object(app.state.nexus, "read") as read_nexus,
            patch.object(app.state.startrack, "create_job") as create_job,
        ):
            saved = client.post("/api/v1/operations/plans", json=example)
            assert saved.status_code == 201, saved.text
            record = saved.json()
            assert record["mode"] == "fixture"
            assert record["state"] == "draft"
            assert record["job_id"] is None
            assert record["receipt"] is None
            assert record["source_request"]["provenance"]["evidence_kind"] == "provided_sample"
            repeated = client.post("/api/v1/operations/plans", json=example)
            assert repeated.json()["id"] == record["id"]
            filtered = client.get(
                "/api/v1/operations",
                params={"request_source_id": example["mapping"]["request_source_id"]},
            ).json()
            assert [item["id"] for item in filtered["movements"]] == [record["id"]]
            assert filtered["complete"] is True
            synced = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
            assert synced.status_code == 200
            assert synced.json()["last_sync_at"] is not None
            assert client.post(f"/api/v1/operations/{record['id']}/queue").status_code == 409
            read_nexus.assert_not_called()
            create_job.assert_not_called()


def test_documented_disabled_live_and_invalid_mode_are_distinct(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'readonly.db'}",
            allow_live_reads=False,
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        result = client.get("/api/v1/hub?mode=live")
        assert result.status_code == 200
        body = result.json()
        assert body["equipment"] == []
        assert body["requests"] == []
        assert body["summary"]["equipment_count"] is None
        assert all(source["status"] == "disabled" for source in body["sources"])
        assert client.get("/api/v1/hub?mode=production").status_code == 422
        assert client.get("/api/v1/operations/catalogs").status_code == 409
