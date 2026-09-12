"""Decision summaries over the selected, bounded request population."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape

import plotly.graph_objects as go

from app.dashboard.analytics import BLUE, GRID, MUTED, operations_for, readable
from app.dashboard.context import QueryContext
from app.models.hub import HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview
from app.services.hub import BUSINESS_TIMEZONE

DAY_MS = 86_400_000
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


@dataclass(frozen=True)
class RequestCounts:
    total: int | None
    unassigned: int | None
    without_confirmed_task: int | None


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
    """Match the current source request and assignment; historical movements remain in detail."""
    evidence = request.provenance
    if (
        workflow is None
        or not workflow.available
        or evidence.source != "nexus"
        or not evidence.source_id
        or not request.project_id
        or not request.machinery_id
    ):
        return []
    matches: list[MovementRecord] = []
    current_request = request.model_dump(mode="json")
    for movement in workflow.movements:
        stored_request = movement.source_request
        stored_equipment = movement.source_equipment or {}
        stored_evidence = stored_request.get("provenance") or {}
        machine_evidence = stored_equipment.get("provenance") or {}
        if not isinstance(stored_evidence, dict) or not isinstance(machine_evidence, dict):
            continue
        if (
            movement.mode == hub.mode
            and movement.environment == evidence.environment
            and movement.request_source_id == evidence.source_id
            and movement.project_source_id == request.project_id
            and stored_request.get("id") == request.id
            and stored_request.get("machinery_id") == request.machinery_id
            and all(
                stored_request.get(field) == current_request.get(field)
                for field in ("starts_on", "ends_on", "approved_at")
            )
            and stored_equipment.get("id") == request.machinery_id
            and movement.machinery_source_id == machine_evidence.get("source_id")
            and all(
                source.get("source") == evidence.source
                and source.get("environment") == evidence.environment
                and source.get("evidence_kind") == evidence.evidence_kind
                and source.get("is_synthetic") == evidence.is_synthetic
                for source in (stored_evidence, machine_evidence)
            )
            and stored_evidence.get("source_id") == evidence.source_id
        ):
            matches.append(movement)
    return matches


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


def request_counts(
    hub: HubResponse, context: QueryContext, workflow: WorkflowOverview | None = None
) -> RequestCounts:
    if context.mode != hub.mode or not readable(hub):
        return RequestCounts(None, None, None)
    requests = requests_in_scope(hub, context, workflow)
    return RequestCounts(
        total=len(requests),
        unassigned=sum(not request.machinery_id for request in requests),
        without_confirmed_task=(
            sum(not has_confirmed_task(hub, request, workflow) for request in requests)
            if workflow is not None and workflow.available
            else None
        ),
    )


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


def request_axis_label(request: RequestRecord) -> str:
    status = {
        "APROBADA": "Aprobada",
        "APPROVED": "Aprobada",
        "PENDIENTE": "Pendiente",
        "PENDING": "Pendiente",
    }.get(request.status, request.status or "Sin estado informado")
    return f"{escape(request.machinery_type or 'Solicitud')}<br>{escape(status)}"


def _figure(height: int = 290) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="plotly_white",
        height=height,
        font={"family": "Inter, sans-serif", "size": 12, "color": MUTED},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 24, "t": 12, "b": 26},
        showlegend=False,
        dragmode=False,
        hoverlabel={"bgcolor": "white", "font_size": 12},
    )
    figure.update_xaxes(fixedrange=True, zeroline=False, gridcolor=GRID, automargin=True)
    figure.update_yaxes(fixedrange=True, zeroline=False, showgrid=False, automargin=True)
    return figure


def states_figure(states: list[tuple[str, int]]) -> go.Figure:
    figure = _figure(max(290, len(states) * 44 + 60))
    if not states:
        return figure
    labels = [escape(state) if state.strip() else "Sin estado informado" for state, _ in states]
    figure.add_bar(
        x=[count for _, count in states],
        y=labels,
        orientation="h",
        width=0.42,
        marker_color=BLUE,
        text=[str(count) for _, count in states],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x} solicitud(es)<extra></extra>",
    )
    figure.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=labels)
    figure.update_xaxes(
        title_text="Solicitudes",
        dtick=1,
        rangemode="tozero",
        range=[0, max(c for _, c in states) * 1.3],
    )
    return figure


def usage_figure(timeline: UsageTimeline) -> go.Figure:
    periods = timeline.periods
    figure = _figure(max(290, len(periods) * 46 + 70))
    if not periods:
        return figure
    identifiers = [period.request.id for period in periods]
    figure.add_bar(
        base=[period.starts_on.isoformat() for period in periods],
        x=[period.calendar_days * DAY_MS for period in periods],
        y=identifiers,
        orientation="h",
        width=0.4,
        marker_color=BLUE,
        customdata=[
            [
                escape(period.request.provenance.source_id or period.request.id),
                escape(period.request.project_name or period.request.project_id or "Sin proyecto"),
                short_date(period.starts_on, year=True),
                short_date(period.ends_on, year=True),
                escape(period.request.status),
            ]
            for period in periods
        ],
        hovertemplate=(
            "%{customdata[1]}<br>Solicitud %{customdata[0]}<br>"
            "Uso solicitado: %{customdata[2]} – %{customdata[3]}<br>"
            "Estado: %{customdata[4]}<extra></extra>"
        ),
    )
    start = min(period.starts_on for period in periods)
    end = max(period.ends_on for period in periods) + timedelta(days=1)
    span = (end - start).days
    step = max(1, (span + 5) // 6)
    ticks = [start + timedelta(days=offset) for offset in range(0, span + 1, step)]
    figure.update_xaxes(
        type="date",
        range=[start.isoformat(), end.isoformat()],
        tickmode="array",
        tickvals=[tick.isoformat() for tick in ticks],
        ticktext=[short_date(tick, year=start.year != end.year) for tick in ticks],
        title_text=f"Uso solicitado · {start.year}" if start.year == end.year else "Uso solicitado",
    )
    figure.update_yaxes(
        categoryorder="array",
        categoryarray=identifiers,
        autorange="reversed",
        tickmode="array",
        tickvals=identifiers,
        ticktext=[request_axis_label(period.request) for period in periods],
    )
    return figure
