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
# Dedicated database for upgrade/downgrade round trips: they rewrite the schema and must
# never share a database with tests that expect the migrated head.
POSTGRES_MIGRATIONS_URL_VARIABLE = "ECON_TEST_POSTGRES_MIGRATIONS_URL"
POSTGRES_MIGRATIONS_DEFAULT_URL = "postgresql+psycopg://econ@127.0.0.1:54329/econ_test_migrations"


def _reachable_postgres(variable: str, default: str) -> str:
    """Skip when the optional database is absent; fail when it was configured but is down."""
    import sqlalchemy

    explicit = os.environ.get(variable)
    url = explicit or default
    engine = None
    try:
        engine = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 2})
        with engine.connect():
            pass
    except Exception as error:  # noqa: BLE001 - any failure means the database is unavailable
        if explicit:
            pytest.fail(
                f"PostgreSQL de pruebas configurado en {variable} no responde "
                f"({type(error).__name__}); no se omite la verificación."
            )
        pytest.skip(f"PostgreSQL de pruebas no disponible ({variable})")
    finally:
        if engine is not None:
            engine.dispose()
    return url


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """Isolated PostgreSQL database for guarantees SQLite cannot accredit; skipped when absent."""
    return _reachable_postgres(POSTGRES_URL_VARIABLE, POSTGRES_DEFAULT_URL)


@pytest.fixture(scope="session")
def postgres_migrations_url() -> str:
    """Separate PostgreSQL database that upgrade/downgrade tests may leave at any revision."""
    return _reachable_postgres(POSTGRES_MIGRATIONS_URL_VARIABLE, POSTGRES_MIGRATIONS_DEFAULT_URL)


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
