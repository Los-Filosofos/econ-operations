from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, event
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine


def build_engine(database_url: str) -> Engine:
    backend = make_url(database_url).get_backend_name()
    connect_args = {}
    if backend == "sqlite":
        connect_args = {"check_same_thread": False}
    elif backend == "postgresql":
        connect_args = {"connect_timeout": 5}
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
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
