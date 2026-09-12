"""Invented local scenarios. They are not exports or current sandbox observations."""

from datetime import UTC, datetime, timedelta

from app.models.hub import (
    EquipmentRecord,
    LocationObservation,
    Provenance,
    RequestRecord,
    TransferRecord,
)

FIXTURE_AS_OF = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)


def provenance(source: str, source_id: str) -> Provenance:
    return Provenance(
        source=source,
        source_id=source_id,
        environment="local",
        observed_at=FIXTURE_AS_OF,
        is_synthetic=True,
    )


def fixture_records() -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    """Return fresh models per request, keeping deterministic event timestamps."""
    equipment = [
        EquipmentRecord(
            id="fixture:eq-re03",
            code="RE-03",
            name="Retroexcavadora 03",
            company="Los Filósofos · ejemplo",
            machinery_status="DISPONIBLE",
            relation_status="unlinked",
            relation_note=(
                "Ejemplo local de vínculo pendiente. No hay una solicitud y un traslado "
                "confirmados; la asignación del kit no acredita una operación actual."
            ),
            provenance=provenance("nexus", "fixture:eq-re03"),
        ),
        EquipmentRecord(
            id="fixture:eq-cf03",
            code="CF-03",
            name="Cargador frontal 03",
            company="ECON · ejemplo",
            project_id="fixture:project-norte",
            project_name="Proyecto Norte · ejemplo",
            driver="Motorista de ejemplo A",
            machinery_status="OCUPADA",
            request_ids=["fixture:request-01"],
            transfers=[
                TransferRecord(
                    id="fixture:transfer-01",
                    code="TR-EJ-001",
                    status="COMPLETADA",
                    request_id="fixture:request-01",
                    destination_project_id="fixture:project-norte",
                    destination_project_name="Proyecto Norte · ejemplo",
                    driver="Motorista de ejemplo A",
                    provenance=provenance("startrack", "fixture:transfer-01"),
                )
            ],
            location=LocationObservation(
                label="Acceso del Proyecto Norte · ubicación simulada",
                observed_at=FIXTURE_AS_OF - timedelta(minutes=18),
                provenance=provenance("startrack", "fixture:location-01"),
            ),
            relation_status="confirmed",
            relation_note=(
                "Relación definida solo para este ejemplo local. OCUPADA describe la "
                "asignación del equipo; COMPLETADA describe la tarea. Pueden coexistir "
                "y no demuestran por sí solas recepción física."
            ),
            provenance=provenance("nexus", "fixture:eq-cf03"),
        ),
        EquipmentRecord(
            id="fixture:eq-ex02",
            code="EX-02",
            name="Excavadora 02",
            company="ECON · ejemplo",
            project_id="fixture:project-sur",
            project_name="Proyecto Sur · ejemplo",
            driver="Motorista de ejemplo B",
            machinery_status="MANTENIMIENTO",
            maintenance_failure_id="fixture:failure-01",
            maintenance_status="ABIERTA",
            maintenance_is_stopped=True,
            request_ids=["fixture:request-02"],
            transfers=[
                TransferRecord(
                    id="fixture:transfer-02",
                    code="TR-EJ-002",
                    status="PENDIENTE",
                    request_id="fixture:request-02",
                    destination_project_id="fixture:project-sur",
                    destination_project_name="Proyecto Sur · ejemplo",
                    driver="Motorista de ejemplo B",
                    provenance=provenance("startrack", "fixture:transfer-02"),
                )
            ],
            relation_status="confirmed",
            relation_note=(
                "Relación definida solo para este ejemplo local. Una falla con paro "
                "registrado y una tarea pendiente requieren revisión de mantenimiento y logística."
            ),
            provenance=provenance("nexus", "fixture:eq-ex02"),
        ),
    ]
    requests = [
        RequestRecord(
            id="fixture:request-01",
            project_id="fixture:project-norte",
            project_name="Proyecto Norte · ejemplo",
            machinery_id="fixture:eq-cf03",
            status="APROBADA",
            starts_on="2026-09-10",
            provenance=provenance("nexus", "fixture:request-01"),
        ),
        RequestRecord(
            id="fixture:request-02",
            project_id="fixture:project-sur",
            project_name="Proyecto Sur · ejemplo",
            machinery_id="fixture:eq-ex02",
            status="PENDIENTE",
            starts_on="2026-09-11",
            provenance=provenance("nexus", "fixture:request-02"),
        ),
        RequestRecord(
            id="fixture:request-03",
            project_id="fixture:project-este",
            project_name="Proyecto Este · ejemplo",
            machinery_id=None,
            status="APROBADA",
            starts_on="2026-09-13",
            provenance=provenance("nexus", "fixture:request-03"),
        ),
    ]
    return equipment, requests
