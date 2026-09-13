"""Decision summaries over the selected, bounded request population."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape

from dash import dcc

from app.dashboard.analytics import operations_for, readable
from app.dashboard.context import QueryContext
from app.dashboard.theme import LINE, figure, state_color, state_label_color
from app.models.hub import HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview
from app.services.evidence import matching_current_movements as current_movements
from app.services.hub import BUSINESS_TIMEZONE

DAY_MS = 86_400_000
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


@dataclass(frozen=True)
class UsagePeriod:
    request: RequestRecord
    starts_on: date
    ends_on: date

    @property
    def calendar_days(self) -> int:
        """Inclusive calendar span for drawing, never machine utilization or delivery duration."""
        return (self.ends_on - self.starts_on).days + 1


@dataclass(frozen=True)
class ExcludedPeriod:
    request: RequestRecord
    reason: str


@dataclass(frozen=True)
class UsageTimeline:
    periods: tuple[UsagePeriod, ...]
    excluded: tuple[ExcludedPeriod, ...]


def matching_current_movements(
    hub: HubResponse, request: RequestRecord, workflow: WorkflowOverview | None
) -> list[MovementRecord]:
    """Use the same source identity rules as the HTTP and equipment projections."""
    if workflow is None or not workflow.available:
        return []
    return current_movements(hub, request, workflow.movements)


def has_confirmed_task(
    hub: HubResponse, request: RequestRecord, workflow: WorkflowOverview | None
) -> bool:
    """Only a sent movement with a recorded provider task ID confirms a task."""
    return any(
        movement.state == "sent" and bool(movement.job_id)
        for movement in matching_current_movements(hub, request, workflow)
    )


def requests_in_scope(
    hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None = None
) -> list[RequestRecord]:
    """The backend already applied search; display filters use the same request identities."""
    if context.mode != hub.mode or not readable(hub):
        return []
    if context.filter == "unassigned":
        return [request for request in hub.requests if not request.machinery_id]
    if context.filter == "unlinked":
        return [
            request for request in hub.requests if not has_confirmed_task(hub, request, workflow)
        ]
    return [operation.request for operation in operations_for(hub, context.filter)]


def request_states(requests: list[RequestRecord]) -> list[tuple[str, int]]:
    """Keep original provider categories, including unknown spellings, instead of merging them."""
    return sorted(Counter(request.status for request in requests).items(), key=lambda row: row[0])


def _calendar_boundary(value: str | None) -> tuple[date, datetime | None] | None:
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            parsed = date.fromisoformat(value)
            return (parsed, None) if parsed.isoformat() == value else None
        # Reject basic dates, week dates and naive timestamps rather than guessing a timezone.
        if len(value) < 19 or value[10] not in {"T", " "}:
            return None
        if date.fromisoformat(value[:10]).isoformat() != value[:10]:
            return None
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            return None
        return instant.astimezone(BUSINESS_TIMEZONE).date(), instant
    except (ValueError, OverflowError):
        return None


def usage_timeline(requests: list[RequestRecord]) -> UsageTimeline:
    """Project source periods to calendar days without using the current clock or snapshot date."""
    periods: list[UsagePeriod] = []
    excluded: list[ExcludedPeriod] = []
    for request in requests:
        if not request.starts_on or not request.ends_on:
            excluded.append(ExcludedPeriod(request, "Inicio o fin sin informar"))
            continue
        start = _calendar_boundary(request.starts_on)
        end = _calendar_boundary(request.ends_on)
        if start is None or end is None:
            excluded.append(ExcludedPeriod(request, "Fecha no válida o con hora sin zona"))
            continue
        if end[0] < start[0] or (start[1] and end[1] and end[1] < start[1]):
            excluded.append(ExcludedPeriod(request, "Fin anterior al inicio"))
            continue
        # Plotly's inclusive calendar rectangle needs a finite following day.
        if end[0] == date.max:
            excluded.append(ExcludedPeriod(request, "Fecha fuera del rango representable"))
            continue
        periods.append(UsagePeriod(request, start[0], end[0]))
    periods.sort(key=lambda period: (period.starts_on, period.ends_on, period.request.id))
    return UsageTimeline(tuple(periods), tuple(excluded))


def short_date(day: date, *, year: bool = False) -> str:
    value = f"{day.day} {MONTHS[day.month - 1]}"
    return f"{value} {day.year}" if year else value


def graph(identifier: str, chart):
    """Plotly figure on the `econ` template; the height travels with the figure."""
    return dcc.Graph(
        id=identifier,
        figure=chart,
        responsive=True,
        config={"displayModeBar": False, "responsive": True, "locale": "es"},
        style={"height": f"{chart.layout.height}px"},
        className="econ-plot",
    )


def request_axis_label(request: RequestRecord) -> str:
    status = {
        "APROBADA": "Aprobada",
        "APPROVED": "Aprobada",
        "PENDIENTE": "Pendiente",
        "PENDING": "Pendiente",
    }.get(request.status, request.status or "Sin estado informado")
    project = request.project_name or "Proyecto sin nombre"
    if len(project) > 18:
        project = project[:15].rstrip() + "…"
    unit = request.machinery_asset_number or (
        "Unidad asignada" if request.machinery_id else "Sin unidad"
    )
    return f"<b>{escape(project.split(' - ')[0])}</b><br>{escape(unit)}<br>{escape(status)}"


def states_figure(states: list[tuple[str, int]]):
    chart = figure(max(190, len(states) * 44 + 84))
    chart.update_layout(margin={"l": 8, "r": 48, "t": 8, "b": 46})
    if not states:
        return chart
    labels = [escape(state) if state.strip() else "Sin estado informado" for state, _ in states]
    # Categories are source values, even when their display labels coincide.
    identifiers = [f"state-{index}" for index in range(len(states))]
    chart.add_bar(
        x=[count for _, count in states],
        y=identifiers,
        customdata=labels,
        orientation="h",
        width=0.42,
        marker_color=[state_color(state) for state, _ in states],
        text=[str(count) for _, count in states],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{customdata}<br>%{x} solicitud(es)<extra></extra>",
    )
    chart.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=identifiers,
        tickmode="array",
        tickvals=identifiers,
        ticktext=labels,
    )
    chart.update_xaxes(
        title_text="Solicitudes de esta lectura",
        title_standoff=12,
        dtick=1,
        ticks="outside",
        ticklen=5,
        tickcolor=LINE,
        rangemode="tozero",
        range=[0, max(count for _, count in states) * 1.3],
    )
    return chart


def usage_figure(timeline: UsageTimeline):
    periods = timeline.periods
    chart = figure(max(200, len(periods) * 54 + 96))
    chart.update_layout(
        uniformtext={"minsize": 11, "mode": "hide"},
        margin={"l": 8, "r": 28, "t": 8, "b": 50},
    )
    if not periods:
        return chart
    identifiers = [period.request.id for period in periods]
    chart.add_bar(
        base=[period.starts_on.isoformat() for period in periods],
        x=[period.calendar_days * DAY_MS for period in periods],
        y=identifiers,
        orientation="h",
        width=0.44,
        marker_color=[state_color(period.request.status) for period in periods],
        text=[
            f"{short_date(period.starts_on)} – {short_date(period.ends_on)}" for period in periods
        ],
        textposition="inside",
        insidetextanchor="middle",
        insidetextfont={
            "color": [state_label_color(period.request.status) for period in periods],
            "size": 12,
        },
        customdata=[
            [
                escape(period.request.provenance.source_id or period.request.id),
                escape(period.request.project_name or period.request.project_id or "Sin proyecto"),
                short_date(period.starts_on, year=True),
                short_date(period.ends_on, year=True),
                escape(period.request.status),
                escape(period.request.machinery_type or "Sin tipo"),
            ]
            for period in periods
        ],
        hovertemplate=(
            "%{customdata[1]} · %{customdata[5]}<br>Solicitud %{customdata[0]}<br>"
            "Uso solicitado: %{customdata[2]} – %{customdata[3]}<br>"
            "Estado: %{customdata[4]}<extra></extra>"
        ),
    )
    start = min(period.starts_on for period in periods)
    end = max(period.ends_on for period in periods) + timedelta(days=1)
    span = (end - start).days
    step = max(1, (span + 3) // 4)
    ticks = [start + timedelta(days=offset) for offset in range(0, span + 1, step)]
    chart.update_xaxes(
        type="date",
        range=[start.isoformat(), end.isoformat()],
        tickmode="array",
        tickvals=[tick.isoformat() for tick in ticks],
        ticktext=[short_date(tick, year=start.year != end.year) for tick in ticks],
        ticks="outside",
        ticklen=5,
        tickcolor=LINE,
        title_standoff=12,
        title_text=(
            f"Período de uso solicitado · {start.year}"
            if start.year == end.year
            else "Período de uso solicitado"
        ),
    )
    chart.update_yaxes(
        categoryorder="array",
        categoryarray=identifiers,
        autorange="reversed",
        tickmode="array",
        tickvals=identifiers,
        ticktext=[request_axis_label(period.request) for period in periods],
    )
    return chart
