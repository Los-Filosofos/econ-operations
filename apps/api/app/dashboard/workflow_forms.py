"""Accessible, explicit operator inputs for persisted movements."""

from dash import dcc, html


def field_id(name: str) -> dict[str, str]:
    return {"type": "workflow-field", "field": name}


def action_id(action: str, movement: str = "") -> dict[str, str]:
    return {"type": "workflow-action", "action": action, "movement": movement}


def field(
    name: str,
    label: str,
    *,
    value: str = "",
    hint: str | None = None,
    required: bool = True,
    readonly: bool = False,
    max_length: int = 255,
    placeholder: str = "",
):
    return html.Div(
        [
            html.Label(
                [
                    html.Span(label),
                    dcc.Input(
                        id=field_id(name),
                        value=value,
                        type="text",
                        required=required,
                        readOnly=readonly,
                        maxLength=max_length,
                        autoComplete="off",
                        placeholder=placeholder,
                    ),
                    html.Small(hint) if hint else None,
                ]
            ),
        ],
        className="workflow-field",
    )


def action_button(action: str, label: str, *, movement="", enabled=True, primary=False):
    return html.Button(
        label,
        id=action_id(action, movement),
        n_clicks=0,
        disabled=not enabled,
        className="button primary" if primary else "button",
        type="button",
    )


def plan_form(
    *,
    request_source_id: str = "",
    machinery_source_id: str = "",
    project_source_id: str = "",
    enabled: bool = False,
):
    return html.Div(
        [
            html.Div(
                [
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
                ],
                className="workflow-form-grid",
            ),
            html.Details(
                [
                    html.Summary("Referencias de integración"),
                    html.Div(
                        [
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
                        ],
                        className="workflow-form-grid",
                    ),
                ],
                className="integration-references",
            ),
            html.Div(
                action_button("save", "Guardar plan local", enabled=enabled, primary=True),
                className="workflow-actions",
            ),
        ],
        className="workflow-form",
    )


def receipt_form(movement: str = "", *, enabled=False):
    return html.Div(
        [
            html.Div(
                [
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
                    field("note", "Observaciones (opcional)", required=False, max_length=2000),
                ],
                className="workflow-form-grid",
            ),
            html.Div(
                action_button(
                    "receipt",
                    "Registrar recepción",
                    movement=movement,
                    enabled=enabled,
                    primary=True,
                ),
                className="workflow-actions",
            ),
        ],
        className="workflow-form",
    )


def validation_controls():
    """Every dynamic callback ID is declared without relaxing layout validation."""
    return html.Div(
        [
            plan_form(),
            receipt_form(),
            action_button("queue", "Poner en cola"),
            action_button("sync", "Sincronizar"),
        ]
    )
