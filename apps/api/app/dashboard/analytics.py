"""Presentation aggregates over one bounded hub read; no duplicated alert rules."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

import plotly.graph_objects as go

from app.models.hub import EquipmentRecord, HubResponse, RequestRecord, TransferRecord
from app.services.hub import BUSINESS_TIMEZONE, _plan_date

BLUE = "#144f81"
MUTED = "#66717d"
GRID = "#e9edf0"
PRIORITY = {"critical": 0, "warning": 1, "info": 2}
REQUEST_CODES = {
    "pending_started": "pending_request_started",
    "approved_unassigned": "approved_without_equipment",
}


def readable(hub: HubResponse) -> bool:
    return any(
        source.id == "nexus" and source.status in {"fixture", "connected", "partial"}
        for source in hub.sources
    )


def equipment_label(item: EquipmentRecord) -> str:
    return item.asset_number or item.code or item.name


def instant(value: datetime | None) -> str:
    return (
        value.astimezone(BUSINESS_TIMEZONE).strftime("%d/%m/%Y · %H:%M") if value else "Sin fecha"
    )


def requests_for(hub: HubResponse, filter: str):
    code = REQUEST_CODES.get(filter)
    if code is None:
        return hub.requests
    identifiers = {alert.request_id for alert in hub.alerts if alert.code == code}
    return [request for request in hub.requests if request.id in identifiers]


@dataclass(frozen=True)
class RequestOperation:
    """Display one request without filling gaps in its source relationships."""

    request: RequestRecord
    equipment: EquipmentRecord | None
    transfers: tuple[TransferRecord, ...]

    @property
    def missing(self) -> list[str]:
        missing = []
        if not self.request.project_id:
            missing.append("ID de proyecto")
        if not self.request.starts_on:
            missing.append("Inicio solicitado")
        if not self.request.ends_on:
            missing.append("Fin solicitado")
        if not self.request.machinery_id:
            missing.append("Unidad asignada")
        elif self.equipment is None:
            missing.append("Registro de la unidad asignada")
        if not self.transfers:
            missing.append("Traslado vinculado")
        elif self.equipment and self.equipment.relation_status != "confirmed":
            missing.append("Validación del vínculo con Startrack")
        for task in self.transfers:
            if not task.destination_project_id:
                missing.append("ID del destino del traslado")
            elif task.destination_project_id != self.request.project_id:
                missing.append("Conciliación del destino del traslado")
        # The read contract has no arrival event or accepted receipt evidence.
        # A completed task, location label or geofence is not either of these records.
        missing.extend(["Evidencia de llegada", "Recepción física"])
        return list(dict.fromkeys(missing))


def request_operation(hub: HubResponse, request: RequestRecord) -> RequestOperation:
    item = next((item for item in hub.equipment if item.id == request.machinery_id), None)
    tasks = tuple(task for task in item.transfers if task.request_id == request.id) if item else ()
    return RequestOperation(request, item, tasks)


def operations_for(hub: HubResponse, filter: str = "all") -> list[RequestOperation]:
    operations = [request_operation(hub, item) for item in requests_for(hub, filter)]
    if filter == "active_failures":
        return [
            item for item in operations if item.equipment and item.equipment.maintenance_failure_id
        ]
    if filter == "unlinked":
        return [
            item
            for item in operations
            if not item.transfers or item.equipment.relation_status != "confirmed"
        ]
    return operations


def exception_groups(hub: HubResponse) -> list[dict]:
    groups: dict[str, dict] = {}
    for alert in hub.alerts:
        key = alert.equipment_id or alert.request_id or alert.id
        group = groups.setdefault(
            key,
            {"id": key, "equipment_id": alert.equipment_id, "alerts": [], "owners": []},
        )
        group["alerts"].append(alert)
        if alert.owner not in group["owners"]:
            group["owners"].append(alert.owner)
    for group in groups.values():
        group["alerts"].sort(key=lambda alert: PRIORITY[alert.severity])
        group["severity"] = group["alerts"][0].severity
    return sorted(groups.values(), key=lambda group: (PRIORITY[group["severity"]], group["id"]))


def distribution(hub: HubResponse) -> list[tuple[str, int]] | None:
    if not readable(hub):
        return None
    counts = Counter(item.machinery_status for item in hub.equipment)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def calendar(hub: HubResponse) -> dict | None:
    if not readable(hub) or hub.data_as_of is None:
        return None
    cutoff = hub.data_as_of.astimezone(BUSINESS_TIMEZONE).date()
    days = {cutoff + timedelta(days=offset): 0 for offset in range(-6, 8)}
    undated = outside = 0
    for request in hub.requests:
        day = _plan_date(request.starts_on)
        if day is None:
            undated += 1
        elif day in days:
            days[day] += 1
        else:
            outside += 1
    return {"days": days, "cutoff": cutoff, "undated": undated, "outside": outside}


def _figure() -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12, "color": MUTED},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 0, "r": 22, "t": 20, "b": 10},
        height=270,
        showlegend=False,
        hoverlabel={"bgcolor": "white", "font_size": 13},
        dragmode=False,
    )
    figure.update_xaxes(fixedrange=True, zeroline=False, gridcolor=GRID)
    figure.update_yaxes(fixedrange=True, zeroline=False, gridcolor=GRID, automargin=True)
    return figure


def distribution_figure(data: list[tuple[str, int]]) -> go.Figure:
    figure = _figure()
    figure.add_bar(
        x=[count for _, count in data],
        y=[state for state, _ in data],
        orientation="h",
        marker_color=BLUE,
        width=0.45,
        text=[count for _, count in data],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x} equipo(s)<extra></extra>",
    )
    figure.update_layout(height=max(270, len(data) * 40 + 45))
    figure.update_yaxes(autorange="reversed", showgrid=False)
    figure.update_xaxes(dtick=1, rangemode="tozero", range=[0, max(c for _, c in data) * 1.2])
    return figure


def calendar_figure(data: dict) -> go.Figure:
    figure = _figure()
    days = list(data["days"])
    counts = list(data["days"].values())
    figure.add_bar(
        x=[day.isoformat() for day in days],
        y=counts,
        marker_color=BLUE,
        text=[str(count) if count else "" for count in counts],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x|%d/%m/%Y}: %{y} solicitud(es)<extra></extra>",
    )
    figure.add_shape(
        type="line",
        x0=data["cutoff"].isoformat(),
        x1=data["cutoff"].isoformat(),
        y0=0,
        y1=1,
        yref="paper",
        line={"color": "#8c959e", "width": 1, "dash": "dot"},
    )
    figure.add_annotation(
        x=data["cutoff"].isoformat(),
        y=1.08,
        yref="paper",
        text="Corte",
        showarrow=False,
    )
    figure.update_xaxes(type="date", tickformat="%d/%m", showgrid=False, nticks=7)
    figure.update_yaxes(dtick=1, rangemode="tozero", range=[0, max(1, max(counts)) * 1.3])
    return figure
