"""Guarantees that only PostgreSQL accredits; SQLite runs cannot stand in for them."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.operations import Movement


def _movement(reference: str, **values):
    now = datetime.now(UTC)
    base = {
        "id": f"mv-{reference}",
        "mode": "live",
        "environment": "sandbox",
        "movement_reference": reference,
        "request_source_id": "req-1",
        "machinery_source_id": "eq-1",
        "project_source_id": "proj-1",
        "mapping": {},
        "source_request": {"id": "req-1"},
        "source_request_hash": "h1",
        "identity_hash": "i1",
        "preparation": {},
        "state": "draft",
        "created_at": now,
        "updated_at": now,
        "next_review_at": now,
    }
    base.update(values)
    return Movement(**base)


def test_movement_identity_is_unique_per_mode_and_environment(postgres_engine):
    with Session(postgres_engine) as session:
        session.add(_movement("traslado-1"))
        session.commit()
    with Session(postgres_engine) as session:
        session.add(_movement("traslado-1", id="mv-other"))
        with pytest.raises(IntegrityError):
            session.commit()
    with Session(postgres_engine) as session:
        session.add(_movement("traslado-1", id="mv-fixture", mode="fixture"))
        session.commit()
