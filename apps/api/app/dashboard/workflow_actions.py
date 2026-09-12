"""Parse explicit UI inputs; the shared server facade owns authorization and writes."""

import re
from datetime import date, datetime, time

from app.services.hub import BUSINESS_TIMEZONE
from app.services.transfers import TransferMapping


def text_field(fields: dict, name: str, *, optional=False) -> str | None:
    value = fields.get(name)
    if optional and (value is None or value == ""):
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Campo obligatorio ausente.")
    return value.strip()


def explicit_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Fecha no válida.")
    return date.fromisoformat(value)


def explicit_time(value: str) -> time:
    if not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", value):
        raise ValueError("Hora no válida.")
    return time.fromisoformat(value)


def execute_action(service, action: str, mode: str, fields: dict, movement: str):
    """Never treat displayed browser flags as permission to call a provider."""
    if action == "save":
        scheduled_time = text_field(fields, "scheduled_time", optional=True)
        mapping = TransferMapping(
            request_source_id=text_field(fields, "request_source_id"),
            machinery_source_id=text_field(fields, "machinery_source_id"),
            project_source_id=text_field(fields, "project_source_id"),
            poi_id=text_field(fields, "poi_id"),
            assigned_user_ids=tuple(
                value.strip() for value in text_field(fields, "assigned_user_ids").split(",")
            ),
            movement_reference=text_field(fields, "movement_reference"),
            scheduled_date=explicit_date(text_field(fields, "scheduled_date")),
            scheduled_time=explicit_time(scheduled_time).isoformat() if scheduled_time else None,
        )
        record = service.save_plan(
            mode, mapping, text_field(fields, "tracked_vehicle_id", optional=True)
        )
        return "Plan guardado en el registro local. Revisa su preparación y evidencia.", record
    if action == "queue" and mode == "live" and movement:
        record = service.queue(movement)
        return "Movimiento en cola. Sincroniza la operación para procesar el envío.", record
    if action == "sync":
        overview = service.sync(mode)
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
            text_field(fields, "receiver"),
            received_at,
            text_field(fields, "reference"),
            text_field(fields, "note", optional=True),
        )
        return "Constancia de recepción registrada con su responsable y referencia.", record
    raise ValueError("Acción no reconocida.")
