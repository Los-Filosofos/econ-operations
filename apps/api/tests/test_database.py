import pytest

from app.core.database import build_engine, normalize_database_url


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_managed_postgres_urls_select_installed_driver_and_preserve_connection_parts(scheme):
    url = normalize_database_url(
        f"{scheme}://reader:p%40ss%3Aword@db.example.test:6543/econ?sslmode=require&application_name=hub"
    )
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "reader"
    assert url.password == "p@ss:word"
    assert url.host == "db.example.test"
    assert url.port == 6543
    assert url.database == "econ"
    assert dict(url.query) == {"sslmode": "require", "application_name": "hub"}
    engine = build_engine(f"{scheme}://reader:test@localhost:5432/econ")
    try:
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def test_sqlite_and_explicit_driver_urls_are_not_rewritten():
    assert normalize_database_url("sqlite:///test.db").drivername == "sqlite"
    assert (
        normalize_database_url("postgresql+asyncpg://localhost/econ").drivername
        == "postgresql+asyncpg"
    )
