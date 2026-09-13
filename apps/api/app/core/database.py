from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, event, text
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


@contextmanager
def cycle_lock(engine: Engine, key: str) -> Iterator[bool]:
    """Cross-process mutual exclusion for one synchronization cycle.

    On PostgreSQL a dedicated connection takes a session-level advisory lock
    (`pg_try_advisory_lock(hashtext(key))`) without waiting: the caller receives True
    when it owns the cycle and False when another process holds it. No transaction stays
    open while the lock is held (the acquiring statement is committed at once), so the
    caller can talk to providers without an SQL transaction in flight. The lock is
    released in `finally`; if the body raises, the connection is invalidated so a pooled
    connection can never keep the lock alive.

    On SQLite (development and tests) this is a documented no-op that yields True:
    SQLite accredits no cross-process guarantee; only the PostgreSQL tests do.
    """
    if engine.dialect.name != "postgresql":
        yield True
        return
    connection = engine.connect()
    try:
        owned = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": key}
            ).scalar_one()
        )
        connection.commit()
    except BaseException:
        connection.invalidate()
        connection.close()
        raise
    if not owned:
        connection.close()
        yield False
        return
    try:
        yield True
    except BaseException:
        # The server drops session-level locks with the connection; never return a
        # connection that may still hold the lock to the pool.
        connection.invalidate()
        raise
    else:
        try:
            connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": key})
            connection.commit()
        except Exception:
            # Closing the DBAPI connection releases the lock server-side; the completed
            # cycle is not reported as failed because of the release statement.
            connection.invalidate()
    finally:
        connection.close()


def get_session(request: Request) -> Generator[Session]:
    # One session per request; writes must explicitly commit their transaction.
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
