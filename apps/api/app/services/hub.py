"""Shared read projection for HTTP and Dash; never fall back between data modes."""

from datetime import UTC, datetime

from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.integrations.fixtures import (
    FIXTURE_AS_OF,
    FIXTURE_EQUIPMENT_TOTAL,
    FIXTURE_OBSERVED_ON,
    FIXTURE_REQUESTS_TOTAL,
    fixture_records,
)
from app.integrations.nexus import (
    NexusConnector,
    NexusEquipment,
    NexusReadError,
    NexusRequest,
    to_records,
)
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.models.hub import (
    AlertRecord,
    DataMode,
    EquipmentRecord,
    HubResponse,
    HubScope,
    HubSummary,
    OperationEvidenceStatus,
    Provenance,
    RequestRecord,
    SourceStatus,
)
from app.services.evidence import project_operation_evidence
from app.services.intervals import (
    BUSINESS_TIMEZONE,
    IntervalRelation,
    assignment_window_of,
    compare,
    parse_day,
    usage_period_of,
)

__all__ = ["BUSINESS_TIMEZONE", "evaluate_alerts", "map_live", "parse_day", "read_hub"]

PENDING = {"PENDIENTE", "PENDING"}
APPROVED = {"APROBADA", "APPROVED"}
SCOPE_DESCRIPTION = (
    "Los conteos describen únicamente los registros devueltos y el filtro local. "
    "No son KPIs globales, disponibilidad física ni tendencias históricas. "
    "Las muestras del contrato tienen cobertura parcial, sin corte conjunto. "
    "En vivo se consultan páginas acotadas. La evidencia local de Startrack "
    "no acredita una consulta actual ni cobertura integrada completa."
)


def _alert(code: str, key: str, severity: str, title: str, owner: str, **fields) -> AlertRecord:
    return AlertRecord(
        id=f"{code}:{key}", code=code, severity=severity, title=title, owner=owner, **fields
    )


def evaluate_alerts(
    equipment: list[EquipmentRecord], requests: list[RequestRecord], as_of: datetime | None
) -> list[AlertRecord]:
    alerts = []
    for item in equipment:
        if not item.maintenance_failure_id:
            continue
        name = item.asset_number or item.code or item.name
        stopped = item.maintenance_is_stopped
        alerts.append(
            _alert(
                "active_failure",
                item.id,
                "warning",
                f"{name}: falla activa registrada",
                "Mantenimiento",
                equipment_id=item.id,
                description=(
                    "Revisar el diagnóstico y la decisión de paro. Una falla activa no "
                    "equivale por sí sola a indisponibilidad física."
                ),
                evidence=[
                    f"active_failure_id={item.maintenance_failure_id}",
                    f"active_failure_is_paro={stopped if stopped is not None else 'desconocido'}",
                ],
            )
        )
        for transfer in item.transfers:
            pending = (
                transfer.workflow_role.strip().lower() == "pending"
                if transfer.workflow_role is not None
                else transfer.status.upper() in PENDING
            )
            if (
                stopped is True
                and item.relation_status == "confirmed"
                and transfer.evidence_current_assignment
                and pending
            ):
                alerts.append(
                    _alert(
                        "maintenance_blocks_transfer",
                        f"{item.id}:{transfer.id}",
                        "critical",
                        f"{name}: revisar traslado pendiente",
                        "Mantenimiento y Logística",
                        equipment_id=item.id,
                        description=(
                            "Hay una falla con paro y una tarea pendiente vinculada con evidencia."
                        ),
                        evidence=[
                            f"active_failure_id={item.maintenance_failure_id}",
                            "active_failure_is_paro=true",
                            f"transfer={transfer.id}; status={transfer.status}",
                            f"workflow_role={transfer.workflow_role or 'desconocido'}",
                            "relation_status=confirmed",
                        ],
                    )
                )
    for item in requests:
        status = item.status.upper()
        starts_on = parse_day(item.starts_on)
        if (
            status in PENDING
            and starts_on is not None
            and as_of is not None
            and starts_on <= as_of.astimezone(BUSINESS_TIMEZONE).date()
        ):
            alerts.append(
                _alert(
                    "pending_request_started",
                    item.id,
                    "warning",
                    "Solicitud pendiente con inicio alcanzado",
                    "Proyectos y Logística",
                    equipment_id=item.machinery_id,
                    request_id=item.id,
                    description=(
                        "Priorizar revisión y asignación. Esta señal no acredita "
                        "incumplimiento de entrega."
                    ),
                    evidence=[f"status={item.status}", f"fecha_inicio={item.starts_on}"],
                )
            )
        if status in APPROVED and not item.machinery_id:
            alerts.append(
                _alert(
                    "approved_without_equipment",
                    item.id,
                    "warning",
                    "Solicitud aprobada sin unidad vinculada",
                    "Logística",
                    request_id=item.id,
                    description=(
                        "Revisar la asignación; la aprobación no confirma "
                        "una unidad ni un traslado."
                    ),
                    evidence=[f"status={item.status}", "maquinaria_id=ausente"],
                )
            )
    alerts.extend(_interval_alerts(equipment, requests))
    return alerts


def _not_verifiable(
    key: str, relation: IntervalRelation, extra: list[str], **fields
) -> AlertRecord:
    """Incomplete dates never become «sin conflicto»; the absent fields stay visible."""
    return _alert(
        "overlap_not_verifiable",
        key,
        "info",
        "Solapamiento no verificable por fechas ausentes",
        "Logística",
        description=relation.reason,
        evidence=[f"missing={name}" for name in relation.missing] + extra,
        **fields,
    )


def _interval_alerts(
    equipment: list[EquipmentRecord], requests: list[RequestRecord]
) -> list[AlertRecord]:
    """Signals from documented dates only; they never use as_of nor the clock.

    ECON cannot prevent Prisma from approving two requests on one unit or from keeping an
    assignment window that differs from the request: these alerts point at the source facts
    so Logística reviews them there. None of them blocks a preparation.
    """
    alerts: list[AlertRecord] = []
    approved = [r for r in requests if r.status.upper() in APPROVED and r.machinery_id]
    approved.sort(key=lambda r: r.id)
    for index, first in enumerate(approved):
        for second in approved[index + 1 :]:
            if second.machinery_id != first.machinery_id or second.id == first.id:
                continue
            key = f"{first.id}|{second.id}"
            relation = compare(usage_period_of(first), usage_period_of(second))
            evidence = [
                f"solicitud={first.id}; período={usage_period_of(first).span()}",
                f"solicitud={second.id}; período={usage_period_of(second).span()}",
                f"maquinaria_id={first.machinery_id}",
            ]
            if relation.status == "not_verifiable":
                alerts.append(
                    _not_verifiable(key, relation, equipment_id=first.machinery_id, extra=evidence)
                )
            elif relation.status == "overlap":
                alerts.append(
                    _alert(
                        "overlapping_approved_requests",
                        key,
                        "warning",
                        "Dos solicitudes aprobadas sobre la misma unidad con períodos que se "
                        "cruzan",
                        "Logística",
                        equipment_id=first.machinery_id,
                        description=(
                            f"{relation.reason} Prisma admite ambas aprobaciones; ECON solo lo "
                            "señala y no modifica la asignación."
                        ),
                        evidence=evidence,
                    )
                )
    equipment_by_id = {item.id: item for item in equipment}
    for request in approved:
        unit = equipment_by_id.get(request.machinery_id)
        if unit is None or not request.project_id or unit.project_id != request.project_id:
            continue
        usage, window = usage_period_of(request), assignment_window_of(unit)
        relation = compare(usage, window)
        evidence = [
            f"solicitud={request.id}; período={usage.span()}",
            f"maquinaria_id={unit.id}; asignación vigente={window.span()}",
            f"project_id={request.project_id}",
        ]
        if relation.status == "not_verifiable":
            alerts.append(
                _not_verifiable(
                    request.id,
                    relation,
                    equipment_id=unit.id,
                    request_id=request.id,
                    extra=evidence,
                )
            )
        elif (usage.start, usage.end) != (window.start, window.end):
            alerts.append(
                _alert(
                    "assignment_window_differs_from_request",
                    request.id,
                    "info",
                    "La asignación vigente de la unidad no coincide con el período solicitado",
                    "Logística",
                    equipment_id=unit.id,
                    request_id=request.id,
                    description=(
                        "Revisar vigencia en Prisma: la ventana de asignación registrada para la "
                        "unidad difiere del período de uso aprobado en la solicitud del mismo "
                        "proyecto. No es un bloqueo ni una falla."
                    ),
                    evidence=evidence,
                )
            )
    return alerts


def map_live(
    equipment: list[NexusEquipment], requests: list[NexusRequest], observed_at: datetime
) -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    """Current sandbox rows share the read completion instant as their observation time."""

    def provenance(_collection: str, _index: int, source_id: str) -> Provenance:
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=observed_at,
            is_synthetic=True,
        )

    return to_records(
        equipment,
        requests,
        provenance,
        "No hay vínculo validado con una tarea de Startrack. Las solicitudes listadas "
        "se relacionan solo por maquinaria_id exacto; no prueban asignación vigente.",
    )


def _matches(search: str, *values: str | None) -> bool:
    return any(search in (value or "").casefold() for value in values)


def _filter_records(
    equipment: list[EquipmentRecord], requests: list[RequestRecord], search: str
) -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    if not search:
        return equipment, requests
    query = search.casefold()
    matching_requests = [r for r in requests if _matches(query, r.id, r.project_id, r.project_name)]
    request_equipment = {r.machinery_id for r in matching_requests if r.machinery_id}
    equipment = [
        e
        for e in equipment
        if e.id in request_equipment
        or _matches(
            query, e.id, e.code, e.asset_number, e.name, e.project_id, e.project_name, e.company
        )
    ]
    equipment_ids = {e.id for e in equipment}
    request_ids = {r.id for r in matching_requests}
    requests = [r for r in requests if r.id in request_ids or r.machinery_id in equipment_ids]
    return equipment, requests


def _startrack_status(
    settings: Settings, mode: DataMode, client: StartrackClient | None
) -> SourceStatus:
    config = client.config if client is not None else StartrackReadConfig.from_settings(settings)
    if mode == "fixture":
        status, message = (
            "fixture",
            (
                "Las muestras del archivo no contienen tareas de Startrack. "
                "Este modo no consulta el proveedor."
            ),
        )
    elif not settings.allow_live_reads or not config.enabled:
        status, message = (
            "disabled",
            "Las lecturas de Startrack están deshabilitadas en el servidor.",
        )
    elif not config.configured:
        status, message = (
            "not_configured",
            "Faltan credenciales de Startrack configuradas en el servidor.",
        )
    else:
        status, message = (
            "not_queried",
            (
                "SDK configurado; esta lectura no consultó Startrack. "
                "El seguimiento se consulta mediante la sincronización explícita."
            ),
        )
    return SourceStatus(
        id="startrack",
        label="Startrack",
        status=status,
        environment="sandbox",
        configured=config.configured,
        message=message,
    )


def read_hub(
    settings: Settings,
    connector: NexusConnector,
    mode: DataMode = "fixture",
    search: str = "",
    *,
    engine: Engine | None = None,
    startrack: StartrackClient | None = None,
) -> HubResponse:
    """Shared read projection for HTTP and Dash; never fall back between data modes."""
    if mode not in {"fixture", "live"} or len(search) > 100:
        raise ValueError("Consulta inválida: comprueba el origen y la búsqueda.")
    search = search.strip()
    equipment: list[EquipmentRecord] = []
    requests: list[RequestRecord] = []
    observed_at = None
    totals: tuple[int | None, int | None] = (None, None)
    nexus = SourceStatus(
        id="nexus",
        label="Prisma / Nexus",
        status="disabled",
        environment="sandbox",
        message="Las lecturas en vivo están deshabilitadas en este servidor.",
    )
    if mode == "fixture":
        equipment, requests = fixture_records()
        observed_at = FIXTURE_AS_OF
        totals = (FIXTURE_EQUIPMENT_TOTAL, FIXTURE_REQUESTS_TOTAL)
        nexus.status, nexus.observed_on = "fixture", FIXTURE_OBSERVED_ON
        nexus.message = (
            "Muestras sintéticas del OpenAPI proporcionado, documentadas el 12/09/2026. "
            "No tienen un corte conjunto ni acreditan el estado actual del sandbox."
        )
    elif settings.allow_live_reads:
        nexus.status = "not_configured"
        nexus.message = "Faltan credenciales de Nexus configuradas en el servidor."
        if connector.configured:
            try:
                snapshot = connector.read()
                observed_at = nexus.observed_at = datetime.now(UTC)
                equipment, requests = map_live(snapshot.equipment, snapshot.requests, observed_at)
                totals = (snapshot.equipment_total, snapshot.requests_total)
                # Nexus page completion does not imply a complete integrated operation.
                nexus.status = "connected" if snapshot.complete else "partial"
                nexus.message = (
                    "Lectura acotada de Prisma en el sandbox."
                    if snapshot.complete
                    else "Lectura parcial: se alcanzó el límite o cambió la paginación."
                )
            except NexusReadError as error:
                nexus.status, nexus.message = "error", str(error)
    available = mode == "fixture" or nexus.status in {"connected", "partial"}
    equipment, requests = _filter_records(equipment, requests, search)
    hub = HubResponse(
        mode=mode,
        generated_at=datetime.now(UTC),
        data_as_of=observed_at,
        sources=[nexus, _startrack_status(settings, mode, startrack)],
        scope=HubScope(
            search=search,
            equipment_total=totals[0],
            requests_total=totals[1],
            equipment_returned=len(equipment),
            requests_returned=len(requests),
            complete=False,
            description=SCOPE_DESCRIPTION,
        ),
        summary=HubSummary(),
        equipment=equipment,
        requests=requests,
        alerts=[],
    )
    if mode == "live" and not settings.allow_live_reads:
        hub.operation_evidence = OperationEvidenceStatus(
            status="disabled", message="Las lecturas del modo live están deshabilitadas."
        )
    else:
        project_operation_evidence(hub, engine)
    hub.alerts = evaluate_alerts(hub.equipment, hub.requests, observed_at)
    if available:
        hub.summary = HubSummary(
            equipment_count=len(equipment),
            administratively_available=sum(
                e.machinery_status.upper() == "DISPONIBLE" for e in equipment
            ),
            active_failures=sum(bool(e.maintenance_failure_id) for e in equipment),
            stopped_equipment=sum(e.maintenance_is_stopped is True for e in equipment),
            unlinked_equipment=sum(e.relation_status != "confirmed" for e in equipment),
            alerts_count=len(hub.alerts),
        )
    return hub
