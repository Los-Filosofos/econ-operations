"""User administration, the CLI bootstrap and the reversible migration."""

import io

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.cli.create_user import main as create_user
from app.core.auth import Role
from app.core.database import build_engine
from tests.test_auth import PASSWORD, add_user, build_app, login, open_client


def test_admin_manages_users_and_the_last_admin_is_protected(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        admin = add_user(app, "admin@example.com", Role.admin)
        login(client, "admin@example.com")
        created = client.post(
            "/api/v1/users",
            json={
                "email": "Nuevo@example.com",
                "full_name": "Nuevo",
                "role": "logistica",
                "password": "another-long-secret",
            },
        )
        assert created.status_code == 201, created.text
        new_id = created.json()["id"]
        assert created.json()["email"] == "nuevo@example.com"
        duplicate = {
            "email": "nuevo@example.com",
            "full_name": "Dup",
            "role": "lectura",
            "password": "another-long-secret",
        }
        assert client.post("/api/v1/users", json=duplicate).status_code == 409
        weak = {"email": "s@example.com", "full_name": "S", "role": "lectura", "password": "short"}
        assert client.post("/api/v1/users", json=weak).status_code == 422
        assert [user["email"] for user in client.get("/api/v1/users").json()] == [
            "admin@example.com",
            "nuevo@example.com",
        ]

        me = client.patch(f"/api/v1/users/{admin.id}", json={"is_active": False})
        assert me.status_code == 409
        last = client.patch(f"/api/v1/users/{admin.id}", json={"role": "lectura"})
        assert last.status_code == 409
        assert client.patch("/api/v1/users/999", json={"role": "lectura"}).status_code == 404

        promoted = client.patch(f"/api/v1/users/{new_id}", json={"role": "admin"})
        assert promoted.json()["role"] == "admin"
        demoted = client.patch(f"/api/v1/users/{admin.id}", json={"role": "control_costos"})
        assert demoted.status_code == 200
        assert client.get("/api/v1/users").status_code == 403


def test_password_reset_ends_previous_sessions(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as admin, TestClient(app) as ops:
        add_user(app, "admin@example.com", Role.admin)
        target = add_user(app, "ops@example.com", Role.logistica)
        login(ops, "ops@example.com")
        assert ops.get("/api/v1/auth/me").status_code == 200
        login(admin, "admin@example.com")
        reset = admin.patch(f"/api/v1/users/{target.id}", json={"password": "brand-new-secret-1"})
        assert reset.status_code == 200
        assert ops.get("/api/v1/auth/me").status_code == 401
        assert login(ops, "ops@example.com", PASSWORD).status_code == 401
        assert login(ops, "ops@example.com", "brand-new-secret-1").status_code == 200


def test_cli_creates_the_first_admin_from_stdin(tmp_path, monkeypatch, capsys):
    app = build_app(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    args = ["--email", "root@example.com", "--role", "admin", "--name", "Root", "--password-stdin"]
    with open_client(app) as client:
        monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
        assert create_user(args) == 2
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{PASSWORD}\n"))
        assert create_user(args) == 0
        assert '"role": "admin"' in capsys.readouterr().out
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{PASSWORD}\n"))
        assert create_user(args) == 2
        assert login(client, "root@example.com").json()["full_name"] == "Root"


def test_users_migration_applies_and_reverts_on_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'migrated.db'}")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = build_engine(f"sqlite:///{tmp_path / 'migrated.db'}")
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    expected = {"id", "email", "full_name", "role", "password_hash", "is_active", "created_at"}
    assert expected <= columns
    command.downgrade(config, "0002_review_schedule")
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()
