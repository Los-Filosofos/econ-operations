"""Persisted plans, provider evidence and explicit receipts, kept separate.

The operations list is read by pages from the ledger (`WorkflowService.read`), a long
movement timeline is sliced from the browser store, a movement outside the first page is
fetched by its id, and an uncertain send is closed only by an explicit operator decision
confirmed in a modal. `register_workflow_callbacks` wires those interactions; every dynamic
id is a pattern, so the validation layout needs no extra declarations.
"""

from math import ceil
from urllib.parse import unquote
from uuid import uuid4

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.core.auth import Permission, actor_from_user, session_user
from app.dashboard.analytics import instant
from app.dashboard.auth_views import ROLE_LABELS, current_user, denied, permitted
from app.dashboard.components import (
    accordion,
    back_link,
    disclosure,
    empty,
    facts,
    grid,
    heading,
    hint,
    link,
    loading,
    markdown_link,
    provenance,
    rows_table,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext, parse_context
from app.dashboard.theme import BRAND
from app.dashboard.workflow_actions import WorkflowInputError
from app.dashboard.workflow_forms import (
    RESOLUTION_REASONS,
    action_button,
    plan_form,
    receipt_form,
    resolve_form,
)
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.models.operations import MovementEventRecord, MovementRecord, ReceiptRecord
from app.models.workflow import WorkflowOverview
from app.services.ledger import LedgerError
from app.services.workflow import WorkflowError

STATES = {
    "draft": "Plan local",
    "blocked": "Preparación bloqueada",
    "queued": "En cola de envío",
    "sending": "Envío en curso",
    "sent": "Tarea vinculada",
    "unknown": "Resultado de envío por conciliar",
    "failed": "Envío fallido",
}
EVENTS = {
    "planned": "Plan guardado",
    "prepared": "Preparación revisada",
    "revalidated": "Preparación validada de nuevo",
    "created": "Plan guardado",
    "queued": "Puesto en cola",
    "sending": "Envío iniciado",
    "sent": "Tarea vinculada",
    "unknown": "Resultado de envío incierto",
    "failed": "Envío fallido",
    "blocked": "Preparación bloqueada",
    "resolved": "Cerrado como fallido por el operador",
    "task_state": "Estado de tarea observado",
    "arrival": "Llegada observada",
    "receipt": "Recepción registrada",
}
ACTOR_KINDS = {
    "local_dev": "desarrollo local sin sesión",
    "cli_worker": "el worker de sincronización",
}
READ_ONLY = "Solo consulta: la gestión de movimientos no está habilitada en esta conexión."
READ_FAILURE = "No se pudo consultar el registro de movimientos. Intenta actualizar."
ACTION_FAILURE = (
    "No se pudo completar la acción. Actualiza el registro para consultar su estado "
    "antes de repetirla."
)
PAGE_SIZES = (25, 50, 100)
DEFAULT_PAGE_SIZE = 50
EVENTS_PAGE_SIZE = 50
# Pattern ids: the controls exist only on the pages that mount them and the callbacks still
# register without any declaration in the validation layout.
PAGE_ID = {"type": "operations-page", "field": "page"}
SIZE_ID = {"type": "operations-page-size", "field": "size"}
TABLE_ID = {"type": "operations-table", "field": "table"}
WINDOW_ID = {"type": "operations-window", "field": "window"}


def _pattern(identifier: dict[str, str]) -> dict:
    return {**identifier, "field": ALL}


def movement_id(kind: str, movement: str) -> dict[str, str]:
    """Per-movement pattern ids: events-page, events, fetch and detail."""
    return {"type": f"movement-{kind}", "movement": movement}


def state_label(movement: MovementRecord):
    return state_text(STATES[movement.state], movement.state)


def task_status(movement: MovementRecord) -> str:
    if not movement.job_id:
        return "Sin tarea vinculada"
    return movement.status or "Estado no observado"


def arrival_label(movement: MovementRecord) -> str:
    arrivals = [event for event in movement.events if event.kind == "arrival"]
    if not arrivals:
        return "Sin evidencia de llegada vinculada"
    latest = max(arrivals, key=lambda event: event.recorded_at)
    when = instant(latest.event_time) if latest.event_time else "sin fecha de evento"
    return f"Llegada observada · {when}"


def receipt_label(movement: MovementRecord) -> str:
    if movement.receipt:
        return f"Recibida · {instant(movement.receipt.received_at)}"
    return "Sin constancia de recepción"


def next_step(movement: MovementRecord) -> str:
    """An operational prompt from the recorded state, without inferring provider facts."""
    if movement.state == "unknown":
        return "Conciliar envío antes de continuar"
    if movement.state == "failed":
        return "Revisar el error de envío"
    if movement.state == "blocked":
        return "Resolver los datos pendientes"
    if movement.mode == "fixture":
        return "Revisar plan local · sin envío"
    if movement.state == "draft":
        return "Revisar preparación del envío"
    if movement.state in {"queued", "sending"}:
        return "Consultar el avance del envío"
    if movement.receipt:
        return "Consultar recepción registrada"
    return "Confirmar recepción con el proyecto"


def declared_by_label(receipt: ReceiptRecord | None) -> str | None:
    """The session that declared a receipt, kept apart from the declared receiver."""
    if receipt is None or not (receipt.declared_by_email or receipt.declared_by_user_id):
        return None
    who = receipt.declared_by_email or f"usuario {receipt.declared_by_user_id}"
    role = ROLE_LABELS.get(receipt.declared_by_role, receipt.declared_by_role)
    return f"{who} · {role}" if role else who


def actor_label(event: MovementEventRecord, movement: MovementRecord) -> str:
    """Who caused the event, exactly as recorded; nobody is inferred when the ledger kept none."""
    if event.kind == "receipt" and (declared := declared_by_label(movement.receipt)):
        return f"declarado por {declared}"
    if event.actor_kind == "session":
        role = ROLE_LABELS.get(event.actor_role, event.actor_role) if event.actor_role else None
        who = f"registrado por usuario {event.actor_user_id}"
        return f"{who} · {role}" if role else who
    if event.actor_kind in ACTOR_KINDS:
        return f"registrado por {ACTOR_KINDS[event.actor_kind]}"
    return "actor no registrado"


def pending_reasons(movement: MovementRecord) -> list[str]:
    reasons = [
        *movement.preparation.get("blocking_reasons", []),
        *movement.preparation.get("missing_fields", []),
    ]
    if movement.state == "unknown":
        reasons.append("Conciliar el resultado antes de intentar otro envío.")
    elif movement.state == "failed":
        reasons.append("Revisar el error registrado antes de preparar otro envío.")
    return list(dict.fromkeys(str(reason) for reason in reasons))


def event_description(event) -> str:
    if event.kind == "task_state":
        return "Estado de tarea: " + str(event.data.get("status") or "No informado")
    if event.kind == "arrival":
        vehicle = event.data.get("vehicle_id") or "sin ID informado"
        return f"Visita del activo GPS {vehicle}; no acredita recepción de la maquinaria."
    if event.kind == "receipt":
        return "Constancia: " + str(event.data.get("reference") or "Ver declaración de recepción")
    if event.kind == "resolved":
        code = event.data.get("reason_code") or "sin código"
        label = RESOLUTION_REASONS.get(code, "código no catalogado")
        return f"Motivo {code}: {label}; sin reenvío."
    return STATES.get(event.state, event.state or EVENTS.get(event.kind, event.kind))


def remaining_evidence(missing: list[str], movements: list[MovementRecord]) -> list[str]:
    """Remove a gap only when every persisted movement has that distinct evidence."""
    if not movements:
        return list(missing)
    evidence = {
        "Traslado vinculado": all(movement.job_id for movement in movements),
        "Evidencia de llegada": all(
            any(event.kind == "arrival" for event in movement.events) for movement in movements
        ),
        "Recepción física": all(movement.receipt for movement in movements),
    }
    return [value for value in missing if not evidence.get(value, False)]


def matching_movements(
    workflow: WorkflowOverview | None, request: RequestRecord
) -> list[MovementRecord]:
    if workflow is None or not workflow.available:
        return []
    return [
        movement
        for movement in workflow.movements
        if movement.request_source_id == request.provenance.source_id
        and movement.source_request.get("id") == request.id
        and movement.environment == request.provenance.environment
    ]


def source_evidence(label: str, source_record: dict | None):
    if source_record is None:
        return None
    try:
        evidence = Provenance.model_validate(source_record.get("provenance"))
    except ValidationError:
        return hint(f"{label}: procedencia incompleta en el registro.")
    return disclosure(label, provenance(evidence))


def workflow_table(movements: list[MovementRecord], context: QueryContext):
    return simple_table(
        ["Movimiento", "Preparación / envío", "Tarea de Startrack", "Llegada", "Recepción"],
        [
            [
                link(movement.movement_reference, context.movement_href(movement.id)),
                state_label(movement),
                task_status(movement),
                arrival_label(movement),
                receipt_label(movement),
            ]
            for movement in movements
        ],
        caption="Movimientos persistidos de esta solicitud",
    )


def request_workflow(workflow, context: QueryContext, request: RequestRecord, equipment):
    movements = matching_movements(workflow, request)
    available = workflow is not None and workflow.available
    allowed = permitted(Permission.manage_transfers)
    enabled = available and workflow.management_enabled and allowed
    has_identity = bool(
        request.provenance.source_id
        and request.project_id
        and equipment
        and equipment.provenance.source_id
    )
    notes = [
        "Guarda la correspondencia de la solicitud con el destino y los usuarios de Startrack. "
        "La preparación valida aprobación y unidad asignada.",
        "Las muestras permiten guardar planes locales. No envían tareas ni registran llegadas "
        "o recepciones."
        if context.mode == "fixture"
        else "Guardar el plan no envía la tarea. Revisa el movimiento antes de ponerlo en cola.",
        None
        if available
        else (workflow.message if workflow else "Consultando el registro de movimientos…"),
        READ_ONLY if available and allowed and not enabled else None,
        "Falta una unidad asignada o un identificador de origen. Completa la asignación en "
        "Prisma para preparar el movimiento."
        if not has_identity
        else None,
    ]
    return [
        hint(
            "Consulta parcial de operaciones. Puede haber movimientos fuera de esta ventana; "
            "revisa el registro antes de preparar otro traslado.",
            role="status",
        )
        if available and not workflow.complete
        else None,
        section(
            "Movimientos de esta solicitud",
            workflow_table(movements, context),
            link("Abrir operaciones", context.href("/operaciones"), mt="sm", display="block"),
        )
        if movements
        else None,
        accordion(
            disclosure(
                "Preparar traslado",
                *[hint(note) for note in notes if note],
                plan_form(
                    request_source_id=request.provenance.source_id or "",
                    machinery_source_id=equipment.provenance.source_id or "" if equipment else "",
                    project_source_id=request.project_id or "",
                    enabled=enabled and has_identity,
                )
                if allowed
                else denied(),
            ),
            mt="md",
        ),
    ]


def page_size_of(value) -> int:
    """A page size the ledger accepts; anything else falls back to the default."""
    try:
        size = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return size if 1 <= size <= 500 else DEFAULT_PAGE_SIZE


def initial_window(workflow: WorkflowOverview) -> tuple[list[MovementRecord], int, int, int]:
    """Page 1 at the default size, sliced from the read the page already has: no second read."""
    total = workflow.coverage.total if workflow.coverage else len(workflow.movements)
    total = max(total, len(workflow.movements))
    if workflow.page == 1 and workflow.page_size >= DEFAULT_PAGE_SIZE:
        return workflow.movements[:DEFAULT_PAGE_SIZE], 1, DEFAULT_PAGE_SIZE, total
    return workflow.movements, workflow.page, workflow.page_size, total


def pagination_controls(page: int, size: int, total: int):
    """Server-side paging; hidden while every size would show the whole ledger anyway."""
    if total <= min(PAGE_SIZES):
        return None
    return dmc.Group(
        [
            dmc.Select(
                id=SIZE_ID,
                label="Movimientos por página",
                data=[str(value) for value in sorted({*PAGE_SIZES, size})],
                value=str(size),
                allowDeselect=False,
                size="xs",
                w=170,
            ),
            dmc.Pagination(
                id=PAGE_ID,
                total=max(1, ceil(total / size)),
                value=page,
                siblings=1,
                boundaries=1,
                withEdges=True,
                size="sm",
                **{"aria-label": "Páginas del registro de movimientos"},
            ),
            dcc.Store(id=WINDOW_ID, data={"page": page, "size": size}),
        ],
        align="flex-end",
        gap="md",
        my="sm",
        className="pagination-controls",
    )


def movements_panel(
    movements: list[MovementRecord], *, total: int, page: int, page_size: int, context: QueryContext
):
    """One ledger page as rows with its visible window; the search only filters this page."""
    pages = max(1, ceil(total / page_size))
    first = (page - 1) * page_size + 1
    if total == 0:
        coverage = "Sin movimientos registrados en este origen."
    elif not movements:
        coverage = f"Sin movimientos en la página {page} de {pages}; {total} registrados."
    else:
        coverage = (
            f"Movimientos {first}–{first + len(movements) - 1} de {total} · "
            f"página {page} de {pages}."
        )
    shown = movements
    if context.query:
        term = context.query.casefold()
        shown = [
            movement
            for movement in movements
            if any(
                term in str(value).casefold()
                for value in (
                    movement.movement_reference,
                    movement.request_source_id,
                    movement.machinery_source_id,
                    movement.project_source_id,
                    movement.source_request.get("project_name", ""),
                )
            )
        ]
        coverage = (
            f"{len(shown)} coincidencia(s) con «{context.query}» en esta página. {coverage} "
            "La búsqueda no consulta otras páginas."
        )
    registry = (
        "Población completa."
        if page == 1 and total <= len(movements)
        else "Registro paginado: la ausencia en esta página no acredita ausencia en otras."
    )
    rows = [
        {
            "reference": markdown_link(
                movement.movement_reference, context.movement_href(movement.id)
            ),
            "project": movement.source_request.get("project_name") or "Proyecto sin nombre",
            "state": STATES[movement.state],
            "job": task_status(movement),
            "receipt": receipt_label(movement),
            "next": next_step(movement),
        }
        for movement in shown
    ]
    table = grid(
        "operations-grid",
        rows,
        [
            ("reference", "Movimiento"),
            ("project", "Proyecto"),
            ("state", "Envío"),
            ("job", "Tarea Startrack"),
            ("receipt", "Recepción"),
            ("next", "Siguiente paso"),
        ],
        state_field="state",
        column_overrides={
            "reference": {"width": 150},
            "project": {"width": 130},
            "state": {"width": 155},
            "job": {"width": 120},
            "receipt": {"width": 135},
            "next": {"width": 170},
        },
        no_rows_message="Sin movimientos registrados"
        if total == 0
        else "Sin coincidencias en esta página",
    )
    # The server already pages the ledger; a second, client-side pager would mislead.
    table.dashGridOptions = {**table.dashGridOptions, "pagination": False}
    return [
        html.Div(dmc.Text(f"{coverage} {registry}", size="xs", c="dimmed", my="xs"), role="status"),
        table,
        link(
            "Abrir solicitudes para preparar un traslado",
            context.href("/solicitudes"),
            mt="sm",
            display="block",
        )
        if total == 0
        else None,
    ]


def operations(workflow: WorkflowOverview | None, context: QueryContext):
    content = [
        heading(
            "Operaciones",
            "Revisa bloqueos, envíos y recepciones pendientes.",
        )
    ]
    if workflow is None:
        return [*content, loading(6)]
    allowed = permitted(Permission.manage_transfers)
    content.append(
        dmc.Group(
            [
                action_button(
                    "sync",
                    "Sincronizar operación" if context.mode == "live" else "Guardar corte local",
                    enabled=workflow.available and workflow.management_enabled,
                    icon_name="refresh",
                )
                if allowed
                else denied(),
                dmc.Text(
                    f"Última sincronización: {instant(workflow.last_sync_at)}"
                    if workflow.last_sync_at
                    else "Sin sincronización registrada",
                    size="xs",
                    c="dimmed",
                ),
            ],
            gap="md",
            mb="md",
        )
    )
    if not workflow.available:
        # The empty state already carries the message; do not repeat it as a hint.
        return [*content, empty("Registro no disponible", workflow.message)]
    movements, page, size, total = initial_window(workflow)
    if allowed and not workflow.management_enabled:
        content.append(hint(READ_ONLY))
    return [
        *content,
        pagination_controls(page, size, total),
        dcc.Loading(
            html.Div(
                movements_panel(movements, total=total, page=page, page_size=size, context=context),
                id=TABLE_ID,
            ),
            custom_spinner=dmc.Loader(color=BRAND, size="sm"),
            overlay_style={"visibility": "visible", "opacity": 0.45},
            delay_show=150,
            show_initially=False,
        ),
        accordion(
            disclosure(
                "Estado del registro y criterios de seguimiento",
                hint(workflow.message),
                hint(
                    "Llegada y recepción son evidencias distintas. Un envío incierto requiere "
                    "conciliación antes de continuar. La búsqueda solo filtra la página cargada."
                ),
            ),
        ),
    ]


def events_panel(movement: MovementRecord, page: int = 1):
    """One page of the persisted timeline with its provenance, oldest record first."""
    events = sorted(movement.events, key=lambda item: item.recorded_at)
    pages = max(1, ceil(len(events) / EVENTS_PAGE_SIZE))
    page = min(max(1, page), pages)
    start = (page - 1) * EVENTS_PAGE_SIZE
    shown = events[start : start + EVENTS_PAGE_SIZE]
    return [
        html.Div(
            dmc.Text(
                f"Eventos {start + 1}–{start + len(shown)} de {len(events)} · "
                f"página {page} de {pages}.",
                size="xs",
                c="dimmed",
                my="xs",
            ),
            role="status",
        )
        if len(events) > EVENTS_PAGE_SIZE
        else None,
        simple_table(
            [
                "Evento",
                "Evidencia conservada",
                "Fecha del evento",
                "Observado",
                "Registrado",
                "Registrado por",
            ],
            [
                [
                    EVENTS.get(event.kind, event.kind),
                    event_description(event),
                    instant(event.event_time),
                    instant(event.observed_at),
                    instant(event.recorded_at),
                    actor_label(event, movement),
                ]
                for event in shown
            ],
            caption="Historial persistido, con fechas de origen y registro separadas",
        ),
        accordion(
            *[
                disclosure(
                    f"Procedencia · {EVENTS.get(event.kind, event.kind)} · "
                    f"{instant(event.recorded_at)}",
                    facts(
                        [
                            ("ID del evento", event.id),
                            ("ID de origen", event.source_id or "Registro local"),
                        ]
                    ),
                    provenance(event.provenance),
                    value=event.id,
                )
                for event in shown
                if event.provenance
            ]
        ),
    ]


def timeline(movement: MovementRecord):
    if not movement.events:
        return hint("No se ha registrado un evento para este movimiento.")
    if len(movement.events) <= EVENTS_PAGE_SIZE:
        return events_panel(movement)
    return [
        dmc.Pagination(
            id=movement_id("events-page", movement.id),
            total=ceil(len(movement.events) / EVENTS_PAGE_SIZE),
            value=1,
            siblings=1,
            boundaries=1,
            withEdges=True,
            size="sm",
            **{"aria-label": "Páginas del historial del movimiento"},
        ),
        html.Div(events_panel(movement), id=movement_id("events", movement.id)),
    ]


def movement_body(workflow: WorkflowOverview, context: QueryContext, movement: MovementRecord):
    allowed = permitted(Permission.manage_transfers)
    enabled = workflow.available and workflow.management_enabled and allowed
    receipt = movement.receipt
    mapping = movement.mapping
    references = {
        "ID de movimiento": movement.id,
        "ID de solicitud": movement.request_source_id,
        "ID de maquinaria": movement.machinery_source_id,
        "ID de proyecto": movement.project_source_id,
        "ID de geocerca de destino": mapping.get("poi_id") or "Sin informar",
        "IDs de usuarios asignados": ", ".join(mapping.get("assigned_user_ids", []))
        or "Sin informar",
        "ID del activo GPS": movement.tracked_vehicle_id or "Sin correspondencia",
        "ID de tarea": movement.job_id or "Sin tarea vinculada",
        "Rol de ejecución": movement.workflow_role or "Sin rol observado",
        "Referencia del estado": movement.reason_code or "Sin incidencia registrada",
        "Creado en el registro": instant(movement.created_at),
        "Actualizado en el registro": instant(movement.updated_at),
    }
    prepared = {
        "Objetivo": (movement.payload or {}).get("objective") or "Sin objetivo",
        "Descripción": (movement.payload or {}).get("description") or "Sin descripción",
        "Referencia externa": (movement.payload or {}).get("remote_id") or "Sin referencia",
    }
    machine = movement.source_equipment or {}
    machine_sections = []
    try:
        equipment = EquipmentRecord.model_validate(machine)
    except ValidationError:
        equipment = None
    if equipment:
        from app.dashboard.evidence_views import interpretation_section, source_comparison

        machine_sections = [
            interpretation_section(equipment, [movement]),
            hint(
                "La comparación usa el corte de Prisma conservado al preparar o validar "
                "este movimiento. Su fecha no cambia al consultar el historial."
            ),
            source_comparison(equipment, [movement], workflow, context)[0],
        ]
    sending_note = (
        "Plan local sobre muestras: el envío está deshabilitado."
        if movement.mode == "fixture"
        else "El envío está deshabilitado en este servidor."
        if not workflow.sending_enabled
        else workflow.message
    )
    can_queue = (
        enabled
        and workflow.sending_enabled
        and movement.mode == "live"
        and movement.state == "draft"
    )
    can_resolve = movement.mode == "live" and movement.state == "unknown"
    can_receive = (
        movement.mode == "live" and movement.state == "sent" and movement.job_id and not receipt
    )
    declared = declared_by_label(receipt)
    reasons = pending_reasons(movement)
    return [
        heading(movement.movement_reference, next_step(movement)),
        facts(
            [
                ("Preparación / envío", state_label(movement)),
                ("Proyecto", movement.source_request.get("project_name") or "Sin nombre"),
                (
                    "Maquinaria",
                    machine.get("asset_number")
                    or machine.get("code")
                    or machine.get("name")
                    or "Sin nombre de unidad",
                ),
            ]
        ),
        link("Ver solicitud de origen", context.request_href(movement.source_request["id"]))
        if movement.source_request.get("id")
        else None,
        section(
            "Acción pendiente",
            dmc.List([dmc.ListItem(reason) for reason in reasons], size="sm") if reasons else None,
            hint(sending_note)
            if movement.mode == "fixture" or not workflow.sending_enabled
            else None,
            dmc.Group(
                [
                    action_button(
                        "queue",
                        "Poner traslado en cola",
                        movement=movement.id,
                        enabled=can_queue,
                        primary=True,
                        icon_name="send",
                    ),
                    hint("El servidor valida los datos y procesa la cola al sincronizar."),
                ]
            )
            if movement.mode == "live" and movement.state == "draft" and allowed
            else denied()
            if movement.mode == "live" and movement.state == "draft"
            else None,
            [
                hint("Comprueba la tarea en Startrack antes de cerrar el envío como fallido."),
                resolve_form(movement.id, enabled=enabled) if allowed else denied(),
            ]
            if can_resolve
            else None,
            (
                receipt_form(
                    movement.id, enabled=workflow.available and workflow.management_enabled
                )
                if permitted(Permission.declare_reception)
                else denied()
            )
            if can_receive
            else None,
        )
        if reasons or movement.mode == "fixture" or movement.state == "draft" or can_receive
        else None,
        section(
            "Seguimiento del traslado",
            facts(
                [
                    ("Programado", mapping.get("scheduled_date") or "Sin fecha programada"),
                    ("Hora programada", mapping.get("scheduled_time") or "Sin informar"),
                    ("Tarea de Startrack", task_status(movement)),
                    ("Envío registrado", instant(movement.sent_at)),
                    ("Llegada", arrival_label(movement)),
                    ("Recepción", receipt_label(movement)),
                ]
            ),
            hint("La llegada observada o una tarea completada no acreditan recepción."),
        ),
        accordion(
            disclosure(
                "Constancia de recepción",
                facts(
                    [
                        ("Recibió", receipt.receiver),
                        ("Referencia", receipt.reference),
                        ("Registrada", instant(receipt.recorded_at)),
                        *([("Declarada por", declared)] if declared else []),
                    ]
                ),
                hint(receipt.note) if receipt.note else None,
            )
            if receipt
            else None,
            disclosure(
                "Historial y evidencia del movimiento",
                hint(
                    "Fechas del hecho, observación y registro separadas; "
                    "el historial puede ser parcial."
                ),
                timeline(movement),
            ),
            disclosure("Comparar evidencia de las fuentes", *machine_sections)
            if machine_sections
            else None,
            disclosure(
                "Referencias de integración y origen",
                rows_table(references),
                accordion(
                    source_evidence("Procedencia de la solicitud", movement.source_request),
                    source_evidence("Procedencia de la unidad", movement.source_equipment),
                ),
            ),
            disclosure(
                "Contenido preparado para Startrack",
                rows_table(prepared),
                dmc.List(
                    [dmc.ListItem(note) for note in movement.preparation.get("notes", [])],
                    size="sm",
                ),
            )
            if movement.payload
            else None,
        ),
    ]


def movement_content(
    workflow: WorkflowOverview | None, context: QueryContext, identifier: str, *, fetch: bool = True
):
    """The detail without its back link, so the fetch callback can render the same body."""
    if workflow is None:
        return [loading(6)]
    if not workflow.available:
        return [empty("Registro de operaciones no disponible", workflow.message)]
    movement = next((item for item in workflow.movements if item.id == identifier), None)
    if movement is not None:
        return movement_body(workflow, context, movement)
    if workflow.complete:
        return [
            empty(
                "Movimiento fuera de la consulta",
                "Comprueba el origen seleccionado y el identificador del movimiento.",
            )
        ]
    placeholder = empty("Movimiento fuera de la primera página del registro", workflow.message)
    if not fetch:
        return [placeholder]
    # A movement beyond the loaded page is fetched by id once the placeholder mounts.
    return [
        dcc.Store(id=movement_id("fetch", identifier), data=context.mode),
        html.Div(placeholder, id=movement_id("detail", identifier)),
    ]


def movement_detail(workflow: WorkflowOverview | None, context: QueryContext, identifier: str):
    back = back_link("Volver a operaciones", context.href("/operaciones", filter=context.filter))
    return [back, *movement_content(workflow, context, identifier)]


def resolution_reason(value) -> str:
    """A closing reason is one of the catalogued codes; anything else is refused before acting."""
    if not isinstance(value, str) or value.strip() not in RESOLUTION_REASONS:
        raise WorkflowInputError("Elige un motivo permitido para cerrar el movimiento.")
    return value.strip()


def overview_from(snapshot, mode: str) -> WorkflowOverview | None:
    if not isinstance(snapshot, dict) or snapshot.get("mode") != mode:
        return None
    try:
        return WorkflowOverview.model_validate(snapshot.get("overview"))
    except ValidationError:
        return None


def _matched(grouping) -> list[dict]:
    """Resolved ids of one pattern output, whatever Dash wrapped them in."""
    if isinstance(grouping, dict):
        return [grouping]
    return list(grouping or [])


def register_workflow_callbacks(dashboard, server) -> None:
    """Pagination, timeline slicing, out-of-page fetch and explicit resolution.

    Idempotent per Dash application, so the tests can call it on an app that already did.
    Every action re-checks the session inside the service; browser state grants nothing.
    """
    if any(TABLE_ID["type"] in key for key in dashboard.callback_map):
        return
    settings = server.state.settings

    def anonymous() -> bool:
        return settings.auth_required and current_user() is None

    def sized(*values):
        """Fit each value to its output: one entry per matched component for pattern outputs."""
        return [
            [value] * len(spec) if isinstance(spec, list) else value
            for spec, value in zip(ctx.outputs_grouping, values, strict=True)
        ]

    @dashboard.callback(
        Output(_pattern(TABLE_ID), "children"),
        Output(_pattern(PAGE_ID), "total"),
        Output(_pattern(PAGE_ID), "value"),
        Output(_pattern(WINDOW_ID), "data"),
        Input(_pattern(PAGE_ID), "value"),
        Input(_pattern(SIZE_ID), "value"),
        State(_pattern(WINDOW_ID), "data"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    async def paginate_operations(pages, sizes, windows, search):
        unchanged = sized(no_update, no_update, no_update, no_update)
        if anonymous() or not pages or not sizes:
            return unchanged
        page = pages[0] if isinstance(pages[0], int) and pages[0] > 0 else 1
        size = page_size_of(sizes[0])
        previous = windows[0] if windows and isinstance(windows[0], dict) else {}
        trigger = ctx.triggered_id
        if (
            isinstance(trigger, dict)
            and trigger.get("type") == SIZE_ID["type"]
            and previous.get("size") != size
        ):
            page = 1
        window = {"page": page, "size": size}
        # Pattern callbacks also fire when their controls mount; that echo reads nothing.
        if previous == window:
            return unchanged
        try:
            context = parse_context(search)
        except ValueError:
            return unchanged
        try:
            overview = await run_in_threadpool(
                server.state.workflow.read, context.mode, page=page, page_size=size
            )
        except Exception:
            panel = empty("Registro no disponible", READ_FAILURE)
            return sized(panel, no_update, no_update, window)
        if not overview.available:
            return sized(
                empty("Registro no disponible", overview.message), no_update, no_update, window
            )
        panel = movements_panel(
            overview.movements,
            total=overview.total,
            page=overview.page,
            page_size=size,
            context=context,
        )
        return sized(panel, overview.total_pages, overview.page, window)

    @dashboard.callback(
        Output({"type": "movement-events", "movement": ALL}, "children"),
        Input({"type": "movement-events-page", "movement": ALL}, "value"),
        State("workflow-snapshot", "data"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    def paginate_events(pages, snapshot, search):
        """Slice the timeline already held by the browser store; no read is needed."""
        outputs = _matched(ctx.outputs_grouping)
        requested = {
            item["id"]["movement"]: item.get("value")
            for item in _matched(ctx.args_grouping[0] if ctx.args_grouping else [])
        }
        try:
            overview = None if anonymous() else overview_from(snapshot, parse_context(search).mode)
        except ValueError:
            overview = None
        if overview is None:
            return [no_update] * len(outputs)
        movements = {movement.id: movement for movement in overview.movements}
        return [
            events_panel(movements[spec["id"]["movement"]], page)
            if spec["id"]["movement"] in movements
            and isinstance(page := requested.get(spec["id"]["movement"]), int)
            else no_update
            for spec in outputs
        ]

    @dashboard.callback(
        Output({"type": "movement-detail", "movement": ALL}, "children"),
        Input({"type": "movement-fetch", "movement": ALL}, "data"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    async def fetch_movement(_modes, search):
        """A movement beyond the loaded page is read by id with its own request's overview."""
        outputs = _matched(ctx.outputs_grouping)
        try:
            context = None if anonymous() else parse_context(search)
        except ValueError:
            context = None
        if context is None:
            return [no_update] * len(outputs)
        service = server.state.workflow
        results = []
        for spec in outputs:
            identifier = spec["id"]["movement"]
            try:
                movement = await run_in_threadpool(service.ledger.get, identifier, context.mode)
                overview = await run_in_threadpool(
                    service.read, context.mode, movement.request_source_id, page_size=500
                )
            except (WorkflowError, LedgerError):
                results.append(no_update)
                continue
            except Exception:
                results.append(empty("Registro no disponible", READ_FAILURE))
                continue
            results.append(movement_content(overview, context, identifier, fetch=False))
        return results

    @dashboard.callback(
        Output({"type": "workflow-resolve", "step": "modal", "movement": ALL}, "opened"),
        Output("workflow-action-result", "data", allow_duplicate=True),
        Input({"type": "workflow-resolve", "step": "open", "movement": ALL}, "n_clicks"),
        Input({"type": "workflow-resolve", "step": "cancel", "movement": ALL}, "n_clicks"),
        Input({"type": "workflow-resolve", "step": "confirm", "movement": ALL}, "n_clicks"),
        State({"type": "workflow-resolve", "step": "reason", "movement": ALL}, "value"),
        State("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    async def resolve_movement(opens, cancels, confirms, reasons, search, path):
        """Open or cancel the confirmation, or close the movement with a permitted code."""
        modals = len(_matched(ctx.outputs_grouping[0]))
        trigger = ctx.triggered_id
        if anonymous() or not isinstance(trigger, dict) or not any([*opens, *cancels, *confirms]):
            return [no_update] * modals, no_update
        if trigger.get("step") == "open":
            return [True] * modals, no_update
        if trigger.get("step") != "confirm":
            return [False] * modals, no_update
        result = {"token": str(uuid4()), "path": path, "search": search}
        try:
            context = parse_context(search)
            reason = resolution_reason(next((value for value in reasons if value), None))
            record = await run_in_threadpool(
                server.state.workflow.resolve,
                trigger.get("movement", ""),
                reason_code=reason,
                actor=actor_from_user(session_user(), kind="session"),
            )
            result.update(
                {
                    "ok": True,
                    "message": (
                        f"Movimiento cerrado como fallido ({RESOLUTION_REASONS[reason]}). "
                        "La unidad queda libre para un nuevo plan; no se reenvió nada."
                    ),
                    "href": context.movement_href(record.id),
                }
            )
        except (WorkflowError, WorkflowInputError, ValueError) as error:
            result.update({"ok": False, "message": str(error)})
        except Exception:
            result.update({"ok": False, "message": ACTION_FAILURE})
        return [False] * modals, result


def workflow_page(path: str, workflow: WorkflowOverview | None, context: QueryContext):
    if path == "/operaciones":
        return operations(workflow, context)
    return movement_detail(workflow, context, unquote(path.removeprefix("/operaciones/")))
