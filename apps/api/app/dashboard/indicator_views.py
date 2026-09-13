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
from datetime import date, datetime, timedelta
from html import escape
from math import isfinite
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
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.dashboard.decision_analytics import graph
from app.dashboard.kpi_views import NUMBERS, duration_text, kpi_board, subject_href
from app.dashboard.theme import FAMILY_COLORS, MEASURE, PAPER, figure
from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.indicators import IndicatorResult, IndicatorRow, IndicatorsReport
from app.models.workflow import WorkflowOverview
from app.services.hub import BUSINESS_TIMEZONE
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
DISPLAY_TITLES = {
    "approval_time": "Tiempo de aprobación",
    "open_request_age": "Solicitudes por resolver",
    "approved_with_unit_without_sent_task": "Envío de traslados",
    "occupied_without_project": "Asignaciones por corregir",
    "assignment_ended": "Fin de asignación",
    "completed_task_without_receipt": "Recepciones pendientes",
    "active_failure_registered": "Fallas registradas",
    "evidence_age": "Actualización de evidencia",
}
DECISION_PROMPTS = {
    "approval_time": "Revisar solicitudes que esperan aprobación.",
    "open_request_age": "Asignar unidad o confirmar la necesidad.",
    "approved_with_unit_without_sent_task": "Revisar la preparación del traslado.",
    "occupied_without_project": "Corregir la asignación en Prisma.",
    "assignment_ended": "Confirmar prórroga, devolución o traslado.",
    "completed_task_without_receipt": "Solicitar la constancia de recepción.",
    "active_failure_registered": "Revisar diagnóstico y decisión de paro.",
    "evidence_age": "Confirmar la lectura antes de decidir.",
}
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
MIN_CHART_ROWS = 1
MAX_CHART_ROWS = 10
MAX_INSIGHT_ROWS = 3
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
    # These flags are published by the service. This only chooses which existing
    # cases to describe first; no dates, SLA or eligibility are recalculated.
    def calls_for_action(row: IndicatorRow) -> bool:
        if result.sheet.id == "active_failure_registered":
            return True
        if result.sheet.id == "occupied_without_project":
            return row.values.get("without_project") is True
        if row.status != "evaluable":
            return False
        return {
            "open_request_age": True,
            "approved_with_unit_without_sent_task": row.values.get("sent_task") is not True,
            "assignment_ended": bool(row.values.get("ended")),
            "completed_task_without_receipt": not row.values.get("receipt_declared"),
        }.get(result.sheet.id, False)

    actionable = sum(calls_for_action(row) for row in result.rows)
    preview = result
    truncated = len(result.rows) > MAX_INSIGHT_ROWS and result.sheet.id != "evidence_age"
    if truncated:
        selected = sorted(
            result.rows,
            key=lambda row: (
                not calls_for_action(row),
                row.status != "evaluable",
                row.values.get("active_failure_is_paro") is not True,
            ),
        )[:MAX_INSIGHT_ROWS]
        counts = Counter(row.status for row in selected)
        preview = result.model_copy(
            update={
                "rows": selected,
                "evaluable_count": counts["evaluable"],
                "partial_count": counts["partial"],
                "not_evaluable_count": counts["not_evaluable"],
            }
        )
    sentences, _ = BUILDERS[result.sheet.id](preview, hub, report)
    if not sentences:
        sentences = [_sentence(result.reason or "sin filas en esta lectura") + "."]
    if truncated:
        sentences.insert(
            0,
            f"{_row_counts(result)} en total. Se describen {MAX_INSIGHT_ROWS} casos; "
            "el resto está en la tabla de filas.",
        )
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


def _chart_label(
    row: IndicatorRow, result: IndicatorResult, hub: HubResponse | None, position: int
):
    """Human labels on axes; original identifiers stay in hover and the evidence table."""

    def compact(value: str | None, fallback: str, limit: int = 28) -> str:
        text = " ".join((value or fallback).split())
        return escape(text if len(text) <= limit else text[: limit - 1] + "…")

    def project(name: str | None) -> str:
        label = name.partition(" - ")[2] or name if name else None
        return compact(label, "Proyecto sin nombre")

    def short_day(value: str | None) -> str:
        if value:
            try:
                return date.fromisoformat(value).strftime("%d/%m")
            except ValueError:
                parsed = _parse(value)
                if parsed:
                    return when_text(parsed)[:5]
        return "sin fecha"

    if hub is not None and result.sheet.grain == "request":
        request = _request_of(hub, row)
        if request is not None:
            return (
                f"{project(request.project_name)}<br>"
                f"{compact(request.machinery_type, 'Maquinaria', 22)} · "
                f"{short_day(request.starts_on)}"
            )
    if hub is not None and result.sheet.grain == "equipment":
        equipment = _equipment_of(hub, row.subject_id)
        if equipment is not None:
            return f"{compact(equipment.name, 'Equipo')}<br>{project(equipment.project_name)}"
    subject = {"request": "Solicitud", "equipment": "Equipo", "movement": "Traslado"}
    return f"{subject[result.sheet.grain]} · fila {position}"


def _approval_interval(result: IndicatorResult, row: IndicatorRow, hub: HubResponse | None):
    """A single observed process on its actual clock, not a self-scaled score."""
    created = _parse(row.values.get("created_at"))
    approved = _parse(row.values.get("approved_at"))
    if created is None or approved is None or approved < created:
        return None
    created, approved = (value.astimezone(BUSINESS_TIMEZONE) for value in (created, approved))
    start = created.replace(second=0, microsecond=0)
    end = approved.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Explicit local tick text prevents the viewer's browser timezone changing the clock.
    def local(value):
        return value.replace(tzinfo=None).isoformat()

    span_minutes = max(1, int((end - start).total_seconds() / 60))
    step = max(1, (span_minutes + 4) // 5)
    ticks = [start + timedelta(minutes=offset) for offset in range(0, span_minutes + 1, step)]
    if ticks[-1] != end:
        ticks.append(end)
    duration = row.values["seconds"]
    chart = figure(230)
    chart.update_layout(meta={"comparable": 1, "displayed": 1, "kind": "interval"})
    chart.add_scatter(
        x=[local(created), local(approved)],
        y=[row.subject_id, row.subject_id],
        mode="lines+markers",
        line={"color": MEASURE, "width": 2},
        marker={"color": MEASURE, "size": 10, "symbol": ["circle-open", "diamond"]},
        customdata=[
            [escape(row.source_id or row.subject_id), label, _business_time(moment)]
            for moment, label in ((created, "Creada"), (approved, "Aprobada"))
        ],
        hovertemplate=(
            "Solicitud %{customdata[0]}<br>%{customdata[1]}: %{customdata[2]}<extra></extra>"
        ),
        cliponaxis=False,
    )
    for moment, label, shift, anchor in (
        (created, "Creada", 38, "left"),
        (approved, "Aprobada", -38, "right"),
    ):
        chart.add_annotation(
            x=local(moment),
            y=row.subject_id,
            text=f"{label} {moment:%H:%M:%S}",
            showarrow=False,
            yshift=shift,
            xanchor=anchor,
            font={"size": 12},
        )
    chart.add_annotation(
        x=local(created + (approved - created) / 2),
        y=row.subject_id,
        text=duration_text(duration),
        showarrow=False,
        yshift=16,
        bgcolor=PAPER,
        font={"color": MEASURE, "size": 17},
    )
    chart.update_xaxes(
        type="date",
        range=[local(start), local(end)],
        tickmode="array",
        tickvals=[local(tick) for tick in ticks],
        ticktext=[tick.strftime("%H:%M") for tick in ticks],
        title_text=f"{created:%d/%m/%Y} · Hora de El Salvador",
    )
    chart.update_yaxes(showticklabels=False)
    return chart


def hours_figure(result: IndicatorResult, hub: HubResponse | None = None) -> go.Figure | None:
    """Compare multiple measured durations in one scale per chart.

    Source values remain unchanged. Proposed SLAs never become chart targets: some
    use business hours while these observations measure elapsed time.
    """
    spec = MAGNITUDES.get(result.sheet.id)
    if spec is None or result.sheet.id == "evidence_age":
        return None
    field, title, divisor = spec
    points = [
        (row, row.values[field] / divisor)
        for row in result.rows
        if row.status == "evaluable"
        and isinstance(row.values.get(field), int | float)
        and not isinstance(row.values.get(field), bool)
        and isfinite(row.values[field])
    ]
    if len(points) < MIN_CHART_ROWS:
        return None
    if result.sheet.id == "approval_time" and len(points) == 1:
        return _approval_interval(result, points[0][0], hub)
    points.sort(key=lambda point: point[1], reverse=True)
    comparable = len(points)
    points = points[:MAX_CHART_ROWS]
    identifiers = [row.subject_id for row, _ in points]
    labels = [
        _chart_label(row, result, hub, index) for index, (row, _) in enumerate(points, start=1)
    ]
    evidence = [
        [escape(row.label or "Registro"), escape(row.source_id or row.subject_id)]
        for row, _ in points
    ]
    largest = max(abs(value) for _, value in points)
    if field == "days_since_end":
        scale, unit, axis_unit = 1, "d", "días"
        axis_title = "Tiempo desde el fin de uso"
    else:
        scale, unit, axis_unit = (
            (3600, "s", "segundos")
            if largest < 1 / 60
            else (60, "min", "minutos")
            if largest < 1
            else (1, "h", "horas corridas")
        )
        axis_title = title.replace("Horas", "Tiempo", 1)
    values = [value * scale for _, value in points]
    chart = figure(max(260, len(points) * 54 + 100))
    chart.update_layout(meta={"comparable": comparable, "displayed": len(points)})
    chart.add_bar(
        x=values,
        y=identifiers,
        orientation="h",
        width=0.36,
        marker_color=MEASURE,
        text=[f"{value:g} {unit}" for value in values],
        textposition="outside",
        cliponaxis=False,
        customdata=evidence,
        hovertemplate="%{customdata[0]}<br>ID: %{customdata[1]}<br>%{x} "
        + unit
        + "<extra></extra>",
    )
    chart.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=identifiers,
        tickmode="array",
        tickvals=identifiers,
        ticktext=labels,
    )
    lower, upper = min(0, min(values) * 1.3), max(0, max(values) * 1.3)
    chart.update_xaxes(
        title_text=f"{axis_title} ({axis_unit})",
        rangemode="tozero",
        range=[lower, upper if upper != lower else 1],
    )
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
    return subject_href(context, result.sheet.grain, row)


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


def indicator_table(result: IndicatorResult, context: QueryContext, *, folded: bool = True):
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
    return (
        accordion(disclosure(f"Ver las {len(result.rows)} filas y su evidencia", block), mt="sm")
        if folded
        else block
    )


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
    """Methodology for a proposed SLA, shown only inside its disclosure."""
    return facts(
        [
            ("Pregunta", sla.question),
            ("Cobertura hoy", sla.coverage),
            ("No evaluable cuando", sla.not_evaluable),
            ("Decisión", sla.decision),
            ("Fórmula", sla.formula),
        ],
        cols=1,
    )


def no_sla_card(result: IndicatorResult):
    """Administrative facts need an action, without an empty SLA card."""
    return hint(result.sheet.decision)


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


def _business_time(value: object) -> str:
    if value is None:
        return "No informado"
    parsed = _parse(value)
    return (
        parsed.astimezone(BUSINESS_TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")
        if parsed
        else "No verificable"
    )


def _business_reason(reason: str | None) -> str:
    if not reason:
        return ""
    if "sin corte de observación" in reason:
        return "Falta un corte de lectura para calcular la antigüedad."
    if "fixture" in reason and "tareas" in reason:
        return "La muestra documental no incluye envíos de tareas."
    if "sin approved_at" in reason and "PENDIENTE" in reason:
        return "Pendiente de aprobación."
    if "sin approved_at" in reason:
        return "Falta la fecha de aprobación."
    if reason.startswith("sin created_at"):
        return "Falta la fecha de creación."
    return reason


def _business_duration(row: IndicatorRow, identifier: str) -> str:
    spec = MAGNITUDES.get(identifier)
    if spec is None:
        return "No aplica"
    field, _, _ = spec
    value = row.values.get(field)
    if not isinstance(value, int | float) or isinstance(value, bool) or not isfinite(value):
        return "No calculable"
    if field == "seconds":
        return duration_text(value)
    if field == "days_since_end":
        return f"{value:g} días"
    if abs(value) < 1 / 60:
        return f"{value * 3600:g} s"
    if abs(value) < 1:
        return f"{value * 60:g} min"
    return f"{value:g} h"


BUSINESS_COLUMNS = {
    "approval_time": [
        ("record", "Solicitud"),
        ("created", "Creada"),
        ("approved", "Aprobada"),
        ("duration", "Tiempo"),
        ("note", "Observación"),
    ],
    "open_request_age": [
        ("record", "Solicitud"),
        ("since", "Abierta desde"),
        ("start", "Inicio solicitado"),
        ("duration", "Antigüedad"),
        ("note", "Observación"),
    ],
    "approved_with_unit_without_sent_task": [
        ("record", "Solicitud"),
        ("approved", "Aprobada"),
        ("sent", "Envío de tarea"),
        ("duration", "Aprobación a envío"),
        ("note", "Observación"),
    ],
    "occupied_without_project": [
        ("record", "Equipo"),
        ("project", "Proyecto asignado"),
        ("note", "Observación"),
    ],
    "assignment_ended": [
        ("record", "Equipo"),
        ("end", "Fin de asignación"),
        ("duration", "Días desde el fin"),
        ("note", "Observación"),
    ],
    "completed_task_without_receipt": [
        ("record", "Tarea"),
        ("completed", "Tarea completada"),
        ("received", "Recepción"),
        ("duration", "Espera de recepción"),
        ("note", "Observación"),
    ],
    "active_failure_registered": [
        ("record", "Equipo"),
        ("failure", "Estado de falla"),
        ("stop", "Decisión de paro"),
        ("note", "Observación"),
    ],
    "evidence_age": [
        ("record", "Tarea"),
        ("read", "Lectura del registro"),
        ("observed", "Observación de la tarea"),
        ("duration", "Antigüedad del registro"),
    ],
}
QUESTION_LABELS = {
    "approval_time": "Aprobación",
    "open_request_age": "Solicitudes abiertas",
    "approved_with_unit_without_sent_task": "Envíos",
    "occupied_without_project": "Asignaciones",
    "assignment_ended": "Fin de uso",
    "completed_task_without_receipt": "Recepciones",
    "active_failure_registered": "Fallas",
    "evidence_age": "Actualización",
}
REQUIRED_DATA = {
    "approval_time": "Se necesitan las fechas de creación y aprobación.",
    "open_request_age": "Se necesita un corte de lectura y la fecha de creación o aprobación.",
    "approved_with_unit_without_sent_task": (
        "Se necesita el registro de envíos de la misma asignación; "
        "debe estar completo para verificar una ausencia."
    ),
    "occupied_without_project": "Se necesita leer el estado y la asignación de los equipos.",
    "assignment_ended": "Se necesitan el corte de lectura y la fecha de fin de asignación.",
    "completed_task_without_receipt": (
        "Se necesita el registro de tareas con fechas de estado y un corte de lectura."
    ),
    "active_failure_registered": "Se necesita leer las fallas activas de los equipos.",
    "evidence_age": "Se necesita una lectura fechada del registro.",
}


def business_rows(result: IndicatorResult, hub: HubResponse, context: QueryContext) -> list[dict]:
    """Business columns use published values; the evidence table retains source fields."""
    identifier = result.sheet.id
    rows = []
    for row in result.rows:
        values = row.values
        request = _request_of(hub, row) if result.sheet.grain == "request" else None
        equipment = (
            _equipment_of(hub, row.subject_id) if result.sheet.grain == "equipment" else None
        )
        if request:
            label = " · ".join(
                [
                    request.machinery_type or "Maquinaria",
                    request.project_name or "Proyecto sin nombre",
                ]
            )
        elif equipment:
            label = equipment.name
            if equipment.asset_number or equipment.code:
                label = f"{equipment_label(equipment)} · {label}"
        else:
            label = row.label or "Movimiento sin referencia"
        item = {
            "record": markdown_link(label, _href(context, result, row)),
            "duration": _business_duration(row, identifier),
            "note": _business_reason(row.reason),
        }
        if identifier == "approval_time":
            item.update(
                created=_business_time(request.created_at if request else values.get("created_at")),
                approved=_business_time(
                    request.approved_at if request else values.get("approved_at")
                ),
            )
        elif identifier == "open_request_age":
            since = values.get("since") or _evidence(row, str(values.get("since_field")))
            item.update(
                since=_business_time(since),
                start=day(request.starts_on if request else values.get("starts_on")),
            )
        elif identifier == "approved_with_unit_without_sent_task":
            sent = values.get("sent_task")
            item.update(
                approved=_business_time(
                    request.approved_at if request else _evidence(row, "approved_at")
                ),
                sent=(
                    _business_time(values.get("sent_at"))
                    if sent is True and values.get("sent_at") is not None
                    else "Enviada · fecha no informada"
                    if sent is True
                    else "Sin tarea enviada"
                    if sent is False
                    else "Sin verificar"
                ),
            )
        elif identifier == "occupied_without_project":
            without_project = values.get("without_project")
            item["project"] = (
                "Sin proyecto"
                if without_project is True
                else _row_project(hub, row)
                if without_project is False
                else "Sin verificar"
            )
        elif identifier == "assignment_ended":
            item["end"] = day(values.get("assignment_ends_on"))
            if values.get("ended") is False:
                item["duration"] = "No aplica"
                item["note"] = "El período no ha vencido al corte."
        elif identifier == "completed_task_without_receipt":
            received = values.get("receipt_declared")
            item.update(
                completed=_business_time(values.get("completed_event_time")),
                received=(
                    _business_time(values.get("received_at"))
                    if received is True and values.get("received_at") is not None
                    else "Declarada · fecha no informada"
                    if received is True
                    else "Sin constancia"
                    if received is False
                    else "Sin verificar"
                ),
            )
            if received is True:
                item["duration"] = "No aplica"
        elif identifier == "active_failure_registered":
            stop = values.get("active_failure_is_paro")
            item.update(
                failure=values.get("active_failure_status") or "No informado",
                stop="Con paro"
                if stop is True
                else "Sin paro registrado"
                if stop is False
                else "No informado",
            )
        elif identifier == "evidence_age":
            item.update(
                read=_business_time(values.get("last_registry_read_at")),
                observed=_business_time(values.get("movement_last_observed_at")),
            )
        rows.append(item)
    return rows


def business_table(result: IndicatorResult, hub: HubResponse, context: QueryContext):
    overrides = {
        "record": {"minWidth": 240, "flex": 2, "wrapText": True, "autoHeight": True},
        "duration": {"width": 150, "minWidth": 130, "flex": 0},
        "note": {"minWidth": 190, "flex": 2, "wrapText": True, "autoHeight": True},
    }
    for field in (
        "created",
        "approved",
        "since",
        "sent",
        "completed",
        "received",
        "read",
        "observed",
    ):
        overrides[field] = {"minWidth": 175, "flex": 1, "wrapText": True, "autoHeight": True}
    table = grid(
        f"indicator-business-{result.sheet.id}",
        business_rows(result, hub, context),
        BUSINESS_COLUMNS[result.sheet.id],
        column_overrides=overrides,
        markdown_fields={"record"},
    )
    table.dashGridOptions.update({"pagination": len(result.rows) > 15})
    return table


def indicator_block(
    result: IndicatorResult, hub: HubResponse, report: IndicatorsReport, context: QueryContext
):
    """One selected analysis: outcome, comparison when useful, then actionable records."""
    sheet = result.sheet
    chart = hours_figure(result, hub)
    title_id = f"indicator-{sheet.id}-title"
    _, family = status_label(result)
    no_cases = status_label(result)[0] == NO_CASES
    if result.evaluable_count:
        headline = (
            f"{result.evaluable_count} de {len(result.rows)} registros con datos suficientes."
        )
        if result.partial_count or result.not_evaluable_count:
            headline += " Consulta los faltantes en la tabla."
    else:
        headline = _business_reason(result.reason) or "No hay registros evaluables en esta lectura."
    details = [
        hint("Fechas en hora de El Salvador. A continuación se conservan los campos originales.")
        if result.rows and sheet.dates
        else None,
        indicator_table(result, context, folded=False) if result.rows else None,
        facts(
            [
                ("Indicador", f"{NUMBERS[sheet.id]} · {sheet.name}"),
                ("Pregunta", sheet.question),
                ("Decisión", sheet.decision),
                ("Población", sheet.population),
                ("Fórmula", sheet.numerator),
                ("Fechas de origen", ", ".join(sheet.dates) or "No requiere fechas"),
                ("Cobertura", result.coverage_note),
                ("Regla de evaluación", sheet.status_rule),
            ],
            cols=1,
        ),
    ]
    proposed = INDICATOR_SLAS[sheet.id]
    if proposed:
        details.append(
            simple_table(
                ["SLA propuesto", "Umbral a validar", "Condición"],
                [[sla.name, sla.threshold, sla.coverage] for sla in proposed],
                caption="SLA propuestos de esta pregunta; no se calcula cumplimiento",
            )
        )
    chart_note = None
    if chart is not None:
        meta = chart.layout.meta
        chart_note = (
            None
            if meta.get("kind") == "interval"
            else f"Las {meta['displayed']} mayores duraciones de {meta['comparable']} comparables."
            if meta["displayed"] < meta["comparable"]
            else None
        )
    return html.Article(
        [
            dmc.Title(DISPLAY_TITLES[sheet.id], order=2, size="h4", id=title_id),
            dmc.Text(
                REQUIRED_DATA[sheet.id],
                size="sm",
                mt="xs",
            )
            if not result.rows and not no_cases
            else None,
            hint(headline, role="status"),
            state_text("Sin casos en los registros leídos", family) if no_cases else None,
            graph(f"indicator-chart-{sheet.id}", chart) if chart is not None else None,
            hint(chart_note) if chart_note else None,
            section(
                {"request": "Solicitudes", "equipment": "Maquinaria", "movement": "Movimientos"}[
                    sheet.grain
                ],
                business_table(result, hub, context),
            )
            if result.rows
            else None,
            accordion(
                disclosure("Definición y datos de origen", *details),
                mt="md",
            ),
        ],
        id=f"indicator-{sheet.id}",
        className="indicator-workspace-panel",
        **{"aria-labelledby": title_id},
    )


def indicators_page(hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None):
    """A single question at a time, with sources and proposed SLAs in a secondary tab."""
    report = compute_indicators(hub, workflow)
    params = {"mode": hub.mode, **({"search": hub.scope.search} if hub.scope.search else {})}
    available = [result for result in report.indicators if result.evaluable_count]
    available.sort(key=lambda result: PRIORITY.index(result.sheet.id))
    selected = available[0].sheet.id if available else report.indicators[0].sheet.id
    cutoff = (
        f"Corte: {instant(report.data_as_of)}."
        if report.data_as_of is not None
        else "Sin corte para calcular antigüedades."
    )
    registry_note = (
        " Registro no disponible."
        if not report.ledger_available
        else " Registro parcial."
        if report.ledger_coverage is not None and not report.ledger_coverage.is_complete
        else ""
    )
    method = [
        dmc.Title("SLA propuestos", order=2, size="h4"),
        hint("Objetivos pendientes de acuerdo con ECON. No se calcula cumplimiento."),
        simple_table(
            ["Objetivo", "Responsable", "Umbral propuesto"],
            [[sla.name, sla.audience, sla.threshold] for sla in SLAS],
            caption="SLA propuestos; no son resultados de la operación",
        ),
        hint("S5 propone 4 h para revisar una falla; su calendario todavía debe acordarse."),
        accordion(
            disclosure(
                "Fuentes, fórmulas y condiciones",
                coverage_block(report),
                hint(_summary(report)),
                dmc.List([dmc.ListItem(note) for note in report.notes], size="sm"),
                link(
                    "Consultar datos y definiciones en JSON",
                    f"/api/v1/indicators?{urlencode(params)}",
                    target="_blank",
                    anchorProps={"rel": "noopener noreferrer"},
                    mt="md",
                    display="block",
                ),
                simple_table(
                    ["SLA", "Área", "Umbral propuesto"],
                    [[f"{sla.id} · {sla.name}", sla.audience, sla.threshold] for sla in SLAS],
                    caption="Propuestas de SLA; no son metas aprobadas ni cumplimiento medido",
                ),
                [
                    html.Section([dmc.Title(sla.name, order=3, size="h6"), sla_card(sla)])
                    for sla in SLAS
                ],
            ),
            mt="md",
        ),
    ]
    return [
        heading("Indicadores"),
        hint(
            f"{cutoff}{registry_note}",
            role="status",
        ),
        kpi_board(report, hub, context),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        *[
                            dmc.TabsTab(QUESTION_LABELS[result.sheet.id], value=result.sheet.id)
                            for result in report.indicators
                        ],
                        dmc.TabsTab("SLA propuestos", value="method"),
                    ],
                    **{"aria-label": "Pregunta de análisis"},
                ),
                *[
                    dmc.TabsPanel(
                        indicator_block(result, hub, report, context),
                        value=result.sheet.id,
                        pt="lg",
                    )
                    for result in report.indicators
                ],
                dmc.TabsPanel(method, value="method", pt="lg"),
            ],
            id="indicator-question",
            value=selected,
            keepMounted=False,
            persistence=f"indicators-{hub.mode}",
            persistence_type="memory",
            className="analysis-tabs indicator-tabs",
        ),
    ]
