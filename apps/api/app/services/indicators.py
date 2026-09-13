"""Per-row indicators from documented source instants; no averages, rates or clock.

`compute_indicators` follows the `build_graph` pattern: one `HubResponse` and one
optional `WorkflowOverview` in, one `IndicatorsReport` out, with no provider, database or
clock access. Rules it enforces:

- Every value is either a fact copied from a row or a difference between two instants a
  source documented: Prisma `created_at`/`approved_at`, the hub's `data_as_of`, a task
  `event_time`, a declared `received_at`, the registry's last reading. A missing date
  makes the row `not_evaluable` with the missing field named; it never becomes zero.
- Nothing is aggregated: no means, percentiles, rates or percentages. Counts describe the
  rows of this bounded reading and the scope (5 of 15 units in fixture) travels with them.
- Fixture samples have no observation cut (`data_as_of` is None) and never send tasks:
  ages and absence-based indicators are `not_evaluable` there, never zero. Absence in
  the archive is not absence in the operation.
- The only «now» is `hub.generated_at`, used solely by `evidence_age`; source facts are
  never compared with the clock, so `datetime.now` is not called here.
- Evidence age uses the last READING of the registry (`max(recorded_at,
  last_confirmed_at)` of the latest snapshot, published as `WorkflowOverview.last_sync_at`),
  not the last change of its content.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime

from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.indicators import (
    IndicatorId,
    IndicatorResult,
    IndicatorRow,
    IndicatorSheet,
    IndicatorsReport,
    IndicatorStatus,
    IndicatorValue,
)
from app.models.operations import MovementEventRecord, MovementRecord
from app.models.workflow import WorkflowOverview
from app.services.evidence import matching_current_movements
from app.services.intervals import BUSINESS_TIMEZONE, parse_day
from app.services.ledger import effective_event_sort_key

PENDING = frozenset({"PENDIENTE", "PENDING"})
APPROVED = frozenset({"APROBADA", "APPROVED"})
REJECTED = frozenset({"RECHAZADA", "REJECTED"})
OCCUPIED = frozenset({"OCUPADA", "OCCUPIED"})
COMPLETED_ROLE = "1"
NO_CUTOFF_FIXTURE = "sin corte de observación (fixture)"
NO_CUTOFF_LIVE = "sin corte de observación: la lectura de Prisma no se completó"
FIXTURE_NO_TASKS = (
    "no evaluable en fixture: las muestras no envían tareas y la ausencia en el archivo no es cero"
)
FIXTURE_NO_READS = "no evaluable en fixture: no hay lecturas de proveedores ni corte del registro"
REGISTRY_UNAVAILABLE = "registro de movimientos no disponible o no consultado"
NOT_APPLICABLE = "No aplica: se publica por fila, sin promedio, percentil ni porcentaje."
PER_ROW_NOTE = (
    "Indicadores por fila, sin promedios ni porcentajes; la ausencia de un dato no es cero y "
    "se publica como no evaluable con el campo que falta."
)

SHEETS: dict[IndicatorId, IndicatorSheet] = {
    "approval_time": IndicatorSheet(
        id="approval_time",
        name="Tiempo de aprobación de la solicitud",
        question="¿Cuánto tardó cada solicitud en pasar de creada a aprobada?",
        decision=(
            "Proyectos y Gerencia revisan las solicitudes que esperan decisión y acuerdan un "
            "plazo de aprobación (SLA a validar con ECON)."
        ),
        owner="Proyectos",
        grain="request",
        population="Solicitudes de la lectura (Prisma GET /api/maquinaria/requests), todo estado.",
        numerator="Solicitud.approved_at − Solicitud.created_at, en segundos.",
        denominator=NOT_APPLICABLE,
        exclusions=[
            "Ninguna fila se oculta: las no aprobadas se publican como no evaluables con motivo."
        ],
        unknowns=[
            "Cambios de decisión posteriores: Prisma no publica historial de la solicitud.",
            "Instante de rechazo: no existe rejected_at en el contrato de Prisma.",
        ],
        dates=["Solicitud.created_at", "Solicitud.approved_at"],
        unit="segundos; también minutos cuando ≥ 60 s",
        status_rule=(
            "evaluable con APROBADA y ambos instantes con zona; PENDIENTE → no evaluable «sin "
            "approved_at»; RECHAZADA → no evaluable «no existe rejected_at»; otro estado → no "
            "evaluable."
        ),
        measurable_in=["fixture", "live"],
    ),
    "open_request_age": IndicatorSheet(
        id="open_request_age",
        name="Antigüedad de la solicitud abierta al corte",
        question=(
            "¿Cuánto lleva abierta cada solicitud pendiente o aprobada sin unidad al corte de "
            "la lectura, y cuántos días pasaron desde su fecha de inicio si ya llegó?"
        ),
        decision="Logística prioriza la asignación; Proyectos confirma si la necesidad sigue.",
        owner="Logística",
        grain="request",
        population="Solicitudes PENDIENTE y APROBADA sin maquinaria_id.",
        numerator=(
            "PENDIENTE: data_as_of − Solicitud.created_at; APROBADA sin unidad: data_as_of − "
            "Solicitud.approved_at (horas). Con Solicitud.fecha_inicio ≤ día del corte en "
            "America/El_Salvador: días = corte − fecha_inicio."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=["APROBADA con unidad (su seguimiento pasa al traslado).", "RECHAZADA."],
        unknowns=[
            "Reprogramaciones o cambios de período (sin historial de la solicitud).",
            "Si la unidad quedó fuera de la página leída.",
        ],
        dates=[
            "HubResponse.data_as_of",
            "Solicitud.created_at",
            "Solicitud.approved_at",
            "Solicitud.fecha_inicio",
        ],
        unit="horas; días desde fecha_inicio cuando está alcanzada",
        status_rule=(
            "no evaluable sin corte de observación (fixture); no evaluable por fila si falta el "
            "instante de origen; un inicio futuro no es atraso (start_reached=false, sin días)."
        ),
        measurable_in=["live"],
    ),
    "approved_with_unit_without_sent_task": IndicatorSheet(
        id="approved_with_unit_without_sent_task",
        name="Aprobadas con unidad sin tarea enviada",
        question=(
            "¿Qué solicitudes aprobadas con unidad asignada no tienen una tarea de Startrack "
            "enviada desde ECON para esa misma asignación y período?"
        ),
        decision="Logística prepara o revisa el traslado; nunca reenvía a ciegas.",
        owner="Logística",
        grain="request",
        population="Solicitudes APROBADA con maquinaria_id cuya unidad está en la lectura.",
        numerator=(
            "Filas sin movimiento en estado sent con job_id que coincida con solicitud, unidad, "
            "proyecto, período y approved_at vigentes (matching_current_movements). Con tarea: "
            "horas Movement.sent_at − Solicitud.approved_at."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=[
            "Movimientos históricos (origen cambiado) y draft/queued/sending/unknown/failed no "
            "cuentan como tarea enviada.",
            "Unidad fuera de la página leída: fila no evaluable, no ausencia.",
        ],
        unknowns=[
            "Tareas creadas fuera de ECON: no se consulta Startrack.",
            "Movimientos fuera de la página del registro: registro parcial → fila parcial.",
        ],
        dates=["Solicitud.approved_at", "Movement.sent_at"],
        unit="lista; horas approved_at → sent_at cuando existe la tarea",
        status_rule=(
            "no evaluable en fixture (las muestras no envían tareas; la ausencia en el archivo "
            "no es cero); parcial si el registro está incompleto; no evaluable si no está "
            "disponible; evaluable solo con registro completo."
        ),
        measurable_in=["live"],
    ),
    "occupied_without_project": IndicatorSheet(
        id="occupied_without_project",
        name="Unidades OCUPADA sin proyecto",
        question="¿Qué unidades figuran OCUPADA en Prisma sin project_id?",
        decision="Logística corrige la asignación en Prisma o libera la unidad.",
        owner="Logística",
        grain="equipment",
        population="Unidades con Maquinaria.estado = OCUPADA en la lectura.",
        numerator="Filas con Maquinaria.project_id ausente (without_project=true).",
        denominator=NOT_APPLICABLE,
        exclusions=["Otros estados administrativos (DISPONIBLE, OBSOLETA, MANTENIMIENTO…)."],
        unknowns=[
            "Unidades fuera de la página leída (5 de 15 en fixture).",
            "Motivo del estado: la lista de Prisma no lo publica (history no implementado).",
        ],
        dates=[],
        unit="lista",
        status_rule=(
            "evaluable por fila con los hechos administrativos de la lista; con 0 unidades "
            "OCUPADA el resultado es «sin casos evaluables», nunca 0 global."
        ),
        measurable_in=["fixture", "live"],
    ),
    "assignment_ended": IndicatorSheet(
        id="assignment_ended",
        name="Asignación vigente vencida al corte",
        question=(
            "¿Qué unidades siguen asignadas a un proyecto cuando fecha_fin_uso ya pasó al "
            "corte de la lectura?"
        ),
        decision="Logística y el proyecto confirman prórroga, devolución o nuevo traslado.",
        owner="Logística",
        grain="equipment",
        population="Unidades con Maquinaria.project_id informado.",
        numerator=(
            "Días = día del corte (America/El_Salvador) − Maquinaria.fecha_fin_uso cuando es "
            "positivo (ended=true)."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=["Unidades sin proyecto."],
        unknowns=[
            "Presencia física y devolución real: no se leen.",
            "Fecha de fin ausente o sin formato de día: fila no evaluable.",
        ],
        dates=["HubResponse.data_as_of", "Maquinaria.fecha_fin_uso"],
        unit="días",
        status_rule=(
            "no evaluable sin corte (fixture); no evaluable por fila sin fecha_fin_uso válida; "
            "una ventana no vencida no es atraso (ended=false, sin días)."
        ),
        measurable_in=["live"],
    ),
    "completed_task_without_receipt": IndicatorSheet(
        id="completed_task_without_receipt",
        name="Tarea completada sin recepción declarada",
        question=(
            "¿Qué traslados tienen la tarea completada en Startrack y aún no tienen recepción "
            "declarada en ECON, y desde cuándo?"
        ),
        decision=(
            "El proyecto declara la recepción o Logística investiga la entrega; una tarea "
            "completada no es recepción."
        ),
        owner="Proyectos",
        grain="movement",
        population=(
            "Movimientos sent con job_id cuyo último task_state (effective_event_sort_key) tiene "
            "workflow_role = '1'."
        ),
        numerator=(
            "Filas sin receipt: horas data_as_of − OperationEvent.event_time del último task_state."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=[
            "Tareas pendientes ('0') o canceladas ('2').",
            "Movimientos sin observación de tarea.",
        ],
        unknowns=[
            "Recepciones declaradas fuera de ECON.",
            "Visitas GPS: no sustituyen la recepción ni la generan.",
        ],
        dates=[
            "OperationEvent.event_time (StartrackJob.last_status_change_date | closed_date | "
            "changed_date)",
            "ReceiptRecord.received_at",
            "HubResponse.data_as_of",
        ],
        unit="horas",
        status_rule=(
            "no evaluable en fixture (sin tareas); no evaluable por fila sin event_time o sin "
            "corte; con recepción declarada la fila es evaluable con receipt_declared=true y "
            "sin edad."
        ),
        measurable_in=["live"],
    ),
    "active_failure_registered": IndicatorSheet(
        id="active_failure_registered",
        name="Falla activa registrada por unidad",
        question="¿Qué unidades de la lectura tienen una falla activa en Prisma y si implica paro?",
        decision=(
            "Mantenimiento revisa el diagnóstico y la decisión de paro; Logística no programa "
            "traslados sobre unidades con paro."
        ),
        owner="Mantenimiento",
        grain="equipment",
        population="Unidades de la lectura con Maquinaria.active_failure_id informado.",
        numerator=(
            "Fila por falla activa con active_failure_status y active_failure_is_paro copiados."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=[],
        unknowns=[
            "Antigüedad de la falla: created_at del reporte no se lee "
            "(/api/maquinaria/fallas/{id} no consultado).",
            "Historial de estados de la falla: solo existe el estado vigente en "
            "/api/maquinaria/fallas.",
        ],
        dates=[],
        unit="lista",
        status_rule=(
            "evaluable por fila con los campos de falla de la lista; 0 fallas activas entre las "
            "filas → «sin casos evaluables», nunca 0 global; la edad no es evaluable."
        ),
        measurable_in=["fixture", "live"],
    ),
    "evidence_age": IndicatorSheet(
        id="evidence_age",
        name="Antigüedad de la evidencia del registro",
        question=(
            "¿Cuánto tiempo pasó desde la última lectura del registro de movimientos, y cuándo "
            "se observó por última vez cada traslado enviado?"
        ),
        decision=(
            "Información/TI decide si hay que ejecutar el ciclo de sincronización antes de "
            "decidir con esta lectura."
        ),
        owner="Información",
        grain="movement",
        population="Movimientos sent del modo.",
        numerator=(
            "HubResponse.generated_at − max(SourceSnapshot.recorded_at, "
            "SourceSnapshot.last_confirmed_at) del último corte del registro (horas). Por fila, "
            "además, max(OperationEvent.observed_at) de sus task_state/arrival."
        ),
        denominator=NOT_APPLICABLE,
        exclusions=["Movimientos no enviados (draft, blocked, queued, sending, unknown, failed)."],
        unknowns=[
            "Qué movimientos revisó ese ciclo: el lote de observación es acotado, por eso se "
            "publica también el observed_at propio de cada movimiento.",
            "Un corte reciente no rejuvenece la evidencia de cada movimiento (observed_at propio).",
        ],
        dates=[
            "HubResponse.generated_at",
            "WorkflowOverview.last_sync_at = max(SourceSnapshot.recorded_at, "
            "SourceSnapshot.last_confirmed_at)",
            "OperationEvent.observed_at",
        ],
        unit="horas",
        status_rule=(
            "no evaluable en fixture (sin lecturas de proveedores); no evaluable sin corte del "
            "registro; único indicador que usa generated_at como «ahora»."
        ),
        measurable_in=["live"],
    ),
}


# ----- helpers ---------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _aware(value: datetime | None) -> datetime | None:
    """Only zoned instants are comparable; an unzoned value stays unknown."""
    return value if value is not None and value.tzinfo is not None else None


def _hours(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 3600, 2)


def _business_day(instant: datetime) -> date:
    return instant.astimezone(BUSINESS_TIMEZONE).date()


def _of(returned: int, total: int | None) -> str:
    return f"{returned} de {total}" if total is not None else f"{returned} (total no informado)"


def _scope_note(hub: HubResponse) -> str:
    scope = hub.scope
    search = f"; búsqueda «{scope.search}»" if scope.search else ""
    return (
        f"Lectura acotada: {_of(scope.equipment_returned, scope.equipment_total)} unidades y "
        f"{_of(scope.requests_returned, scope.requests_total)} solicitudes{search}. Los conteos "
        "describen solo estas filas, no la flota ni la operación completa."
    )


def _row(
    subject: RequestRecord | EquipmentRecord | MovementRecord,
    status: IndicatorStatus,
    *,
    values: dict[str, IndicatorValue] | None = None,
    evidence: Iterable[str] = (),
    reason: str | None = None,
) -> IndicatorRow:
    if isinstance(subject, MovementRecord):
        subject_id, source_id, label = f"econ:movement:{subject.id}", subject.id, subject.job_id
    elif isinstance(subject, EquipmentRecord):
        subject_id, source_id = subject.id, subject.provenance.source_id
        label = subject.asset_number or subject.code or subject.name
    else:
        subject_id, source_id = subject.id, subject.provenance.source_id
        label = (
            f"{subject.status} {subject.starts_on or 'ausente'} → {subject.ends_on or 'ausente'}"
        )
    return IndicatorRow(
        subject_id=subject_id,
        source_id=source_id,
        label=label,
        values=values or {},
        evidence=list(evidence),
        status=status,
        reason=reason,
    )


def _result(
    sheet: IndicatorSheet,
    rows: list[IndicatorRow],
    hub: HubResponse,
    *,
    reason: str | None = None,
    empty: str = "ninguna fila de la población en esta lectura",
    extra: str | None = None,
) -> IndicatorResult:
    counts = Counter(row.status for row in rows)
    if reason is not None:
        status: IndicatorStatus = "not_evaluable"
    elif not rows:
        status, reason = "not_evaluable", f"sin casos evaluables: {empty}"
    elif counts["not_evaluable"] == len(rows):
        status, reason = "not_evaluable", "ninguna fila es evaluable; ver el motivo de cada una"
    elif counts["evaluable"] == len(rows):
        status = "evaluable"
    else:
        status = "partial"
    population = f"{len(rows)} fila(s) en la población."
    note = " ".join(part for part in (population, _scope_note(hub), extra) if part)
    return IndicatorResult(
        sheet=sheet,
        status=status,
        reason=reason,
        rows=rows,
        evaluable_count=counts["evaluable"],
        partial_count=counts["partial"],
        not_evaluable_count=counts["not_evaluable"],
        coverage_note=note,
    )


def _cutoff_reason(hub: HubResponse) -> str:
    return NO_CUTOFF_FIXTURE if hub.mode == "fixture" else NO_CUTOFF_LIVE


def _sent_movements(hub: HubResponse, workflow: WorkflowOverview | None) -> list[MovementRecord]:
    """Sent movements of the hub's mode and environment; other states are never tasks."""
    if workflow is None or not workflow.available:
        return []
    environments = {source.environment for source in hub.sources}
    return [
        movement
        for movement in workflow.movements
        if movement.mode == hub.mode
        and movement.environment in environments
        and movement.state == "sent"
        and movement.job_id
    ]


def _latest_task_state(movement: MovementRecord) -> MovementEventRecord | None:
    states = [
        event
        for event in movement.events
        if event.kind == "task_state" and event.data.get("job_id") == movement.job_id
    ]
    return max(states, key=effective_event_sort_key, default=None)


def _last_observed_at(movement: MovementRecord) -> datetime | None:
    return max(
        (
            event.observed_at
            for event in movement.events
            if event.kind in {"task_state", "arrival"} and event.observed_at is not None
        ),
        default=None,
    )


def _last_registry_read(workflow: WorkflowOverview | None) -> datetime | None:
    """Last reading of the registry, never the last content change alone.

    `WorkflowOverview.last_sync_at` is published by the workflow as
    `ledger.last_read_at(snapshot)` = max(recorded_at, last_confirmed_at) of the latest cut:
    a cut confirmed without changes moves `last_confirmed_at`, not `recorded_at`.
    """
    if workflow is None or not workflow.available:
        return None
    return _aware(workflow.last_sync_at)


# ----- indicators ------------------------------------------------------------------------


def _approval_time(hub: HubResponse) -> IndicatorResult:
    rows = []
    for request in hub.requests:
        status = request.status.upper()
        created, approved = _aware(request.created_at), _aware(request.approved_at)
        evidence = [
            f"status={request.status}",
            f"created_at={_iso(request.created_at)}",
            f"approved_at={_iso(request.approved_at)}",
        ]
        if status in APPROVED:
            if request.approved_at is None:
                reason = "sin approved_at en la solicitud aprobada"
            elif approved is None:
                reason = "approved_at sin zona horaria"
            elif request.created_at is None:
                reason = "sin created_at"
            elif created is None:
                reason = "created_at sin zona horaria"
            elif approved < created:
                reason = "approved_at anterior a created_at: instantes no comparables"
            else:
                seconds = (approved - created).total_seconds()
                rows.append(
                    _row(
                        request,
                        "evaluable",
                        values={
                            "created_at": _iso(created),
                            "approved_at": _iso(approved),
                            "seconds": seconds,
                            "minutes": round(seconds / 60, 2) if seconds >= 60 else None,
                        },
                        evidence=evidence,
                    )
                )
                continue
        elif status in PENDING:
            reason = "sin approved_at: la solicitud sigue PENDIENTE"
        elif status in REJECTED:
            reason = "no existe rejected_at en el contrato de Prisma"
        else:
            reason = f"estado {request.status} sin instante de decisión documentado"
        rows.append(_row(request, "not_evaluable", evidence=evidence, reason=reason))
    return _result(SHEETS["approval_time"], rows, hub, empty="ninguna solicitud en la lectura")


def _open_request_age(hub: HubResponse) -> IndicatorResult:
    as_of = _aware(hub.data_as_of)
    rows = []
    for request in hub.requests:
        status = request.status.upper()
        if status in PENDING:
            variant, since_field, since = "pendiente", "created_at", request.created_at
        elif status in APPROVED and not request.machinery_id:
            variant, since_field, since = "aprobada_sin_unidad", "approved_at", request.approved_at
        else:
            continue
        evidence = [
            f"status={request.status}",
            f"{since_field}={_iso(since)}",
            f"fecha_inicio={request.starts_on}",
            f"data_as_of={_iso(hub.data_as_of)}",
        ]
        values: dict[str, IndicatorValue] = {"variant": variant, "since_field": since_field}
        if as_of is None:
            rows.append(
                _row(
                    request,
                    "not_evaluable",
                    values=values,
                    evidence=evidence,
                    reason=_cutoff_reason(hub),
                )
            )
            continue
        instant = _aware(since)
        if instant is None:
            reason = f"sin {since_field}" if since is None else f"{since_field} sin zona horaria"
            rows.append(
                _row(request, "not_evaluable", values=values, evidence=evidence, reason=reason)
            )
            continue
        if instant > as_of:
            rows.append(
                _row(
                    request,
                    "not_evaluable",
                    values=values,
                    evidence=evidence,
                    reason=f"{since_field} posterior al corte: instantes no comparables",
                )
            )
            continue
        starts_on = parse_day(request.starts_on)
        as_of_day = _business_day(as_of)
        reached = starts_on is not None and starts_on <= as_of_day
        values.update(
            {
                "since": _iso(instant),
                "hours": _hours(instant, as_of),
                "starts_on": request.starts_on,
                "start_reached": reached,
                "days_since_start": (as_of_day - starts_on).days if reached else None,
            }
        )
        rows.append(_row(request, "evaluable", values=values, evidence=evidence))
    reason = _cutoff_reason(hub) if as_of is None else None
    return _result(
        SHEETS["open_request_age"],
        rows,
        hub,
        reason=reason,
        empty="ninguna solicitud PENDIENTE ni APROBADA sin unidad en la lectura",
    )


def _approved_without_sent_task(
    hub: HubResponse, workflow: WorkflowOverview | None
) -> IndicatorResult:
    sheet = SHEETS["approved_with_unit_without_sent_task"]
    approved = [r for r in hub.requests if r.status.upper() in APPROVED and r.machinery_id]
    equipment_ids = {item.id for item in hub.equipment}
    empty = "ninguna solicitud APROBADA con unidad en la lectura"
    if hub.mode == "fixture":
        rows = [_row(r, "not_evaluable", reason=FIXTURE_NO_TASKS) for r in approved]
        return _result(sheet, rows, hub, reason=FIXTURE_NO_TASKS, empty=empty)
    registry_ready = workflow is not None and workflow.available
    if not registry_ready:
        rows = [_row(r, "not_evaluable", reason=REGISTRY_UNAVAILABLE) for r in approved]
        return _result(sheet, rows, hub, reason=REGISTRY_UNAVAILABLE, empty=empty)
    rows = []
    for request in approved:
        evidence = [
            f"status={request.status}",
            f"maquinaria_id={request.machinery_id}",
            f"approved_at={_iso(request.approved_at)}",
        ]
        if request.machinery_id not in equipment_ids:
            rows.append(
                _row(
                    request,
                    "not_evaluable",
                    evidence=evidence,
                    reason="unidad fuera de la lectura: la ausencia de tarea no es verificable",
                )
            )
            continue
        sent = [
            movement
            for movement in matching_current_movements(hub, request, workflow.movements)
            if movement.state == "sent" and movement.job_id
        ]
        approved_at = _aware(request.approved_at)
        if sent:
            latest = max(
                (m for m in sent if m.sent_at is not None), key=lambda m: m.sent_at, default=None
            )
            sent_at = _aware(latest.sent_at) if latest is not None else None
            rows.append(
                _row(
                    request,
                    "evaluable",
                    values={
                        "sent_task": True,
                        "job_ids": ", ".join(sorted(m.job_id for m in sent)),
                        "movement_ids": ", ".join(sorted(m.id for m in sent)),
                        "sent_at": _iso(sent_at),
                        "hours_approved_to_sent": (
                            _hours(approved_at, sent_at)
                            if approved_at is not None and sent_at is not None
                            else None
                        ),
                    },
                    evidence=evidence + [f"movements={len(sent)}"],
                )
            )
        elif workflow.complete:
            rows.append(
                _row(
                    request,
                    "evaluable",
                    values={"sent_task": False, "job_ids": None, "movement_ids": None},
                    evidence=evidence + ["registro completo"],
                )
            )
        else:
            rows.append(
                _row(
                    request,
                    "partial",
                    values={"sent_task": None, "job_ids": None, "movement_ids": None},
                    evidence=evidence + ["registro parcial"],
                    reason="registro parcial: la ausencia de tarea no es verificable",
                )
            )
    extra = None if workflow.complete else f"Registro parcial: {workflow.message}"
    return _result(sheet, rows, hub, empty=empty, extra=extra)


def _occupied_without_project(hub: HubResponse) -> IndicatorResult:
    occupied = [e for e in hub.equipment if e.machinery_status.upper() in OCCUPIED]
    rows = [
        _row(
            unit,
            "evaluable",
            values={
                "machinery_status": unit.machinery_status,
                "project_id": unit.project_id,
                "without_project": unit.project_id is None,
                "assignment_starts_on": unit.assignment_starts_on,
                "assignment_ends_on": unit.assignment_ends_on,
            },
            evidence=[f"estado={unit.machinery_status}", f"project_id={unit.project_id}"],
        )
        for unit in occupied
    ]
    return _result(
        SHEETS["occupied_without_project"],
        rows,
        hub,
        empty=(
            f"ninguna unidad OCUPADA entre las {hub.scope.equipment_returned} filas leídas "
            f"({_of(hub.scope.equipment_returned, hub.scope.equipment_total)})"
        ),
    )


def _assignment_ended(hub: HubResponse) -> IndicatorResult:
    as_of = _aware(hub.data_as_of)
    assigned = [e for e in hub.equipment if e.project_id]
    rows = []
    for unit in assigned:
        evidence = [
            f"project_id={unit.project_id}",
            f"fecha_fin_uso={unit.assignment_ends_on}",
            f"data_as_of={_iso(hub.data_as_of)}",
        ]
        values: dict[str, IndicatorValue] = {
            "machinery_status": unit.machinery_status,
            "project_id": unit.project_id,
            "assignment_ends_on": unit.assignment_ends_on,
        }
        if as_of is None:
            rows.append(
                _row(
                    unit,
                    "not_evaluable",
                    values=values,
                    evidence=evidence,
                    reason=_cutoff_reason(hub),
                )
            )
            continue
        end = parse_day(unit.assignment_ends_on)
        if end is None:
            reason = (
                "sin fecha_fin_uso" if not unit.assignment_ends_on else "fecha_fin_uso inválida"
            )
            rows.append(
                _row(unit, "not_evaluable", values=values, evidence=evidence, reason=reason)
            )
            continue
        days = (_business_day(as_of) - end).days
        values.update({"ended": days > 0, "days_since_end": days if days > 0 else None})
        rows.append(_row(unit, "evaluable", values=values, evidence=evidence))
    reason = _cutoff_reason(hub) if as_of is None else None
    return _result(
        SHEETS["assignment_ended"],
        rows,
        hub,
        reason=reason,
        empty="ninguna unidad con project_id en la lectura",
    )


def _completed_without_receipt(
    hub: HubResponse, workflow: WorkflowOverview | None
) -> IndicatorResult:
    sheet = SHEETS["completed_task_without_receipt"]
    empty = "ningún movimiento sent con tarea completada en el registro"
    if hub.mode == "fixture":
        return _result(sheet, [], hub, reason=FIXTURE_NO_TASKS, empty=empty)
    if workflow is None or not workflow.available:
        return _result(sheet, [], hub, reason=REGISTRY_UNAVAILABLE, empty=empty)
    as_of = _aware(hub.data_as_of)
    rows = []
    for movement in _sent_movements(hub, workflow):
        latest = _latest_task_state(movement)
        if latest is None or latest.data.get("workflow_role") != COMPLETED_ROLE:
            continue
        event_time = _aware(latest.event_time)
        evidence = [
            f"job_id={movement.job_id}",
            f"task_status={latest.data.get('status')}",
            f"workflow_role={latest.data.get('workflow_role')}",
            f"event_time={_iso(latest.event_time)}",
            f"observed_at={_iso(latest.observed_at)}",
            f"data_as_of={_iso(hub.data_as_of)}",
        ]
        values: dict[str, IndicatorValue] = {
            "job_id": movement.job_id,
            "completed_event_time": _iso(latest.event_time),
            "receipt_declared": movement.receipt is not None,
        }
        if movement.receipt is not None:
            values.update(
                {
                    "received_at": _iso(movement.receipt.received_at),
                    "receipt_reference": movement.receipt.reference,
                }
            )
            rows.append(_row(movement, "evaluable", values=values, evidence=evidence))
            continue
        if event_time is None:
            reason = (
                "sin event_time en el último task_state: la lectura no acredita el instante"
                if latest.event_time is None
                else "event_time sin zona horaria"
            )
            rows.append(
                _row(movement, "not_evaluable", values=values, evidence=evidence, reason=reason)
            )
        elif as_of is None:
            rows.append(
                _row(
                    movement,
                    "not_evaluable",
                    values=values,
                    evidence=evidence,
                    reason=NO_CUTOFF_LIVE,
                )
            )
        elif event_time > as_of:
            rows.append(
                _row(
                    movement,
                    "not_evaluable",
                    values=values,
                    evidence=evidence,
                    reason="event_time posterior al corte: instantes no comparables",
                )
            )
        else:
            values["hours_since_completion"] = _hours(event_time, as_of)
            rows.append(_row(movement, "evaluable", values=values, evidence=evidence))
    extra = None if workflow.complete else f"Registro parcial: {workflow.message}"
    return _result(sheet, rows, hub, empty=empty, extra=extra)


def _active_failures(hub: HubResponse) -> IndicatorResult:
    rows = [
        _row(
            unit,
            "evaluable",
            values={
                "machinery_status": unit.machinery_status,
                "active_failure_id": unit.maintenance_failure_id,
                "active_failure_status": unit.maintenance_status,
                "active_failure_is_paro": unit.maintenance_is_stopped,
                "failure_age": None,
            },
            evidence=[
                f"active_failure_id={unit.maintenance_failure_id}",
                f"active_failure_is_paro={unit.maintenance_is_stopped}",
                "edad de la falla: no verificable (reporte de falla no consultado)",
            ],
        )
        for unit in hub.equipment
        if unit.maintenance_failure_id
    ]
    return _result(
        SHEETS["active_failure_registered"],
        rows,
        hub,
        empty=(
            f"ninguna falla activa entre las {hub.scope.equipment_returned} filas leídas "
            f"({_of(hub.scope.equipment_returned, hub.scope.equipment_total)})"
        ),
    )


def _evidence_age(hub: HubResponse, workflow: WorkflowOverview | None) -> IndicatorResult:
    sheet = SHEETS["evidence_age"]
    empty = "ningún movimiento sent en el registro"
    if hub.mode == "fixture":
        return _result(sheet, [], hub, reason=FIXTURE_NO_READS, empty=empty)
    if workflow is None or not workflow.available:
        return _result(sheet, [], hub, reason=REGISTRY_UNAVAILABLE, empty=empty)
    last_read = _last_registry_read(workflow)
    now = _aware(hub.generated_at)
    if last_read is None or now is None:
        return _result(
            sheet, [], hub, reason="sin lectura del registro: ningún corte registrado", empty=empty
        )
    rows = [
        _row(
            movement,
            "evaluable",
            values={
                "last_registry_read_at": _iso(last_read),
                "evidence_age_hours": _hours(last_read, now),
                "movement_last_observed_at": _iso(_last_observed_at(movement)),
            },
            evidence=[
                f"generated_at={_iso(now)}",
                f"last_registry_read_at={_iso(last_read)}",
                f"job_id={movement.job_id}",
            ],
        )
        for movement in _sent_movements(hub, workflow)
    ]
    return _result(sheet, rows, hub, empty=empty)


# ----- report ----------------------------------------------------------------------------


def _notes(hub: HubResponse, workflow: WorkflowOverview | None) -> list[str]:
    notes = [PER_ROW_NOTE]
    if hub.mode == "fixture":
        notes.append(
            "Modo fixture: muestras documentales sin corte de observación (data_as_of=null) y sin "
            "tareas enviadas; las antigüedades y las ausencias no son evaluables."
        )
    elif hub.data_as_of is None:
        notes.append(
            "Modo live sin corte: la lectura de Prisma no se completó; no hay fallback a fixture."
        )
    else:
        notes.append(
            f"Modo live: corte data_as_of={hub.data_as_of.isoformat()} de la lectura acotada."
        )
    notes.extend(f"{source.label}: {source.status}. {source.message}" for source in hub.sources)
    notes.append(f"Registro de movimientos (hub): {hub.operation_evidence.message}")
    if workflow is None:
        notes.append("Registro de movimientos: no consultado en esta lectura.")
    else:
        notes.append(f"Registro de movimientos: {workflow.message}")
    return notes


def compute_indicators(hub: HubResponse, workflow: WorkflowOverview | None) -> IndicatorsReport:
    """Compute every sheet over one hub reading and one ledger page; pure and clockless."""
    return IndicatorsReport(
        mode=hub.mode,
        generated_at=hub.generated_at,
        data_as_of=hub.data_as_of,
        scope=hub.scope,
        registry=hub.operation_evidence,
        ledger_coverage=workflow.coverage if workflow is not None else None,
        ledger_available=bool(workflow is not None and workflow.available),
        last_registry_read_at=_last_registry_read(workflow),
        indicators=[
            _approval_time(hub),
            _open_request_age(hub),
            _approved_without_sent_task(hub, workflow),
            _occupied_without_project(hub),
            _assignment_ended(hub),
            _completed_without_receipt(hub, workflow),
            _active_failures(hub),
            _evidence_age(hub, workflow),
        ],
        notes=_notes(hub, workflow),
    )
