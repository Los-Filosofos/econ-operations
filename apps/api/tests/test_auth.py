"""Session login, role gates and redirects with AUTH_REQUIRED=true."""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.users import new_user
from app.core.auth import Role
from app.core.config import Settings
from app.main import create_app
from app.models import metadata
from app.models.users import User

PASSWORD = "correct-horse-battery"


def build_app(tmp_path, **overrides):
    values = {
        "database_url": f"sqlite:///{tmp_path / 'auth.db'}",
        "auth_required": True,
        "session_secret": "unit-test-secret",
        "allow_local_management": True,
        "_env_file": None,
    }
    return create_app(Settings(**(values | overrides)))


@contextmanager
def open_client(app, **kwargs):
    """Start the app (its engine lives in the lifespan) and create the schema explicitly."""
    with TestClient(app, **kwargs) as client:
        metadata.create_all(app.state.engine)
        yield client


def add_user(app, email, role, password=PASSWORD, active=True) -> User:
    with Session(app.state.engine) as db:
        user = new_user(email, email.split("@")[0], role, password)
        user.is_active = active
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_session_secret_is_mandatory_when_auth_is_required(tmp_path):
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        Settings(database_url="sqlite://", auth_required=True, _env_file=None)
    Settings(database_url="sqlite://", auth_required=False, _env_file=None)


def test_anonymous_requests_get_401_json_or_login_redirect(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        assert client.get("/health/live").status_code == 200
        hub = client.get("/api/v1/hub")
        assert hub.status_code == 401
        assert hub.json() == {"detail": "Autenticación requerida"}
        assert client.get("/api/v1/auth/me").status_code == 401
        page = client.get("/equipos?search=CF-03", follow_redirects=False)
        assert page.status_code == 302
        assert page.headers["location"] == "/login?next=%2Fequipos%3Fsearch%3DCF-03"
        assert client.get("/login").status_code == 200
        assert client.get("/_dash-layout").status_code == 200
        assert client.get("/docs", follow_redirects=False).status_code == 302


def test_login_creates_httponly_session_and_logout_ends_it(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        add_user(app, "ana@example.com", Role.lectura)
        assert login(client, "ana@example.com", "wrong-password").status_code == 401
        assert login(client, "nobody@example.com").status_code == 401
        response = login(client, "Ana@example.com")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["role"] == "lectura"
        assert body["permissions"] == ["read"]
        assert "password_hash" not in body
        cookie = response.headers["set-cookie"].lower()
        assert "econ_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
        assert client.get("/api/v1/auth/me").json()["email"] == "ana@example.com"
        assert client.get("/api/v1/hub").status_code == 200
        assert client.get("/", follow_redirects=False).status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401


def test_repeated_failures_from_one_address_are_throttled(tmp_path):
    app = build_app(tmp_path)
    with open_client(app, client=("10.0.0.9", 4000)) as client, patch("app.api.auth._failures", {}):
        for _ in range(10):
            assert login(client, "x@example.com", "wrong-password").status_code == 401
        assert login(client, "x@example.com", "wrong-password").status_code == 429


def test_read_role_cannot_write_and_logistics_can(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        add_user(app, "lectura@example.com", Role.lectura)
        add_user(app, "logistica@example.com", Role.logistica)
        add_user(app, "gerencia@example.com", Role.gerencia_proyecto)
        login(client, "lectura@example.com")
        denied = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert denied.status_code == 403
        assert client.get("/api/v1/operations").json()["management_enabled"] is False
        assert client.get("/api/v1/users").status_code == 403
        assert client.post("/api/v1/auth/logout").status_code == 204

        login(client, "gerencia@example.com")
        assert client.post("/api/v1/operations/sync", json={"mode": "fixture"}).status_code == 403
        receipt = client.post(
            "/api/v1/operations/missing/receipt",
            json={
                "mode": "fixture",
                "receiver": "Ana",
                "received_at": "2026-09-14T14:00:00-06:00",
                "reference": "acta-1",
            },
        )
        assert receipt.status_code == 409  # authorized; the movement does not exist
        client.post("/api/v1/auth/logout")

        login(client, "logistica@example.com")
        assert client.get("/api/v1/operations").json()["management_enabled"] is True
        synced = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert synced.status_code == 200, synced.text


def test_deactivated_user_loses_the_session(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        user = add_user(app, "temp@example.com", Role.mantenimiento)
        login(client, "temp@example.com")
        assert client.get("/api/v1/auth/me").status_code == 200
        with Session(app.state.engine) as db:
            row = db.get(User, user.id)
            row.is_active = False
            db.add(row)
            db.commit()
        assert client.get("/api/v1/auth/me").status_code == 401
        assert login(client, "temp@example.com").status_code == 401


def test_without_auth_required_loopback_dev_mode_still_manages(tmp_path):
    app = build_app(tmp_path, auth_required=False, session_secret=None)
    with open_client(app, base_url="http://localhost", client=("127.0.0.1", 5500)) as client:
        assert client.get("/", follow_redirects=False).status_code == 200
        assert client.get("/api/v1/operations").json()["management_enabled"] is True
    with TestClient(app, base_url="http://localhost", client=("10.1.1.1", 5500)) as client:
        assert client.get("/api/v1/operations").json()["management_enabled"] is False


def test_dash_callbacks_can_read_the_session_user(tmp_path):
    from dash import Input, Output

    from app.core.auth import session_user

    app = build_app(tmp_path)

    @app.state.dashboard.callback(Output("auth-probe-out", "children"), Input("auth-probe", "n"))
    def probe(_clicks):
        user = session_user()
        return "anónimo" if user is None else f"{user.email}:{user.role}"

    payload = {
        "output": "auth-probe-out.children",
        "outputs": {"id": "auth-probe-out", "property": "children"},
        "inputs": [{"id": "auth-probe", "property": "n", "value": 1}],
        "changedPropIds": ["auth-probe.n"],
        "state": [],
    }
    with open_client(app) as client:
        add_user(app, "ops@example.com", Role.logistica)
        anonymous = client.post("/_dash-update-component", json=payload)
        assert anonymous.status_code == 200
        assert anonymous.json()["response"]["auth-probe-out"]["children"] == "anónimo"
        login(client, "ops@example.com")
        signed = client.post("/_dash-update-component", json=payload).json()
        assert signed["response"]["auth-probe-out"]["children"] == "ops@example.com:logistica"
