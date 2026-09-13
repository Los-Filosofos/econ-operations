"""Bounded Startrack reads and independently gated task creation.

Contract reviewed on 2026-09-12:
https://support.gps-platform.com/api/intro/
https://support.gps-platform.com/api/jobs/
https://support.gps-platform.com/api/pois/

The sandbox response contract still needs an authorized, authenticated check.
This client is deliberately not mounted in the public hub or enabled by default.
"""

import json
from collections import deque
from datetime import UTC, date, datetime
from time import monotonic
from typing import Annotated, Literal, Self

import httpx
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
    StrictBool,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from app.core.config import Settings
from app.integrations.http import MAX_RESPONSE_BYTES, BoundedClient

STARTRACK_ORIGIN = "https://staging.gps.gt"
TIME_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$"
__all__ = ["MAX_RESPONSE_BYTES", "StartrackClient"]
Identifier = Annotated[str, StringConstraints(strict=True, min_length=1, pattern=r"^\S+$")]


def _explicit_date(value: object) -> object:
    # Reject epochs and timestamps before Pydantic could coerce them into a day.
    if type(value) is date:
        return value
    try:
        if isinstance(value, str) and date.fromisoformat(value).isoformat() == value:
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise ValueError("La fecha debe ser una fecha explícita con formato YYYY-MM-DD.")


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ValueError("Los IDs no deben repetirse.")
    return values


def _numeric_source_id(value: object) -> object:
    # Reports and job-type examples use JSON integers, while jobs use strings.
    # Never coerce floats/bools or reformat an existing string such as "00042".
    return str(value) if type(value) is int and value >= 0 else value


ExplicitDate = Annotated[date, BeforeValidator(_explicit_date)]
UniqueIds = Annotated[tuple[Identifier, ...], AfterValidator(_unique)]
ReportIdentifier = Annotated[Identifier, BeforeValidator(_numeric_source_id)]


class StartrackReadError(Exception):
    """Fixed safe messages only; never expose provider bodies or credentials."""


class StartrackWriteRejected(Exception):
    """The request was not sent or the provider explicitly rejected it."""


class StartrackWriteUnknown(Exception):
    """Creation may have succeeded. Reconcile externally; never automatically POST again."""


class StartrackReadConfig(BaseModel):
    """Server-owned options; intentionally independent of browser state."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    enabled: StrictBool = False
    allow_writes: StrictBool = False
    api_key: SecretStr | None = Field(default=None, repr=False, exclude=True)
    password: SecretStr | None = Field(default=None, repr=False, exclude=True)
    page_size: int = Field(default=25, ge=1, le=100, strict=True)
    max_pages: int = Field(default=2, ge=1, le=10, strict=True)
    timeout_seconds: float = Field(default=5, gt=0, le=30, allow_inf_nan=False)
    budget_seconds: float = Field(default=20, gt=0, le=60, allow_inf_nan=False)
    max_report_records: int = Field(default=1000, ge=1, le=5000, strict=True)

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            enabled=settings.allow_live_reads,
            allow_writes=settings.allow_live_writes,
            api_key=settings.startrack_api_key,
            password=settings.startrack_password,
            page_size=settings.startrack_page_size,
            max_pages=settings.startrack_max_pages,
            timeout_seconds=settings.startrack_timeout_seconds,
            budget_seconds=settings.startrack_budget_seconds,
        )

    @property
    def configured(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.get_secret_value().strip()
            and self.password
            and self.password.get_secret_value().strip()
        )


class StartrackJob(BaseModel):
    """Source IDs and dates are retained without interpreting task completion as receipt."""

    model_config = ConfigDict(extra="ignore")

    id: Identifier
    objective: str
    start_date: str
    start_time: str | None = None
    description: str | None = None
    remote_id: str | None = None
    status: str | None = None
    poi_id: str | None = None
    assigned_user_ids: list[str] | None = None
    creation_date: str | None = None
    changed_date: str | None = None
    closed_date: str | None = None
    last_status_change_date: str | None = None
    job_type_id: str | None = None
    form_ids: list[str] | None = None
    required_form_ids: list[str] | None = None


class StartrackPoi(BaseModel):
    """Only the fields needed to review an explicit project-to-geofence mapping."""

    model_config = ConfigDict(extra="ignore")

    id: Identifier
    name: str
    remote_id: str | None = None
    creation_date: str | None = None
    changed_date: str | None = None


class StartrackUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Identifier
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    mobile_worker_app_enabled: StrictBool | None = None


class StartrackVehicle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Identifier
    description: str | None = None
    vin: str | None = None
    driver_id: str | None = None
    creation_date: str | None = None
    changed_date: str | None = None
    deactivated: str | None = None


class StartrackJobStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Identifier
    name: str | None = None
    workflow_role: str | None = None
    deactivated: str | None = None


class StartrackJobType(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: ReportIdentifier
    name: str
    remote_id: str | None = None
    deactivated: StrictBool | str | None = None


class StartrackVisit(BaseModel):
    """An observed presence at a POI, never a confirmation of machinery receipt."""

    model_config = ConfigDict(extra="ignore")

    id: ReportIdentifier
    poi_id: ReportIdentifier
    vehicle_id: ReportIdentifier | None = None
    driver_id: ReportIdentifier | None = None
    start_date: str
    end_date: str | None = None


class StartrackPage[T: BaseModel](BaseModel):
    success: StrictBool
    data: list[T]


class StartrackReadResult[T: BaseModel](BaseModel):
    items: list[T]
    observed_at: datetime
    pages_read: int
    exhausted: bool
    # The documented response has no total, cursor or consistent snapshot guarantee.
    complete: Literal[False] = False
    source: Literal["startrack"] = "startrack"
    environment: Literal["sandbox"] = "sandbox"
    is_synthetic: Literal[True] = True


class StartrackTaskDraft(BaseModel):
    """A validated local proposal, not evidence that a task or mapping exists.

    IDs must come from explicitly reviewed mappings. In particular, remote_id
    is a correlation value, not a documented uniqueness or idempotency guarantee.
    Payload validity does not verify permissions, IDs or provider acceptance.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: Annotated[str, StringConstraints(min_length=1, max_length=255, pattern=r"\S")]
    start_date: ExplicitDate
    remote_id: Identifier
    poi_id: Identifier
    assigned_user_ids: UniqueIds = Field(min_length=1)
    description: str | None = None
    start_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    job_type_id: Identifier | None = None
    form_ids: UniqueIds | None = None
    required_form_ids: UniqueIds | None = None
    notify_contact: Literal[False] = False

    @model_validator(mode="after")
    def required_forms_are_associated(self) -> Self:
        if self.required_form_ids and not set(self.required_form_ids) <= set(self.form_ids or ()):
            raise ValueError("Los formularios obligatorios deben estar asociados a la tarea.")
        return self

    def payload(self) -> dict:
        """Return documented body fields for review, without sending a request."""
        return self.model_dump(mode="json", exclude_none=True)


class StartrackClient(BoundedClient):
    error = StartrackReadError

    def __init__(self, config: StartrackReadConfig, transport: httpx.BaseTransport | None = None):
        super().__init__(STARTRACK_ORIGIN, "Startrack", config.timeout_seconds, transport)
        self.config = config
        self._report_calls: deque[float] = deque()

    @property
    def configured(self) -> bool:
        return self.config.configured

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(
            self.config.api_key.get_secret_value(), self.config.password.get_secret_value()
        )

    def _get(self, path: str, params: dict, deadline: float) -> bytes:
        status, body = self._bounded("GET", path, deadline, params=params, auth=self._auth())
        if status == 401:
            raise StartrackReadError("Startrack rechazó las credenciales de API.")
        if status == 403:
            raise StartrackReadError("La cuenta de Startrack no permite esta lectura.")
        if status in (429, 529):
            raise StartrackReadError(
                "Startrack limitó temporalmente las consultas; intente más tarde."
            )
        if status != 200:
            raise StartrackReadError("Startrack no devolvió una lectura válida.")
        return body

    def _report_slot(self) -> None:
        # Report endpoints are locally capped to 10 calls per 5 minutes; never sleep or retry.
        now = monotonic()
        while self._report_calls and now - self._report_calls[0] >= 300:
            self._report_calls.popleft()
        if len(self._report_calls) >= 10:
            raise StartrackReadError(
                "Se alcanzó el límite local de informes de Startrack; intente más tarde."
            )
        self._report_calls.append(now)

    def _read[T: BaseModel](
        self,
        path: str,
        model: type[T],
        *,
        params: dict | None = None,
        paginated: bool = True,
        fields_and_sort: bool = True,
        report: bool = False,
    ) -> StartrackReadResult[T]:
        if not self.config.enabled:
            raise StartrackReadError("Las lecturas de Startrack están deshabilitadas.")
        if not self.configured:
            raise StartrackReadError("Faltan las credenciales de API de Startrack en el servidor.")
        items: list[T] = []
        seen: set[str] = set()
        exhausted = False
        record_limit = self.config.page_size if paginated else self.config.max_report_records
        with self._exclusive(self.config.budget_seconds) as deadline:
            if report:
                self._report_slot()
            for page_number in range(self.config.max_pages if paginated else 1):
                query = dict(params or {})
                if paginated:
                    query.update(page_size=self.config.page_size, page_num=page_number)
                if fields_and_sort:
                    query.update(sort_by="id", sort_dir="asc", fields=",".join(model.model_fields))
                try:
                    page = StartrackPage[model].model_validate_json(
                        self._get(path, query, deadline)
                    )
                except ValidationError:
                    raise StartrackReadError(
                        "El formato de Startrack cambió; el cliente requiere revisión."
                    ) from None
                if not page.success:
                    raise StartrackReadError("Startrack no confirmó una lectura válida.")
                if len(page.data) > record_limit:
                    raise StartrackReadError("Startrack excedió el límite de registros solicitado.")
                if seen.intersection(item.id for item in page.data) or len(
                    {item.id for item in page.data}
                ) < len(page.data):
                    raise StartrackReadError(
                        "Startrack devolvió IDs repetidos; la paginación requiere revisión."
                    )
                seen.update(item.id for item in page.data)
                items.extend(page.data)
                if paginated and len(page.data) < self.config.page_size:
                    exhausted = True
                    break
        return StartrackReadResult[model](
            items=items,
            observed_at=datetime.now(UTC),
            pages_read=page_number + 1,
            exhausted=exhausted,
        )

    def list_jobs(self) -> StartrackReadResult[StartrackJob]:
        return self._read("/api/job", StartrackJob)

    def list_pois(self) -> StartrackReadResult[StartrackPoi]:
        return self._read("/api/pois", StartrackPoi)

    def list_users(self) -> StartrackReadResult[StartrackUser]:
        return self._read("/api/user", StartrackUser, paginated=False, fields_and_sort=False)

    def list_vehicles(self) -> StartrackReadResult[StartrackVehicle]:
        return self._read("/api/vehicles", StartrackVehicle, fields_and_sort=False)

    def list_job_statuses(self) -> StartrackReadResult[StartrackJobStatus]:
        return self._read("/api/job/status", StartrackJobStatus)

    def list_job_types(self) -> StartrackReadResult[StartrackJobType]:
        return self._read("/api/job/type", StartrackJobType)

    @staticmethod
    def _filter(field: Literal["id", "remote_id"], value: str) -> dict:
        try:
            TypeAdapter(Identifier).validate_python(value)
        except ValidationError:
            raise StartrackReadError("El identificador de consulta no es válido.") from None
        # The provider interprets these as filter separators; percent-encoding does not escape them.
        if "|" in value or "," in value:
            raise StartrackReadError(
                "El identificador contiene separadores de filtro no admitidos."
            )
        return {"filter_by": field, "filter_values": value, "filter_comp": "equal"}

    def find_pois_by_remote_id(self, remote_id: str) -> StartrackReadResult[StartrackPoi]:
        """Look up a destination geofence by its documented external reference.

        This resolves a project-to-geofence correspondence by ID instead of by name.
        It never creates a POI: the geometry and the destination decision belong to
        Startrack and to the person who confirms the mapping.
        """
        result = self._read("/api/pois", StartrackPoi, params=self._filter("remote_id", remote_id))
        if any(item.remote_id != remote_id for item in result.items):
            raise StartrackReadError("Startrack no respetó el filtro de referencia solicitado.")
        return result

    def find_jobs_by_remote_id(self, remote_id: str) -> StartrackReadResult[StartrackJob]:
        result = self._read("/api/job", StartrackJob, params=self._filter("remote_id", remote_id))
        if any(item.remote_id != remote_id for item in result.items):
            raise StartrackReadError("Startrack no respetó el filtro de referencia solicitado.")
        return result

    def get_job(self, job_id: str) -> StartrackJob | None:
        """Return an exact-ID match; None means absent from this bounded provider response."""
        result = self._read("/api/job", StartrackJob, params=self._filter("id", job_id))
        if any(item.id != job_id for item in result.items) or len(result.items) > 1:
            raise StartrackReadError("Startrack no respetó el ID de tarea solicitado.")
        return result.items[0] if result.items else None

    @staticmethod
    def _report_ids(values: tuple[str, ...]) -> str:
        if not 0 < len(values) <= 100 or any(
            not isinstance(v, str) or not v.isascii() or not v.isdecimal() for v in values
        ):
            raise StartrackReadError("El informe requiere IDs numéricos explícitos y acotados.")
        return ",".join(values)

    def list_visits(
        self,
        *,
        start_date: date,
        end_date: date,
        poi_ids: tuple[str, ...],
        vehicle_ids: tuple[str, ...] = (),
        driver_ids: tuple[str, ...] = (),
    ) -> StartrackReadResult[StartrackVisit]:
        if (
            type(start_date) is not date
            or type(end_date) is not date
            or not 0 <= (end_date - start_date).days < 7
        ):
            raise StartrackReadError("El informe requiere fechas explícitas de hasta siete días.")
        if bool(vehicle_ids) == bool(driver_ids):
            raise StartrackReadError("Seleccione vehículos o conductores para acotar las visitas.")
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_time": "00:00:00",
            "end_time": "23:59:59",
            "pois": self._report_ids(poi_ids),
        }
        if vehicle_ids:
            params.update(findby="veh", vehicle_ids=self._report_ids(vehicle_ids))
        else:
            params.update(findby="driver", driver_ids=self._report_ids(driver_ids))
        result = self._read(
            "/api/visits",
            StartrackVisit,
            params=params,
            paginated=False,
            fields_and_sort=False,
            report=True,
        )
        if any(
            item.poi_id not in poi_ids
            or (vehicle_ids and item.vehicle_id not in vehicle_ids)
            or (driver_ids and item.driver_id not in driver_ids)
            for item in result.items
        ):
            raise StartrackReadError("Startrack devolvió visitas fuera del alcance solicitado.")
        return result

    def create_job(self, draft: StartrackTaskDraft) -> StartrackJob:
        """One POST only. The durable caller must reconcile unknown outcomes before any new send."""
        if not self.config.allow_writes:
            raise StartrackWriteRejected("Las escrituras de Startrack están deshabilitadas.")
        if not self.configured:
            raise StartrackWriteRejected(
                "Faltan las credenciales de API de Startrack en el servidor."
            )
        try:
            # Revalidate even frozen models copied with unvalidated updates.
            draft = StartrackTaskDraft.model_validate(draft.model_dump())
        except (ValidationError, AttributeError):
            raise StartrackWriteRejected("El borrador de tarea no es válido.") from None
        payload = {
            key: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if isinstance(value, list)
            else str(value)
            for key, value in draft.payload().items()
        }
        # PHP-style form booleans: string "false" may otherwise be interpreted as true.
        payload["notify_contact"] = "0"
        with self._exclusive(self.config.budget_seconds, StartrackWriteRejected) as deadline:
            status, body = self._bounded(
                "POST", "/api/job", deadline, StartrackWriteUnknown, data=payload, auth=self._auth()
            )
        if 400 <= status < 500 and status != 408:
            raise StartrackWriteRejected("Startrack rechazó la creación de la tarea.")
        if status not in (200, 201):
            raise StartrackWriteUnknown(
                "No se confirmó la creación; concilie la tarea antes de reenviar."
            )
        try:
            result = json.loads(body)
            if isinstance(result, dict) and result.get("success") is False:
                if isinstance(result.get("data"), dict) and result["data"].get("id"):
                    raise StartrackWriteUnknown("La respuesta de creación es contradictoria.")
                raise StartrackWriteRejected("Startrack rechazó la creación de la tarea.")
            if not isinstance(result, dict) or result.get("success") is not True:
                raise ValueError
            created = StartrackJob.model_validate(result["data"])
            if created.remote_id is not None and created.remote_id != draft.remote_id:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise StartrackWriteUnknown(
                "Startrack no confirmó un ID válido; concilie la tarea antes de reenviar."
            ) from None
        return created
