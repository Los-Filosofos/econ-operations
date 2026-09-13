"""Full-viewport operations graph built only from normalized hub and workflow evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from math import atan2, degrees, hypot
from typing import Any
from unicodedata import normalize

from dash import html

from app.models.hub import EquipmentRecord, HubResponse, Provenance, RequestRecord, TransferRecord
from app.models.operations import MovementRecord
from app.models.workflow import WorkflowOverview

PLACE_RADIUS = 48
MACHINE_RADIUS = 29
COLLECTION_RADIUS = 42
UNASSIGNED_KEY = "collection:unassigned"
MODE_LABELS = {"fixture": "Muestras proporcionadas", "live": "Sandbox actual · sintético"}
READABLE_SOURCE_STATES = {"fixture", "connected", "partial"}
ACTIVE_TRANSFER_ROLES = {"pending", "active", "in_progress", "in progress", "en curso"}
ACTIVE_TRANSFER_STATES = {"PENDIENTE", "PENDING", "ACTIVE", "IN_PROGRESS", "EN CURSO"}


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
    member_keys: list[str] = field(default_factory=list)
    member_of: str | None = None

    @property
    def radius(self) -> int:
        if self.kind == "place":
            return PLACE_RADIUS
        if self.kind == "collection":
            return COLLECTION_RADIUS
        return MACHINE_RADIUS


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
    return f"Proyecto {source_id[:8]}"


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
    width = max(1120, 880 + max(0, len(project_nodes) - 1) * 180)
    height = max(680, 340 + max(1, len(project_nodes)) * 180)
    center_y = height / 2
    for index, node in enumerate(project_nodes):
        node.x = 210
        node.y = center_y + (index - (len(project_nodes) - 1) / 2) * 180
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
        target = min(targets.get(node.key, []), default=None)
        if target in grouped:
            grouped[target].append(node)
        else:
            unassigned.append(node)

    max_group_rows = 1
    for project in project_nodes:
        group = sorted(grouped[project.key], key=lambda value: value.entity_id)
        max_group_rows = max(max_group_rows, (len(group) + 2) // 3)
        for index, node in enumerate(group):
            row, column = divmod(index, 3)
            node.x = 495 + column * 132
            node.y = project.y + (row - (len(group) - 1) / 6) * 104

    collection_nodes: list[GraphNode] = []
    if unassigned:
        center_x = width - 215
        collection = GraphNode(
            key=UNASSIGNED_KEY,
            kind="collection",
            subtype="pool",
            entity_id="unassigned",
            source_id=None,
            label="SIN ASIGNACIÓN",
            subtitle=f"{len(unassigned)} UNIDAD{'ES' if len(unassigned) != 1 else ''}",
            status="Agrupación visual; no es una ubicación física",
            source="Derivado de la ausencia de una asignación verificable en esta lectura",
            age="Conserva la fecha individual de cada unidad",
            member_keys=[node.key for node in unassigned],
            x=center_x,
            y=center_y,
        )
        collection_nodes.append(collection)
        ring = (
            (0, -112),
            (112, 0),
            (0, 112),
            (-112, 0),
            (82, -82),
            (82, 82),
            (-82, 82),
            (-82, -82),
        )
        for index, node in enumerate(unassigned):
            lap, position = divmod(index, len(ring))
            dx, dy = ring[position]
            factor = 1 + lap * 0.58
            node.x = center_x + dx * factor
            node.y = center_y + dy * factor
            node.member_of = collection.key
        height = max(height, int(center_y + 180 + max(0, (len(unassigned) - 1) // 8) * 110))
    return OperationsGraph(
        nodes=[*project_nodes, *collection_nodes, *machine_nodes],
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
    return [
        html.P("Proyecto / obra", className="graph-detail-kicker"),
        html.H2(node.label),
        _facts(
            [
                ("ID original", node.source_id),
                ("Fuente", node.source),
                ("Observación", node.age),
                ("Solicitudes visibles", len(requests)),
                ("Unidades relacionadas", len(connected)),
            ]
        ),
        html.Section(
            [
                html.H3("Asignaciones verificadas"),
                html.Ul(
                    [
                        html.Li(f"{item.label} · {item.source_id or item.entity_id}")
                        for item in connected
                    ]
                )
                if connected
                else html.P("Sin maquinaria relacionada por un ID verificable."),
            ]
        ),
        html.Section(
            [
                html.H3("Solicitudes"),
                html.Ul(
                    [
                        html.Li(
                            [
                                html.Strong(request.provenance.source_id or request.id),
                                html.Span(f" · {request.status}"),
                                html.Br(),
                                html.Span(
                                    f"{request.machinery_type or 'Tipo no informado'} · "
                                    f"{request.starts_on or 'inicio pendiente'} → "
                                    f"{request.ends_on or 'fin pendiente'}"
                                ),
                                html.Br(),
                                html.Span(
                                    "Unidad: "
                                    + (
                                        equipment_by_id[request.machinery_id].label
                                        if request.machinery_id in equipment_by_id
                                        else "sin asignación verificable"
                                    )
                                    + f" · Solicita: {request.requested_by or 'no informado'}"
                                ),
                            ]
                        )
                        for request in requests
                    ]
                )
                if requests
                else html.P("Sin solicitudes dentro de esta lectura."),
            ]
        ),
        html.P(
            "Hay nombres contradictorios para el mismo ID de proyecto; "
            "se conserva el ID como identidad."
            if len(labels) > 1
            else "Las conexiones se derivan de project_id y maquinaria_id, nunca del nombre.",
            className="graph-detail-note",
        ),
    ]


def _collection_detail(node: GraphNode, graph: OperationsGraph):
    members = [candidate for candidate in graph.nodes if candidate.key in node.member_keys]
    available = [member for member in members if member.status.strip().upper() == "DISPONIBLE"]
    other = [member for member in members if member not in available]

    def member_list(values: list[GraphNode]):
        return (
            html.Ul(
                [
                    html.Li(
                        [
                            html.Strong(member.label),
                            html.Span(f" · {member.status}"),
                            html.Br(),
                            html.Span(
                                f"{member.equipment.equipment_class or 'Tipo no informado'} · "
                                f"{member.source_id or member.entity_id}"
                                if member.equipment
                                else member.entity_id
                            ),
                            html.Br(),
                            html.Span(member.age),
                        ]
                    )
                    for member in values
                ]
            )
            if values
            else html.P("Ninguna en esta lectura.")
        )

    return [
        html.P("Agrupación operativa", className="graph-detail-kicker"),
        html.H2("Sin asignación verificada"),
        html.P(
            "Reúne visualmente unidades que no tienen una relación exacta con un proyecto "
            "en la lectura actual.",
            className="graph-detail-subtitle",
        ),
        _facts(
            [
                ("Unidades", len(members)),
                ("Disponibles", len(available)),
                ("Otros estados", len(other)),
                ("Ubicación física", "No proporcionada"),
            ]
        ),
        html.Section([html.H3("Disponibles"), member_list(available)]),
        html.Section([html.H3("Otros estados"), member_list(other)]) if other else None,
        html.P(
            "Este nodo no representa una base, almacén o taller físico. Cuando el origen "
            "exponga un ID y tipo de lugar verificables, podrá mostrarse como ubicación real.",
            className="graph-detail-warning",
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
    destination = (
        transfer.destination_project_name or transfer.destination_project_id or "no informado"
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
                html.Strong(transfer.code or transfer.id),
                html.Span(f" · {transfer.status or 'sin estado'}"),
                html.Br(),
                html.Span(f"Destino: {destination}"),
                html.Br(),
                html.Span("Origen físico: no proporcionado por el servicio normalizado"),
                html.Br(),
                html.Span(f"Responsable: {transfer.driver or 'no informado'}"),
                html.Br(),
                html.Span(f"Programación Startrack: {scheduled or 'no informada'}"),
                html.Br(),
                html.Span(
                    f"Duración planificada: {planned_duration}"
                    if planned_duration
                    else "Duración planificada no informada"
                ),
                html.Br(),
                html.Span(
                    "En traslado · tiempo no disponible"
                    if active
                    else "Sin estimación temporal respaldada por la fuente"
                ),
                html.Br(),
                html.Span(
                    "Presencia del vehículo GPS observada; no acredita recepción."
                    if transfer.arrival_observed
                    else "Sin evidencia de llegada vinculada."
                ),
                html.Br(),
                html.Span(
                    f"Recepción declarada por {transfer.receipt.receiver} · "
                    f"{transfer.receipt.reference}"
                    if transfer.receipt
                    else "Sin constancia de recepción."
                ),
            ]
        )
    ]


def _machine_detail(
    node: GraphNode, hub: HubResponse, workflow: WorkflowOverview | None, graph: OperationsGraph
):
    item = node.equipment
    requests = [request for request in hub.requests if request.machinery_id == node.entity_id]
    project_ids = {
        value
        for value in [
            item.project_id if item else None,
            *(request.project_id for request in requests),
            *(transfer.destination_project_id for transfer in (item.transfers if item else [])),
        ]
        if value
    }
    movements = [
        movement
        for movement in (workflow.movements if workflow else [])
        if item is not None and _movement_matches(item, movement, hub)
    ]
    transfers = item.transfers if item else []
    alerts = [alert for alert in hub.alerts if alert.equipment_id == node.entity_id]
    missing = []
    if item is None:
        missing.append("El registro de la maquinaria no fue devuelto en esta lectura acotada.")
    elif item.location is None:
        missing.append("Ubicación física de la maquinaria no proporcionada.")
    if not project_ids:
        missing.append("Proyecto o ubicación asignada no identificados.")
    if not transfers:
        missing.append("Sin tarea Startrack confirmada para la asignación y período actuales.")
        missing.append("Recepción física no evaluable sin un traslado vinculado.")
    if transfers and all(transfer.receipt is None for transfer in transfers):
        missing.append("Recepción física sin constancia vinculada.")
    if workflow is None or not workflow.available:
        missing.append("Registro persistido de movimientos no disponible en esta vista.")
    elif not workflow.complete:
        missing.append("Registro persistido parcial; puede haber evidencia fuera de la ventana.")
    detail = [
        html.P("Maquinaria", className="graph-detail-kicker"),
        html.H2(node.label),
        html.P(
            item.name if item else "Tipo y descripción no disponibles",
            className="graph-detail-subtitle",
        ),
        _facts(
            [
                ("ID normalizado", node.entity_id),
                ("ID original", node.source_id),
                ("Tipo informado", item.equipment_class if item else None),
                ("Estado administrativo", node.status),
                ("Fuente", node.source),
                ("Observación", node.age),
                ("Proyecto conocido", ", ".join(sorted(project_ids)) or None),
                (
                    "Período de asignación",
                    (
                        f"{item.assignment_starts_on or 'inicio no informado'} → "
                        f"{item.assignment_ends_on or 'fin no informado'}"
                    )
                    if item and (item.assignment_starts_on or item.assignment_ends_on)
                    else None,
                ),
                (
                    "Ubicación observada",
                    item.location.label if item and item.location else None,
                ),
            ]
        ),
    ]
    if item and item.operators is not None:
        detail.append(
            html.Section(
                [
                    html.H3("Operadores asociados en Prisma"),
                    html.Ul(
                        [
                            html.Li(
                                f"{operator.name or 'Nombre no informado'} · "
                                f"{operator.worker_code or operator.id} · "
                                + (
                                    "activo"
                                    if operator.is_active is True
                                    else "inactivo"
                                    if operator.is_active is False
                                    else "vigencia no informada"
                                )
                            )
                            for operator in item.operators
                        ]
                    )
                    if item.operators
                    else html.P("Prisma informó que no hay operadores asociados."),
                ]
            )
        )
    if item and (item.assignment_note or item.project_rate):
        detail.append(
            html.Section(
                [
                    html.H3("Asignación administrativa"),
                    _facts(
                        [
                            ("Nota", item.assignment_note),
                            (
                                "Tarifa horaria informada",
                                item.project_rate.hourly_rate if item.project_rate else None,
                            ),
                            (
                                "Proyecto de la tarifa",
                                item.project_rate.project_id if item.project_rate else None,
                            ),
                        ]
                    ),
                    html.P(
                        "La fuente no aporta aquí una moneda; la tarifa no se interpreta "
                        "como costo de traslado ni como duración.",
                        className="graph-detail-note",
                    )
                    if item.project_rate
                    else None,
                ]
            )
        )
    if item and (
        item.maintenance_failure_id or item.maintenance_status or item.maintenance_is_stopped
    ):
        detail.append(
            html.Section(
                [
                    html.H3("Mantenimiento e incidentes"),
                    _facts(
                        [
                            ("ID de falla", item.maintenance_failure_id),
                            ("Estado de mantenimiento", item.maintenance_status),
                            (
                                "Paro explícito",
                                "Sí" if item.maintenance_is_stopped is True else "No informado",
                            ),
                        ]
                    ),
                ]
            )
        )
    if transfers:
        detail.append(
            html.Section(
                [
                    html.H3("Traslados vinculados"),
                    html.Ul(sum((_transfer_lines(t) for t in transfers), [])),
                ]
            )
        )
    if movements:
        detail.append(
            html.Section(
                [
                    html.H3("Historial y evidencia"),
                    html.Ul(
                        [
                            html.Li(
                                f"{movement.movement_reference} · {movement.state} · "
                                f"{len(movement.events)} evento(s) · destino POI "
                                f"{movement.mapping.get('poi_id') or 'no informado'}"
                            )
                            for movement in movements
                        ]
                    ),
                ]
            )
        )
    if alerts:
        detail.append(
            html.Section(
                [
                    html.H3("Incidentes confirmados por reglas"),
                    html.Ul([html.Li(f"{alert.title}: {alert.description}") for alert in alerts]),
                ],
                className="graph-detail-incidents",
            )
        )
    if len(project_ids) > 1:
        detail.append(
            html.P(
                "Contradicción visible: las fuentes relacionan esta unidad con más de un "
                "proyecto. Revisa los IDs y la vigencia.",
                className="graph-detail-warning",
            )
        )
    if missing:
        detail.append(
            html.Section(
                [html.H3("Datos pendientes"), html.Ul([html.Li(value) for value in missing])]
            )
        )
    detail.append(
        html.P(
            "Mover o ampliar este nodo sólo cambia la vista; nunca modifica Prisma, "
            "Startrack ni el registro operativo.",
            className="graph-detail-note",
        )
    )
    return detail


def _detail(
    node: GraphNode, hub: HubResponse, workflow: WorkflowOverview | None, graph: OperationsGraph
):
    if node.kind == "place":
        content = _project_detail(node, graph)
    elif node.kind == "collection":
        content = _collection_detail(node, graph)
    else:
        content = _machine_detail(node, hub, workflow, graph)
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
    tooltip = " · ".join(
        [node.label, node.source_id or node.entity_id, node.status, node.source, node.age]
    )
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
            "data-members": "|".join(node.member_keys),
            "data-member-of": node.member_of or "",
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
    label = (
        f"TRASLADO · {count or 1} EVIDENCIA"
        if edge.kind == "transfer"
        else f"ASIGNACIÓN · {count or 1} SOLICITUD"
    )
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
        html.P("Conexión operativa", className="graph-detail-kicker"),
        html.H2(heading),
        _facts(
            [
                ("Maquinaria", source.label if source.kind == "machine" else target.label),
                ("Proyecto", target.label if target.kind == "place" else source.label),
                ("Solicitudes", len(requests)),
                ("Traslados", len(transfers)),
                ("Actividad", "En traslado" if edge.active else "Sin actividad confirmada"),
            ]
        ),
        html.Section(
            [
                html.H3("Evidencia de la relación"),
                html.Ul([html.Li(value) for value in dict.fromkeys(edge.evidence)]),
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
                                    html.Strong(request.provenance.source_id or request.id),
                                    html.Span(f" · {request.status}"),
                                    html.Br(),
                                    html.Span(
                                        f"Período solicitado: {request.starts_on or 'pendiente'} "
                                        f"→ {request.ends_on or 'pendiente'}"
                                    ),
                                    html.Br(),
                                    html.Span(
                                        f"Solicita: {request.requested_by or 'no informado'} · "
                                        f"Aprueba: {request.approved_by or 'no informado'}"
                                    ),
                                ]
                            )
                            for request in requests
                        ]
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
        html.P(
            "La línea representa correspondencia documental. Su longitud no representa "
            "distancia, duración, avance ni tiempo restante.",
            className="graph-detail-note",
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
        **{"data-layout-key": layout_key},
    )
