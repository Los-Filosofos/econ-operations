from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine


def normalize_database_url(database_url: str) -> URL:
    """Select the installed psycopg driver for common managed Postgres URLs."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


def build_engine(database_url: str) -> Engine:
    url = normalize_database_url(database_url)
    backend = url.get_backend_name()
    connect_args = {}
    if backend == "sqlite":
        connect_args = {"check_same_thread": False}
    elif backend == "postgresql":
        connect_args = {"connect_timeout": 5}
    pool_options = {"poolclass": StaticPool} if backend == "sqlite" and not url.database else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, **pool_options)
    if backend == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_session(request: Request) -> Generator[Session]:
    # One session per request; writes must explicitly commit their transaction.
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
