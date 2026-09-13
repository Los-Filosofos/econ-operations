"""Supplied sandbox examples, kept separate from current provider observations."""

import json
from datetime import date, datetime
from pathlib import Path

from app.integrations.nexus import NexusEquipment, NexusRequest, to_records
from app.models.hub import EquipmentRecord, Provenance, RequestRecord

SAMPLE_PATH = Path(__file__).with_name("data") / "sandbox_samples.json"
FIXTURE_AS_OF: datetime | None = None
FIXTURE_OBSERVED_ON = date(2026, 9, 12)
FIXTURE_EQUIPMENT_TOTAL = 15
FIXTURE_REQUESTS_TOTAL = 2


def fixture_records() -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    """Read fresh models without inventing missing source times or relationships."""
    supplied = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

    def provenance(collection: str, index: int, source_id: str) -> Provenance:
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=None,
            observed_on=FIXTURE_OBSERVED_ON,
            is_synthetic=True,
            evidence_kind="provided_sample",
            source_reference=(
                f"{supplied['source_document']}{supplied[collection]['source_reference']}"
                f"/items/{index}"
            ),
        )

    return to_records(
        [NexusEquipment.model_validate(item) for item in supplied["equipment"]["items"]],
        [NexusRequest.model_validate(item) for item in supplied["requests"]["items"]],
        provenance,
        "Muestra del OpenAPI entregado. Las solicitudes se relacionan por maquinaria_id exacto. "
        "No hay traslado de Startrack ni recepción documentados para esta unidad.",
    )
