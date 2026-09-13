"""Explicit day intervals of the domain, compared inclusively and never converted.

Four facts share the shape "from one day to another" but never a meaning
(docs/solucion-integracion.md, «Tiempos del traslado: qué se sabe y qué no»;
docs/contexto-vigente.md: «Fechas de uso no son ventana de entrega»):

- ``usage_period``: when the project needs the machine (``Solicitud.fecha_inicio`` /
  ``fecha_fin``). It is not a delivery window nor a transfer schedule.
- ``assignment_window``: the unit's current administrative assignment in Prisma
  (``fecha_inicio_uso`` / ``fecha_fin_uso``). It is not physical presence.
- ``scheduled``: the transfer day decided by Logística (``TransferMapping.scheduled_date``
  → ``StartrackJob.start_date``). It is not derived from the usage period.
- ``observed``: an interval reconstructed from recorded instants (visits, receipts).
  A bounded report yields partial coverage, which is declared, not completed.

This module performs no I/O and never reads the clock: it only compares dates that a
source documented. A missing boundary, a partial coverage or an instant without a time
zone yields ``not_verifiable``; it is never reported as «sin conflicto».
"""

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.hub import EquipmentRecord, RequestRecord

# El Salvador has no daylight-saving offset. Date-only plans stay dates.
BUSINESS_TIMEZONE = timezone(timedelta(hours=-6), name="America/El_Salvador")

IntervalKind = Literal["usage_period", "assignment_window", "scheduled", "observed"]
RelationStatus = Literal["overlap", "disjoint", "not_verifiable"]

KIND_LABELS: dict[IntervalKind, str] = {
    "usage_period": "período de uso solicitado",
    "assignment_window": "asignación vigente de la unidad",
    "scheduled": "programación del traslado",
    "observed": "intervalo observado",
}


def parse_day(value: str | None) -> date | None:
    """A documented day stays a day; a zoned instant is read in El Salvador; unzoned is unknown."""
    try:
        if value and len(value) == 10:
            return date.fromisoformat(value)
        instant = datetime.fromisoformat(value) if value else None
    except ValueError:
        return None
    return instant.astimezone(BUSINESS_TIMEZONE).date() if instant and instant.tzinfo else None


class DayInterval(BaseModel):
    """Closed interval of calendar days; ``None`` boundaries are unknown, not open-ended."""

    model_config = ConfigDict(frozen=True)

    kind: IntervalKind
    start: date | None
    end: date | None
    source: str = Field(description="Campo de origen exacto del que proceden las fechas.")
    partial: bool = Field(
        default=False,
        description=(
            "True cuando el intervalo procede de una lectura acotada que puede no cubrir "
            "todo el rango (p. ej. un informe de visitas limitado a días o filas)."
        ),
    )

    @property
    def label(self) -> str:
        return KIND_LABELS[self.kind]

    def missing(self) -> list[str]:
        """Qualified names of what prevents a verifiable comparison, in a stable order."""
        absent = [f"{self.kind}.{name}" for name in ("start", "end") if getattr(self, name) is None]
        if self.partial:
            absent.append(f"{self.kind}.coverage")
        if self.start is not None and self.end is not None and self.start > self.end:
            absent.append(f"{self.kind}.order")
        return absent

    def span(self) -> str:
        """Human-readable boundaries; an unknown boundary stays visible as «ausente»."""
        return f"{self.start.isoformat() if self.start else 'ausente'} → " + (
            self.end.isoformat() if self.end else "ausente"
        )


class IntervalRelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: RelationStatus
    reason: str
    missing: list[str] = Field(default_factory=list)


def usage_period_of(request: RequestRecord) -> DayInterval:
    return DayInterval(
        kind="usage_period",
        start=parse_day(request.starts_on),
        end=parse_day(request.ends_on),
        source=f"Solicitud {request.provenance.source_id or request.id}: fecha_inicio/fecha_fin",
    )


def assignment_window_of(equipment: EquipmentRecord) -> DayInterval:
    return DayInterval(
        kind="assignment_window",
        start=parse_day(equipment.assignment_starts_on),
        end=parse_day(equipment.assignment_ends_on),
        source=(
            f"Maquinaria {equipment.provenance.source_id or equipment.id}: "
            "fecha_inicio_uso/fecha_fin_uso"
        ),
    )


def scheduled_day(day: date | None, source: str = "TransferMapping.scheduled_date") -> DayInterval:
    """A transfer schedule is a single day; it is never widened to the usage period."""
    return DayInterval(kind="scheduled", start=day, end=day, source=source)


def compare(a: DayInterval, b: DayInterval) -> IntervalRelation:
    """Inclusive comparison by days: sharing one day is an overlap; adjacency is disjoint."""
    missing = a.missing() + b.missing()
    if missing:
        return IntervalRelation(
            status="not_verifiable",
            reason=(
                f"No se puede comparar {a.label} ({a.span()}) con {b.label} ({b.span()}): "
                f"falta {', '.join(missing)}."
            ),
            missing=missing,
        )
    if a.start <= b.end and b.start <= a.end:
        first, last = max(a.start, b.start), min(a.end, b.end)
        return IntervalRelation(
            status="overlap",
            reason=(
                f"{a.label.capitalize()} ({a.span()}) y {b.label} ({b.span()}) se cruzan "
                f"del {first.isoformat()} al {last.isoformat()}."
            ),
        )
    return IntervalRelation(
        status="disjoint",
        reason=f"{a.label.capitalize()} ({a.span()}) y {b.label} ({b.span()}) no se cruzan.",
    )


def covers(interval: DayInterval, day: date | None, what: str = "el día") -> IntervalRelation:
    """Whether a documented day falls inside the interval, inclusive of both boundaries."""
    missing = interval.missing()
    if day is None:
        missing = [*missing, "day"]
    if missing:
        return IntervalRelation(
            status="not_verifiable",
            reason=(
                f"No se puede situar {what} en {interval.label} ({interval.span()}): "
                f"falta {', '.join(missing)}."
            ),
            missing=missing,
        )
    if interval.start <= day <= interval.end:
        return IntervalRelation(
            status="overlap",
            reason=(
                f"{what.capitalize()} {day.isoformat()} cae en {interval.label} "
                f"({interval.span()})."
            ),
        )
    return IntervalRelation(
        status="disjoint",
        reason=(
            f"{what.capitalize()} {day.isoformat()} queda fuera de {interval.label} "
            f"({interval.span()})."
        ),
    )
