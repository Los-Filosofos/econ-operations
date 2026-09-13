"""Supplied sandbox examples, kept separate from current provider observations."""

import json
from datetime import date, datetime
from pathlib import Path

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

    requests = [
        RequestRecord(
            id=f"nexus:request:{item['id']}",
            project_id=item["project_id"],
            project_name=item["project_name"],
            machinery_id=(
                f"nexus:equipment:{item['maquinaria_id']}" if item["maquinaria_id"] else None
            ),
            machinery_type=item["tipo"],
            status=item["status"],
            starts_on=item["fecha_inicio"],
            ends_on=item["fecha_fin"],
            requested_by=item["requested_by_name"],
            requested_by_id=item["requested_by_user_id"],
            comments=item["comentarios"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            approved_at=item["approved_at"],
            approved_by_user_id=item.get("approved_by_user_id"),
            provenance=provenance("requests", index, item["id"]),
        )
        for index, item in enumerate(supplied["requests"]["items"])
    ]
    equipment = [
        EquipmentRecord(
            id=f"nexus:equipment:{item['id']}",
            code=item["clave"],
            asset_number=item["no_activo"],
            name=item["nombre"],
            company=item["empresa"],
            equipment_class=item["clase_equipo"],
            project_id=item["project_id"],
            project_name=item["project_name"],
            machinery_status=item["estado"],
            maintenance_failure_id=item["active_failure_id"],
            maintenance_status=item["active_failure_status"],
            maintenance_is_stopped=item["active_failure_is_paro"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            request_ids=[
                request.id
                for request in requests
                if request.machinery_id == f"nexus:equipment:{item['id']}"
            ],
            relation_status="unlinked",
            relation_note=(
                "Muestra del OpenAPI entregado. Las solicitudes se relacionan por "
                "maquinaria_id exacto. No hay traslado de Startrack ni recepción "
                "documentados para esta unidad."
            ),
            provenance=provenance("equipment", index, item["id"]),
        )
        for index, item in enumerate(supplied["equipment"]["items"])
    ]
    return equipment, requests
