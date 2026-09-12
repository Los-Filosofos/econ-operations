from datetime import UTC, date, datetime, timedelta, timezone

from app.core.config import Settings
from app.integrations.fixtures import FIXTURE_AS_OF, fixture_records
from app.integrations.nexus import NexusConnector, NexusReadError, NexusSnapshot
from app.models.hub import (
    AlertRecord,
    DataMode,
    EquipmentRecord,
    HubResponse,
    HubScope,
    HubSummary,
    Provenance,
    RequestRecord,
    SourceStatus,
)

# El Salvador has no daylight-saving offset. Date-only plans stay dates.
BUSINESS_TIMEZONE = timezone(timedelta(hours=-6), name="America/El_Salvador")


def _plan_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is not None:
            return instant.astimezone(BUSINESS_TIMEZONE).date()
    except ValueError:
        pass
    return None


def evaluate_alerts(
    equipment: list[EquipmentRecord], requests: list[RequestRecord], as_of: datetime
) -> list[AlertRecord]:
    alerts = []
    for item in equipment:
        display_name = item.code or item.asset_number or item.name
        if item.maintenance_failure_id:
            stopped = item.maintenance_is_stopped
            alerts.append(
                AlertRecord(
                    id=f"active-failure:{item.id}",
                    code="active_failure",
                    severity="warning",
                    equipment_id=item.id,
                    title=f"{display_name}: falla activa registrada",
                    description=(
                        "Revisar el diagnóstico y la decisión de paro. Una falla activa no "
                        "equivale por sí sola a indisponibilidad física."
                    ),
                    owner="Mantenimiento",
                    evidence=[
                        f"active_failure_id={item.maintenance_failure_id}",
                        "active_failure_is_paro="
                        f"{stopped if stopped is not None else 'desconocido'}",
                    ],
                )
            )
            for transfer in item.transfers:
                if not (
                    stopped is True
                    and item.relation_status == "confirmed"
                    and transfer.status.upper() in {"PENDIENTE", "PENDING"}
                ):
                    continue
                alerts.append(
                    AlertRecord(
                        id=f"maintenance-transfer:{item.id}:{transfer.id}",
                        code="maintenance_blocks_transfer",
                        severity="critical",
                        equipment_id=item.id,
                        title=f"{display_name}: revisar traslado pendiente",
                        description=(
                            "Hay una falla con paro y una tarea pendiente vinculada con evidencia."
                        ),
                        owner="Mantenimiento y Logística",
                        evidence=[
                            f"active_failure_id={item.maintenance_failure_id}",
                            "active_failure_is_paro=true",
                            f"transfer={transfer.id}; status={transfer.status}",
                            "relation_status=confirmed",
                        ],
                    )
                )
    for item in requests:
        status = item.status.upper()
        starts_on = _plan_date(item.starts_on)
        if status in {"PENDIENTE", "PENDING"} and starts_on is not None:
            if starts_on <= as_of.astimezone(BUSINESS_TIMEZONE).date():
                alerts.append(
                    AlertRecord(
                        id=f"pending-start:{item.id}",
                        code="pending_request_started",
                        severity="warning",
                        equipment_id=item.machinery_id,
                        request_id=item.id,
                        title="Solicitud pendiente con inicio alcanzado",
                        description=(
                            "Priorizar revisión y asignación. Esta señal no acredita "
                            "incumplimiento de entrega."
                        ),
                        owner="Proyectos y Logística",
                        evidence=[f"status={item.status}", f"fecha_inicio={item.starts_on}"],
                    )
                )
        if status in {"APROBADA", "APPROVED"} and not item.machinery_id:
            alerts.append(
                AlertRecord(
                    id=f"approved-unassigned:{item.id}",
                    code="approved_without_equipment",
                    severity="warning",
                    request_id=item.id,
                    title="Solicitud aprobada sin unidad vinculada",
                    description=(
                        "Revisar la asignación; la aprobación no confirma "
                        "una unidad ni un traslado."
                    ),
                    owner="Logística",
                    evidence=[f"status={item.status}", "maquinaria_id=ausente"],
                )
            )
    return alerts


def _map_live(
    snapshot: NexusSnapshot, observed_at: datetime
) -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    def provenance(source_id: str) -> Provenance:
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=observed_at,
            is_synthetic=True,
        )

    requests = [
        RequestRecord(
            id=f"nexus:request:{item.id}",
            project_id=item.project_id,
            project_name=item.project_name,
            machinery_id=f"nexus:equipment:{item.maquinaria_id}" if item.maquinaria_id else None,
            status=item.status,
            starts_on=item.fecha_inicio,
            provenance=provenance(item.id),
        )
        for item in snapshot.requests
    ]
    equipment = [
        EquipmentRecord(
            id=f"nexus:equipment:{item.id}",
            code=item.clave,
            asset_number=item.no_activo,
            name=item.nombre,
            company=item.empresa,
            project_id=item.project_id,
            project_name=item.project_name,
            machinery_status=item.estado,
            maintenance_failure_id=item.active_failure_id,
            maintenance_status=item.active_failure_status,
            maintenance_is_stopped=item.active_failure_is_paro,
            request_ids=[r.id for r in requests if r.machinery_id == f"nexus:equipment:{item.id}"],
            relation_status="unlinked",
            relation_note=(
                "No hay vínculo validado con una tarea de Startrack. Las solicitudes listadas "
                "se relacionan solo por maquinaria_id exacto; no prueban asignación vigente."
            ),
            provenance=provenance(item.id),
        )
        for item in snapshot.equipment
    ]
    return equipment, requests


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


def read_hub(
    settings: Settings, connector: NexusConnector, mode: DataMode = "fixture", search: str = ""
) -> HubResponse:
    """Shared read projection for HTTP and Dash; never fall back between data modes."""
    if mode not in {"fixture", "live"} or len(search) > 100:
        raise ValueError("Consulta inválida: comprueba el origen y la búsqueda.")
    generated_at = datetime.now(UTC)
    search = search.strip()
    equipment: list[EquipmentRecord] = []
    requests: list[RequestRecord] = []
    observed_at = None
    equipment_total = requests_total = None
    complete = False
    available = False
    if mode == "fixture":
        equipment, requests = fixture_records()
        observed_at = FIXTURE_AS_OF
        equipment_total, requests_total = len(equipment), len(requests)
        complete = available = True
        sources = [
            SourceStatus(
                id=source,
                label=label,
                status="fixture",
                environment="local",
                observed_at=observed_at,
                message="Casos sintéticos locales; no son lecturas ni copias del sandbox.",
            )
            for source, label in [("nexus", "Prisma / Nexus"), ("startrack", "Startrack")]
        ]
    else:
        nexus_status = "disabled"
        message = "Las lecturas en vivo están deshabilitadas en este servidor."
        if settings.allow_live_reads:
            nexus_status = "not_configured"
            message = "Faltan credenciales de Nexus configuradas en el servidor."
            if connector.configured:
                try:
                    snapshot = connector.read()
                    observed_at = datetime.now(UTC)
                    equipment, requests = _map_live(snapshot, observed_at)
                    equipment_total, requests_total = (
                        snapshot.equipment_total,
                        snapshot.requests_total,
                    )
                    available = True
                    # Nexus page completion does not imply a complete integrated operation.
                    nexus_status = "connected" if snapshot.complete else "partial"
                    message = (
                        "Lectura acotada del sandbox; Startrack y los vínculos siguen pendientes."
                        if snapshot.complete
                        else "Lectura parcial: se alcanzó el límite o cambió la paginación."
                    )
                except NexusReadError as error:
                    nexus_status, message = "error", str(error)
        sources = [
            SourceStatus(
                id="nexus",
                label="Prisma / Nexus",
                status=nexus_status,
                environment="sandbox",
                observed_at=observed_at,
                message=message,
            ),
            SourceStatus(
                id="startrack",
                label="Startrack",
                status="not_configured",
                environment="sandbox",
                message="API key pendiente; no hay lecturas autenticadas ni vínculos verificados.",
            ),
        ]
    equipment, requests = _filter_records(equipment, requests, search)
    alerts = evaluate_alerts(equipment, requests, observed_at or generated_at)
    summary = HubSummary()
    if available:
        summary = HubSummary(
            equipment_count=len(equipment),
            administratively_available=sum(
                e.machinery_status.upper() == "DISPONIBLE" for e in equipment
            ),
            active_failures=sum(bool(e.maintenance_failure_id) for e in equipment),
            stopped_equipment=sum(e.maintenance_is_stopped is True for e in equipment),
            unlinked_equipment=sum(e.relation_status != "confirmed" for e in equipment),
            alerts_count=len(alerts),
        )
    return HubResponse(
        mode=mode,
        generated_at=datetime.now(UTC),
        data_as_of=observed_at,
        sources=sources,
        scope=HubScope(
            search=search,
            equipment_total=equipment_total,
            requests_total=requests_total,
            equipment_returned=len(equipment),
            requests_returned=len(requests),
            complete=complete,
            description=(
                "Los conteos describen únicamente los registros devueltos y el filtro local. "
                "No son KPIs globales, disponibilidad física ni tendencias históricas. "
                "En vivo se consultan páginas acotadas y Startrack permanece pendiente."
            ),
        ),
        summary=summary,
        equipment=equipment,
        requests=requests,
        alerts=alerts,
    )
