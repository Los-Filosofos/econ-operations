"""Accessible, explicit operator inputs for persisted movements."""

import dash_mantine_components as dmc
from dash import html

from app.dashboard.components import accordion, disclosure, icon
from app.services.ledger import SAFE_REASON_CODES

# Operator-readable closing reasons; the ledger admits only these codes, never free text.
RESOLUTION_REASONS = {
    code: label
    for code, label in [
        ("operator_resolved", "Comprobado a mano: la tarea no existe en Startrack"),
        ("provider_rejected", "El proveedor rechazó la creación"),
        ("provider_unavailable", "El proveedor no estaba disponible"),
        ("provider_timeout", "La creación agotó el tiempo de espera"),
        ("invalid_response", "La respuesta del proveedor no fue válida"),
        ("ambiguous_response", "La respuesta del proveedor fue ambigua"),
        ("mapping_conflict", "Conflicto de correspondencias (destino, usuarios o referencia)"),
        ("source_changed", "La solicitud o la unidad cambiaron en Prisma"),
        ("not_approved", "La solicitud ya no está aprobada"),
        ("worker_interrupted", "El proceso de envío se interrumpió"),
        ("dispatch_blocked", "El envío quedó bloqueado antes de crear la tarea"),
        ("unknown", "Motivo no determinado"),
    ]
    if code in SAFE_REASON_CODES
}


def field_id(name: str) -> dict[str, str]:
    return {"type": "workflow-field", "field": name}


def action_id(action: str, movement: str = "") -> dict[str, str]:
    return {"type": "workflow-action", "action": action, "movement": movement}


def resolve_id(step: str, movement: str = "") -> dict[str, str]:
    """Steps of the explicit resolution: open, reason, cancel, confirm and the modal itself."""
    return {"type": "workflow-resolve", "step": step, "movement": movement}


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


def resolve_form(movement: str = "", *, enabled=False):
    """Explicit exit from an uncertain send: a modal confirms the code before the ledger acts.

    Nothing is sent to Startrack and the creation POST is never repeated; the button only
    opens the confirmation, and the confirmation only records a permitted reason code.
    """
    return html.Div(
        [
            dmc.Button(
                "Resolver como fallido",
                id=resolve_id("open", movement),
                n_clicks=0,
                disabled=not enabled,
                variant="default",
                leftSection=icon("alert-triangle", 16),
            ),
            dmc.Modal(
                [
                    dmc.Text(
                        "Cierra este movimiento como fallido con el motivo elegido y libera la "
                        "unidad para un nuevo plan. No consulta ni modifica Startrack y nunca "
                        "repite el envío.",
                        size="sm",
                    ),
                    dmc.Text(
                        "Si la tarea sí existe en Startrack, no lo resuelvas: la sincronización "
                        "la vincula por referencia y contenido.",
                        size="sm",
                        c="dimmed",
                        mt="xs",
                    ),
                    dmc.Select(
                        id=resolve_id("reason", movement),
                        label="Motivo del cierre",
                        description=(
                            "Solo códigos permitidos por el registro; no admite texto libre."
                        ),
                        data=[
                            {"value": code, "label": f"{label} ({code})"}
                            for code, label in RESOLUTION_REASONS.items()
                        ],
                        value="operator_resolved",
                        allowDeselect=False,
                        required=True,
                        withAsterisk=True,
                        mt="md",
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Cancelar",
                                id=resolve_id("cancel", movement),
                                n_clicks=0,
                                variant="default",
                            ),
                            dmc.Button(
                                "Confirmar cierre como fallido",
                                id=resolve_id("confirm", movement),
                                n_clicks=0,
                                color="red",
                                leftSection=icon("alert-triangle", 16),
                            ),
                        ],
                        justify="flex-end",
                        mt="lg",
                    ),
                ],
                id=resolve_id("modal", movement),
                title="Resolver el movimiento como fallido",
                opened=False,
                centered=True,
                closeButtonProps={"aria-label": "Cerrar sin resolver"},
            ),
        ],
        className="resolve-form",
    )
