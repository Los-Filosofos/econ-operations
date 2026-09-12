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
from threading import Lock
from time import monotonic
from typing import Annotated, Literal, Self

import httpx
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    SecretStr,
    StrictBool,
    StrictInt,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

STARTRACK_ORIGIN = "https://staging.gps.gt"
MAX_RESPONSE_BYTES = 1_000_000
Identifier = Annotated[str, StringConstraints(strict=True, min_length=1, pattern=r"^\S+$")]


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


def _numeric_source_id(value: object) -> object:
    # Reports and job-type examples use JSON integers, while jobs use strings.
    # Never coerce floats/bools or reformat an existing string such as "00042".
    return str(value) if type(value) is int and value >= 0 else value


ReportIdentifier = Annotated[Identifier, BeforeValidator(_numeric_source_id)]


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


class StartrackFormJob(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: ReportIdentifier
    title: str | None = None
    remote_id: str | None = None


class StartrackFormPoi(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: ReportIdentifier
    name: str | None = None


class StartrackFormResponse(BaseModel):
    """Original Unix instants and explicit associations, without inferring acceptance."""

    model_config = ConfigDict(extra="ignore")

    id: ReportIdentifier
    user_id: ReportIdentifier | None = None
    date: StrictInt
    server_date: StrictInt | None = None
    gps_epoch: StrictInt | None = None
    driver_id: ReportIdentifier | None = None
    vehicle_id: ReportIdentifier | None = None
    job: StartrackFormJob | None = None
    poi: StartrackFormPoi | None = None
    answers: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def retain_question_answers(cls, value: object) -> object:
        if isinstance(value, dict):
            value = dict(value)
            supplied_answers = value.get("answers", {})
            if not isinstance(supplied_answers, dict):
                raise ValueError("Las respuestas del formulario requieren un objeto.")
            value["answers"] = supplied_answers | {
                key: answer for key, answer in value.items() if key.isdecimal()
            }
        return value


class StartrackFormPage(BaseModel):
    success: StrictBool
    responses: list[StartrackFormResponse]


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

    objective: str = Field(min_length=1, max_length=255)
    start_date: date
    remote_id: Identifier
    poi_id: Identifier
    assigned_user_ids: tuple[Identifier, ...] = Field(min_length=1)
    description: str | None = None
    start_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
    job_type_id: Identifier | None = None
    form_ids: tuple[Identifier, ...] | None = None
    required_form_ids: tuple[Identifier, ...] | None = None
    notify_contact: Literal[False] = False

    @field_validator("objective")
    @classmethod
    def objective_has_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La tarea requiere un objetivo explícito.")
        return value

    @field_validator("start_date", mode="before")
    @classmethod
    def explicit_date_only(cls, value: object) -> object:
        if type(value) is date:
            return value
        if isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                pass
            else:
                if parsed.isoformat() == value:
                    return parsed
        raise ValueError("La fecha debe ser una fecha explícita con formato YYYY-MM-DD.")

    @field_validator("assigned_user_ids")
    @classmethod
    def unique_assignments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("Los IDs de usuarios asignados no deben repetirse.")
        return value

    def payload(self) -> dict:
        """Return documented body fields for review, without sending a request."""
        return self.model_dump(mode="json", exclude_none=True)

    @model_validator(mode="after")
    def validate_forms(self) -> Self:
        for values in (self.form_ids, self.required_form_ids):
            if values is not None and len(values) != len(set(values)):
                raise ValueError("Los IDs de formularios no deben repetirse.")
        if self.required_form_ids and not set(self.required_form_ids) <= set(self.form_ids or ()):
            raise ValueError("Los formularios obligatorios deben estar asociados a la tarea.")
        return self


class StartrackClient:
    def __init__(self, config: StartrackReadConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._lock = Lock()
        self._report_calls: deque[float] = deque()
        self._client = httpx.Client(
            base_url=STARTRACK_ORIGIN,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "ECON-Hub/0.2"},
        )

    def close(self) -> None:
        self._client.close()

    @property
    def configured(self) -> bool:
        return bool(
            self.config.api_key
            and self.config.api_key.get_secret_value().strip()
            and self.config.password
            and self.config.password.get_secret_value().strip()
        )

    def _get(self, path: str, params: dict, deadline: float) -> bytes:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise StartrackReadError("La lectura de Startrack superó el tiempo permitido.")
        try:
            with self._client.stream(
                "GET",
                path,
                params=params,
                auth=httpx.BasicAuth(
                    self.config.api_key.get_secret_value(),
                    self.config.password.get_secret_value(),
                ),
                timeout=min(remaining, self.config.timeout_seconds),
            ) as response:
                if response.status_code == 401:
                    raise StartrackReadError("Startrack rechazó las credenciales de API.")
                if response.status_code == 403:
                    raise StartrackReadError("La cuenta de Startrack no permite esta lectura.")
                if response.status_code in (429, 529):
                    raise StartrackReadError(
                        "Startrack limitó temporalmente las consultas; intente más tarde."
                    )
                if response.status_code != 200:
                    raise StartrackReadError("Startrack no devolvió una lectura válida.")
                body = bytearray()
                for chunk in response.iter_bytes():
                    if monotonic() > deadline:
                        raise StartrackReadError(
                            "La lectura de Startrack superó el tiempo permitido."
                        )
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise StartrackReadError(
                            "La respuesta de Startrack excedió el tamaño permitido."
                        )
                    body.extend(chunk)
                if monotonic() > deadline:
                    raise StartrackReadError("La lectura de Startrack superó el tiempo permitido.")
                return bytes(body)
        except httpx.HTTPError:
            raise StartrackReadError(
                "No fue posible consultar Startrack dentro del tiempo permitido."
            ) from None

    def _read[T: BaseModel](
        self,
        path: str,
        model: type[T],
        *,
        params: dict | None = None,
        paginated: bool = True,
        fields_and_sort: bool = True,
        report: bool = False,
        form_responses: bool = False,
    ) -> StartrackReadResult[T]:
        if not self.config.enabled:
            raise StartrackReadError("Las lecturas de Startrack están deshabilitadas.")
        if not self.configured:
            raise StartrackReadError("Faltan las credenciales de API de Startrack en el servidor.")
        deadline = monotonic() + self.config.budget_seconds
        if not self._lock.acquire(timeout=self.config.budget_seconds):
            raise StartrackReadError("Ya hay una lectura de Startrack en curso; intente más tarde.")
        try:
            if report:
                now = monotonic()
                while self._report_calls and now - self._report_calls[0] >= 300:
                    self._report_calls.popleft()
                if len(self._report_calls) >= 10:
                    raise StartrackReadError(
                        "Se alcanzó el límite local de informes de Startrack; intente más tarde."
                    )
                self._report_calls.append(now)
            items: list[T] = []
            seen: set[str] = set()
            exhausted = False
            for page_number in range(self.config.max_pages if paginated else 1):
                query = dict(params or {})
                if paginated:
                    query.update(page_size=self.config.page_size, page_num=page_number)
                if fields_and_sort:
                    query.update(sort_by="id", sort_dir="asc", fields=",".join(model.model_fields))
                body = self._get(
                    path,
                    query,
                    deadline,
                )
                try:
                    if form_responses:
                        report_page = StartrackFormPage.model_validate_json(body)
                        page = StartrackPage[model](
                            success=report_page.success, data=report_page.responses
                        )
                    else:
                        page = StartrackPage[model].model_validate_json(body)
                except ValidationError:
                    raise StartrackReadError(
                        "El formato de Startrack cambió; el cliente requiere revisión."
                    ) from None
                if not page.success:
                    raise StartrackReadError("Startrack no confirmó una lectura válida.")
                record_limit = (
                    self.config.page_size if paginated else self.config.max_report_records
                )
                if len(page.data) > record_limit:
                    raise StartrackReadError("Startrack excedió el límite de registros solicitado.")
                for item in page.data:
                    if item.id in seen:
                        raise StartrackReadError(
                            "Startrack devolvió IDs repetidos; la paginación requiere revisión."
                        )
                    seen.add(item.id)
                    items.append(item)
                if paginated and len(page.data) < self.config.page_size:
                    exhausted = True
                    break
            return StartrackReadResult[model](
                items=items,
                observed_at=datetime.now(UTC),
                pages_read=page_number + 1,
                exhausted=exhausted,
            )
        finally:
            self._lock.release()

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
    def _date_window(start_date: date, end_date: date) -> dict:
        if (
            type(start_date) is not date
            or type(end_date) is not date
            or not 0 <= (end_date - start_date).days < 7
        ):
            raise StartrackReadError("El informe requiere fechas explícitas de hasta siete días.")
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_time": "00:00:00",
            "end_time": "23:59:59",
        }

    @staticmethod
    def _report_ids(values: tuple[str, ...]) -> str:
        if (
            not values
            or len(values) > 100
            or any(
                not isinstance(value, str) or not value.isascii() or not value.isdecimal()
                for value in values
            )
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
        params = self._date_window(start_date, end_date)
        params["pois"] = self._report_ids(poi_ids)
        if bool(vehicle_ids) == bool(driver_ids):
            raise StartrackReadError("Seleccione vehículos o conductores para acotar las visitas.")
        if vehicle_ids:
            params.update(findby="veh", vehicle_ids=self._report_ids(vehicle_ids))
        if driver_ids:
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

    def list_form_responses(
        self,
        *,
        form_id: str,
        start_date: date,
        end_date: date,
        job_id: str | None = None,
        user_ids: tuple[str, ...] = (),
    ) -> StartrackReadResult[StartrackFormResponse]:
        params = self._date_window(start_date, end_date)
        params["form_id"] = self._report_ids((form_id,))
        if job_id is not None:
            params["job_id"] = self._report_ids((job_id,))
        if user_ids:
            params["user_ids"] = self._report_ids(user_ids)
        result = self._read(
            "/api/form-responses",
            StartrackFormResponse,
            params=params,
            paginated=False,
            fields_and_sort=False,
            report=True,
            form_responses=True,
        )
        if any(
            (job_id is not None and (item.job is None or item.job.id != job_id))
            or (user_ids and item.user_id not in user_ids)
            for item in result.items
        ):
            raise StartrackReadError("Startrack devolvió formularios fuera del alcance solicitado.")
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
        deadline = monotonic() + self.config.budget_seconds
        if not self._lock.acquire(timeout=self.config.budget_seconds):
            raise StartrackWriteRejected("Ya hay una operación de Startrack en curso.")
        try:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise StartrackWriteRejected("La tarea no se envió dentro del tiempo permitido.")
            try:
                with self._client.stream(
                    "POST",
                    "/api/job",
                    data=payload,
                    auth=httpx.BasicAuth(
                        self.config.api_key.get_secret_value(),
                        self.config.password.get_secret_value(),
                    ),
                    timeout=min(remaining, self.config.timeout_seconds),
                ) as response:
                    if 400 <= response.status_code < 500 and response.status_code != 408:
                        raise StartrackWriteRejected("Startrack rechazó la creación de la tarea.")
                    if response.status_code not in (200, 201):
                        raise StartrackWriteUnknown(
                            "No se confirmó la creación; concilie la tarea antes de reenviar."
                        )
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if monotonic() > deadline or len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise StartrackWriteUnknown(
                                "Respuesta incompleta; concilie la tarea antes de reenviar."
                            )
                        body.extend(chunk)
                    if monotonic() > deadline:
                        raise StartrackWriteUnknown(
                            "La respuesta llegó tarde; concilie la tarea antes de reenviar."
                        )
            except httpx.HTTPError:
                raise StartrackWriteUnknown(
                    "El resultado del envío es incierto; concilie la tarea antes de reenviar."
                ) from None
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
        finally:
            self._lock.release()
