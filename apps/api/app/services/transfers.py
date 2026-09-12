"""Prepare an explicit Prisma-to-Startrack mapping for review without writing remotely."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.integrations.startrack import Identifier, StartrackTaskDraft
from app.models.hub import EquipmentRecord, Provenance, RequestRecord


class TransferMapping(BaseModel):
    """A mapping supplied by the operator, never inferred from display names."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_source_id: Identifier
    machinery_source_id: Identifier
    project_source_id: Identifier
    poi_id: Identifier
    assigned_user_ids: tuple[Identifier, ...] = Field(min_length=1)
    movement_reference: Identifier
    scheduled_date: date
    scheduled_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
    job_type_id: Identifier | None = None

    @field_validator("scheduled_date", mode="before")
    @classmethod
    def explicit_date_only(cls, value: object) -> object:
        # Apply the draft boundary before Pydantic can coerce an epoch or timestamp.
        return StartrackTaskDraft.explicit_date_only(value)

    @field_validator("assigned_user_ids")
    @classmethod
    def unique_assignments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return StartrackTaskDraft.unique_assignments(value)


class TransferPreparation(BaseModel):
    request_id: str
    machinery_id: str | None
    project_id: str | None
    request_provenance: Provenance
    equipment_provenance: Provenance | None
    status: Literal["missing_information", "review_required", "draft_prepared"]
    missing_fields: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    draft: StartrackTaskDraft | None = None
    remote_writes: Literal[False] = False


def prepare_transfer(
    request: RequestRecord,
    equipment: EquipmentRecord | None,
    mapping: TransferMapping | None = None,
) -> TransferPreparation:
    """Build a reviewable draft only after checking identity and required facts.

    Even draft_prepared does not certify current availability, remote acceptance,
    a valid Startrack mapping, idempotency, arrival, or receipt. Supplied samples
    can be used to review a draft but cannot authorize a remote business write.
    """
    missing: list[str] = []
    blockers: list[str] = []
    notes = [
        "Preparación local: no se ha creado una tarea ni modificado Prisma.",
        "Verificar los IDs de Startrack y tareas previas antes de enviar; "
        "remote_id no garantiza unicidad.",
        "La fecha de uso no se convierte automáticamente en programación de entrega.",
        "El estado administrativo no acredita disponibilidad física para el traslado.",
        f"Estado de la solicitud: {request.status}.",
    ]
    if request.provenance.evidence_kind != "live_read":
        notes.append(
            "La solicitud procede de una muestra; comprobar su estado actual en el sandbox."
        )
    if request.status.upper() not in {"APROBADA", "APPROVED"}:
        blockers.append("La solicitud no acredita aprobación con un estado reconocido.")
    if request.provenance.source != "nexus":
        blockers.append("La solicitud no procede de Prisma.")
    if not request.provenance.source_id:
        missing.append("ID original de la solicitud")
    if not request.project_id:
        missing.append("ID original del proyecto")
    if not request.machinery_id:
        missing.append("Unidad asignada a la solicitud")
    if equipment is None:
        missing.append("Registro de la unidad asignada")
    elif equipment.id != request.machinery_id:
        blockers.append("La unidad consultada no coincide con maquinaria_id de la solicitud.")
    else:
        if not equipment.provenance.source_id:
            missing.append("ID original de maquinaria")
        if (
            request.provenance.source != equipment.provenance.source
            or request.provenance.environment != equipment.provenance.environment
            or request.provenance.evidence_kind != equipment.provenance.evidence_kind
            or request.provenance.is_synthetic != equipment.provenance.is_synthetic
        ):
            blockers.append(
                "Solicitud y unidad pertenecen a fuentes o clases de evidencia distintas."
            )
        if equipment.provenance.source != "nexus":
            blockers.append("La unidad no procede de Prisma.")
        if equipment.project_id and equipment.project_id != request.project_id:
            blockers.append(
                "El proyecto de la unidad difiere del proyecto solicitado; revisar vigencia."
            )
        if equipment.maintenance_is_stopped is True:
            blockers.append(
                "La unidad tiene paro explícito; revisar con Mantenimiento y Logística."
            )
        elif equipment.maintenance_is_stopped is None:
            notes.append("Se desconoce si la unidad tiene paro de mantenimiento; comprobarlo.")
        if equipment.maintenance_failure_id:
            notes.append(
                f"Falla registrada: {equipment.maintenance_failure_id}; "
                f"estado: {equipment.maintenance_status or 'sin dato'}; revisar su vigencia."
            )
        notes.append(f"Estado administrativo de la unidad: {equipment.machinery_status}.")

    if mapping is None:
        missing.extend(
            [
                "Correspondencia de proyecto con poi_id de destino",
                "Usuarios asignables de Startrack confirmados",
                "Referencia única del movimiento en la integración",
                "Fecha programada de traslado",
            ]
        )
    else:
        if mapping.request_source_id != request.provenance.source_id:
            blockers.append("El mapeo referencia otra solicitud de origen.")
        if mapping.project_source_id != request.project_id:
            blockers.append("El mapeo referencia otro proyecto de origen.")
        if equipment is not None and mapping.machinery_source_id != equipment.provenance.source_id:
            blockers.append("El mapeo referencia otra maquinaria de origen.")

    draft = None
    if not blockers and not missing and equipment is not None and mapping is not None:
        equipment_label = equipment.code or equipment.asset_number or equipment.name
        project_label = request.project_name or request.project_id
        draft = StartrackTaskDraft(
            objective=f"Traslado de {equipment_label} a {project_label}"[:255],
            description=(
                f"Solicitud Prisma: {mapping.request_source_id}; "
                f"maquinaria: {mapping.machinery_source_id}; "
                f"proyecto: {mapping.project_source_id}; "
                f"movimiento: {mapping.movement_reference}."
            ),
            start_date=mapping.scheduled_date,
            start_time=mapping.scheduled_time,
            remote_id=mapping.movement_reference,
            poi_id=mapping.poi_id,
            assigned_user_ids=mapping.assigned_user_ids,
            job_type_id=mapping.job_type_id,
        )

    return TransferPreparation(
        request_id=request.id,
        machinery_id=request.machinery_id,
        project_id=request.project_id,
        request_provenance=request.provenance.model_copy(deep=True),
        equipment_provenance=(
            equipment.provenance.model_copy(deep=True) if equipment is not None else None
        ),
        status="review_required"
        if blockers
        else "missing_information"
        if missing
        else "draft_prepared",
        missing_fields=missing,
        blocking_reasons=blockers,
        notes=notes,
        draft=draft,
    )
