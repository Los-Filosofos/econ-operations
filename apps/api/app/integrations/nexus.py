"""Bounded reads of observed Nexus sandbox routes, with a private cookie session."""

import json
from dataclasses import dataclass
from threading import Lock
from time import monotonic

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from app.core.config import Settings

NEXUS_ORIGIN = "https://econ-key.maic.ai"
MAX_RESPONSE_BYTES = 1_000_000


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
    project_id: str | None = None
    project_name: str | None = None
    active_failure_id: str | None = None
    active_failure_status: str | None = None
    active_failure_is_paro: StrictBool | None = None


class NexusRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    status: str
    project_id: str | None = None
    project_name: str | None = None
    maquinaria_id: str | None = None
    fecha_inicio: str | None = None


class NexusPage[T: BaseModel](BaseModel):
    items: list[T]
    total: StrictInt = Field(ge=0)
    page: StrictInt = Field(ge=1)
    limit: StrictInt = Field(ge=1)


@dataclass
class NexusSnapshot:
    equipment: list[NexusEquipment]
    requests: list[NexusRequest]
    equipment_total: int
    requests_total: int
    complete: bool


class NexusConnector:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._client = httpx.Client(
            base_url=NEXUS_ORIGIN,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "ECON-Hub/0.2"},
        )
        # Serialize reads and reauthentication in this process. No session tokens leave it.
        self._lock = Lock()
        self._authenticated = False

    def close(self) -> None:
        self._client.close()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.nexus_email
            and self.settings.nexus_email.get_secret_value()
            and self.settings.nexus_password
            and self.settings.nexus_password.get_secret_value()
        )

    def _request(self, method: str, path: str, deadline: float, **kwargs) -> tuple[int, bytes]:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise NexusReadError("La lectura superó el tiempo permitido.")
        try:
            with self._client.stream(
                method,
                path,
                timeout=min(remaining, self.settings.nexus_timeout_seconds),
                **kwargs,
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if monotonic() > deadline:
                        raise NexusReadError("La lectura superó el tiempo permitido.")
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise NexusReadError("La respuesta excedió el tamaño de lectura permitido.")
                    body.extend(chunk)
                return response.status_code, bytes(body)
        except httpx.HTTPError:
            raise NexusReadError(
                "No fue posible consultar Nexus dentro del tiempo permitido."
            ) from None

    def _login(self, deadline: float) -> None:
        if not self.configured:
            raise NexusReadError("Faltan las credenciales de lectura de Nexus en el servidor.")
        self._authenticated = False
        self._client.cookies.clear()
        status, body = self._request(
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
            result = json.loads(body)
            success = isinstance(result, dict) and result.get("success") is True
        except (ValueError, UnicodeDecodeError):
            success = False
        if not success or not any(
            cookie.name == "auth-token" for cookie in self._client.cookies.jar
        ):
            raise NexusReadError("Nexus no confirmó una sesión válida.")
        self._authenticated = True

    def _get(self, path: str, params: dict, deadline: float) -> bytes:
        if not self._authenticated:
            self._login(deadline)
        status, body = self._request("GET", path, deadline, params=params)
        if status == 401:
            # Exactly one coordinated reauthentication and repeat of a safe read.
            self._login(deadline)
            status, body = self._request("GET", path, deadline, params=params)
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
        stable_total = True
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
            if total is not None and total != page.total:
                stable_total = False
            total = page.total
            for item in page.items:
                if item.id in seen:
                    stable_total = False
                    continue
                seen.add(item.id)
                records.append(item)
            if not page.items or len(records) >= total:
                break
        return records, total or 0, stable_total and len(records) == total

    def read(self) -> NexusSnapshot:
        deadline = monotonic() + self.settings.nexus_budget_seconds
        if not self._lock.acquire(timeout=self.settings.nexus_budget_seconds):
            raise NexusReadError("Ya hay una lectura de Nexus en curso; intente más tarde.")
        try:
            equipment, equipment_total, equipment_complete = self._pages(
                "/api/maquinaria/equipos", NexusEquipment, deadline
            )
            requests, requests_total, requests_complete = self._pages(
                "/api/maquinaria/requests", NexusRequest, deadline
            )
            return NexusSnapshot(
                equipment,
                requests,
                equipment_total,
                requests_total,
                equipment_complete and requests_complete,
            )
        finally:
            self._lock.release()
