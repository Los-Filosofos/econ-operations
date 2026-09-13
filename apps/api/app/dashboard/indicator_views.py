"""Indicators and proposed SLAs read as decisions: one plain-language insight per sheet.

Every sentence is derived from the rows `compute_indicators` publishes (values, evidence
and reasons) and from the same hub reading that produced them; no rule is recomputed here
and nothing is compared with the clock. Instants are shown in El Salvador time; the table
keeps the original ISO values with their zone. The SLA cards are the table of
docs/indicadores-calculables.md copied as data: every threshold stays «a validar con ECON»
and no compliance is calculated (a cohort of one or two rows would be invented).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from html import escape
from urllib.parse import urlencode

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import html

from app.dashboard.analytics import day, equipment_label, instant
from app.dashboard.components import (
    accordion,
    disclosure,
    facts,
    grid,
    heading,
    hint,
    link,
    markdown_link,
    section,
    state_text,
)
from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import graph
from app.dashboard.theme import FAMILY_COLORS, SEQUENTIAL, figure
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.indicators import IndicatorResult, IndicatorRow, IndicatorsReport
from app.models.workflow import WorkflowOverview
from app.services.indicators import SHEETS, compute_indicators

# ----- static data ------------------------------------------------------------------------

AUDIENCES = (
    (
        "Mantenimiento",
        "Revisa el diagnóstico y la decisión de paro; Logística no programa traslados sobre "
        "unidades con paro.",
    ),
    (
        "Logística",
        "Asigna unidades, envía la tarea a Startrack y confirma la vigencia de cada asignación.",
    ),
    ("Proyectos", "Decide cada solicitud y declara la recepción en obra."),
    (
        "Información",
        "Confirma que la evidencia del registro es reciente antes de decidir con ella.",
    ),
)
NUMBERS = {identifier: f"I{index}" for index, identifier in enumerate(SHEETS, start=1)}
RESULT_STATES = {
    "evaluable": ("Evaluable", "active"),
    "partial": ("Parcial", "pending"),
    "not_evaluable": ("No evaluable", "neutral"),
}
NO_CASES = "Sin casos evaluables"
PLURALS = {
    "Evaluable": "evaluables",
    "Parcial": "parciales",
    "No evaluable": "no evaluables",
    NO_CASES: "sin casos evaluables",
}
NO_CUTOFF_FIXTURE = "Sin corte; antigüedades no evaluables"
# What calls for action first when several indicators have evaluable rows.
PRIORITY = (
    "active_failure_registered",
    "completed_task_without_receipt",
    "approved_with_unit_without_sent_task",
    "occupied_without_project",
    "assignment_ended",
    "open_request_age",
    "evidence_age",
    "approval_time",
)
# Magnitude published per row: (field, axis title, divisor). Lists have no magnitude.
MAGNITUDES = {
    "approval_time": ("seconds", "Horas hasta la aprobación", 3600),
    "open_request_age": ("hours", "Horas abierta al corte", 1),
    "approved_with_unit_without_sent_task": (
        "hours_approved_to_sent",
        "Horas de aprobar a enviar",
        1,
    ),
    "assignment_ended": ("days_since_end", "Días desde fecha_fin_uso al corte", 1),
    "completed_task_without_receipt": (
        "hours_since_completion",
        "Horas desde la tarea completada",
        1,
    ),
    "evidence_age": ("evidence_age_hours", "Horas desde la última lectura", 1),
}
MIN_CHART_ROWS = 3
FOLD_TABLE_ROWS = 5
PAGE_SIZE = 10
COLUMNS = [
    ("subject", "Fila"),
    ("subject_id", "Sujeto"),
    ("source_id", "ID de origen"),
    ("status", "Estado"),
    ("values", "Valores"),
    ("evidence", "Evidencia"),
    ("reason", "Motivo"),
]
WIDTHS = {
    "subject": 140,
    "subject_id": 140,
    "source_id": 120,
    "status": 100,
    "values": 170,
    "evidence": 170,
    "reason": 130,
}
VARIANTS = {"pendiente": "pendiente", "aprobada_sin_unidad": "aprobada sin unidad"}


@dataclass(frozen=True)
class ProposedSla:
    """One row of «Fichas de SLA propuestas» in docs/indicadores-calculables.md."""

    id: str
    name: str
    audience: str
    question: str
    population: str
    formula: str
    threshold: str
    coverage: str
    not_evaluable: str
    decision: str
    indicators: tuple[str, ...]

    @property
    def threshold_text(self) -> str:
        return f"{self.threshold} · a validar con ECON"


SLAS = (
    ProposedSla(
        "S1",
        "Aprobación de la solicitud",
        "Proyectos, Gerencia",
        "¿Se decide cada solicitud dentro del plazo?",
        "Solicitud; APROBADA (y las PENDIENTE vencidas si se acuerda).",
        "approved_at − created_at (I1); pendientes: data_as_of − created_at (I2).",
        "≤ 24 h hábiles",
        "I1 en fixture y live; I2 solo live.",
        "Sin approved_at ni corte; RECHAZADA (no existe rejected_at).",
        "Escalar solicitudes sin decisión.",
        ("approval_time", "open_request_age"),
    ),
    ProposedSla(
        "S2",
        "Asignación de unidad tras aprobar",
        "Logística",
        "¿Cada aprobación recibe unidad a tiempo?",
        "Solicitud; APROBADA sin maquinaria_id.",
        "data_as_of − approved_at (I2, variante aprobada_sin_unidad).",
        "≤ 8 h hábiles",
        "Solo live.",
        "Sin corte; approved_at ausente.",
        "Asignar o justificar la espera.",
        ("open_request_age",),
    ),
    ProposedSla(
        "S3",
        "Envío de la tarea tras asignar",
        "Logística, Información",
        "¿Se envía la tarea a Startrack poco después de aprobar con unidad?",
        "Solicitud; APROBADA con unidad en la lectura.",
        "Movement.sent_at − Solicitud.approved_at (I3, hours_approved_to_sent); sin tarea: "
        "fila abierta.",
        "≤ 4 h hábiles",
        "Solo live con registro completo.",
        "Fixture; registro parcial o no disponible.",
        "Preparar el traslado pendiente.",
        ("approved_with_unit_without_sent_task",),
    ),
    ProposedSla(
        "S4",
        "Recepción tras tarea completada",
        "Proyectos",
        "¿El proyecto declara la recepción poco después de completarse la tarea?",
        "Movimiento; último task_state con workflow_role = '1'.",
        "Sin recepción: data_as_of − event_time (I6); con recepción: ReceiptRecord.received_at − "
        "event_time.",
        "≤ 24 h",
        "Solo live.",
        "Sin event_time; sin corte.",
        "Reclamar la constancia de recepción.",
        ("completed_task_without_receipt",),
    ),
    ProposedSla(
        "S5",
        "Atención de falla con paro",
        "Mantenimiento",
        "¿Cuánto tarda una falla con paro en salir de SIN_REVISAR y en cerrarse?",
        "Falla; reportes con is_paro = true.",
        "Primer cambio de estado − created_at y FINALIZADO − created_at del reporte "
        "(/api/maquinaria/fallas/{id}).",
        "≤ 4 h para revisar",
        "No calculable: /fallas no se lee y no publica instantes por transición.",
        "Siempre, hasta implementar la lectura y un historial de estados.",
        "Priorizar diagnóstico y decisión de paro.",
        ("active_failure_registered",),
    ),
    ProposedSla(
        "S6",
        "Frescura de la evidencia",
        "Información",
        "¿La lectura que sostiene una decisión es reciente y completa?",
        "Registro por modo (I8).",
        "generated_at − last_sync_at; WorkflowOverview.complete.",
        "≤ 1 h con el worker activo",
        "Solo live.",
        "Fixture; sin corte del registro.",
        "Ejecutar el ciclo antes de decidir.",
        ("evidence_age",),
    ),
)
INDICATOR_SLAS: dict[str, list[ProposedSla]] = {
    identifier: [sla for sla in SLAS if identifier in sla.indicators] for identifier in SHEETS
}


@dataclass(frozen=True)
class Insight:
    """Plain-language reading of one indicator, built only from its rows."""

    id: str
    name: str
    question: str
    text: str
    status: str
    family: str
    reason: str | None
    actionable: int
    evaluable_rows: int


# ----- text helpers -----------------------------------------------------------------------


def _parse(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def when_text(value: object) -> str:
    """A documented, zoned instant in El Salvador time; anything else stays «sin fecha»."""
    parsed = _parse(value)
    return instant(parsed) if parsed is not None else "sin fecha"


def duration_text(seconds: float) -> str:
    total = round(seconds)
    if total < 60:
        return f"{total} s"
    hours, minutes = divmod(total // 60, 60)
    if hours == 0:
        return f"{minutes} min"
    days, hours = divmod(hours, 24)
    if days >= 2:
        return f"{days} días" + (f" {hours} h" if hours else "")
    hours += days * 24
    return f"{hours} h" + (f" {minutes} min" if minutes else "")


def _hours(value: object) -> str:
    return duration_text(float(value) * 3600) if isinstance(value, int | float) else "sin duración"


def _count(number: int, singular: str, plural: str | None = None) -> str:
    return f"{number} {singular if number == 1 else plural or singular + 's'}"


def _join(items: Iterable[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _evidence(row: IndicatorRow, key: str | None) -> str | None:
    """A cited fact of the row (`key=value`); «None» is an absent value, not text."""
    if key is None:
        return None
    prefix = f"{key}="
    value = next((item[len(prefix) :] for item in row.evidence if item.startswith(prefix)), None)
    return None if value in (None, "None", "") else value


def _by_reason(rows: list[IndicatorRow]) -> list[tuple[str, list[IndicatorRow]]]:
    grouped: dict[str, list[IndicatorRow]] = {}
    for row in rows:
        grouped.setdefault(row.reason or "sin motivo publicado", []).append(row)
    return list(grouped.items())


def _rows(result: IndicatorResult, status: str) -> list[IndicatorRow]:
    return [row for row in result.rows if row.status == status]


def _request_of(hub: HubResponse, row: IndicatorRow) -> RequestRecord | None:
    return next((item for item in hub.requests if item.id == row.subject_id), None)


def _equipment_of(hub: HubResponse, identifier: str | None) -> EquipmentRecord | None:
    return next((item for item in hub.equipment if item.id == identifier), None)


def _project_code(name: str | None, identifier: str | None) -> str:
    if name:
        first = name.split(" - ", 1)[0].strip()
        return first or name
    return identifier or "proyecto sin identificar"


def _request_subject(hub: HubResponse, row: IndicatorRow) -> str:
    request = _request_of(hub, row)
    if request is None:
        return f"la solicitud {row.source_id or row.subject_id}"
    return (
        f"la solicitud de {request.machinery_type or 'maquinaria'} para "
        f"{_project_code(request.project_name, request.project_id)}"
    )


def _unit_label(hub: HubResponse, row: IndicatorRow) -> str:
    equipment = _equipment_of(hub, row.subject_id)
    return equipment_label(equipment) if equipment else (row.label or row.source_id or "unidad")


def _state_counts(hub: HubResponse) -> str:
    counts = Counter(item.machinery_status for item in hub.equipment)
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return ", ".join(f"{number} {state}" for state, number in ordered)


# ----- insights per sheet -----------------------------------------------------------------

Builder = Callable[[IndicatorResult, HubResponse, IndicatorsReport], tuple[list[str], int]]


def _approval_time(result, hub, report):
    sentences = []
    for row in _rows(result, "evaluable"):
        created = when_text(row.values.get("created_at"))
        approved = when_text(row.values.get("approved_at"))
        sentences.append(
            f"{_sentence(_request_subject(hub, row))} se aprobó en "
            f"{duration_text(float(row.values['seconds']))}: creada el {created}, aprobada el "
            f"{approved}."
        )
    for reason, rows in _by_reason(_rows(result, "not_evaluable")):
        listing = _join(
            f"{_request_subject(hub, row)}, creada el {when_text(_evidence(row, 'created_at'))}"
            for row in rows
        )
        sentences.append(
            f"{_count(len(rows), 'solicitud', 'solicitudes')} sin tiempo de aprobación: "
            f"{listing}. Motivo: {reason}."
        )
    return sentences, 0


def _open_request_age(result, hub, report):
    sentences, actionable = [], 0
    for row in _rows(result, "evaluable"):
        values = row.values
        if values.get("variant") == "aprobada_sin_unidad":
            state = "aprobada sin unidad asignada"
        else:
            state = "pendiente de decisión"
        text = (
            f"{_sentence(_request_subject(hub, row))} lleva {_hours(values.get('hours'))} "
            f"{state} desde {when_text(values.get('since'))}"
        )
        days = values.get("days_since_start")
        if values.get("start_reached") and isinstance(days, int):
            text += f"; su inicio solicitado ({day(values.get('starts_on'))}) " + (
                "es el día del corte" if days == 0 else f"se alcanzó hace {_count(days, 'día')}"
            )
        elif values.get("starts_on"):
            text += f"; su inicio solicitado ({day(values.get('starts_on'))}) aún no llega"
        sentences.append(text + ".")
        actionable += 1
    for reason, rows in _by_reason(_rows(result, "not_evaluable")):
        listing = _join(_open_request(hub, row) for row in rows)
        sentences.append(
            f"{_count(len(rows), 'solicitud abierta', 'solicitudes abiertas')} sin antigüedad "
            f"evaluable: {listing}. Motivo: {reason}."
        )
    return sentences, actionable


def _open_request(hub: HubResponse, row: IndicatorRow) -> str:
    variant = VARIANTS.get(str(row.values.get("variant")), "abierta")
    since = when_text(_evidence(row, str(row.values.get("since_field"))))
    return f"{_request_subject(hub, row)} ({variant} desde {since})"


def _approved_without_sent_task(result, hub, report):
    sentences, actionable = [], 0

    def described(row: IndicatorRow) -> str:
        request = _request_of(hub, row)
        unit = _equipment_of(hub, request.machinery_id) if request else None
        approved = when_text(request.approved_at if request else _evidence(row, "approved_at"))
        label = equipment_label(unit) if unit else "unidad fuera de la lectura"
        return f"{_request_subject(hub, row)} con {label}, aprobada el {approved}"

    for row in _rows(result, "evaluable"):
        values = row.values
        if values.get("sent_task") is True:
            sent = when_text(values.get("sent_at"))
            elapsed = values.get("hours_approved_to_sent")
            sentences.append(
                f"{_sentence(described(row))}, tiene la tarea {values.get('job_ids')} enviada el "
                f"{sent}"
                + (
                    f", {_hours(elapsed)} después de aprobar."
                    if isinstance(elapsed, int | float)
                    else "; sin instantes comparables entre aprobación y envío."
                )
            )
        else:
            sentences.append(
                f"{_sentence(described(row))}, no tiene tarea enviada desde ECON (registro "
                "completo)."
            )
            actionable += 1
    wordings = (
        ("partial", "cuya ausencia de tarea no es verificable"),
        ("not_evaluable", "sin evaluar"),
    )
    for status, wording in wordings:
        for reason, rows in _by_reason(_rows(result, status)):
            count = _count(
                len(rows), "solicitud aprobada con unidad", "solicitudes aprobadas con unidad"
            )
            sentences.append(
                f"{count} {wording}: {_join(described(row) for row in rows)}. Motivo: {reason}."
            )
    return sentences, actionable


def _occupied_without_project(result, hub, report):
    if not hub.equipment:
        return [], 0
    without = [row for row in result.rows if row.values.get("without_project") is True]
    assigned = [row for row in result.rows if row.values.get("without_project") is False]
    sentences = []
    if without:
        sentences.append(
            f"{_count(len(without), 'unidad OCUPADA', 'unidades OCUPADA')} sin proyecto: "
            f"{_join(_unit_label(hub, row) for row in without)}."
        )
    if assigned:
        sentences.append(
            f"{_count(len(assigned), 'unidad OCUPADA', 'unidades OCUPADA')} con proyecto: "
            f"{_join(f'{_unit_label(hub, row)} en {_row_project(hub, row)}' for row in assigned)}."
        )
    if not result.rows:
        sentences.append(
            f"Sin casos: ninguna de las {len(hub.equipment)} unidades leídas figura OCUPADA "
            f"({_state_counts(hub)})."
        )
    return sentences, len(without)


def _row_project(hub: HubResponse, row: IndicatorRow) -> str:
    equipment = _equipment_of(hub, row.subject_id)
    return _project_code(
        equipment.project_name if equipment else None, str(row.values.get("project_id"))
    )


def _assignment_ended(result, hub, report):
    sentences, current, actionable = [], [], 0
    for row in _rows(result, "evaluable"):
        values = row.values
        end = day(values.get("assignment_ends_on"))
        if values.get("ended"):
            days = values.get("days_since_end")
            elapsed = _count(days, "día") if isinstance(days, int) else "un tiempo no calculado"
            sentences.append(
                f"{_unit_label(hub, row)} sigue asignada a {_row_project(hub, row)} con "
                f"fecha_fin_uso {end}, vencida hace {elapsed} al corte "
                f"({when_text(report.data_as_of)})."
            )
            actionable += 1
        else:
            current.append(f"{_unit_label(hub, row)} hasta {end}")
    if current:
        sentences.append(
            f"{_count(len(current), 'asignación vigente', 'asignaciones vigentes')} al corte: "
            f"{_join(current)}."
        )
    for reason, rows in _by_reason(_rows(result, "not_evaluable")):
        listing = _join(
            f"{_unit_label(hub, row)} asignada a {_row_project(hub, row)} hasta "
            f"{day(row.values.get('assignment_ends_on')) or 'sin fecha_fin_uso'}"
            for row in rows
        )
        sentences.append(
            f"{_count(len(rows), 'unidad asignada', 'unidades asignadas')} sin evaluar: "
            f"{listing}. Motivo: {reason}."
        )
    return sentences, actionable


def _completed_without_receipt(result, hub, report):
    sentences, actionable = [], 0
    for row in _rows(result, "evaluable"):
        values = row.values
        completed = when_text(values.get("completed_event_time"))
        if values.get("receipt_declared"):
            sentences.append(
                f"La tarea {values.get('job_id')} completada el {completed} tiene recepción "
                f"declarada el {when_text(values.get('received_at'))} (referencia "
                f"{values.get('receipt_reference')})."
            )
        else:
            sentences.append(
                f"La tarea {values.get('job_id')} completada el {completed} lleva "
                f"{_hours(values.get('hours_since_completion'))} sin recepción declarada al corte."
            )
            actionable += 1
    for reason, rows in _by_reason(_rows(result, "not_evaluable")):
        listing = _join(str(row.values.get("job_id") or row.label) for row in rows)
        sentences.append(
            f"{_count(len(rows), 'traslado', 'traslados')} con tarea completada sin evaluar: "
            f"{listing}. Motivo: {reason}."
        )
    return sentences, actionable


def _active_failures(result, hub, report):
    if not hub.equipment:
        return [], 0
    if not result.rows:
        return [
            f"Sin casos: ninguna de las {len(hub.equipment)} unidades leídas tiene "
            "active_failure_id en Prisma."
        ], 0
    stopped = [row for row in result.rows if row.values.get("active_failure_is_paro") is True]
    ordered = stopped + [row for row in result.rows if row not in stopped]
    parts = [f"{_unit_label(hub, row)} ({_failure_state(row)})" for row in ordered]
    return [
        f"{_count(len(result.rows), 'unidad', 'unidades')} con falla activa registrada: "
        f"{_join(parts)}; la antigüedad de la falla no se lee."
    ], len(result.rows)


def _failure_state(row: IndicatorRow) -> str:
    stopped = row.values.get("active_failure_is_paro")
    if stopped is True:
        stop = "con paro"
    elif stopped is False:
        stop = "sin paro registrado"
    else:
        stop = "paro sin informar"
    return f"{row.values.get('active_failure_status') or 'estado sin informar'}, {stop}"


def _evidence_age(result, hub, report):
    if not result.rows:
        return [], 0
    first = result.rows[0].values
    observed = [
        parsed
        for parsed in (_parse(row.values.get("movement_last_observed_at")) for row in result.rows)
        if parsed is not None
    ]
    latest = f", el más reciente observado el {when_text(max(observed))}" if observed else ""
    sent = _count(len(result.rows), "traslado enviado", "traslados enviados")
    return [
        f"La última lectura del registro fue el {when_text(first.get('last_registry_read_at'))}, "
        f"hace {_hours(first.get('evidence_age_hours'))} respecto a la consulta "
        f"({when_text(report.generated_at)}); {sent} en el registro{latest}."
    ], 0


BUILDERS: dict[str, Builder] = {
    "approval_time": _approval_time,
    "open_request_age": _open_request_age,
    "approved_with_unit_without_sent_task": _approved_without_sent_task,
    "occupied_without_project": _occupied_without_project,
    "assignment_ended": _assignment_ended,
    "completed_task_without_receipt": _completed_without_receipt,
    "active_failure_registered": _active_failures,
    "evidence_age": _evidence_age,
}


def status_label(result: IndicatorResult) -> tuple[str, str]:
    """Status text and color family; an empty population is «sin casos», never zero."""
    no_cases = (result.reason or "").startswith("sin casos evaluables")
    if result.status == "not_evaluable" and no_cases:
        return NO_CASES, "neutral"
    return RESULT_STATES[result.status]


def insight_of(result: IndicatorResult, hub: HubResponse, report: IndicatorsReport) -> Insight:
    sentences, actionable = BUILDERS[result.sheet.id](result, hub, report)
    if not sentences:
        sentences = [_sentence(result.reason or "sin filas en esta lectura") + "."]
    status, family = status_label(result)
    return Insight(
        id=result.sheet.id,
        name=result.sheet.name,
        question=result.sheet.question,
        text=" ".join(sentences),
        status=status,
        family=family,
        reason=result.reason,
        actionable=actionable,
        evaluable_rows=result.evaluable_count,
    )


def top_insights(report: IndicatorsReport, hub: HubResponse, limit: int = 3) -> list[Insight]:
    """The most actionable readings: evaluable rows first, then the fixed priority order."""
    candidates = [
        insight_of(result, hub, report)
        for result in report.indicators
        if result.status != "not_evaluable" and result.evaluable_count > 0
    ]
    candidates.sort(key=lambda item: (0 if item.actionable else 1, PRIORITY.index(item.id)))
    return candidates[:limit]


# ----- figure and table -------------------------------------------------------------------


def hours_figure(result: IndicatorResult) -> go.Figure | None:
    """Horizontal bars, one per evaluable row, only when at least three rows carry a magnitude."""
    spec = MAGNITUDES.get(result.sheet.id)
    if spec is None:
        return None
    field, title, divisor = spec
    points = [
        (row, row.values[field] / divisor)
        for row in result.rows
        if row.status == "evaluable"
        and isinstance(row.values.get(field), int | float)
        and not isinstance(row.values.get(field), bool)
    ]
    if len(points) < MIN_CHART_ROWS:
        return None
    points.sort(key=lambda point: point[1], reverse=True)
    identifiers = [row.subject_id for row, _ in points]
    labels = [escape(row.label or row.source_id or row.subject_id) for row, _ in points]
    values = [round(value, 2) for _, value in points]
    unit = "días" if divisor == 1 and field == "days_since_end" else "h"
    chart = figure(max(200, len(points) * 36 + 80))
    chart.add_bar(
        x=values,
        y=identifiers,
        orientation="h",
        width=0.36,
        marker_color=SEQUENTIAL[2],
        text=[f"{value:g} {unit}" for value in values],
        textposition="outside",
        cliponaxis=False,
        customdata=labels,
        hovertemplate="%{customdata}<br>%{x} " + unit + "<extra></extra>",
    )
    chart.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=identifiers,
        tickmode="array",
        tickvals=identifiers,
        ticktext=labels,
    )
    chart.update_xaxes(title_text=title, rangemode="tozero", range=[0, max(values) * 1.3])
    return chart


def _format(value: object) -> str:
    if value is None:
        return "sin valor"
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _href(context: QueryContext, result: IndicatorResult, row: IndicatorRow) -> str:
    if result.sheet.grain == "request":
        return context.request_href(row.subject_id)
    if result.sheet.grain == "equipment":
        return context.equipment_href(row.subject_id)
    return context.movement_href(row.source_id or row.subject_id.removeprefix("econ:movement:"))


def indicator_rows(result: IndicatorResult, context: QueryContext) -> list[dict]:
    return [
        {
            "subject": markdown_link(
                row.label or row.source_id or row.subject_id, _href(context, result, row)
            ),
            "subject_id": row.subject_id,
            "source_id": row.source_id or "Sin ID de origen",
            "status": RESULT_STATES[row.status][0],
            "values": " · ".join(f"{key}: {_format(value)}" for key, value in row.values.items())
            or "Sin valores publicados",
            "evidence": " · ".join(row.evidence) or "Sin evidencia citada",
            "reason": row.reason or "Fila evaluable",
        }
        for row in result.rows
    ]


def indicator_table(result: IndicatorResult, context: QueryContext):
    table = grid(f"indicator-rows-{result.sheet.id}", indicator_rows(result, context), COLUMNS)
    table.dashGridOptions.update(
        {"paginationPageSize": PAGE_SIZE, "paginationPageSizeSelector": [PAGE_SIZE, 25, 50]}
    )
    for column in table.columnDefs:
        column["minWidth"] = WIDTHS[column["field"]]
        if column["field"] == "status":
            column["cellStyle"] = {
                "styleConditions": [
                    {
                        "condition": f"params.value == {label!r}",
                        "style": {"borderLeft": f"3px solid {FAMILY_COLORS[family]}"},
                    }
                    for label, family in RESULT_STATES.values()
                ]
            }
    caption = f"Filas de {result.sheet.name}: {_count(len(result.rows), 'fila')} de esta lectura."
    block = html.Div(
        [dmc.Text(caption, size="xs", c="dimmed", mb=4), table],
        role="group",
        **{"aria-label": caption},
    )
    if len(result.rows) > FOLD_TABLE_ROWS:
        return accordion(disclosure(f"Ver las {len(result.rows)} filas", block), mt="sm")
    return block


# ----- page -------------------------------------------------------------------------------


def _of(returned: int, total: int | None) -> str:
    return f"{returned} de {total}" if total is not None else f"{returned} (total no informado)"


def coverage_block(report: IndicatorsReport):
    scope = report.scope
    if report.data_as_of is not None:
        cut = instant(report.data_as_of)
    elif report.mode == "fixture":
        cut = NO_CUTOFF_FIXTURE
    else:
        cut = "Sin corte: la lectura de Prisma no se completó"
    if report.ledger_available and report.ledger_coverage is not None:
        coverage = report.ledger_coverage
        registry = f"{coverage.displayed} de {coverage.total} movimientos" + (
            "" if coverage.is_complete else " · registro parcial"
        )
    else:
        registry = report.registry.message
    search = f" · búsqueda «{scope.search}»" if scope.search else ""
    return facts(
        [
            ("Corte de la lectura (data_as_of)", cut),
            (
                "Última lectura del registro (last_registry_read_at)",
                instant(report.last_registry_read_at)
                if report.last_registry_read_at
                else "Sin lectura del registro",
            ),
            (
                "Alcance de la lectura",
                f"{_of(scope.equipment_returned, scope.equipment_total)} unidades · "
                f"{_of(scope.requests_returned, scope.requests_total)} solicitudes{search}",
            ),
            ("Registro de movimientos", registry),
            ("Consulta (generated_at)", instant(report.generated_at)),
        ]
    )


def _summary(report: IndicatorsReport) -> str:
    counts = Counter(status_label(result)[0] for result in report.indicators)
    detail = ", ".join(
        f"{number} {PLURALS[label] if number != 1 else label.lower()}"
        for label, number in counts.items()
    )
    mode = next((note for note in report.notes if note.startswith("Modo ")), "")
    return f"De los {len(report.indicators)} indicadores: {detail}. {mode}".strip()


def sla_card(sla: ProposedSla):
    return dmc.Paper(
        [
            dmc.Text(f"SLA propuesto · {sla.id} · {sla.audience}", size="xs", c="dimmed"),
            dmc.Title(sla.name, order=4, size="h6", mb=4),
            dmc.Text(sla.question, size="sm", mb="xs"),
            facts(
                [
                    ("Umbral sugerido", sla.threshold_text),
                    ("Cobertura hoy", sla.coverage),
                    ("No evaluable cuando", sla.not_evaluable),
                    ("Decisión", sla.decision),
                    ("Fórmula", sla.formula),
                ],
                cols=1,
            ),
        ],
        withBorder=True,
        p="md",
        mb="sm",
        className="sla-card",
    )


def no_sla_card(result: IndicatorResult):
    return dmc.Paper(
        [
            dmc.Text("Sin SLA propuesto", size="xs", c="dimmed"),
            dmc.Title("Hecho administrativo por fila", order=4, size="h6", mb=4),
            dmc.Text(
                "No hay un plazo que medir: cada fila copia un hecho de Prisma y pide una "
                "corrección, no un tiempo.",
                size="sm",
                mb="xs",
            ),
            facts([("Decisión", result.sheet.decision)], cols=1),
        ],
        withBorder=True,
        p="md",
        mb="sm",
        className="sla-card",
    )


def _row_counts(result: IndicatorResult) -> str:
    if not result.rows:
        return "0 filas"
    parts = [
        f"{number} {label}"
        for number, label in (
            (result.evaluable_count, "evaluable"),
            (result.partial_count, "parcial"),
            (result.not_evaluable_count, "no evaluable"),
        )
        if number
    ]
    return f"{_count(len(result.rows), 'fila')}: {', '.join(parts)}"


def indicator_block(
    result: IndicatorResult, hub: HubResponse, report: IndicatorsReport, context: QueryContext
):
    sheet = result.sheet
    insight = insight_of(result, hub, report)
    chart = hours_figure(result)
    title_id = f"indicator-{sheet.id}-title"
    dates = ", ".join(sheet.dates) or "ninguna (hecho administrativo de la fila)"
    cards = [sla_card(sla) for sla in INDICATOR_SLAS[sheet.id]] or [no_sla_card(result)]
    # The reason is part of the insight when it comes from the rows; state it once.
    reason = result.reason if result.reason and result.reason not in insight.text else None
    note = result.coverage_note
    partial = note[note.index("Registro parcial:") :] if "Registro parcial:" in note else ""
    reading = [
        dmc.Group(
            [
                state_text(insight.status, insight.family),
                dmc.Text(_row_counts(result), size="xs", c="dimmed"),
            ],
            gap="md",
        ),
        dmc.Text(
            insight.text,
            size="md",
            fw=500,
            mt="xs",
            maw="80ch",
            className="indicator-insight",
            style={"overflowWrap": "anywhere"},
        ),
        hint(f"Motivo: {reason}.") if reason else None,
        hint(
            f"Evidencia: {_count(len(result.rows), 'fila')} en la población; fechas de origen: "
            f"{dates}. {partial}".rstrip()
        ),
    ]
    return html.Article(
        [
            dmc.Title(f"{NUMBERS[sheet.id]} · {sheet.name}", order=3, size="h5", id=title_id),
            dmc.Text(sheet.question, size="sm", c="dimmed", maw="80ch", mb="sm"),
            dmc.Grid(
                [
                    dmc.GridCol(reading, span={"base": 12, "md": 8}),
                    dmc.GridCol(cards, span={"base": 12, "md": 4}),
                ],
                gutter="lg",
            ),
            [
                graph(f"indicator-chart-{sheet.id}", chart),
                hint("Una barra por fila evaluable, ordenadas por magnitud; sin promedios."),
            ]
            if chart is not None
            else None,
            indicator_table(result, context) if result.rows else None,
        ],
        id=f"indicator-{sheet.id}",
        className="indicator",
        style={"marginTop": 24},
        **{"aria-labelledby": title_id},
    )


def indicators_page(hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None):
    """Eight sheets grouped by the area that acts on them, each with its proposed SLA beside."""
    report = compute_indicators(hub, workflow)
    params = {"mode": hub.mode, **({"search": hub.scope.search} if hub.scope.search else {})}
    sections = []
    for audience, role in AUDIENCES:
        results = [result for result in report.indicators if result.sheet.owner == audience]
        blocks = []
        for index, result in enumerate(results):
            if index:
                blocks.append(dmc.Divider(my="lg"))
            blocks.append(indicator_block(result, hub, report, context))
        sections.append(
            section(
                audience,
                dmc.Text(role, size="sm", c="dimmed", maw="80ch"),
                blocks,
                **{"aria-label": f"Indicadores para {audience}"},
            )
        )
    return [
        heading(
            "Indicadores y SLA",
            "Qué dicen las lecturas de hoy, por fila y sin promedios, y el SLA propuesto para "
            "cada pregunta. La ausencia de un dato no es cero.",
        ),
        coverage_block(report),
        hint(_summary(report)),
        hint(
            "Fechas en hora de El Salvador (America/El_Salvador); la tabla conserva los "
            "instantes de origen con su zona. Los conteos describen esta lectura, no la flota. "
            "Los umbrales de SLA son puntos de partida para acordarlos con cada área; no se "
            "calcula cumplimiento."
        ),
        *sections,
        accordion(
            disclosure(
                "Notas de la lectura",
                dmc.List([dmc.ListItem(note) for note in report.notes], size="sm"),
                link(
                    "Contrato JSON de estos indicadores",
                    f"/api/v1/indicators?{urlencode(params)}",
                    target="_blank",
                    anchorProps={"rel": "noopener noreferrer"},
                    mt="sm",
                    display="block",
                ),
            ),
            mt="lg",
        ),
    ]


def indicator_insights(hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None):
    """«Lo que dicen los indicadores»: the three most actionable readings for the decisions page."""
    report = compute_indicators(hub, workflow)
    top = top_insights(report, hub)
    with_rows = sum(1 for result in report.indicators if result.evaluable_count)
    if report.data_as_of is not None:
        cut = f"Corte de la lectura: {instant(report.data_as_of)}."
    elif report.mode == "fixture":
        cut = f"{NO_CUTOFF_FIXTURE} (muestras sin corte de observación)."
    else:
        cut = "Sin corte de observación: la lectura de Prisma no se completó."
    items = [
        dmc.Paper(
            [
                dmc.Group(
                    [
                        state_text(item.status, item.family),
                        dmc.Title(f"{NUMBERS[item.id]} · {item.name}", order=3, size="h6"),
                    ],
                    gap="sm",
                ),
                dmc.Text(item.text, size="sm", mt=6, style={"overflowWrap": "anywhere"}),
            ],
            withBorder=True,
            p="md",
            className="insight-card",
        )
        for item in top
    ]
    return section(
        "Lo que dicen los indicadores",
        hint(
            f"{with_rows} de {len(report.indicators)} indicadores tienen filas evaluables en esta "
            f"lectura. {cut}"
        ),
        dmc.Stack(items, gap="sm")
        if items
        else hint(
            "Ningún indicador tiene filas evaluables en esta lectura; los ocho se publican con su "
            "motivo en la página de indicadores.",
            role="status",
        ),
        link(
            "Ver los 8 indicadores y sus SLA propuestos",
            context.href("/indicadores"),
            mt="sm",
            display="block",
        ),
        **{"aria-label": "Lo que dicen los indicadores"},
    )
