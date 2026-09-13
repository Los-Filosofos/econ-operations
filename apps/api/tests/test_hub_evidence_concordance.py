"""Tests for HTTP/Dash concordance of arrival and receipt evidence (Issue #13).

Verifies:
1. Hub HTTP GET /api/v1/hub exposes arrival and receipt fields on equipment[].transfers[].
2. Dash detail_view renders confirmed arrival presence and declared receipt.
3. Separation of concerns: task status, GPS arrival, and receipt are never collapsed.
4. Movements without arrival/receipt correctly default to arrival_observed=False and receipt=None.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import build_engine
from app.dashboard.context import QueryContext
from app.dashboard.evidence_views import source_comparison
from app.integrations.nexus import NexusEquipment, NexusRequest, NexusSnapshot
from app.main import create_app
from app.models import metadata
from app.models.hub import Provenance
from app.services.hub import read_hub
from app.services.ledger import OperationsLedger
from app.services.transfers import TransferMapping

OBSERVED = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)
EVENT_TIME = OBSERVED - timedelta(hours=1)


def _snapshot() -> NexusSnapshot:
    return NexusSnapshot(
        equipment=[
            NexusEquipment(
                id="conc-test-unit",
                clave="conc-test-code",
                no_activo="conc-test-asset",
                nombre="Unidad Concordancia",
                estado="OCUPADA",
                active_failure_is_paro=False,
            )
        ],
        requests=[
            NexusRequest(
                id="conc-test-request",
                status="APROBADA",
                project_id="conc-test-project",
                project_name="Proyecto Concordancia",
                maquinaria_id="conc-test-unit",
                fecha_inicio="2026-09-12",
                fecha_fin="2026-09-15",
                approved_at="2026-09-11T15:00:00Z",
                approved_by_user_id="conc-test-approver",
            )
        ],
        equipment_total=1,
        requests_total=1,
        complete=True,
    )


@pytest.fixture
def env(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'concordance.db'}",
        allow_live_reads=True,
        _env_file=None,
    )
    engine = build_engine(settings.database_url)
    metadata.create_all(engine)
    connector = Mock(configured=True)
    connector.read.return_value = _snapshot()
    ledger = OperationsLedger(engine)
    yield settings, engine, connector, ledger
    engine.dispose()


def _create_sent_movement(env, reference="conc-mv-1", job_id="conc-job-1"):
    settings, _, connector, ledger = env
    hub = read_hub(settings, connector, "live")
    request, equipment = hub.requests[0], hub.equipment[0]
    movement = ledger.create(
        "live",
        request,
        equipment,
        TransferMapping(
            request_source_id=request.provenance.source_id,
            machinery_source_id=equipment.provenance.source_id,
            project_source_id=request.project_id,
            poi_id="conc-poi-destination",
            assigned_user_ids=("conc-driver",),
            movement_reference=reference,
            scheduled_date=date(2026, 9, 12),
        ),
        tracked_vehicle_id="conc-vehicle-1",
    )
    ledger.queue(movement.id)
    ledger.claim(movement.id)
    return ledger.finish_sent(movement.id, job_id, status="Pendiente", workflow_role="pending")


def test_hub_http_exposes_arrival_and_receipt_in_transfer_record(env):
    """GET /api/v1/hub serializes arrival_observed and receipt summary on transfers."""
    settings, engine, connector, ledger = env
    movement = _create_sent_movement(env)

    # 1. Record task observation: status="Completada"
    ledger.record_observation(
        movement.id,
        "live",
        kind="task_state",
        source_id=movement.job_id,
        event_time=EVENT_TIME,
        observed_at=OBSERVED,
        data={"job_id": movement.job_id, "status": "Completada", "workflow_role": "completed"},
        provenance=Provenance(
            source="startrack",
            source_id=movement.job_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    )

    # 2. Record arrival observation: poi_id="conc-poi-destination"
    ledger.record_observation(
        movement.id,
        "live",
        kind="arrival",
        source_id="conc-visit-1",
        event_time=EVENT_TIME + timedelta(minutes=30),
        observed_at=OBSERVED,
        data={
            "poi_id": "conc-poi-destination",
            "tracked_asset_id": "conc-vehicle-1",
            "latitude": 13.7,
            "longitude": -89.2,
        },
        provenance=Provenance(
            source="startrack",
            source_id="conc-visit-1",
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    )

    # 3. Record receipt declaration
    ledger.record_receipt(
        movement.id,
        "live",
        receiver="Juan Pérez",
        received_at=OBSERVED,
        reference="REC-2026-001",
        note="Recepción en buen estado",
    )

    # 4. Test HTTP API endpoint
    app = create_app(settings)
    with TestClient(app) as client:
        with (
            patch.object(type(app.state.nexus), "configured", True),
            patch.object(app.state.nexus, "read", return_value=_snapshot()),
        ):
            response = client.get("/api/v1/hub?mode=live")
            assert response.status_code == 200
            data = response.json()

    transfers = data["equipment"][0]["transfers"]
    assert len(transfers) == 1
    transfer = transfers[0]

    # Task status is preserved
    assert transfer["status"] == "Completada"
    assert transfer["workflow_role"] == "completed"

    # Arrival is exposed
    assert transfer["arrival_observed"] is True
    assert transfer["arrival_poi_id"] == "conc-poi-destination"
    assert transfer["arrival_evidence_origin"] == "visit_observation"

    # Receipt is exposed separately, not collapsed into status
    assert transfer["receipt"] is not None
    assert transfer["receipt"]["receiver"] == "Juan Pérez"
    assert transfer["receipt"]["reference"] == "REC-2026-001"
    assert transfer["receipt"]["note"] == "Recepción en buen estado"


def test_dash_detail_view_renders_arrival_and_receipt_facts(env):
    """Dash equipment detail view renders GPS arrival and receipt facts."""
    settings, engine, connector, ledger = env
    movement = _create_sent_movement(env)

    # Add task state, arrival, and receipt
    ledger.record_observation(
        movement.id,
        "live",
        kind="task_state",
        source_id=movement.job_id,
        event_time=EVENT_TIME,
        observed_at=OBSERVED,
        data={"job_id": movement.job_id, "status": "Completada"},
        provenance=Provenance(
            source="startrack",
            source_id=movement.job_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    )
    ledger.record_observation(
        movement.id,
        "live",
        kind="arrival",
        source_id="conc-visit-1",
        event_time=EVENT_TIME + timedelta(minutes=15),
        observed_at=OBSERVED,
        data={"poi_id": "conc-poi-destination", "tracked_asset_id": "conc-vehicle-1"},
        provenance=Provenance(
            source="startrack",
            source_id="conc-visit-1",
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    )
    ledger.record_receipt(
        movement.id,
        "live",
        receiver="María Gómez",
        received_at=OBSERVED,
        reference="CONSTANCIA-77",
    )

    hub = read_hub(settings, connector, "live", engine=engine)
    item = hub.equipment[0]
    movements = ledger.list("live")
    context = QueryContext(mode="live")

    # Render Dash source_comparison components
    sections = source_comparison(item, movements, None, context, hub)
    assert len(sections) == 2


def test_transfers_without_arrival_or_receipt_default_safely(env):
    """Transfers without arrival or receipt have arrival_observed=False and receipt=None."""
    settings, engine, connector, ledger = env
    movement = _create_sent_movement(env)

    ledger.record_observation(
        movement.id,
        "live",
        kind="task_state",
        source_id=movement.job_id,
        event_time=EVENT_TIME,
        observed_at=OBSERVED,
        data={"job_id": movement.job_id, "status": "En camino"},
        provenance=Provenance(
            source="startrack",
            source_id=movement.job_id,
            environment="sandbox",
            observed_at=OBSERVED,
            evidence_kind="live_read",
            is_synthetic=True,
        ),
    )

    hub = read_hub(settings, connector, "live", engine=engine)
    transfer = hub.equipment[0].transfers[0]

    assert transfer.status == "En camino"
    assert transfer.arrival_observed is False
    assert transfer.arrival_event_time is None
    assert transfer.arrival_poi_id is None
    assert transfer.receipt is None
