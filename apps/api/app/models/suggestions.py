"""Read-only suggestion contract: ECON lists candidate units; Prisma records the assignment.

Nothing here ranks by score, distance or ETA, and nothing here uses GPS presence: the
tracked device may belong to the carrier, and entering a geofence proves neither location
nor availability. Every candidate carries its reasons, its review points, its exclusions
and what the bounded read could not verify.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.hub import DataMode, HubScope, OperationEvidenceStatus, Provenance

Eligibility = Literal["eligible", "review_required", "excluded"]

AUTHORITY_NOTE = (
    "Recomendar no es asignar: la asignación se registra en Prisma "
    "(PATCH /api/maquinaria/requests/{id}/approve). ECON no asigna, no consulta proveedores "
    "para esta sugerencia y no estima distancias, tiempos de ruta ni ETA."
)


class SuggestionEvidence(BaseModel):
    """A dated source fact quoted for a candidate; administrative, never an observed location."""

    fact: str
    source: Literal["nexus", "startrack", "econ"]
    field: str = Field(description="Campo(s) de origen exacto(s) que sostienen el hecho.")
    nature: Literal["administrative"] = Field(
        default="administrative",
        description=(
            "Solo hechos administrativos registrados en la fuente. La presencia GPS o una "
            "visita a geocerca no se ofrece como evidencia de ubicación de la unidad."
        ),
    )
    event_time: datetime | None = None
    observed_at: datetime | None = None
    observed_on: date | None = None
    reference: str | None = Field(
        default=None, description="Referencia local (movimiento, evento o marca de origen)."
    )


class CandidateUnit(BaseModel):
    equipment_id: str
    equipment_source_id: str | None
    label: str
    requested_class: str | None = Field(
        description="request.machinery_type tal como se comparó (sin normalizar)."
    )
    equipment_class: str | None = Field(
        description="equipment.equipment_class tal como se comparó (sin normalizar)."
    )
    class_match: bool = Field(description="True solo con igualdad exacta tras strip.")
    machinery_status: str
    project_id: str | None
    project_name: str | None = None
    assignment_starts_on: str | None
    assignment_ends_on: str | None
    maintenance_failure_id: str | None
    maintenance_status: str | None
    maintenance_is_stopped: bool | None
    eligibility: Eligibility
    reasons: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    exclusion_reasons: list[str] = Field(default_factory=list)
    missing: list[str] = Field(
        default_factory=list,
        description="Hechos que la lectura acotada no cubre; cada uno queda «no verificable».",
    )
    overlapping_requests: list[str] = Field(default_factory=list)
    overlapping_movements: list[str] = Field(default_factory=list)
    same_project_evidence: SuggestionEvidence | None = Field(
        default=None,
        description=(
            "Asignación administrativa vigente en Prisma al mismo project_id que termina antes "
            "del período solicitado. Es continuidad administrativa, no ubicación observada."
        ),
    )
    operators_known: bool = Field(
        default=False,
        description="False significa lectura acotada sin operadores, no «sin operadores».",
    )
    provenance: Provenance


class AssignmentSuggestion(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime
    data_as_of: datetime | None = None
    request_id: str
    request_source_id: str | None
    request_status: str
    project_id: str | None
    project_label: str
    requested_class: str | None
    requested_starts_on: str | None
    requested_ends_on: str | None
    applicable: bool
    message: str
    rules: list[str]
    scope: HubScope
    registry: OperationEvidenceStatus
    candidates: list[CandidateUnit]
    similar_classes: list[str] = Field(
        default_factory=list,
        description=(
            "Clases de la lectura con grafía cercana a la solicitada (mayúsculas o plural). "
            "Informativo: no une registros ni cambia el nivel de ninguna candidata."
        ),
    )
    authority_note: str = AUTHORITY_NOTE
    remote_writes: Literal[False] = False
