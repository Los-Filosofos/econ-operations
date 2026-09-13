"""Indicator sheets and per-row results computed only from documented source instants.

Every indicator publishes a sheet (`IndicatorSheet`) with the points that
docs/contexto-vigente.md («Límites de los datos») requires before a measurement is
published: question and decision, grain, population, numerator and denominator,
exclusions and unknowns, the exact date fields involved, unit, owner and the rule that
decides evaluable / partial / not evaluable. Results are rows (`IndicatorRow`), never
means, percentiles or percentages: a missing date makes the row not evaluable with the
missing field named, and an empty population is «sin casos evaluables», never zero.
"""

from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.hub import DataMode, HubScope, OperationEvidenceStatus
from app.models.workflow import OperationsCoverage

IndicatorId = Literal[
    "approval_time",
    "open_request_age",
    "approved_with_unit_without_sent_task",
    "occupied_without_project",
    "assignment_ended",
    "completed_task_without_receipt",
    "active_failure_registered",
    "evidence_age",
]
IndicatorGrain = Literal["request", "equipment", "movement"]
IndicatorStatus = Literal["evaluable", "partial", "not_evaluable"]
# bool is listed explicitly so flags stay booleans instead of collapsing into int.
IndicatorValue = str | bool | int | float | None
NOT_EVALUABLE_LABEL = "no verificable"


class IndicatorSheet(BaseModel):
    """Definition of one indicator; the same sheet is documented in
    docs/indicadores-calculables.md and published with every result."""

    id: IndicatorId
    name: str = Field(description="Nombre del indicador en español.")
    question: str = Field(description="Pregunta que responde cada fila.")
    decision: str = Field(description="Decisión que habilita y quién la toma.")
    owner: str = Field(description="Área responsable de actuar sobre el resultado.")
    grain: IndicatorGrain = Field(description="Grano de la fila: solicitud, unidad o movimiento.")
    population: str = Field(description="Registros de la lectura acotada que forman la población.")
    numerator: str = Field(description="Fórmula por fila con los campos exactos de origen.")
    denominator: str = Field(
        description="Denominador; «no aplica» cuando el indicador se publica por fila."
    )
    exclusions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(
        default_factory=list, description="Lo que la lectura no permite saber."
    )
    dates: list[str] = Field(
        default_factory=list, description="Nombres exactos de los campos de fecha usados."
    )
    unit: str
    status_rule: str = Field(description="Cuándo la fila y el indicador son evaluables o no.")
    measurable_in: list[DataMode] = Field(
        default_factory=list, description="Modos en los que hoy existe alguna fila evaluable."
    )


class IndicatorRow(BaseModel):
    """One request, unit or movement with the values computed from its own dates."""

    subject_id: str = Field(description="ID del hub: nexus:request:…, nexus:equipment:…, …")
    source_id: str | None = Field(default=None, description="ID de origen sin prefijo.")
    label: str | None = Field(default=None, description="Etiqueta legible (activo, código).")
    values: dict[str, IndicatorValue] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list, description="Hechos de origen citados.")
    status: IndicatorStatus
    reason: str | None = Field(
        default=None, description="Por qué la fila no es evaluable o es parcial."
    )


class IndicatorResult(BaseModel):
    sheet: IndicatorSheet
    status: IndicatorStatus
    reason: str | None = Field(
        default=None, description="Motivo cuando el indicador completo no es evaluable."
    )
    rows: list[IndicatorRow] = Field(default_factory=list)
    evaluable_count: int = 0
    partial_count: int = 0
    not_evaluable_count: int = 0
    coverage_note: str = Field(description="Población, alcance de la lectura y límites.")

    @model_validator(mode="after")
    def _counts_match_rows(self) -> "IndicatorResult":
        counts = Counter(row.status for row in self.rows)
        expected = (counts["evaluable"], counts["partial"], counts["not_evaluable"])
        if (self.evaluable_count, self.partial_count, self.not_evaluable_count) != expected:
            raise ValueError("Los conteos del indicador deben coincidir con sus filas.")
        return self


class IndicatorsReport(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime = Field(
        description="Instante de la lectura del hub; solo evidence_age lo usa como «ahora»."
    )
    data_as_of: datetime | None = Field(
        default=None, description="Corte de la lectura de Prisma; null en fixture."
    )
    scope: HubScope
    registry: OperationEvidenceStatus
    ledger_coverage: OperationsCoverage | None = None
    ledger_available: bool = False
    last_registry_read_at: datetime | None = Field(
        default=None,
        description="Última lectura del registro (max(recorded_at, last_confirmed_at) del corte).",
    )
    indicators: list[IndicatorResult]
    notes: list[str] = Field(default_factory=list)
    remote_writes: Literal[False] = False
