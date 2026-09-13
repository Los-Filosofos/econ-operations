"""One derivation of the Prisma → ECON → Startrack data path, shared by HTTP and Dash.

Nothing here estimates, infers or completes a fact: every value is read from the bounded
hub projection, the persisted movement or the local preparation. A missing value stays
missing and is reported as such.
"""

from datetime import datetime, time
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.models.hub import DataMode, EquipmentRecord, HubResponse, Provenance, RequestRecord
from app.models.operations import MovementEventRecord, MovementRecord
from app.models.workflow import WorkflowOverview
from app.services.hub import BUSINESS_TIMEZONE
from app.services.transfers import TransferMapping, TransferPreparation, prepare_transfer

Treatment = Literal["kept", "transformed", "manual", "absent"]
StageKey = Literal["prisma", "econ", "startrack_request", "startrack_response"]
StageState = Literal["done", "pending", "blocked"]

TREATMENTS: dict[Treatment, str] = {
    "kept": "Conservado",
    "transformed": "Transformado",
    "manual": "Manual (operador)",
    "absent": "Sin equivalente",
}
# Preset roles of /api/job/status; the status itself is a client catalogue ID, never read
# as a meaning. Custom statuses of an account map onto one of these three roles.
WORKFLOW_ROLES = {"0": "Pendiente", "1": "Completada", "2": "Cancelada"}
NORMALIZATION_RULES = [
    "IDs conservados: el identificador de origen viaja en provenance.source_id.",
    "Período de uso ≠ fecha de entrega: ECON no convierte fecha_inicio en start_date.",
    "Estado administrativo ≠ disponibilidad física de la unidad.",
    "Operador ↔ conductor por código MOT documentado, nunca por nombre.",
    "La tarifa por hora del proyecto no viaja a Startrack.",
]
TIMELINE_NOTE = (
    "ECON no estima tiempos de ruta; muestra los instantes y la duración esperada que las "
    'fuentes registran. La fecha límite ("Completar antes de") y la ventana horaria del '
    "formulario no están en el Job Data Object público."
)
PROVIDER_DATE_NOTE = (
    "Startrack documenta sus fechas como YYYY-MM-DD HH:mm:ss±hh:mm (con espacio, no «T»)."
)
NO_MOVEMENT = "Sin envío registrado para esta solicitud"


class TraceCell(BaseModel):
    """One column of the field map: the source field name and its observed value."""

    field: str | None = Field(default=None, description="Nombre del campo en esa plataforma.")
    value: str | None = Field(default=None, description="Valor observado; null si no se informa.")


class TraceEntry(TraceCell):
    label: str


class TraceField(BaseModel):
    concept: str
    prisma: TraceCell
    econ: TraceCell
    startrack: TraceCell
    treatment: Treatment
    note: str | None = None

    @property
    def treatment_label(self) -> str:
        return TREATMENTS[self.treatment]


class TraceStage(BaseModel):
    key: StageKey
    title: str
    summary: str
    state: StageState
    entries: list[TraceEntry] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    provenance: Provenance | None = None
    equipment_provenance: Provenance | None = None


class TraceInstant(BaseModel):
    key: str
    label: str
    at: datetime | None = None
    source: str


class TraceDuration(BaseModel):
    key: str
    label: str
    seconds: float
    detail: str


class TraceTimeline(BaseModel):
    note: str = TIMELINE_NOTE
    instants: list[TraceInstant] = Field(default_factory=list)
    durations: list[TraceDuration] = Field(default_factory=list)
    expected_duration_seconds: float | None = Field(
        default=None,
        description="Campo duration del Job Data Object, en segundos; null si no se informa.",
    )


class IntegrationTrace(BaseModel):
    """What Prisma delivers, what ECON normalizes and what Startrack receives and returns."""

    schema_version: Literal["1.0"] = "1.0"
    mode: DataMode
    generated_at: datetime
    request_id: str
    request_source_id: str | None = None
    request_label: str
    project_label: str
    equipment_label: str | None = None
    movement_id: str | None = None
    movement_reference: str | None = None
    movement_state: str | None = None
    job_id: str | None = None
    message: str = ""
    preparation: TransferPreparation
    payload: dict[str, Any] | None = None
    stages: list[TraceStage]
    field_map: list[TraceField]
    timeline: TraceTimeline


def _text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, datetime):
        return value.astimezone(BUSINESS_TIMEZONE).isoformat(sep=" ", timespec="seconds")
    if isinstance(value, list | tuple):
        joined = ", ".join(str(item) for item in value if item not in (None, ""))
        return joined or None
    return str(value)


def _cell(field: str | None, value: Any) -> TraceCell:
    return TraceCell(field=field, value=_text(value))


def _entry(label: str, field: str, value: Any) -> TraceEntry:
    return TraceEntry(label=label, field=field, value=_text(value))


def _seconds(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def traceable_requests(hub: HubResponse) -> list[RequestRecord]:
    """Requests of the current read; the assigned ones come first so a trace has a unit."""
    return sorted(hub.requests, key=lambda item: (item.machinery_id is None, item.id))


def default_request_id(hub: HubResponse) -> str | None:
    candidates = traceable_requests(hub)
    return candidates[0].id if candidates else None


def movement_for(
    workflow: WorkflowOverview | None, request: RequestRecord
) -> MovementRecord | None:
    """The latest movement whose stored source request is this one; identity by IDs only."""
    if workflow is None or not workflow.available:
        return None
    matches = [
        movement
        for movement in workflow.movements
        if movement.request_source_id == request.provenance.source_id
        and movement.source_request.get("id") == request.id
        and movement.environment == request.provenance.environment
    ]
    return max(matches, key=lambda movement: movement.created_at, default=None)


def _latest(events: list[MovementEventRecord]) -> MovementEventRecord | None:
    return max(events, key=lambda event: event.recorded_at, default=None)


def _observed_job(movement: MovementRecord | None) -> dict[str, Any]:
    if movement is None:
        return {}
    latest = _latest([event for event in movement.events if event.kind == "task_state"])
    return dict(latest.data) if latest else {}


def _arrival(movement: MovementRecord | None) -> MovementEventRecord | None:
    if movement is None:
        return None
    return _latest([event for event in movement.events if event.kind == "arrival"])


def _mapping_of(movement: MovementRecord | None) -> TransferMapping | None:
    if movement is None:
        return None
    try:
        return TransferMapping.model_validate(movement.mapping)
    except ValidationError:
        return None


def _scheduled_at(mapping: TransferMapping | None) -> datetime | None:
    if mapping is None:
        return None
    return datetime.combine(
        mapping.scheduled_date,
        time.fromisoformat(mapping.scheduled_time or "00:00:00"),
        BUSINESS_TIMEZONE,
    )


def _operator_codes(equipment: EquipmentRecord | None) -> list[str] | None:
    if equipment is None or equipment.operators is None:
        return None
    return [operator.worker_code or operator.id for operator in equipment.operators]


def _prisma_stage(request: RequestRecord, equipment: EquipmentRecord | None) -> TraceStage:
    entries = [
        _entry("Solicitud", "id", request.provenance.source_id),
        _entry("Tipo de maquinaria", "tipo", request.machinery_type),
        _entry("Estado", "status", request.status),
        _entry("Inicio solicitado", "fecha_inicio", request.starts_on),
        _entry("Fin solicitado", "fecha_fin", request.ends_on),
        _entry("Proyecto", "project_id", request.project_id),
        _entry("Nombre del proyecto", "project_name", request.project_name),
        _entry("Maquinaria asignada", "maquinaria_id", _source_id(request.machinery_id)),
        _entry("Activo", "maquinaria_no_activo", request.machinery_asset_number),
        _entry("Solicitante", "requested_by_name", request.requested_by),
        _entry("Aprobó", "approved_by_name", request.approved_by),
        _entry("Comentarios", "comentarios", request.comments),
    ]
    if equipment is not None:
        entries += [
            _entry("Estado de la unidad", "estado", equipment.machinery_status),
            _entry("Falla activa", "active_failure_status", equipment.maintenance_status),
            _entry("Paro registrado", "active_failure_is_paro", equipment.maintenance_is_stopped),
            _entry(
                "Operadores asociados",
                "associated_operators[].cod_trabajador",
                _operator_codes(equipment),
            ),
            _entry(
                "Tarifa por hora",
                "current_project_rate.precio_x_hora",
                equipment.project_rate.hourly_rate if equipment.project_rate else None,
            ),
            _entry("Inicio de uso", "fecha_inicio_uso", equipment.assignment_starts_on),
            _entry("Fin de uso", "fecha_fin_uso", equipment.assignment_ends_on),
        ]
    return TraceStage(
        key="prisma",
        title="Prisma entrega",
        summary=(
            "Campos tal como los devuelve el sandbox de Prisma para esta solicitud y su unidad."
            if equipment is not None
            else "Campos de la solicitud; la unidad asignada no está en esta consulta."
        ),
        state="done",
        entries=entries,
        provenance=request.provenance,
        equipment_provenance=equipment.provenance if equipment is not None else None,
    )


def _source_id(identifier: str | None) -> str | None:
    """Strip the ECON namespace prefix to show the original Prisma identifier."""
    return identifier.rsplit(":", 1)[-1] if identifier else None


def _econ_stage(request: RequestRecord, equipment: EquipmentRecord | None) -> TraceStage:
    entries = [
        _entry("Solicitud", "RequestRecord.id", request.id),
        _entry("ID de origen", "RequestRecord.provenance.source_id", request.provenance.source_id),
        _entry("Tipo de maquinaria", "RequestRecord.machinery_type", request.machinery_type),
        _entry("Estado", "RequestRecord.status", request.status),
        _entry("Inicio solicitado", "RequestRecord.starts_on", request.starts_on),
        _entry("Fin solicitado", "RequestRecord.ends_on", request.ends_on),
        _entry("Proyecto", "RequestRecord.project_id", request.project_id),
        _entry("Unidad asignada", "RequestRecord.machinery_id", request.machinery_id),
        _entry("Solicitante", "RequestRecord.requested_by", request.requested_by),
        _entry("Aprobó", "RequestRecord.approved_by", request.approved_by),
        _entry("Comentarios", "RequestRecord.comments", request.comments),
    ]
    if equipment is not None:
        entries += [
            _entry(
                "Estado de la unidad",
                "EquipmentRecord.machinery_status",
                equipment.machinery_status,
            ),
            _entry(
                "Falla activa", "EquipmentRecord.maintenance_status", equipment.maintenance_status
            ),
            _entry(
                "Paro registrado",
                "EquipmentRecord.maintenance_is_stopped",
                equipment.maintenance_is_stopped,
            ),
            _entry(
                "Códigos de operador",
                "EquipmentRecord.operators[].worker_code",
                _operator_codes(equipment),
            ),
            _entry(
                "Tarifa por hora",
                "EquipmentRecord.project_rate.hourly_rate",
                equipment.project_rate.hourly_rate if equipment.project_rate else None,
            ),
            _entry(
                "Inicio de uso",
                "EquipmentRecord.assignment_starts_on",
                equipment.assignment_starts_on,
            ),
            _entry(
                "Fin de uso", "EquipmentRecord.assignment_ends_on", equipment.assignment_ends_on
            ),
        ]
    return TraceStage(
        key="econ",
        title="ECON normaliza",
        summary="Los mismos hechos con los nombres del modelo de lectura; sin completar vacíos.",
        state="done",
        entries=entries,
        rules=list(NORMALIZATION_RULES),
    )


def _startrack_request_stage(
    preparation: TransferPreparation, payload: dict[str, Any] | None
) -> TraceStage:
    body = payload or {}
    entries = [
        _entry("Título de la tarea", "objective", body.get("objective")),
        _entry("Descripción", "description", body.get("description")),
        _entry("Fecha programada", "start_date", body.get("start_date")),
        _entry("Hora programada", "start_time", body.get("start_time")),
        _entry("ID remoto", "remote_id", body.get("remote_id")),
        _entry("Geocerca de destino", "poi_id", body.get("poi_id")),
        _entry("Usuarios asignados", "assigned_user_ids", body.get("assigned_user_ids")),
        _entry("Tipo de tarea", "job_type_id", body.get("job_type_id")),
    ]
    if payload:
        state: StageState = "done"
        summary = "Cuerpo que ECON construye para POST /api/job; ningún campo se inventa."
    elif preparation.blocking_reasons:
        state, summary = "blocked", "La preparación está bloqueada; ECON no construye el cuerpo."
    else:
        state, summary = "pending", "Faltan datos explícitos; ECON no construye el cuerpo."
    return TraceStage(
        key="startrack_request",
        title="Startrack recibe",
        summary=summary,
        state=state,
        entries=entries,
        rules=[*preparation.blocking_reasons, *preparation.missing_fields],
    )


def _startrack_response_stage(movement: MovementRecord | None) -> TraceStage:
    if movement is None or not movement.job_id:
        return TraceStage(
            key="startrack_response",
            title="Startrack devuelve",
            summary=NO_MOVEMENT if movement is None else "Movimiento sin tarea vinculada.",
            state="pending",
            entries=[],
            rules=[PROVIDER_DATE_NOTE],
        )
    job = _observed_job(movement)
    arrival = _arrival(movement)
    role = WORKFLOW_ROLES.get(str(movement.workflow_role or job.get("workflow_role") or ""))
    entries = [
        _entry("ID de tarea", "id", movement.job_id),
        _entry("Estado remoto (ID de catálogo)", "status", job.get("status") or movement.status),
        _entry("Rol de flujo", "workflow_role", role or movement.workflow_role),
        _entry(
            "Último cambio de estado", "last_status_change_date", job.get("last_status_change_date")
        ),
        _entry("Cierre de la tarea", "closed_date", job.get("closed_date")),
        _entry("Geocerca informada", "poi_name", job.get("poi_name") or job.get("poi_id")),
        _entry("Latitud de cierre", "completed_lat", job.get("completed_lat")),
        _entry("Longitud de cierre", "completed_lon", job.get("completed_lon")),
        _entry(
            "Llegada observada (visita a la geocerca)",
            "visit.start_date",
            arrival.event_time if arrival else None,
        ),
        _entry(
            "Geocerca de la llegada",
            "visit.poi_id",
            arrival.data.get("poi_id") if arrival else None,
        ),
        _entry(
            "Recepción declarada",
            "receipt.received_at",
            movement.receipt.received_at if movement.receipt else None,
        ),
    ]
    return TraceStage(
        key="startrack_response",
        title="Startrack devuelve",
        summary=(
            "Lo observado de la tarea creada. El ID de estado pertenece al catálogo del cliente; "
            "su significado viene del workflow_role, no del número."
        ),
        state="done",
        entries=entries,
        rules=[
            PROVIDER_DATE_NOTE,
            "Una visita a la geocerca no acredita recepción de la maquinaria.",
        ],
    )


def _field_map(
    request: RequestRecord,
    equipment: EquipmentRecord | None,
    mapping: TransferMapping | None,
    payload: dict[str, Any] | None,
) -> list[TraceField]:
    body = payload or {}
    rate = equipment.project_rate.hourly_rate if equipment and equipment.project_rate else None
    rows = [
        TraceField(
            concept="Identificador de la solicitud",
            prisma=_cell("id", request.provenance.source_id),
            econ=_cell("RequestRecord.id", request.id),
            startrack=_cell("description", body.get("description")),
            treatment="transformed",
            note="El ID de origen se conserva; ECON solo antepone su espacio de nombres y "
            "lo escribe dentro de la descripción de la tarea.",
        ),
        TraceField(
            concept="Tipo de maquinaria",
            prisma=_cell("tipo", request.machinery_type),
            econ=_cell("RequestRecord.machinery_type", request.machinery_type),
            startrack=_cell("objective", body.get("objective")),
            treatment="transformed",
            note="El título de la tarea es un texto compuesto por ECON, no un campo de Prisma.",
        ),
        TraceField(
            concept="Estado de la solicitud",
            prisma=_cell("status", request.status),
            econ=_cell("RequestRecord.status", request.status),
            startrack=_cell(None, None),
            treatment="absent",
            note="El status de Startrack es un ID de su propio catálogo /api/job/status; "
            "ECON no envía el estado administrativo de Prisma.",
        ),
        TraceField(
            concept="Período de uso solicitado",
            prisma=_cell("fecha_inicio / fecha_fin", [request.starts_on, request.ends_on]),
            econ=_cell("RequestRecord.starts_on / ends_on", [request.starts_on, request.ends_on]),
            startrack=_cell(None, None),
            treatment="absent",
            note="El período de uso no es una fecha de entrega: start_date es la programación "
            "del traslado que decide el operador.",
        ),
        TraceField(
            concept="Proyecto de destino",
            prisma=_cell("project_id / project_name", [request.project_id, request.project_name]),
            econ=_cell("RequestRecord.project_id", request.project_id),
            startrack=_cell("poi_id", body.get("poi_id") or (mapping.poi_id if mapping else None)),
            treatment="manual",
            note="La correspondencia proyecto ↔ geocerca la declara el operador; Prisma no "
            "publica el ID de geocerca de Startrack.",
        ),
        TraceField(
            concept="Unidad asignada",
            prisma=_cell(
                "maquinaria_id / maquinaria_no_activo",
                [_source_id(request.machinery_id), request.machinery_asset_number],
            ),
            econ=_cell("RequestRecord.machinery_id", request.machinery_id),
            startrack=_cell("objective / description", body.get("objective")),
            treatment="transformed",
            note="La unidad viaja como texto dentro del título y la descripción; el job no "
            "tiene un campo de maquinaria.",
        ),
        TraceField(
            concept="Solicitante",
            prisma=_cell("requested_by_name", request.requested_by),
            econ=_cell("RequestRecord.requested_by", request.requested_by),
            startrack=_cell(None, None),
            treatment="absent",
        ),
        TraceField(
            concept="Aprobación",
            prisma=_cell("approved_by_name", request.approved_by),
            econ=_cell("RequestRecord.approved_by", request.approved_by),
            startrack=_cell(None, None),
            treatment="absent",
        ),
        TraceField(
            concept="Comentarios de la solicitud",
            prisma=_cell("comentarios", request.comments),
            econ=_cell("RequestRecord.comments", request.comments),
            startrack=_cell(None, None),
            treatment="absent",
        ),
        TraceField(
            concept="Estado administrativo de la unidad",
            prisma=_cell("estado", equipment.machinery_status if equipment else None),
            econ=_cell(
                "EquipmentRecord.machinery_status",
                equipment.machinery_status if equipment else None,
            ),
            startrack=_cell(None, None),
            treatment="absent",
            note="Estado administrativo no equivale a disponibilidad física.",
        ),
        TraceField(
            concept="Falla registrada",
            prisma=_cell(
                "active_failure_status", equipment.maintenance_status if equipment else None
            ),
            econ=_cell(
                "EquipmentRecord.maintenance_status",
                equipment.maintenance_status if equipment else None,
            ),
            startrack=_cell(None, None),
            treatment="absent",
        ),
        TraceField(
            concept="Paro de mantenimiento",
            prisma=_cell(
                "active_failure_is_paro", equipment.maintenance_is_stopped if equipment else None
            ),
            econ=_cell(
                "EquipmentRecord.maintenance_is_stopped",
                equipment.maintenance_is_stopped if equipment else None,
            ),
            startrack=_cell(None, None),
            treatment="absent",
            note="Un paro bloquea la preparación en ECON; no viaja como campo de la tarea.",
        ),
        TraceField(
            concept="Operador ↔ conductor",
            prisma=_cell("associated_operators[].cod_trabajador", _operator_codes(equipment)),
            econ=_cell("EquipmentRecord.operators[].worker_code", _operator_codes(equipment)),
            startrack=_cell("assigned_user_ids", body.get("assigned_user_ids")),
            treatment="manual",
            note="La correspondencia es por código MOT documentado, nunca por nombre. Hoy ECON "
            "envía assigned_user_ids; el código MOT podría viajar como assigned_user_remote_ids "
            "si los usuarios de Startrack tuvieran ese remote_id, algo pendiente de verificar "
            "en la cuenta.",
        ),
        TraceField(
            concept="Tarifa por hora del proyecto",
            prisma=_cell("current_project_rate.precio_x_hora", rate),
            econ=_cell("EquipmentRecord.project_rate.hourly_rate", rate),
            startrack=_cell(None, None),
            treatment="absent",
            note="La tarifa no viaja a Startrack: pertenece al costo del proyecto en Prisma.",
        ),
        TraceField(
            concept="Período de uso de la unidad",
            prisma=_cell(
                "fecha_inicio_uso / fecha_fin_uso",
                [
                    equipment.assignment_starts_on if equipment else None,
                    equipment.assignment_ends_on if equipment else None,
                ],
            ),
            econ=_cell(
                "EquipmentRecord.assignment_starts_on / ends_on",
                [
                    equipment.assignment_starts_on if equipment else None,
                    equipment.assignment_ends_on if equipment else None,
                ],
            ),
            startrack=_cell(None, None),
            treatment="absent",
        ),
        TraceField(
            concept="Programación del traslado",
            prisma=_cell(None, None),
            econ=_cell(
                "TransferMapping.scheduled_date / scheduled_time",
                [
                    mapping.scheduled_date if mapping else None,
                    mapping.scheduled_time if mapping else None,
                ],
            ),
            startrack=_cell(
                "start_date / start_time", [body.get("start_date"), body.get("start_time")]
            ),
            treatment="manual",
            note="Prisma no informa la fecha de entrega; la decide el operador al preparar.",
        ),
        TraceField(
            concept="Referencia del movimiento",
            prisma=_cell(None, None),
            econ=_cell(
                "TransferMapping.movement_reference",
                mapping.movement_reference if mapping else None,
            ),
            startrack=_cell("remote_id", body.get("remote_id")),
            treatment="manual",
            note="remote_id es un valor de correlación; no garantiza unicidad en Startrack.",
        ),
        TraceField(
            concept="Tipo de tarea",
            prisma=_cell(None, None),
            econ=_cell("TransferMapping.job_type_id", mapping.job_type_id if mapping else None),
            startrack=_cell("job_type_id", body.get("job_type_id")),
            treatment="manual",
            note="Catálogo propio de Startrack (/api/job/type); también admite job_type_remote_id.",
        ),
    ]
    rows += [
        TraceField(
            concept=concept,
            prisma=_cell(None, None),
            econ=_cell(None, None),
            startrack=_cell(field, None),
            treatment=treatment,
            note=note,
        )
        for concept, field, treatment, note in STARTRACK_ONLY
    ]
    return rows


# Fields of the real "Nueva tarea" form of Startrack that ECON never sends.
STARTRACK_ONLY: list[tuple[str, str | None, Treatment, str]] = [
    (
        "Completar antes de (fecha límite)",
        None,
        "absent",
        "El formulario lo pide, pero no aparece en el Job Data Object público consultado.",
    ),
    (
        "Origen (geocerca)",
        None,
        "absent",
        "El job documenta una sola geocerca (poi_id); no hay origen y destino separados.",
    ),
    (
        "Ventana horaria de entrega",
        None,
        "absent",
        "Presente en el formulario; ausente del Job Data Object público consultado.",
    ),
    (
        "Duración esperada",
        "duration",
        "manual",
        "Segundos; ECON no la envía. Se muestra si la tarea devuelta la informa.",
    ),
    (
        "Dirección o referencia",
        "address",
        "manual",
        "Texto libre del formulario; ECON no lo envía.",
    ),
    (
        "Formularios de la tarea",
        "form_ids / required_form_ids",
        "manual",
        "Se eligen en Startrack; ECON no los envía.",
    ),
    (
        "Artículos de la tarea",
        None,
        "absent",
        "Cantidades, SKU, volumen, peso y precio solo existen en el formulario.",
    ),
    (
        "Contacto de la tarea",
        "contact_name / phone_number / contact_email",
        "manual",
        "Se completa en Startrack; ECON no envía datos de contacto ni activa notificaciones.",
    ),
]


def _timeline(movement: MovementRecord | None, mapping: TransferMapping | None) -> TraceTimeline:
    job = _observed_job(movement)
    arrival = _arrival(movement)
    task_state = _latest(
        [event for event in movement.events if event.kind == "task_state"] if movement else []
    )
    instants = [
        TraceInstant(
            key="scheduled",
            label="Programado",
            at=_scheduled_at(mapping),
            source="TransferMapping · start_date + start_time",
        ),
        TraceInstant(
            key="sent",
            label="Enviado a Startrack",
            at=movement.sent_at if movement else None,
            source="Registro local · sent_at",
        ),
        TraceInstant(
            key="status_change",
            label="Último cambio de estado",
            at=task_state.event_time if task_state else None,
            source="Startrack · last_status_change_date",
        ),
        TraceInstant(
            key="arrival",
            label="Llegada observada",
            at=arrival.event_time if arrival else None,
            source="Startrack · visita a la geocerca de destino",
        ),
        TraceInstant(
            key="receipt",
            label="Recepción declarada",
            at=movement.receipt.received_at if movement and movement.receipt else None,
            source="Declaración manual · receipt.received_at",
        ),
    ]
    at = {instant.key: instant.at for instant in instants}
    durations = [
        TraceDuration(
            key=key,
            label=label,
            seconds=(at[end] - at[start]).total_seconds(),
            detail=detail,
        )
        for key, label, start, end, detail in [
            (
                "scheduled_to_arrival",
                "Programado → llegada observada",
                "scheduled",
                "arrival",
                "Diferencia entre dos instantes registrados; no es un tiempo de ruta estimado.",
            ),
            (
                "arrival_to_receipt",
                "Llegada → recepción",
                "arrival",
                "receipt",
                "La llegada del vehículo y la recepción declarada son hechos distintos.",
            ),
        ]
        if at[start] is not None and at[end] is not None
    ]
    return TraceTimeline(
        instants=instants,
        durations=durations,
        expected_duration_seconds=_seconds(job.get("duration")),
    )


def build_trace(
    hub: HubResponse, request_id: str, workflow: WorkflowOverview | None = None
) -> IntegrationTrace | None:
    """Derive the whole path for one request; None when the request is outside the read."""
    request = next(
        (
            item
            for item in hub.requests
            if item.id == request_id or item.provenance.source_id == request_id
        ),
        None,
    )
    if request is None:
        return None
    equipment = next((item for item in hub.equipment if item.id == request.machinery_id), None)
    movement = movement_for(workflow, request)
    mapping = _mapping_of(movement)
    preparation = prepare_transfer(request, equipment, mapping)
    payload = (movement.payload if movement else None) or (
        preparation.draft.payload() if preparation.draft else None
    )
    return IntegrationTrace(
        mode=hub.mode,
        generated_at=hub.generated_at,
        request_id=request.id,
        request_source_id=request.provenance.source_id,
        request_label=request.machinery_type or "Solicitud de maquinaria",
        project_label=request.project_name or request.project_id or "Proyecto sin nombre",
        equipment_label=(
            equipment.asset_number or equipment.code or equipment.name if equipment else None
        ),
        movement_id=movement.id if movement else None,
        movement_reference=movement.movement_reference if movement else None,
        movement_state=movement.state if movement else None,
        job_id=movement.job_id if movement else None,
        message="" if movement else NO_MOVEMENT,
        preparation=preparation,
        payload=payload,
        stages=[
            _prisma_stage(request, equipment),
            _econ_stage(request, equipment),
            _startrack_request_stage(preparation, payload),
            _startrack_response_stage(movement),
        ],
        field_map=_field_map(request, equipment, mapping, payload),
        timeline=_timeline(movement, mapping),
    )
