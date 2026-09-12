from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app.core.config import Settings
from app.main import create_app


def test_app_starts_and_connects_to_database(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        schema = client.get("/openapi.json").json()
        assert "/health/ready" in schema["paths"]


def test_database_failure_is_503_without_exposing_details(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        with patch.object(
            Session,
            "execute",
            side_effect=OperationalError("SELECT 1", {}, Exception("private connection details")),
        ):
            response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Base de datos no disponible"}
        assert client.get("/health/live").status_code == 200
