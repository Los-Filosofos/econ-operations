"""Presentation helpers over one bounded hub read; no duplicated alert rules."""

from dataclasses import dataclass
from datetime import date, datetime

from app.models.hub import EquipmentRecord, HubResponse, RequestRecord, TransferRecord
from app.services.hub import BUSINESS_TIMEZONE

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


def day(value: date | str | None) -> str:
    """Dates are shown as documented days; an invalid source value stays visible as-is."""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y") if value else "Sin fecha"


def project_label(record: RequestRecord | EquipmentRecord) -> str:
    return " · ".join(filter(None, [record.project_id, record.project_name])) or "Sin proyecto"


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
