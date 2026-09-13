"""Bounded reads of observed Nexus sandbox routes, with a private cookie session."""

import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from app.core.config import Settings
from app.integrations.http import MAX_RESPONSE_BYTES, BoundedClient
from app.models.hub import EquipmentRecord, Provenance, RequestRecord

NEXUS_ORIGIN = "https://econ-key.maic.ai"
__all__ = ["MAX_RESPONSE_BYTES", "NexusConnector", "NexusReadError", "NexusSnapshot"]


class NexusReadError(Exception):
    """Only fixed, public messages are allowed; upstream content is never included."""


class NexusEquipment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    clave: str | None
    no_activo: str | None = None
    nombre: str
    estado: str
    empresa: str | None = None
    clase_equipo: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    active_failure_id: str | None = None
    active_failure_status: str | None = None
    active_failure_is_paro: StrictBool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NexusRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    status: str
    project_id: str | None = None
    project_name: str | None = None
    maquinaria_id: str | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    tipo: str | None = None
    requested_by_name: str | None = None
    requested_by_user_id: str | None = None
    comentarios: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by_user_id: str | None = None
    operador_id: str | None = None


class NexusPage[T: BaseModel](BaseModel):
    items: list[T]
    total: StrictInt = Field(ge=0)
    page: StrictInt = Field(ge=1)
    limit: StrictInt = Field(ge=1)


class NexusSnapshot(BaseModel):
    equipment: list[NexusEquipment]
    requests: list[NexusRequest]
    equipment_total: int
    requests_total: int
    complete: bool


ProvenanceFactory = Callable[[str, int, str], Provenance]


def to_records(
    equipment: list[NexusEquipment],
    requests: list[NexusRequest],
    provenance: ProvenanceFactory,
    relation_note: str,
) -> tuple[list[EquipmentRecord], list[RequestRecord]]:
    """Project source rows onto the read contract; requests link only by exact maquinaria_id."""
    request_records = [
        RequestRecord(
            id=f"nexus:request:{item.id}",
            project_id=item.project_id,
            project_name=item.project_name,
            machinery_id=f"nexus:equipment:{item.maquinaria_id}" if item.maquinaria_id else None,
            status=item.status,
            starts_on=item.fecha_inicio,
            ends_on=item.fecha_fin,
            machinery_type=item.tipo,
            requested_by=item.requested_by_name,
            requested_by_id=item.requested_by_user_id,
            comments=item.comentarios,
            created_at=item.created_at,
            updated_at=item.updated_at,
            approved_at=item.approved_at,
            approved_by_user_id=item.approved_by_user_id,
            provenance=provenance("requests", index, item.id),
        )
        for index, item in enumerate(requests)
    ]
    equipment_records = [
        EquipmentRecord(
            id=f"nexus:equipment:{item.id}",
            code=item.clave,
            asset_number=item.no_activo,
            name=item.nombre,
            company=item.empresa,
            equipment_class=item.clase_equipo,
            project_id=item.project_id,
            project_name=item.project_name,
            machinery_status=item.estado,
            maintenance_failure_id=item.active_failure_id,
            maintenance_status=item.active_failure_status,
            maintenance_is_stopped=item.active_failure_is_paro,
            request_ids=[
                r.id for r in request_records if r.machinery_id == f"nexus:equipment:{item.id}"
            ],
            relation_status="unlinked",
            relation_note=relation_note,
            provenance=provenance("equipment", index, item.id),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for index, item in enumerate(equipment)
    ]
    return equipment_records, request_records


class NexusConnector(BoundedClient):
    error = NexusReadError

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        super().__init__(NEXUS_ORIGIN, "Nexus", settings.nexus_timeout_seconds, transport)
        self.settings = settings
        self._authenticated = False

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.nexus_email
            and self.settings.nexus_email.get_secret_value()
            and self.settings.nexus_password
            and self.settings.nexus_password.get_secret_value()
        )

    def _login(self, deadline: float) -> None:
        if not self.configured:
            raise NexusReadError("Faltan las credenciales de lectura de Nexus en el servidor.")
        self._authenticated = False
        self._client.cookies.clear()
        status, body = self._bounded(
            "POST",
            "/api/auth/login",
            deadline,
            json={
                "email": self.settings.nexus_email.get_secret_value(),
                "password": self.settings.nexus_password.get_secret_value(),
            },
        )
        if status != 200:
            raise NexusReadError("Nexus rechazó la autenticación de la cuenta configurada.")
        try:
            success = json.loads(body).get("success") is True
        except (ValueError, AttributeError):
            success = False
        if not success or not any(c.name == "auth-token" for c in self._client.cookies.jar):
            raise NexusReadError("Nexus no confirmó una sesión válida.")
        self._authenticated = True

    def _get(self, path: str, params: dict, deadline: float) -> bytes:
        if not self._authenticated:
            self._login(deadline)
        status, body = self._bounded("GET", path, deadline, params=params)
        if status == 401:
            # Exactly one coordinated reauthentication and repeat of a safe read.
            self._login(deadline)
            status, body = self._bounded("GET", path, deadline, params=params)
        if status == 401:
            self._authenticated = False
            raise NexusReadError("Nexus no autorizó la lectura después de reautenticar.")
        if status == 403:
            raise NexusReadError("La cuenta de Nexus no tiene permiso para esta lectura.")
        if status == 429:
            raise NexusReadError("Nexus limitó temporalmente las consultas; intente más tarde.")
        if status != 200:
            raise NexusReadError("Nexus no devolvió una lectura válida.")
        return body

    def _pages[T: BaseModel](
        self, path: str, model: type[T], deadline: float
    ) -> tuple[list[T], int, bool]:
        records: list[T] = []
        seen: set[str] = set()
        total: int | None = None
        stable = True
        for page_number in range(1, self.settings.nexus_max_pages + 1):
            body = self._get(
                path, {"page": page_number, "limit": self.settings.nexus_page_size}, deadline
            )
            try:
                page = NexusPage[model].model_validate_json(body)
            except ValidationError:
                raise NexusReadError(
                    "El formato de Nexus cambió; el conector requiere revisión."
                ) from None
            if page.page != page_number or page.limit != self.settings.nexus_page_size:
                raise NexusReadError("Nexus devolvió una paginación inesperada.")
            if len(page.items) > self.settings.nexus_page_size:
                raise NexusReadError("Nexus excedió el límite de registros solicitado.")
            stable = stable and total in (None, page.total)
            total = page.total
            for item in page.items:
                stable = stable and item.id not in seen
                if item.id not in seen:
                    seen.add(item.id)
                    records.append(item)
            if not page.items or len(records) >= total:
                break
        return records, total or 0, stable and len(records) == total

    def read(self) -> NexusSnapshot:
        with self._exclusive(self.settings.nexus_budget_seconds) as deadline:
            equipment, equipment_total, equipment_complete = self._pages(
                "/api/maquinaria/equipos", NexusEquipment, deadline
            )
            requests, requests_total, requests_complete = self._pages(
                "/api/maquinaria/requests", NexusRequest, deadline
            )
        return NexusSnapshot(
            equipment=equipment,
            requests=requests,
            equipment_total=equipment_total,
            requests_total=requests_total,
            complete=equipment_complete and requests_complete,
        )

    def _detail[T: BaseModel](self, path: str, identifier: str, model: type[T]) -> T:
        try:
            if len(identifier) != 36:
                raise ValueError
            UUID(identifier)
        except (TypeError, ValueError):
            raise NexusReadError("La consulta requiere un UUID de origen válido.") from None
        with self._exclusive(self.settings.nexus_budget_seconds) as deadline:
            body = self._get(f"{path}/{identifier}", {}, deadline)
        try:
            item = model.model_validate_json(body)
        except ValidationError:
            raise NexusReadError(
                "El detalle de Nexus cambió; el conector requiere revisión."
            ) from None
        if item.id != identifier:
            raise NexusReadError("Nexus devolvió un ID distinto al solicitado.")
        return item

    def get_request(self, request_id: str) -> NexusRequest:
        return self._detail("/api/maquinaria/requests", request_id, NexusRequest)

    def get_equipment(self, equipment_id: str) -> NexusEquipment:
        return self._detail("/api/maquinaria/equipos", equipment_id, NexusEquipment)
