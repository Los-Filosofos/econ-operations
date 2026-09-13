"""Existing tests build Settings(_env_file=None) without a login; keep them in dev mode."""

import os

import pytest

os.environ.setdefault("AUTH_REQUIRED", "false")
# TestClient speaks plain http; a Secure cookie would never be sent back.
os.environ.setdefault("SESSION_HTTPS_ONLY", "false")


@pytest.fixture(autouse=True)
def local_development_mode(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("SESSION_HTTPS_ONLY", "false")


POSTGRES_URL_VARIABLE = "ECON_TEST_POSTGRES_URL"
POSTGRES_DEFAULT_URL = "postgresql+psycopg://econ@127.0.0.1:54329/econ_test"


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """Isolated PostgreSQL database for guarantees SQLite cannot accredit; skipped when absent."""
    import sqlalchemy

    url = os.environ.get(POSTGRES_URL_VARIABLE, POSTGRES_DEFAULT_URL)
    try:
        engine = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 2})
        with engine.connect():
            pass
    except Exception:  # noqa: BLE001 - any failure means the optional database is unavailable
        pytest.skip(f"PostgreSQL de pruebas no disponible ({POSTGRES_URL_VARIABLE})")
    finally:
        try:
            engine.dispose()
        except UnboundLocalError:
            pass
    return url


@pytest.fixture
def postgres_engine(postgres_url, monkeypatch):
    """Migrated schema on the isolated PostgreSQL database, emptied before each test."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from app.core.database import build_engine

    monkeypatch.setenv("DATABASE_URL", postgres_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = build_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE operation_events, operation_movements, operation_snapshots, users")
        )
    try:
        yield engine
    finally:
        engine.dispose()
