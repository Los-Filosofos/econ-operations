"""Parse explicit UI inputs; the shared server facade owns authorization and writes."""

import re
from datetime import date, datetime, time

from app.core.auth import actor_from_user, session_user
from app.services.hub import BUSINESS_TIMEZONE
from app.services.transfers import TransferMapping

FIELD_LABELS = {
    "request_source_id": "ID original de solicitud",
    "machinery_source_id": "ID original de maquinaria",
    "project_source_id": "ID original de proyecto",
    "poi_id": "ID de geocerca de destino en Startrack",
    "assigned_user_ids": "IDs de usuarios asignables en Startrack",
    "movement_reference": "Referencia del movimiento",
    "scheduled_date": "Fecha programada de traslado",
    "scheduled_time": "Hora programada",
    "tracked_vehicle_id": "ID del activo GPS",
    "receiver": "Persona que recibió la maquinaria",
    "received_date": "Fecha de recepción",
    "received_time": "Hora de recepción",
    "reference": "Referencia de la constancia",
    "note": "Observaciones",
}


class WorkflowInputError(ValueError):
    """Safe operator guidance composed only from known labels and fixed messages."""


def text_field(fields: dict, name: str, *, optional=False) -> str | None:
    value = fields.get(name)
    if optional and (value is None or isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str) or not value.strip():
        label = FIELD_LABELS.get(name, "Campo obligatorio")
        raise WorkflowInputError(f"Completa el campo «{label}».")
    return value.strip()


def explicit_date(value: str) -> date:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise WorkflowInputError(
            "Fecha no válida. Usa una fecha existente con formato AAAA-MM-DD."
        ) from None


def explicit_time(value: str) -> time:
    try:
        if not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", value):
            raise ValueError
        return time.fromisoformat(value)
    except ValueError:
        raise WorkflowInputError("Hora no válida. Usa el formato HH:MM de 24 horas.") from None


def assigned_users(fields: dict) -> tuple[str, ...]:
    users = tuple(value.strip() for value in text_field(fields, "assigned_user_ids").split(","))
    if any(not user or re.search(r"\s", user) for user in users):
        raise WorkflowInputError(
            "Revisa los IDs de usuarios: sepáralos con comas, sin nombres ni entradas vacías."
        )
    if len(users) != len(set(users)):
        raise WorkflowInputError("Los IDs de usuarios asignados no deben repetirse.")
    return users


def execute_action(service, action: str, mode: str, fields: dict, movement: str):
    """Never treat displayed browser flags as permission to call a provider.

    The session user of the callback travels as the actor of every transition; without
    a login (development only) the service records the loopback developer, never a user.
    """
    actor = actor_from_user(session_user(), kind="session")
    if action == "save":
        scheduled_time = text_field(fields, "scheduled_time", optional=True)
        mapping = TransferMapping(
            request_source_id=text_field(fields, "request_source_id"),
            machinery_source_id=text_field(fields, "machinery_source_id"),
            project_source_id=text_field(fields, "project_source_id"),
            poi_id=text_field(fields, "poi_id"),
            assigned_user_ids=assigned_users(fields),
            movement_reference=text_field(fields, "movement_reference"),
            scheduled_date=explicit_date(text_field(fields, "scheduled_date")),
            scheduled_time=explicit_time(scheduled_time).isoformat() if scheduled_time else None,
        )
        # The form does not collect the device kind yet: it stays undeclared, never guessed.
        record = service.save_plan(
            mode,
            mapping,
            tracked_vehicle_id=text_field(fields, "tracked_vehicle_id", optional=True),
            tracked_vehicle_kind=None,
            actor=actor,
        )
        return "Plan guardado en el registro local. Revisa su preparación y evidencia.", record
    if action == "queue" and mode == "live" and movement:
        record = service.queue(movement, actor=actor)
        return "Movimiento en cola. Sincroniza la operación para procesar el envío.", record
    if action == "sync":
        overview = service.sync(mode, actor=actor)
        return overview.message, None
    if action == "receipt" and movement:
        received_at = datetime.combine(
            explicit_date(text_field(fields, "received_date")),
            explicit_time(text_field(fields, "received_time")),
            tzinfo=BUSINESS_TIMEZONE,
        )
        record = service.record_receipt(
            movement,
            mode,
            receiver=text_field(fields, "receiver"),
            received_at=received_at,
            reference=text_field(fields, "reference"),
            note=text_field(fields, "note", optional=True),
            actor=actor,
        )
        return "Constancia de recepción registrada con su responsable y referencia.", record
    raise ValueError("Acción no reconocida.")
