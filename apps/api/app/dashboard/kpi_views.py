"""Executive KPI band for /indicadores; aggregation happens only in the presentation layer.

`compute_indicators` stays the single source of every rule. The band counts rows of the
populations that report already published, or copies the value of one row, and never
recomputes a date, queries a provider or reads the clock: the only «now» is
`HubResponse.generated_at`, and it arrives inside `IndicatorsReport`.

Three shapes cover every figure:

- a count of rows of one published population, when belonging to it is a fact of the row
  (a `variant`, a `without_project` flag) and not a measurement that needs a cut-off;
- one value copied from a single row (an elapsed time the service already computed);
- the published reason, when the indicator is not evaluable or nothing could be checked.

An absence is never a zero: a missing cut-off, a fixture without tasks or an incomplete
registry give «No evaluable» or «No verificable» with the reason, and an empty population
gives «Sin casos» with its coverage. No mean, median, percentile or percentage appears;
the cohort is two requests and five units in fixture (docs/indicadores-calculables.md and
docs/kpis-tablero.md).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from dash import html

from app.dashboard.analytics import equipment_label, instant
from app.dashboard.components import data_strip, hint, icon, link, section
from app.dashboard.context import QueryContext
from app.dashboard.theme import state_color
from app.models.hub import HubResponse
from app.models.indicators import IndicatorResult, IndicatorRow, IndicatorsReport
from app.services.indicators import SHEETS

NUMBERS = {identifier: f"I{index}" for index, identifier in enumerate(SHEETS, start=1)}
# `_result` in app/services/indicators.py opens the reason of an empty population with this.
EMPTY_POPULATION = "sin casos evaluables"
NO_CASES = "Sin casos"
NOT_EVALUABLE = "No evaluable"
NOT_VERIFIABLE = "No verificable"
MAX_LINKS = 3
MODES = {"fixture": "muestras proporcionadas", "live": "sandbox actual sintético"}
REGISTRY_WORDS = {
    "not_queried": "No consultado",
    "available": "Disponible",
    "partial": "Parcial",
    "disabled": "Deshabilitado",
    "error": "Con error",
}
GRAIN_HREF = {
    "request": lambda context, row: context.request_href(row.subject_id),
    "equipment": lambda context, row: context.equipment_href(row.subject_id),
}


# ----- shared formatting -------------------------------------------------------------------


def duration_text(seconds: float) -> str:
    """An elapsed time in words; the source value is never rounded into a different unit."""
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


def count_text(number: int, singular: str, plural: str | None = None) -> str:
    return f"{number} {singular if number == 1 else plural or singular + 's'}"


def reason_text(reason: str) -> str:
    """The reason the service published, read as a sentence; the wording is never rewritten."""
    text = reason.removeprefix("no evaluable en fixture: ")
    if text != reason:
        text = f"en fixture, {text}"
    text = text.removeprefix("no evaluable: ")
    return text[:1].upper() + text[1:]


def of_total(returned: int, total: int | None) -> str:
    return f"{returned} de {total}" if total is not None else f"{returned} (total no informado)"


def subject_href(context: QueryContext, grain: str, row: IndicatorRow) -> str:
    """The detail page of the subject of a row; movements keep their registry identifier."""
    builder = GRAIN_HREF.get(grain)
    if builder is not None:
        return builder(context, row)
    return context.movement_href(row.source_id or row.subject_id.removeprefix("econ:movement:"))


def project_code(name: str | None, identifier: str | None) -> str:
    """The project code as the source writes it («PROY-014 - Obra» → «PROY-014»)."""
    if name:
        return name.split(" - ", 1)[0].strip() or name
    return identifier or "proyecto sin identificar"


def subject_name(hub: HubResponse, grain: str, row: IndicatorRow) -> str:
    """A short label a logistics lead recognises; identifiers stay in the rows table."""
    if grain == "request":
        request = next((item for item in hub.requests if item.id == row.subject_id), None)
        if request is not None:
            project = project_code(request.project_name, request.project_id)
            return f"{request.machinery_type or 'Maquinaria'} · {project}"
    if grain == "equipment":
        unit = next((item for item in hub.equipment if item.id == row.subject_id), None)
        if unit is not None:
            return equipment_label(unit)
    return row.label or row.source_id or row.subject_id


# ----- one figure --------------------------------------------------------------------------


@dataclass(frozen=True)
class Kpi:
    """One figure of the band with the coverage and the rows that hold it up."""

    key: str
    label: str
    figure: str
    coverage: str
    source: str
    word: bool = False
    rows: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    remaining: int = 0
    # (text, state family of theme.py) when the source publishes a real state.
    state: tuple[str, str] | None = None


def _matching(result: IndicatorResult, predicate: Callable[[IndicatorRow], bool]):
    return [row for row in result.rows if predicate(row)]


def _counted(
    matched: Sequence[IndicatorRow], unchecked: Sequence[IndicatorRow]
) -> tuple[str, bool]:
    """A count, «no verificable» when a row could not be checked, «sin casos» when none matched."""
    if matched:
        return str(len(matched)), False
    if unchecked:
        return NOT_VERIFIABLE, True
    return NO_CASES, True


def _unavailable(result: IndicatorResult) -> tuple[str, str] | None:
    """Figure and published reason when the indicator publishes no countable population."""
    if result.status != "not_evaluable":
        return None
    reason = result.reason or "sin motivo publicado"
    if reason.startswith(EMPTY_POPULATION):
        return NO_CASES, reason[len(EMPTY_POPULATION) :].lstrip(": ")
    return NOT_EVALUABLE, reason


def _row_links(
    hub: HubResponse,
    context: QueryContext,
    grain: str,
    rows: Sequence[IndicatorRow],
) -> tuple[tuple[tuple[str, str], ...], int]:
    shown = rows[:MAX_LINKS]
    links = tuple(
        (subject_name(hub, grain, row), subject_href(context, grain, row)) for row in shown
    )
    return links, len(rows) - len(shown)


def _source(result: IndicatorResult, detail: str | None = None) -> str:
    name = f"{NUMBERS[result.sheet.id]} · {result.sheet.name}"
    return f"{name} ({detail})" if detail else name


def _kpi(
    key: str,
    label: str,
    result: IndicatorResult,
    hub: HubResponse,
    context: QueryContext,
    *,
    matched: Sequence[IndicatorRow],
    figure: str,
    word: bool,
    coverage: str,
    detail: str | None = None,
    state: tuple[str, str] | None = None,
) -> Kpi:
    """A figure with the rows behind it; a blocked figure still points at the population."""
    linkable = list(matched) or (list(result.rows) if word and figure != NO_CASES else [])
    links, remaining = _row_links(hub, context, result.sheet.grain, linkable)
    return Kpi(
        key=key,
        label=label,
        figure=figure,
        coverage=coverage,
        source=_source(result, detail),
        word=word,
        rows=links,
        remaining=remaining,
        state=state,
    )


def _requests_read(report: IndicatorsReport) -> str:
    returned = of_total(report.scope.requests_returned, report.scope.requests_total)
    return f"{returned} solicitudes leídas"


def _equipment_read(report: IndicatorsReport) -> str:
    returned = of_total(report.scope.equipment_returned, report.scope.equipment_total)
    return f"{returned} unidades leídas"


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _age_note(result: IndicatorResult, rows: Sequence[IndicatorRow]) -> str | None:
    """The age of the oldest row, or why no age can be computed; never an average."""
    measured = [row for row in rows if _number(row.values.get("hours")) is not None]
    if measured:
        oldest = max(measured, key=lambda row: _number(row.values["hours"]) or 0.0)
        hours = _number(oldest.values["hours"]) or 0.0
        return f"la fila más antigua lleva {duration_text(hours * 3600)}"
    if not rows:
        return None
    blocked = _unavailable(result)
    return f"sin antigüedad: {blocked[1]}" if blocked and blocked[0] != NO_CASES else None


# ----- the figures of each area --------------------------------------------------------------


def _open_requests(
    result: IndicatorResult,
    hub: HubResponse,
    context: QueryContext,
    report: IndicatorsReport,
    *,
    variant: str,
    key: str,
    label: str,
    population: str,
) -> Kpi:
    """Membership is a fact of the row (`variant`); only its age needs an observation cut."""
    matched = _matching(result, lambda row: row.values.get("variant") == variant)
    figure, word = _counted(matched, ())
    coverage = " · ".join(
        part for part in (population, _requests_read(report), _age_note(result, matched)) if part
    )
    return _kpi(
        key,
        label,
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
        detail=f"variante {variant.replace('_', ' ')}",
    )


def _without_sent_task(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = _matching(result, lambda row: row.values.get("sent_task") is False)
        unchecked = [row for row in result.rows if row.status != "evaluable"]
        figure, word = _counted(matched, unchecked)
        approved = count_text(len(result.rows), "aprobada", "aprobadas")
        coverage = f"{approved} con unidad en la lectura"
        if unchecked:
            coverage += f" · {len(unchecked)} sin verificar: el registro no está completo"
    return _kpi(
        "sin-tarea",
        "Aprobadas con unidad sin tarea enviada",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _occupied_without_project(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = _matching(result, lambda row: row.values.get("without_project") is True)
        unchecked = _matching(result, lambda row: row.values.get("without_project") is None)
        figure, word = _counted(matched, unchecked)
        occupied = count_text(len(result.rows), "unidad", "unidades")
        coverage = f"{occupied} OCUPADA · {_equipment_read(report)}"
    return _kpi(
        "ocupada-sin-proyecto",
        "Unidades OCUPADA sin proyecto",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _assignment_ended(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
        if result.rows:
            coverage += f" · {count_text(len(result.rows), 'unidad', 'unidades')} con project_id"
    else:
        matched = _matching(result, lambda row: row.values.get("ended") is True)
        unchecked = [row for row in result.rows if row.status != "evaluable"]
        figure, word = _counted(matched, unchecked)
        assigned = count_text(len(result.rows), "unidad", "unidades")
        coverage = f"{assigned} con project_id · corte {instant(report.data_as_of)}"
    return _kpi(
        "asignacion-vencida",
        "Asignaciones vencidas al corte",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _approval_measured(result, hub, context, report) -> Kpi:
    matched = [row for row in result.rows if row.status == "evaluable"]
    figure, word = _counted(matched, ())
    pending = len(result.rows) - len(matched)
    parts = [_requests_read(report)]
    if pending:
        parts.append(f"{pending} sin instantes comparables")
    longest = max((_number(row.values.get("seconds")) or 0.0 for row in matched), default=None)
    if longest is not None:
        label = "tiempo medido" if len(matched) == 1 else "el mayor tiempo medido"
        parts.append(f"{label}: {duration_text(longest)}")
    return _kpi(
        "aprobacion-medida",
        "Aprobaciones con tiempo medido",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=" · ".join(parts),
    )


def _without_receipt(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = [
            row
            for row in result.rows
            if row.status == "evaluable" and row.values.get("receipt_declared") is False
        ]
        unchecked = [row for row in result.rows if row.status != "evaluable"]
        figure, word = _counted(matched, unchecked)
        completed = count_text(len(result.rows), "tarea completada", "tareas completadas")
        coverage = f"{completed} en el registro"
        if unchecked:
            coverage += f" · {len(unchecked)} sin instante verificable"
    return _kpi(
        "sin-recepcion",
        "Tareas completadas sin recepción",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _active_failures(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = list(result.rows)
        figure, word = _counted(matched, ())
        coverage = f"{_equipment_read(report)} · la edad de la falla no se lee"
    return _kpi(
        "falla-activa",
        "Unidades con falla activa",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _stopped_failures(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    state = None
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = _matching(result, lambda row: row.values.get("active_failure_is_paro") is True)
        unchecked = _matching(result, lambda row: row.values.get("active_failure_is_paro") is None)
        figure, word = _counted(matched, unchecked)
        coverage = f"{count_text(len(result.rows), 'falla activa', 'fallas activas')} leídas"
        if unchecked:
            coverage += f" · {len(unchecked)} sin informar el paro"
        if matched:
            state = ("Paro declarado en Prisma", "issue")
    return _kpi(
        "falla-con-paro",
        "Fallas con decisión de paro",
        result,
        hub,
        context,
        matched=matched,
        figure=figure,
        word=word,
        coverage=coverage,
        detail="active_failure_is_paro",
        state=state,
    )


def _evidence_age(result, hub, context, report) -> Kpi:
    blocked = _unavailable(result)
    matched: list[IndicatorRow] = []
    if blocked is not None:
        figure, word, coverage = blocked[0], True, reason_text(blocked[1])
    else:
        matched = list(result.rows)
        hours = _number(matched[0].values.get("evidence_age_hours")) if matched else None
        figure, word = (
            (duration_text(hours * 3600), False) if hours is not None else (NOT_EVALUABLE, True)
        )
        sent = count_text(len(matched), "traslado enviado", "traslados enviados")
        coverage = (
            f"{sent} en el registro; última lectura "
            f"{instant(report.last_registry_read_at)}; consulta {instant(report.generated_at)}"
        )
    # `evidence_age_hours` is the same value on every row (it belongs to the registry read,
    # not to one movement), so no row is linked as if it were the one holding the figure up.
    return _kpi(
        "evidencia",
        "Antigüedad de la evidencia",
        result,
        hub,
        context,
        matched=[],
        figure=figure,
        word=word,
        coverage=coverage,
    )


def _scope_kpis(report: IndicatorsReport) -> list[Kpi]:
    """Coverage of the reading itself: what was read and what the registry answered."""
    search = f" · búsqueda «{report.scope.search}»" if report.scope.search else ""
    bounded = "lectura acotada" if report.scope.bounded else "lectura sin acotar"
    coverage = report.ledger_coverage
    if report.ledger_available and coverage is not None:
        registry_figure, registry_word = f"{coverage.displayed} de {coverage.total}", False
        registry_note = (
            "Registro completo en esta página"
            if coverage.is_complete
            else "Registro parcial: una ausencia de tarea no es verificable"
        )
    elif report.ledger_available:
        registry_figure, registry_word = "Disponible", True
        registry_note = "Registro consultado; esta lectura no publica su cobertura por página"
    else:
        registry_figure, registry_word = REGISTRY_WORDS[report.registry.status], True
        registry_note = report.registry.message
    return [
        Kpi(
            key="unidades-leidas",
            label="Unidades leídas",
            figure=of_total(report.scope.equipment_returned, report.scope.equipment_total),
            coverage=f"Población de I4, I5 e I7{search}",
            source=f"HubResponse.scope · {bounded}; los conteos describen estas filas, no la flota",
        ),
        Kpi(
            key="solicitudes-leidas",
            label="Solicitudes leídas",
            figure=of_total(report.scope.requests_returned, report.scope.requests_total),
            coverage=f"Población de I1, I2 e I3{search}",
            source=f"HubResponse.scope · {bounded}",
        ),
        Kpi(
            key="registro-movimientos",
            label="Registro de movimientos",
            figure=registry_figure,
            word=registry_word,
            coverage=registry_note,
            source="HubResponse.operation_evidence · WorkflowOverview",
            state=("Lectura del registro con error", "issue")
            if report.registry.status == "error"
            else None,
        ),
    ]


def build_kpis(
    report: IndicatorsReport, hub: HubResponse, context: QueryContext
) -> list[tuple[str, list[Kpi]]]:
    """The band grouped by the area that decides, as the page already orders its questions."""
    results = {result.sheet.id: result for result in report.indicators}
    open_requests = results["open_request_age"]
    failures = results["active_failure_registered"]
    return [
        (
            "Logística",
            [
                _open_requests(
                    open_requests,
                    hub,
                    context,
                    report,
                    variant="aprobada_sin_unidad",
                    key="aprobada-sin-unidad",
                    label="Aprobadas sin unidad asignada",
                    population="APROBADA sin maquinaria_id",
                ),
                _without_sent_task(
                    results["approved_with_unit_without_sent_task"], hub, context, report
                ),
                _occupied_without_project(
                    results["occupied_without_project"], hub, context, report
                ),
                _assignment_ended(results["assignment_ended"], hub, context, report),
            ],
        ),
        (
            "Proyectos",
            [
                _open_requests(
                    open_requests,
                    hub,
                    context,
                    report,
                    variant="pendiente",
                    key="pendiente-de-decision",
                    label="Solicitudes pendientes de decisión",
                    population="PENDIENTE sin decisión registrada",
                ),
                _approval_measured(results["approval_time"], hub, context, report),
                _without_receipt(results["completed_task_without_receipt"], hub, context, report),
            ],
        ),
        (
            "Mantenimiento",
            [
                _active_failures(failures, hub, context, report),
                _stopped_failures(failures, hub, context, report),
            ],
        ),
        (
            "Información",
            [_evidence_age(results["evidence_age"], hub, context, report), *_scope_kpis(report)],
        ),
    ]


# ----- rendering ---------------------------------------------------------------------------


def _qualifier(kpi: Kpi):
    lines = [html.Span(kpi.coverage, className="kpi-line")]
    if kpi.state is not None:
        label, family = kpi.state
        # Same rule as components.state_text: the icon carries the color, the text the meaning.
        lines.append(
            html.Span(
                [
                    html.Span(icon("alert-triangle", 14), style={"color": state_color(family)}),
                    label,
                ],
                className="kpi-line kpi-state",
            )
        )
    trail: list = [kpi.source]
    for label, href in kpi.rows:
        trail.extend([" · ", link(label, href, size="xs")])
    if kpi.remaining:
        more = count_text(kpi.remaining, "fila", "filas")
        trail.append(f" · {more} más en la tabla del indicador")
    lines.append(html.Span(trail, className="kpi-line kpi-source"))
    return lines


def _cell(kpi: Kpi):
    figure = html.Span(kpi.figure, className="kpi-word") if kpi.word else kpi.figure
    return (kpi.label, figure, _qualifier(kpi))


def board_note(report: IndicatorsReport) -> str:
    cut = (
        f"Corte de la lectura: {instant(report.data_as_of)}."
        if report.data_as_of is not None
        else "Sin corte de observación: las antigüedades al corte no se evalúan."
    )
    return (
        f"Conteos de filas de esta lectura ({MODES[report.mode]}). {cut} Sin promedios, "
        "medianas ni porcentajes: la cohorte es pequeña y cada cifra describe filas leídas. "
        "Un indicador sin datos publica su motivo; la ausencia no es cero. Cada cifra enlaza "
        "con las filas que la sustentan y con el indicador que la define."
    )


def kpi_board(report: IndicatorsReport, hub: HubResponse, context: QueryContext):
    """Band at the top of /indicadores: what each area has to decide with this reading."""
    groups = [
        html.Div(
            [
                html.H3(area, className="eyebrow kpi-area"),
                data_strip([_cell(kpi) for kpi in kpis]),
            ],
            className="kpi-group",
        )
        for area, kpis in build_kpis(report, hub, context)
    ]
    return section(
        "Tablero de indicadores",
        hint(board_note(report)),
        *groups,
        className="page-section kpi-board",
    )
