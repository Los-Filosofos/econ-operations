"""Full-viewport operations graph built only from normalized hub and workflow evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from math import atan2, degrees, hypot
from typing import Any
from unicodedata import normalize

from dash import html

from app.dashboard.components import icon
from app.dashboard.theme import GRAPH_THEME
from app.models.hub import EquipmentRecord, HubResponse, Provenance, RequestRecord, TransferRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview

PLACE_RADIUS = 40
MACHINE_RADIUS = 24
MODE_LABELS = {"fixture": "Muestras proporcionadas", "live": "Sandbox actual · sintético"}
READABLE_SOURCE_STATES = {"fixture", "connected", "partial"}
ACTIVE_TRANSFER_ROLES = {"pending", "active", "in_progress", "in progress", "en curso"}
ACTIVE_TRANSFER_STATES = {"PENDIENTE", "PENDING", "ACTIVE", "IN_PROGRESS", "EN CURSO"}
MONTHS = ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC")
GRAPH_STYLE = {
    "--graph-bg": GRAPH_THEME["background"],
    "--graph-surface": GRAPH_THEME["panel"],
    "--graph-border": GRAPH_THEME["border"],
    "--graph-text": GRAPH_THEME["text_primary"],
    "--graph-muted": GRAPH_THEME["text_secondary"],
    "--graph-line": GRAPH_THEME["line"],
    "--graph-amber": GRAPH_THEME["warning"],
}


@dataclass
class GraphNode:
    key: str
    kind: str
    subtype: str
    entity_id: str
    source_id: str | None
    label: str
    status: str
    source: str
    age: str
    subtitle: str | None = None
    equipment: EquipmentRecord | None = None
    project_records: list[RequestRecord | EquipmentRecord | TransferRecord] = field(
        default_factory=list
    )
    x: float = 0
    y: float = 0
    place_keys: list[str] = field(default_factory=list)

    @property
    def radius(self) -> int:
        return PLACE_RADIUS if self.kind == "place" else MACHINE_RADIUS


@dataclass
class GraphEdge:
    key: str
    source: str
    target: str
    kind: str = "assignment"
    active: bool = False
    evidence: list[str] = field(default_factory=list)
    request_ids: list[str] = field(default_factory=list)
    transfer_ids: list[str] = field(default_factory=list)


@dataclass
class OperationsGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    width: int
    height: int


def _source(provenance: Provenance | None) -> str:
    if provenance is None:
        return "Identidad informada por una solicitud"
    nature = {
        "provided_sample": "Muestra proporcionada",
        "live_read": "Lectura del sandbox",
        "test_case": "Caso interno de prueba",
    }[provenance.evidence_kind]
    provider = "Prisma / Nexus" if provenance.source == "nexus" else "Startrack"
    return f"{provider} · {nature} · {provenance.environment}"


def _age(provenance: Provenance | None, generated_at: datetime) -> str:
    if provenance is None:
        return "Antigüedad no disponible"
    if provenance.observed_at is not None:
        observed = provenance.observed_at
        if observed.tzinfo is None:
            return "Observación sin zona horaria"
        elapsed = max(
            0, int((generated_at.astimezone(UTC) - observed.astimezone(UTC)).total_seconds())
        )
        if elapsed < 60:
            return "Observado hace menos de un minuto"
        if elapsed < 3600:
            return f"Observado hace {elapsed // 60} min"
        if elapsed < 86400:
            return f"Observado hace {elapsed // 3600} h"
        return f"Observado hace {elapsed // 86400} días"
    if provenance.observed_on is not None:
        return f"Fecha documental {provenance.observed_on:%d/%m/%Y}; hora no disponible"
    return "Sin fecha de observación"


def _short_project(name: str | None, source_id: str) -> str:
    if name:
        first = name.split(" - ", 1)[0].strip()
        return first if first else name[:28]
    return "Proyecto identificado"


def _compact_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value).date()
    except ValueError:
        return value
    return f"{parsed.day:02d} {MONTHS[parsed.month - 1]} {parsed.year}"


def _period(starts_on: str | None, ends_on: str | None) -> str | None:
    start, end = _compact_date(starts_on), _compact_date(ends_on)
    if not start and not end:
        return None
    return f"{start or 'Inicio pendiente'}  →  {end or 'Fin pendiente'}"


def _provider(provenance: Provenance | None) -> tuple[str, str | None]:
    if provenance is None:
        return "Prisma / Nexus", "Identidad informada por solicitud"
    name = "Prisma / Nexus" if provenance.source == "nexus" else "Startrack"
    nature = {
        "provided_sample": "Muestra documental",
        "live_read": "Lectura sandbox",
        "test_case": "Prueba interna",
    }[provenance.evidence_kind]
    return name, f"{nature} · {provenance.environment}"


def _observation(provenance: Provenance | None, age: str) -> tuple[str, str]:
    if provenance and provenance.observed_on:
        return "Fecha documental", f"{provenance.observed_on:%d/%m/%Y}; hora no disponible"
    if provenance and provenance.observed_at:
        return "Última observación", age
    return "Observación", "Sin fecha disponible"


def _status_tone(value: str | None) -> str:
    return "attention" if (value or "").strip().upper() in {"OBSOLETA", "OBSOLETE"} else "neutral"


def _project_label(project_id: str, graph: OperationsGraph) -> str:
    project = next(
        (node for node in graph.nodes if node.kind == "place" and node.entity_id == project_id),
        None,
    )
    return project.label if project else "Proyecto identificado"


def _visual_fact(
    icon_name: str,
    label: str,
    value: Any,
    secondary: str | None = None,
    *,
    tone: str = "neutral",
):
    return html.Div(
        [
            html.Span(icon(icon_name, 17), className="graph-detail-fact-icon"),
            html.Div(
                [
                    html.Span(label, className="graph-detail-fact-label"),
                    html.Strong(
                        str(value) if value not in (None, "") else "Sin confirmar",
                        className="graph-detail-fact-value",
                    ),
                    html.Span(secondary, className="graph-detail-fact-meta") if secondary else None,
                ]
            ),
        ],
        className=f"graph-detail-fact graph-detail-fact--{tone}",
    )


def _signal(icon_name: str, label: str, value: str, *, tone: str = "neutral"):
    return html.Li(
        [
            icon(icon_name, 16),
            html.Span(label, className="graph-detail-signal-label"),
            html.Strong(value),
        ],
        className=f"graph-detail-signal graph-detail-signal--{tone}",
    )


def _evidence_label(value: str) -> str:
    return {
        "maquinaria.project_id": "Proyecto asignado en Prisma",
        "solicitud.maquinaria_id + solicitud.project_id": (
            "Solicitud, unidad y proyecto coinciden"
        ),
        "tarea Startrack vinculada a la asignación actual por IDs y período": (
            "Tarea vinculada a la asignación vigente"
        ),
    }.get(value, "Correspondencia validada por el servicio")


def _machine_subtype(item: EquipmentRecord | None) -> str:
    if item is None or not item.equipment_class:
        return "machinery"
    value = normalize("NFKD", item.equipment_class).encode("ascii", "ignore").decode().casefold()
    if "excavador" in value:
        return "excavator"
    if "cargador" in value:
        return "loader"
    if "rodillo" in value or "compactador" in value:
        return "roller"
    if "camion" in value or "transport" in value:
        return "truck"
    return "machinery"


def _machine_label(item: EquipmentRecord | None, entity_id: str) -> str:
    if item is None:
        return f"Unidad {entity_id.rsplit(':', 1)[-1][:8]}"
    return item.asset_number or item.code or item.name


def _project_key(source_id: str) -> str:
    return f"project:{source_id}"


def _machine_key(entity_id: str) -> str:
    return f"machine:{entity_id}"


def _active_transfer(transfer: TransferRecord) -> bool:
    if transfer.receipt is not None:
        return False
    role = (transfer.workflow_role or "").strip().casefold()
    state = transfer.status.strip().upper()
    return role in ACTIVE_TRANSFER_ROLES or state in ACTIVE_TRANSFER_STATES


def _add_project(
    projects: dict[str, GraphNode],
    source_id: str | None,
    name: str | None,
    record: RequestRecord | EquipmentRecord | TransferRecord,
    generated_at: datetime,
) -> str | None:
    if not source_id:
        return None
    key = _project_key(source_id)
    provenance = record.provenance
    if key not in projects:
        projects[key] = GraphNode(
            key=key,
            kind="place",
            subtype="project",
            entity_id=source_id,
            source_id=source_id,
            label=_short_project(name, source_id),
            status="Proyecto identificado",
            source=_source(provenance),
            age=_age(provenance, generated_at),
        )
    projects[key].project_records.append(record)
    return key


def _edge(edges: dict[tuple[str, str], GraphEdge], source: str, target: str) -> GraphEdge:
    pair = (source, target)
    if pair not in edges:
        digest = sha256(f"{source}|{target}".encode()).hexdigest()[:12]
        edges[pair] = GraphEdge(key=f"edge:{digest}", source=source, target=target)
    return edges[pair]


def build_operations_graph(hub: HubResponse) -> OperationsGraph:
    """Project exact IDs and verified relationships into a stable visual layout."""
    projects: dict[str, GraphNode] = {}
    machines: dict[str, GraphNode] = {}
    edges: dict[tuple[str, str], GraphEdge] = {}

    for item in sorted(hub.equipment, key=lambda value: value.id):
        key = _machine_key(item.id)
        machines[key] = GraphNode(
            key=key,
            kind="machine",
            subtype=_machine_subtype(item),
            entity_id=item.id,
            source_id=item.provenance.source_id,
            label=_machine_label(item, item.id),
            status=item.machinery_status,
            source=_source(item.provenance),
            age=_age(item.provenance, hub.generated_at),
            subtitle=item.machinery_status,
            equipment=item,
        )
        project = _add_project(projects, item.project_id, item.project_name, item, hub.generated_at)
        if project:
            connection = _edge(edges, key, project)
            connection.evidence.append("maquinaria.project_id")

    for request in sorted(hub.requests, key=lambda value: value.id):
        project = _add_project(
            projects, request.project_id, request.project_name, request, hub.generated_at
        )
        if not request.machinery_id:
            continue
        machine = _machine_key(request.machinery_id)
        if machine not in machines:
            machines[machine] = GraphNode(
                key=machine,
                kind="machine",
                subtype="machinery",
                entity_id=request.machinery_id,
                source_id=None,
                label=_machine_label(None, request.machinery_id),
                status="Registro fuera de la lectura",
                source="ID de maquinaria informado por la solicitud",
                age=_age(request.provenance, hub.generated_at),
                subtitle="FUERA DE LA LECTURA",
            )
        if project:
            connection = _edge(edges, machine, project)
            connection.evidence.append("solicitud.maquinaria_id + solicitud.project_id")
            connection.request_ids.append(request.id)

    for item in hub.equipment:
        machine = _machine_key(item.id)
        for transfer in item.transfers:
            project = _add_project(
                projects,
                transfer.destination_project_id,
                transfer.destination_project_name,
                transfer,
                hub.generated_at,
            )
            if not project or not transfer.evidence_current_assignment:
                continue
            connection = _edge(edges, machine, project)
            connection.kind = "transfer"
            connection.active = connection.active or _active_transfer(transfer)
            connection.evidence.append(
                "tarea Startrack vinculada a la asignación actual por IDs y período"
            )
            connection.transfer_ids.append(transfer.id)

    project_nodes = sorted(projects.values(), key=lambda value: value.entity_id)
    machine_nodes = sorted(machines.values(), key=lambda value: value.entity_id)
    columns = max(1, min(3, len(project_nodes)))
    rows = max(1, (len(project_nodes) + columns - 1) // columns)
    width = max(900, columns * 300)
    height = max(560, rows * 240)
    column_gap = width / columns
    row_gap = height / rows
    for index, node in enumerate(project_nodes):
        row, column = divmod(index, columns)
        node.x = column_gap * (column + 0.5)
        node.y = row_gap * (row + 0.5)
        request_count = sum(isinstance(record, RequestRecord) for record in node.project_records)
        node.subtitle = (
            f"{request_count} SOLICITUD{'ES' if request_count != 1 else ''}"
            if request_count
            else "SIN SOLICITUD VISIBLE"
        )

    targets: dict[str, list[str]] = {}
    for connection in edges.values():
        targets.setdefault(connection.source, []).append(connection.target)
    grouped: dict[str, list[GraphNode]] = {node.key: [] for node in project_nodes}
    unassigned: list[GraphNode] = []
    for node in machine_nodes:
        node.place_keys = sorted(targets.get(node.key, []))
        target = min(node.place_keys, default=None)
        if target in grouped:
            grouped[target].append(node)
        else:
            unassigned.append(node)

    for project in project_nodes:
        group = sorted(grouped[project.key], key=lambda value: value.entity_id)
        offsets = ((280, 0), (245, -85), (245, 85), (350, -85), (350, 85), (385, 0))
        for index, node in enumerate(group):
            lap, position = divmod(index, len(offsets))
            dx, dy = offsets[position]
            node.x = min(width - 28, project.x + dx + lap * 42)
            node.y = min(height - 28, max(28, project.y + dy))
    for index, node in enumerate(unassigned):
        node.x = width - 20 - (index % 5) * 38
        node.y = height - 20 - (index // 5) * 38
    return OperationsGraph(
        nodes=[*project_nodes, *machine_nodes],
        edges=sorted(edges.values(), key=lambda value: value.key),
        width=width,
        height=height,
    )


def _line_geometry(source: GraphNode, target: GraphNode) -> dict[str, str]:
    dx, dy = target.x - source.x, target.y - source.y
    distance = hypot(dx, dy)
    if not distance:
        return {"display": "none"}
    ux, uy = dx / distance, dy / distance
    start_x = source.x + ux * source.radius
    start_y = source.y + uy * source.radius
    end_x = target.x - ux * target.radius
    end_y = target.y - uy * target.radius
    length = max(0, hypot(end_x - start_x, end_y - start_y))
    angle = degrees(atan2(end_y - start_y, end_x - start_x))
    return {
        "left": f"{start_x:.2f}px",
        "top": f"{start_y:.2f}px",
        "width": f"{length:.2f}px",
        "transform": f"rotate({angle:.3f}deg)",
        "--edge-angle": f"{angle:.3f}deg",
        "--edge-counter-angle": f"{-angle:.3f}deg",
    }


def _fact(label: str, value: Any):
    return html.Div(
        [html.Dt(label), html.Dd(str(value) if value not in (None, "") else "No informado")]
    )


def _facts(values: list[tuple[str, Any]]):
    return html.Dl([_fact(label, value) for label, value in values], className="graph-detail-facts")


def _movement_matches(item: EquipmentRecord, movement: MovementRecord, hub: HubResponse) -> bool:
    return bool(
        item.provenance.source_id
        and movement.mode == hub.mode
        and movement.environment == item.provenance.environment
        and movement.machinery_source_id == item.provenance.source_id
    )


def _project_detail(node: GraphNode, graph: OperationsGraph):
    requests = [record for record in node.project_records if isinstance(record, RequestRecord)]
    connected = [
        candidate
        for candidate in graph.nodes
        if candidate.kind == "machine"
        and any(edge.source == candidate.key and edge.target == node.key for edge in graph.edges)
    ]
    labels = {
        record.project_name
        for record in node.project_records
        if getattr(record, "project_name", None)
    }
    equipment_by_id = {candidate.entity_id: candidate for candidate in connected}
    provenance = node.project_records[0].provenance if node.project_records else None
    provider, provider_context = _provider(provenance)
    observation_label, observation_value = _observation(provenance, node.age)
    return [
        html.Div(
            [
                html.Span(
                    html.Img(src="/assets/graph-project.svg", alt=""),
                    className="graph-detail-hero-icon",
                    **{"aria-hidden": "true"},
                ),
                html.Div(
                    [
                        html.P("Proyecto / obra", className="graph-detail-kicker"),
                        html.H2(node.label),
                        html.P("Flujo operativo", className="graph-detail-subtitle"),
                    ]
                ),
            ],
            className="graph-detail-hero",
        ),
        html.Div(
            [
                _visual_fact(
                    "bulldozer",
                    "Maquinaria relacionada",
                    len(connected),
                    "Por identificadores exactos",
                ),
                _visual_fact("clipboard-list", "Solicitudes", len(requests), "En esta lectura"),
                _visual_fact("database", "Origen", provider, provider_context),
                _visual_fact("eye-check", observation_label, observation_value),
            ],
            className="graph-detail-visual-grid",
        ),
        html.Section(
            [
                html.H3("Asignación verificada"),
                html.Ul(
                    [
                        _signal(
                            "bulldozer",
                            item.label,
                            item.status.capitalize(),
                            tone=_status_tone(item.status),
                        )
                        for item in connected
                    ],
                    className="graph-detail-signals",
                )
                if connected
                else html.Div(_signal("bulldozer", "Maquinaria", "Sin relación verificable")),
            ]
        ),
        html.Section(
            [
                html.H3("Solicitudes"),
                html.Ul(
                    [
                        html.Li(
                            [
                                html.Div(
                                    [
                                        icon("clipboard-list", 16),
                                        html.Strong(f"Solicitud {request.status.lower()}"),
                                    ],
                                    className="graph-detail-event-title",
                                ),
                                html.Span(
                                    _period(request.starts_on, request.ends_on)
                                    or "Período pendiente",
                                    className="graph-detail-event-meta",
                                ),
                                html.Span(
                                    request.machinery_type or "Tipo pendiente",
                                    className="graph-detail-event-meta",
                                ),
                                html.Span(
                                    (
                                        equipment_by_id[request.machinery_id].label
                                        if request.machinery_id in equipment_by_id
                                        else "Unidad pendiente"
                                    ),
                                    className="graph-detail-event-tag",
                                ),
                            ],
                            className="graph-detail-event",
                        )
                        for request in requests
                    ],
                    className="graph-detail-timeline",
                )
                if requests
                else html.Div(_signal("clipboard-list", "Solicitudes", "Sin registros")),
            ]
        ),
        html.Div(
            [
                icon("alert-circle", 15) if len(labels) > 1 else icon("check", 15),
                html.Span(
                    "Nombres contradictorios; identidad técnica preservada"
                    if len(labels) > 1
                    else "Relaciones verificadas por identidad técnica"
                ),
            ],
            className="graph-detail-proof",
        ),
    ]


def _duration_label(raw: Any) -> str | None:
    try:
        seconds = int(float(str(raw)))
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if seconds or not parts:
        parts.append(f"{seconds} s")
    return " ".join(parts)


def _transfer_lines(transfer: TransferRecord) -> list:
    active = _active_transfer(transfer)
    destination = transfer.destination_project_name or (
        "Proyecto identificado" if transfer.destination_project_id else "Destino pendiente"
    )
    planned_duration = _duration_label(transfer.source_data.get("duration"))
    scheduled = " ".join(
        str(value)
        for value in [
            transfer.source_data.get("start_date"),
            transfer.source_data.get("start_time"),
        ]
        if value not in (None, "")
    )
    return [
        html.Li(
            [
                html.Div(
                    [
                        icon("truck", 18),
                        html.Div(
                            [
                                html.Strong(
                                    f"Traslado {transfer.code}"
                                    if transfer.code
                                    else "Traslado identificado"
                                ),
                                html.Span(
                                    transfer.status or "Sin estado",
                                    className="graph-detail-event-tag",
                                ),
                            ]
                        ),
                    ],
                    className="graph-detail-event-title",
                ),
                html.Div(
                    [
                        _visual_fact("layout-dashboard", "Destino", destination),
                        _visual_fact(
                            "user-circle", "Responsable", transfer.driver or "Sin asignar"
                        ),
                        _visual_fact(
                            "arrows-exchange",
                            "Programación",
                            scheduled or "Sin fecha",
                            (
                                f"Duración {planned_duration}"
                                if planned_duration
                                else "Duración no disponible"
                            ),
                        ),
                    ],
                    className="graph-detail-visual-grid graph-detail-visual-grid--transfer",
                ),
                html.Ul(
                    [
                        _signal(
                            "arrows-exchange",
                            "Actividad",
                            (
                                "En traslado · tiempo no disponible"
                                if active
                                else "Sin actividad confirmada"
                            ),
                            tone="transfer" if active else "neutral",
                        ),
                        _signal(
                            "eye-check",
                            "Llegada",
                            (
                                "GPS observado · no confirma recepción"
                                if transfer.arrival_observed
                                else "Sin evidencia vinculada"
                            ),
                        ),
                        _signal(
                            "clipboard-check",
                            "Recepción",
                            (
                                f"Confirmada · {transfer.receipt.receiver}"
                                if transfer.receipt
                                else "Sin constancia de recepción"
                            ),
                            tone="active" if transfer.receipt else "neutral",
                        ),
                    ],
                    className="graph-detail-signals",
                ),
            ],
            className="graph-transfer-item",
        )
    ]


def _machine_detail(
    node: GraphNode, hub: HubResponse, workflow: WorkflowOverview | None, graph: OperationsGraph
):
    item = node.equipment
    requests = [request for request in hub.requests if request.machinery_id == node.entity_id]
    movements = [
        movement
        for movement in (workflow.movements if workflow else [])
        if item is not None and _movement_matches(item, movement, hub)
    ]
    transfers = item.transfers if item else []
    alerts = [alert for alert in hub.alerts if alert.equipment_id == node.entity_id]
    project_evidence: dict[str, list[tuple[str, str, str]]] = {}

    def add_project(project_id: str | None, icon_name: str, label: str, value: str):
        if project_id:
            evidence = (icon_name, label, value)
            if evidence not in project_evidence.setdefault(project_id, []):
                project_evidence[project_id].append(evidence)

    if item:
        add_project(item.project_id, "clipboard-check", "Asignación Prisma", item.machinery_status)
    for request in requests:
        add_project(
            request.project_id,
            "clipboard-list",
            "Solicitud",
            " · ".join(
                value
                for value in [request.status, _period(request.starts_on, request.ends_on)]
                if value
            ),
        )
    for transfer in transfers:
        add_project(
            transfer.destination_project_id,
            "truck",
            "Traslado Startrack",
            transfer.status or "Sin estado",
        )
    for movement in movements:
        add_project(
            movement.project_source_id,
            "arrows-exchange",
            "Movimiento ECON",
            f"{movement.state} · {len(movement.events)} evento(s)",
        )

    project_ids = set(project_evidence)
    project_labels = [_project_label(project_id, graph) for project_id in sorted(project_ids)]
    project_summary = (
        project_labels[0]
        if len(project_labels) == 1
        else f"{len(project_labels)} proyectos relacionados"
        if project_labels
        else "Sin proyecto confirmado"
    )
    provenance = item.provenance if item else None
    provider, provider_context = _provider(provenance)
    observation_label, observation_value = _observation(provenance, node.age)
    active_transfer = any(_active_transfer(transfer) for transfer in transfers)
    status_tone = (
        "issue"
        if alerts or (item and item.maintenance_failure_id)
        else "maintenance"
        if item and (item.maintenance_status or item.maintenance_is_stopped is True)
        else "transfer"
        if active_transfer
        else _status_tone(node.status)
    )

    missing = []
    if item is None:
        missing.append(_signal("alert-circle", "Ficha de maquinaria", "Fuera de la lectura"))
    if not project_ids:
        missing.append(_signal("layout-dashboard", "Proyecto", "Sin relación confirmada"))
    if workflow is None or not workflow.available:
        missing.append(_signal("database", "Historial ECON", "No disponible"))
    elif not workflow.complete:
        missing.append(_signal("database", "Historial ECON", "Cobertura parcial"))

    detail = [
        html.Div(
            [
                html.Span(
                    html.Img(src=f"/assets/graph-{node.subtype}.svg", alt=""),
                    className="graph-detail-hero-icon",
                    **{"aria-hidden": "true"},
                ),
                html.Div(
                    [
                        html.P("Maquinaria", className="graph-detail-kicker"),
                        html.H2(node.label),
                        html.P(
                            item.name if item else "Tipo no disponible",
                            className="graph-detail-subtitle",
                        ),
                    ]
                ),
                html.Span(
                    [
                        icon("alert-triangle", 14)
                        if status_tone in {"issue", "attention"}
                        else None,
                        node.status.capitalize(),
                    ],
                    className=f"graph-detail-status graph-detail-status--{status_tone}",
                ),
            ],
            className="graph-detail-hero",
        ),
        html.Div(
            [
                _visual_fact(
                    "layout-dashboard",
                    "Proyecto",
                    project_summary,
                    (
                        f"{len(project_ids)} proyecto relacionado"
                        if len(project_ids) == 1
                        else f"{len(project_ids)} proyectos relacionados"
                        if project_ids
                        else None
                    ),
                ),
                _visual_fact(
                    "arrows-exchange",
                    "Período",
                    _period(item.assignment_starts_on, item.assignment_ends_on) if item else None,
                ),
                _visual_fact("database", "Origen", provider, provider_context),
                _visual_fact("eye-check", observation_label, observation_value),
                *(
                    [_visual_fact("eye-check", "Ubicación", item.location.label)]
                    if item and item.location
                    else []
                ),
            ],
            className="graph-detail-visual-grid",
        ),
    ]

    if project_evidence:
        detail.append(
            html.Section(
                [
                    html.Div(
                        [
                            html.H3("Recorrido por proyectos"),
                            html.Span(
                                str(len(project_ids)),
                                className="graph-detail-count",
                                title="Proyectos relacionados en la evidencia visible",
                            ),
                        ],
                        className="graph-detail-section-heading",
                    ),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Div(
                                        [
                                            icon("layout-dashboard", 18),
                                            html.Strong(_project_label(project_id, graph)),
                                        ],
                                        className="graph-detail-event-title",
                                    ),
                                    html.Ul(
                                        [
                                            _signal(icon_name, label, value)
                                            for icon_name, label, value in project_evidence[
                                                project_id
                                            ]
                                        ],
                                        className=(
                                            "graph-detail-signals graph-detail-signals--nested"
                                        ),
                                    ),
                                ],
                                className="graph-detail-project",
                            )
                            for project_id in sorted(project_evidence)
                        ],
                        className="graph-detail-timeline",
                    ),
                    html.Div(
                        [
                            icon("eye-check", 15),
                            html.Span("Evidencia documental · no confirma presencia física"),
                        ],
                        className="graph-detail-proof",
                    ),
                ]
            )
        )

    if item and item.operators is not None:
        detail.append(
            html.Section(
                [
                    html.H3("Operadores"),
                    html.Ul(
                        [
                            _signal(
                                "user-circle",
                                operator.name or "Operador sin nombre",
                                (
                                    "Activo"
                                    if operator.is_active is True
                                    else "Inactivo"
                                    if operator.is_active is False
                                    else "Vigencia pendiente"
                                ),
                            )
                            for operator in item.operators
                        ],
                        className="graph-detail-signals",
                    )
                    if item.operators
                    else html.Div(_signal("user-circle", "Operadores", "Sin asignación")),
                ]
            )
        )

    if item and (item.assignment_note or item.project_rate):
        detail.append(
            html.Section(
                [
                    html.H3("Asignación"),
                    html.Div(
                        [
                            _visual_fact("clipboard-check", "Nota", item.assignment_note)
                            if item.assignment_note
                            else None,
                            _visual_fact(
                                "database",
                                "Tarifa informada",
                                item.project_rate.hourly_rate,
                                "Moneda no informada",
                            )
                            if item.project_rate and item.project_rate.hourly_rate is not None
                            else None,
                        ],
                        className="graph-detail-visual-grid",
                    ),
                ]
            )
        )

    if item and (
        item.maintenance_failure_id or item.maintenance_status or item.maintenance_is_stopped
    ):
        maintenance_signals = []
        if item.maintenance_status:
            maintenance_signals.append(
                _signal(
                    "alert-triangle",
                    "Mantenimiento",
                    item.maintenance_status,
                    tone="maintenance",
                )
            )
        if item.maintenance_is_stopped is True:
            maintenance_signals.append(_signal("alert-circle", "Paro", "Confirmado", tone="issue"))
        if item.maintenance_failure_id:
            maintenance_signals.append(
                _signal("alert-triangle", "Falla", "Evidencia vinculada", tone="issue")
            )
        detail.append(
            html.Section(
                [
                    html.H3("Mantenimiento e incidentes"),
                    html.Ul(maintenance_signals, className="graph-detail-signals"),
                ]
            )
        )

    if transfers:
        detail.append(
            html.Section(
                [
                    html.H3("Traslados"),
                    html.Ul(
                        sum((_transfer_lines(transfer) for transfer in transfers), []),
                        className="graph-detail-timeline",
                    ),
                ]
            )
        )

    if movements:
        detail.append(
            html.Section(
                [
                    html.H3("Historial ECON"),
                    html.Ul(
                        [
                            _signal(
                                "arrows-exchange",
                                "Movimiento registrado",
                                f"{movement.state} · {len(movement.events)} evento(s)",
                            )
                            for movement in movements
                        ],
                        className="graph-detail-signals",
                    ),
                ]
            )
        )

    if alerts:
        detail.append(
            html.Section(
                [
                    html.H3("Incidentes confirmados"),
                    html.Ul(
                        [
                            _signal(
                                "alert-triangle",
                                alert.title,
                                alert.description,
                                tone="issue",
                            )
                            for alert in alerts
                        ],
                        className="graph-detail-signals",
                    ),
                ],
                className="graph-detail-incidents",
            )
        )

    if len(project_ids) > 1:
        detail.append(
            html.Div(
                [
                    icon("alert-triangle", 16),
                    html.Span("Asignaciones simultáneas · revisar vigencia"),
                ],
                className="graph-detail-proof graph-detail-proof--warning",
            )
        )
    if missing:
        detail.append(
            html.Section(
                [
                    html.H3("Cobertura pendiente"),
                    html.Ul(missing, className="graph-detail-signals"),
                ]
            )
        )
    return detail


def _detail(
    node: GraphNode, hub: HubResponse, workflow: WorkflowOverview | None, graph: OperationsGraph
):
    content = (
        _project_detail(node, graph)
        if node.kind == "place"
        else _machine_detail(node, hub, workflow, graph)
    )
    return html.Aside(
        [
            html.Button(
                "Cerrar",
                type="button",
                className="graph-detail-close",
                **{"data-graph-close": "true", "aria-label": "Cerrar detalle"},
            ),
            *content,
        ],
        className="graph-detail",
        hidden=True,
        role="dialog",
        **{
            "aria-hidden": "true",
            "aria-label": f"Detalle de {node.label}",
            "data-node-detail": node.key,
        },
    )


def _node(node: GraphNode):
    token = sha256(node.key.encode()).hexdigest()[:12]
    tooltip_id = f"graph-tooltip-{token}"
    item = node.equipment
    incident = bool(item and item.maintenance_failure_id)
    maintenance = bool(item and (item.maintenance_status or item.maintenance_is_stopped is True))
    transfer_active = bool(item and any(_active_transfer(task) for task in item.transfers))
    classes = ["graph-node", f"graph-node--{node.kind}", f"graph-node--{node.subtype}"]
    if incident:
        classes.append("graph-node--incident")
    elif maintenance:
        classes.append("graph-node--maintenance")
    if transfer_active:
        classes.append("graph-node--active-transfer")
    tooltip = " · ".join([node.label, node.status, node.source, node.age])
    label_class = f"graph-node-label graph-node-label--{node.kind}"
    return html.Button(
        [
            html.Span(
                html.Img(src=f"/assets/graph-{node.subtype}.svg", alt="", draggable="false"),
                className="graph-node-disc",
                **{"aria-hidden": "true"},
            ),
            html.Span(
                [
                    html.Span(node.label, className="graph-node-label-main"),
                    html.Span(node.subtitle, className="graph-node-label-meta")
                    if node.subtitle
                    else None,
                ],
                className=label_class,
            ),
            html.Span("!", className="graph-node-incident", **{"aria-hidden": "true"})
            if incident
            else None,
            html.Span(tooltip, id=tooltip_id, className="graph-tooltip", role="tooltip"),
        ],
        type="button",
        className=" ".join(classes),
        style={"left": f"{node.x}px", "top": f"{node.y}px"},
        title=tooltip,
        **{
            "aria-label": tooltip,
            "aria-describedby": tooltip_id,
            "data-node-key": node.key,
            "data-node-kind": node.kind,
            "data-places": "|".join(node.place_keys),
            "data-always-visible": "true" if transfer_active else "false",
        },
    )


def _edge_component(edge: GraphEdge, nodes: dict[str, GraphNode]):
    source, target = nodes[edge.source], nodes[edge.target]
    classes = ["graph-edge", f"graph-edge--{edge.kind}"]
    if edge.active:
        classes.append("graph-edge--active")
    relationship = (
        f"Traslado confirmado de {source.label} hacia {target.label}"
        if edge.kind == "transfer"
        else f"Asignación verificada entre {source.label} y {target.label}"
    )
    count = len(edge.transfer_ids) if edge.kind == "transfer" else len(edge.request_ids)
    label = "Asignación registrada"
    if edge.kind == "transfer":
        label = f"TRASLADO · {count or 1} EVIDENCIA"
    return html.Div(
        [
            html.Span(className="graph-edge-pulse", **{"aria-hidden": "true"})
            if edge.active
            else None,
            html.Button(
                label,
                type="button",
                className="graph-edge-label",
                title=f"{relationship}. Abrir evidencia de la conexión.",
                **{
                    "aria-label": f"{relationship}. Abrir evidencia de la conexión.",
                    "data-edge-select": edge.key,
                },
            ),
        ],
        className=" ".join(classes),
        style=_line_geometry(source, target),
        title=relationship,
        **{
            "data-edge-key": edge.key,
            "data-source": edge.source,
            "data-target": edge.target,
        },
    )


def _edge_detail(edge: GraphEdge, nodes: dict[str, GraphNode], hub: HubResponse):
    source, target = nodes[edge.source], nodes[edge.target]
    requests = [request for request in hub.requests if request.id in edge.request_ids]
    transfers = [
        transfer
        for item in hub.equipment
        for transfer in item.transfers
        if transfer.id in edge.transfer_ids
    ]
    heading = "Traslado confirmado" if edge.kind == "transfer" else "Asignación verificada"
    content = [
        html.Div(
            [
                html.Span(
                    icon("arrows-exchange", 22),
                    className="graph-detail-hero-icon graph-detail-hero-icon--ui",
                ),
                html.Div(
                    [
                        html.P("Conexión operativa", className="graph-detail-kicker"),
                        html.H2(heading),
                        html.P(
                            f"{source.label}  →  {target.label}",
                            className="graph-detail-subtitle",
                        ),
                    ]
                ),
            ],
            className="graph-detail-hero",
        ),
        html.Div(
            [
                _visual_fact("bulldozer", "Maquinaria", source.label),
                _visual_fact("layout-dashboard", "Proyecto", target.label),
                _visual_fact("clipboard-list", "Solicitudes", len(requests)),
                _visual_fact(
                    "truck",
                    "Actividad",
                    "En traslado" if edge.active else "Sin traslado activo",
                    tone="transfer" if edge.active else "neutral",
                ),
            ],
            className="graph-detail-visual-grid",
        ),
        html.Section(
            [
                html.H3("Evidencia de la relación"),
                html.Ul(
                    [
                        _signal(
                            "check",
                            "Correspondencia verificada",
                            _evidence_label(value),
                            tone="active",
                        )
                        for value in dict.fromkeys(edge.evidence)
                    ],
                    className="graph-detail-signals",
                ),
            ]
        ),
    ]
    if requests:
        content.append(
            html.Section(
                [
                    html.H3("Solicitudes relacionadas"),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Div(
                                        [
                                            icon("clipboard-list", 16),
                                            html.Strong(f"Solicitud {request.status.lower()}"),
                                        ],
                                        className="graph-detail-event-title",
                                    ),
                                    html.Span(
                                        _period(request.starts_on, request.ends_on)
                                        or "Período pendiente",
                                        className="graph-detail-event-meta",
                                    ),
                                    html.Span(
                                        f"Solicita · {request.requested_by or 'Pendiente'}",
                                        className="graph-detail-event-meta",
                                    ),
                                    html.Span(
                                        f"Aprueba · {request.approved_by or 'Pendiente'}",
                                        className="graph-detail-event-meta",
                                    ),
                                ],
                                className="graph-detail-event",
                            )
                            for request in requests
                        ],
                        className="graph-detail-timeline",
                    ),
                ]
            )
        )
    if transfers:
        content.append(
            html.Section(
                [
                    html.H3("Tareas Startrack"),
                    html.Ul(sum((_transfer_lines(t) for t in transfers), [])),
                ]
            )
        )
    content.append(
        html.Div(
            [
                icon("eye-check", 15),
                html.Span("Relación documental · la geometría no mide tiempo ni distancia"),
            ],
            className="graph-detail-proof",
        )
    )
    return html.Aside(
        [
            html.Button(
                "Cerrar",
                type="button",
                className="graph-detail-close",
                **{"data-graph-close": "true", "aria-label": "Cerrar detalle"},
            ),
            *content,
        ],
        className="graph-detail",
        hidden=True,
        role="dialog",
        **{
            "aria-hidden": "true",
            "aria-label": f"Detalle de {heading.lower()}",
            "data-edge-detail": edge.key,
        },
    )


def _meta(hub: HubResponse):
    source = next((item for item in hub.sources if item.id == "nexus"), None)
    query_time = hub.generated_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
    evidence_time = (
        f"Corte {hub.data_as_of.astimezone(UTC):%d/%m/%Y %H:%M UTC}"
        if hub.data_as_of and hub.data_as_of.tzinfo
        else f"Fecha documental {source.observed_on:%d/%m/%Y}"
        if source and source.observed_on
        else "Sin corte común"
    )
    coverage = "Cobertura completa" if hub.scope.complete else "Cobertura parcial"
    return html.Div(
        [
            html.Span(className="graph-origin-dot", **{"aria-hidden": "true"}),
            html.Span(MODE_LABELS[hub.mode]),
            html.Span("·"),
            html.Span(coverage),
            html.Span("·"),
            html.Span(evidence_time),
            html.Span("·"),
            html.Span(f"Consulta {query_time}"),
        ],
        className="graph-meta",
        role="status",
    )


def _controls():
    return html.Div(
        [
            html.Button(
                "+", type="button", **{"aria-label": "Acercar", "data-graph-control": "in"}
            ),
            html.Button(
                "−", type="button", **{"aria-label": "Alejar", "data-graph-control": "out"}
            ),
            html.Button(
                "◎",
                type="button",
                **{"aria-label": "Centrar vista", "data-graph-control": "center"},
            ),
            html.Button(
                "↻",
                type="button",
                **{"aria-label": "Actualizar datos", "data-graph-control": "refresh"},
            ),
        ],
        className="graph-controls",
        **{"aria-label": "Controles del grafo"},
    )


def graph_status(hub: HubResponse | None, title: str, message: str):
    return html.Div(
        [
            _meta(hub) if hub else None,
            html.Div([html.H1(title), html.P(message)], className="graph-empty", role="status"),
            _controls(),
        ],
        className="operations-graph operations-graph--status",
        style=GRAPH_STYLE,
        **{"data-layout-key": f"status:{hub.mode if hub else 'unknown'}"},
    )


def operations_graph_view(hub: HubResponse, workflow: WorkflowOverview | None = None):
    source = next((item for item in hub.sources if item.id == "nexus"), None)
    if source is None or source.status not in READABLE_SOURCE_STATES:
        message = source.message if source else "La fuente principal no respondió a esta consulta."
        return graph_status(hub, "Origen no disponible", message)
    graph = build_operations_graph(hub)
    if not graph.nodes:
        return graph_status(
            hub,
            "Sin entidades verificables",
            "La lectura no devolvió proyectos ni maquinaria con identidad preservada.",
        )
    if not any(node.kind == "place" for node in graph.nodes):
        return graph_status(
            hub,
            "Sin lugares verificables",
            "La maquinaria sin asignación o ubicación confirmada no se agrupa en una base.",
        )
    nodes = {node.key: node for node in graph.nodes}
    identities = "|".join(node.key for node in graph.nodes)
    layout_key = f"{hub.mode}:{sha256(identities.encode()).hexdigest()[:16]}"
    relationships = [
        (
            f"Traslado confirmado de {nodes[edge.source].label} hacia {nodes[edge.target].label}."
            if edge.kind == "transfer"
            else (
                f"Asignación verificada entre {nodes[edge.source].label} "
                f"y {nodes[edge.target].label}."
            )
        )
        for edge in graph.edges
    ]
    return html.Div(
        [
            _meta(hub),
            html.Div(
                html.Div(
                    [
                        *[_edge_component(edge, nodes) for edge in graph.edges],
                        *[_node(node) for node in graph.nodes],
                    ],
                    id="operations-graph-world",
                    className="operations-graph-world",
                    style={"width": f"{graph.width}px", "height": f"{graph.height}px"},
                    **{"data-world-width": graph.width, "data-world-height": graph.height},
                ),
                id="operations-graph-viewport",
                className="operations-graph-viewport",
                tabIndex=0,
                role="region",
                **{
                    "aria-label": (
                        "Grafo de proyectos, maquinaria y relaciones operativas. "
                        "Use más, menos o rueda para ampliar; arrastre el fondo "
                        "para desplazarse."
                    ),
                },
            ),
            html.Ul([html.Li(value) for value in relationships], className="sr-only"),
            _controls(),
            *[_detail(node, hub, workflow, graph) for node in graph.nodes],
            *[_edge_detail(edge, nodes, hub) for edge in graph.edges],
        ],
        className="operations-graph",
        style=GRAPH_STYLE,
        **{"data-layout-key": layout_key},
    )
