"""Accessible, explicit operator inputs for persisted movements."""

import dash_mantine_components as dmc

from app.dashboard.components import accordion, disclosure, icon


def field_id(name: str) -> dict[str, str]:
    return {"type": "workflow-field", "field": name}


def action_id(action: str, movement: str = "") -> dict[str, str]:
    return {"type": "workflow-action", "action": action, "movement": movement}


def field(name, label, *, value="", hint=None, required=True, readonly=False, placeholder=""):
    return dmc.TextInput(
        id=field_id(name),
        label=label,
        description=hint,
        value=value,
        required=required,
        withAsterisk=required and not readonly,
        readOnly=readonly,
        placeholder=placeholder,
        autoComplete="off",
        size="sm",
    )


def action_button(
    action: str, label: str, *, movement="", enabled=True, primary=False, icon_name=None
):
    return dmc.Button(
        label,
        id=action_id(action, movement),
        n_clicks=0,
        disabled=not enabled,
        variant="filled" if primary else "default",
        leftSection=icon(icon_name, 16) if icon_name else None,
    )


def form_grid(*fields):
    return dmc.SimpleGrid(list(fields), cols={"base": 1, "xs": 2, "md": 3}, spacing="md")


def plan_form(*, request_source_id="", machinery_source_id="", project_source_id="", enabled=False):
    return dmc.Stack(
        [
            form_grid(
                field(
                    "poi_id",
                    "ID de geocerca de destino en Startrack",
                    hint="Confirma el destino por su ID de origen.",
                ),
                field(
                    "assigned_user_ids",
                    "IDs de usuarios asignables en Startrack",
                    hint="Separa varios IDs con comas. No introduzcas nombres.",
                ),
                field(
                    "movement_reference",
                    "Referencia del movimiento",
                    hint="Identifica este traslado concreto; una solicitud puede tener varios.",
                ),
                field(
                    "scheduled_date",
                    "Fecha programada de traslado",
                    placeholder="AAAA-MM-DD",
                    hint="Programación explícita, independiente del período de uso.",
                ),
                field(
                    "scheduled_time",
                    "Hora programada (opcional)",
                    required=False,
                    placeholder="HH:MM",
                    hint="Hora local de El Salvador.",
                ),
                field(
                    "tracked_vehicle_id",
                    "ID del activo GPS (opcional)",
                    required=False,
                    hint="Indica el activo observado; puede ser el transportador.",
                ),
            ),
            accordion(
                disclosure(
                    "Referencias de integración",
                    form_grid(
                        field(
                            "request_source_id",
                            "ID original de solicitud",
                            value=request_source_id,
                            readonly=True,
                        ),
                        field(
                            "machinery_source_id",
                            "ID original de maquinaria",
                            value=machinery_source_id,
                            readonly=True,
                        ),
                        field(
                            "project_source_id",
                            "ID original de proyecto",
                            value=project_source_id,
                            readonly=True,
                        ),
                    ),
                )
            ),
            dmc.Group(
                action_button(
                    "save",
                    "Guardar plan local",
                    enabled=enabled,
                    primary=True,
                    icon_name="device-floppy",
                )
            ),
        ],
        gap="md",
        className="workflow-form",
    )


def receipt_form(movement: str = "", *, enabled=False):
    return dmc.Stack(
        [
            form_grid(
                field("receiver", "Persona que recibió la maquinaria"),
                field("received_date", "Fecha de recepción", placeholder="AAAA-MM-DD"),
                field(
                    "received_time",
                    "Hora de recepción",
                    placeholder="HH:MM",
                    hint="Hora local de El Salvador.",
                ),
                field(
                    "reference",
                    "Referencia de la constancia",
                    hint="Folio o identificador de la evidencia de recepción.",
                ),
                field("note", "Observaciones (opcional)", required=False),
            ),
            dmc.Group(
                action_button(
                    "receipt",
                    "Registrar recepción",
                    movement=movement,
                    enabled=enabled,
                    primary=True,
                    icon_name="clipboard-check",
                )
            ),
        ],
        gap="md",
        className="workflow-form",
    )
