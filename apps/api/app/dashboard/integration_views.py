"""The data path of one request, stage by stage and field by field.

Everything shown comes from `services.integration_trace`, the same derivation the HTTP
route returns, so the page and `GET /api/v1/integration/{request_id}` cannot diverge.

The exchange is laid out as a sober sequence diagram: three actors in fixed lanes and one
row per interaction, carrying its origin, destination, endpoint and the fields that travel.
A row states the contract between two systems; it never claims that a request happened, and
a prepared body is never presented as a sent one.
"""

import json
from urllib.parse import quote

import dash_mantine_components as dmc
from dash import ALL, html

from app.dashboard.analytics import instant
from app.dashboard.components import (
    accordion,
    disclosure,
    empty,
    facts,
    heading,
    hint,
    icon,
    link,
    provenance,
    rows_table,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.dashboard.theme import state_color
from app.models.hub import HubResponse
from app.services.integration_trace import (
    TREATMENTS,
    IntegrationTrace,
    TraceCell,
    TraceEntry,
    TraceField,
    TraceStage,
    build_trace,
    default_request_id,
    traceable_requests,
)

# Pattern ids: the controls only exist on this page, and the callback still registers.
SELECT_ID = {"type": "integration-request", "field": "request"}
PANEL_ID = {"type": "integration-trace", "field": "panel"}
SELECT_PATTERN = {"type": "integration-request", "field": ALL}
PANEL_PATTERN = {"type": "integration-trace", "field": ALL}
# Stage progress reuses the shared state palette: no decorative colors.
STAGE_STATES = {
    "done": ("active", "Completa"),
    "pending": ("pending", "Pendiente"),
    "blocked": ("issue", "Bloqueada"),
}
TREATMENT_ICONS = {
    "kept": "check",
    "transformed": "arrows-exchange",
    "manual": "hand-click",
    "absent": "minus",
}
TREATMENT_MEANINGS = {
    "kept": "el mismo dato con el mismo significado.",
    "transformed": "ECON lo reescribe para el contrato de destino.",
    "manual": "lo decide una persona al preparar el traslado.",
    "absent": "el dato no viaja a la otra plataforma.",
}
NO_VALUE = "No informado"
NO_FIELD = "Sin campo equivalente"
INTRO = (
    "Recorrido de una solicitud entre Prisma, ECON y Startrack: qué entrega cada API, "
    "qué prepara la nuestra y qué evidencia vuelve."
)
# Three actors, fixed lanes. ECON is the middle lane because it coordinates every exchange.
ACTORS = [
    ("Prisma · Nexus", "Origen", "Proyecto, solicitud, aprobación y unidad asignada."),
    (
        "ECON · nuestra API",
        "Intermediario",
        "Normaliza, valida, prepara el envío y conserva la evidencia.",
    ),
    ("Startrack", "Destino", "Tarea de traslado y observaciones de su ejecución."),
]
# One row per interaction: step, lane span, direction, endpoint and what travels.
EXCHANGES: dict[str, dict[str, str]] = {
    "prisma": {
        "step": "01",
        "title": "Consultar solicitud y unidad",
        "route": "ECON ⇄ Prisma",
        "lane": "read",
        "icon": "database",
        "endpoint": "GET /api/maquinaria/requests · GET /api/maquinaria/equipos",
        "carries": "Identificadores de origen, estado, aprobación, asignación y fechas.",
    },
    "econ": {
        "step": "02",
        "title": "Normalizar y validar",
        "route": "Dentro de ECON",
        "lane": "normalize",
        "icon": "arrows-exchange",
        "endpoint": "Servicios compartidos de ECON · IDs, aprobación y correspondencias",
        "carries": "Los mismos hechos con los nombres del modelo de lectura.",
    },
    "startrack_request": {
        "step": "03",
        "title": "Preparar tarea de traslado",
        "route": "ECON → Startrack",
        "lane": "send",
        "icon": "send",
        "endpoint": "POST /api/job",
        "carries": "Objetivo, descripción, programación, geocerca y usuarios asignados.",
    },
    "startrack_response": {
        "step": "04",
        "title": "Consultar evidencia de retorno",
        "route": "Startrack → ECON",
        "lane": "return",
        "icon": "clipboard-check",
        "endpoint": "GET /api/job · GET /api/visits",
        "carries": "Estado de la tarea, cierre y visitas a la geocerca vinculadas por ID.",
    },
}
CONTRACT_NOTE = (
    "Cada fila describe el contrato de interacción entre dos sistemas. No es una captura de "
    "tráfico: una flecha no prueba que la petición se haya hecho."
)
PREPARED_NOTE = (
    "Un cuerpo preparado no acredita envío. La llegada por GPS, el cierre de la tarea y la "
    "recepción declarada son hechos distintos y se registran por separado."
)
MODE_NOTES = {
    "fixture": (
        "Origen «fixture»: muestras documentales leídas de archivo. En esta pantalla no se "
        "contactó a ningún proveedor."
    ),
    "live": (
        "Origen «live»: lecturas del sandbox hechas desde el servidor. Las credenciales no "
        "salen de él y no hay respaldo entre orígenes."
    ),
}
STATE_CAPTION = (
    "El estado de cada fila describe la evidencia disponible en esta lectura, no que la "
    "petición se haya ejecutado."
)
RECEIPT_NOTE = (
    "Fuera de este intercambio: la recepción la declara el proyecto en ECON "
    "(POST /api/v1/operations/{movement_id}/receipt) con responsable, instante con zona y "
    "constancia. Startrack no la devuelve y una visita a la geocerca no la sustituye."
)


def request_options(hub: HubResponse):
    return [
        {
            "value": request.id,
            "label": " · ".join(
                filter(
                    None,
                    [
                        request.project_name or request.project_id or "Proyecto sin nombre",
                        request.machinery_type,
                        request.machinery_asset_number or "sin unidad asignada",
                    ],
                )
            ),
        }
        for request in traceable_requests(hub)
    ]


def eyebrow(text: str, className: str = "eyebrow"):
    """Micro-label above a block; the shared class keeps it aligned with the base sheet."""
    return html.P(text, className=className)


def code(value: str | None):
    return dmc.Code(value, fz="xs") if value else dmc.Text(NO_FIELD, size="xs", c="dimmed")


def observed(value: str | None, **props):
    """A missing value is dimmed and named, never blank and never invented."""
    return dmc.Text(value or NO_VALUE, size="sm", **({} if value else {"c": "dimmed"}), **props)


def cell_view(cell: TraceCell):
    """One platform column of the field map; a missing counterpart is named, not dimmed away."""
    if cell.field is None:
        return html.Span(NO_FIELD, className="fm-none")
    return html.Div([code(cell.field), observed(cell.value, mt=2)])


def entry_view(entry: TraceEntry):
    return html.Div([observed(entry.value), code(entry.field)])


def treatment_view(treatment: str):
    return dmc.Group(
        [icon(TREATMENT_ICONS[treatment], 15), dmc.Text(TREATMENTS[treatment], size="sm")],
        gap=6,
        wrap="nowrap",
    )


def stage_state_span(stage: TraceStage):
    """Phrasing-only state label for the diagram row: text first, icon only for an issue."""
    family, label = STAGE_STATES[stage.state]
    parts = []
    if family == "issue":
        parts.append(html.Span(icon("alert-triangle", 14), style={"color": state_color(family)}))
    parts.append(html.Span(label, className="exchange-state-label"))
    return html.Span(parts, className=f"exchange-state exchange-state-{family}")


def fields_count(stage: TraceStage) -> str:
    """How much of the contract this read actually fills; absence is never counted as zero."""
    total = len(stage.entries)
    if not total:
        return "Sin campos observados en esta lectura"
    informed = sum(1 for entry in stage.entries if entry.value)
    return f"{informed} de {total} campos con valor"


def fields_preview(stage: TraceStage) -> str | None:
    names = [entry.field for entry in stage.entries if entry.field]
    if not names:
        return None
    shown = " · ".join(names[:3])
    return f"{shown} …" if len(names) > 3 else shown


def stage_note(trace: IntegrationTrace, key: str) -> str:
    """What this interaction does and does not prove, for the mode that is being read."""
    if key == "prisma":
        return (
            "Datos del archivo de muestras; no se hizo una consulta HTTP a Prisma."
            if trace.mode == "fixture"
            else "ECON consulta Prisma desde el servidor y conserva el origen de los datos."
        )
    if key == "econ":
        return (
            "ECON conserva los identificadores y transforma los nombres de los campos. "
            "Para preparar una tarea exige aprobación, unidad y correspondencias explícitas."
        )
    if key == "startrack_request":
        return (
            "Este es el contrato de creación. En muestras nunca se envía. En live requiere "
            "un plan validado, autorización y envío habilitado en el servidor. "
            "Un cuerpo preparado no acredita que Startrack haya recibido la tarea."
        )
    return (
        "ECON consulta tareas y visitas y conserva la evidencia vinculada por ID. "
        "Este retorno no es un webhook de aprobación. La llegada observada y la "
        "recepción declarada por el proyecto siguen siendo hechos distintos."
    )


def actors_row():
    """Lane headers of the diagram; every row below is aligned to these three columns."""
    return html.Div(
        [
            html.Div(
                [
                    eyebrow(role, "exchange-role"),
                    html.P(name, className="exchange-actor-name"),
                    html.P(duty, className="exchange-duty"),
                ],
                className="exchange-actor",
            )
            for name, role, duty in ACTORS
        ],
        className="exchange-actors",
    )


def connection_tab(stage: TraceStage):
    """One interaction of the sequence: its lane span states origin and destination."""
    meta = EXCHANGES[stage.key]
    preview = fields_preview(stage)
    return dmc.TabsTab(
        [
            html.Span(
                [
                    html.Span(f"Paso {meta['step']}", className="exchange-step"),
                    html.Span(meta["route"], className="exchange-route"),
                    stage_state_span(stage),
                ],
                className="exchange-head",
            ),
            html.Span(meta["title"], className="exchange-title"),
            html.Span(meta["endpoint"], className="exchange-endpoint-line"),
            html.Span(
                [
                    html.Span(fields_count(stage), className="exchange-fields-count"),
                    html.Span(preview, className="exchange-fields-list") if preview else None,
                ],
                className="exchange-fields",
            ),
        ],
        value=stage.key,
        className=f"exchange-call exchange-{meta['lane']}",
    )


def contract_block(stage: TraceStage):
    meta = EXCHANGES[stage.key]
    return html.Div(
        [
            eyebrow(f"Contrato de interacción · paso {meta['step']}"),
            dmc.Group(
                [icon(meta["icon"], 16), html.Span(meta["route"], className="contract-route")],
                gap=8,
                wrap="nowrap",
            ),
            dmc.Code(meta["endpoint"], block=True, className="exchange-endpoint"),
            html.P(meta["carries"], className="contract-carries"),
            html.P(fields_count(stage), className="contract-count"),
        ],
        className="exchange-contract",
    )


def json_block(*, kind: str, contract: str, body: str, label: str, note: str | None = None):
    """A JSON contract with its name attached: what it is, and what it does not prove."""
    return html.Figure(
        [
            html.Figcaption(
                [
                    eyebrow(kind, "json-kind"),
                    html.Span(contract, className="json-contract"),
                ],
                className="json-caption",
            ),
            html.Pre(body, className="exchange-json", tabIndex=0, **{"aria-label": label}),
            html.P(note, className="json-note") if note else None,
        ],
        className="json-figure",
    )


def prepared_payload(trace: IntegrationTrace):
    if trace.payload is None:
        return empty(
            "Todavía no hay cuerpo para enviar",
            "Revisa los datos pendientes de esta etapa.",
        )
    return json_block(
        kind="Petición preparada",
        contract="POST /api/job · cuerpo construido por ECON",
        body=json.dumps(trace.payload, indent=2, ensure_ascii=False),
        label="JSON preparado para Startrack",
        note="Preparado no es enviado: este cuerpo no acredita que Startrack lo haya recibido.",
    )


def exchange_view(trace: IntegrationTrace, context: QueryContext):
    """A selectable sequence of server interactions, backed by the shared trace.

    Rows describe the connector contract, never a packet capture or evidence of a POST.
    The view is read-only: selecting a row only reveals its already-loaded projection.
    """
    return html.Div(
        [
            dmc.Title("Interacción entre las APIs", order=2, size="h4"),
            html.P(
                "Prisma y Startrack no se llaman entre sí: ECON coordina cada intercambio "
                "desde el servidor y conserva las evidencias por separado.",
                className="exchange-lede",
            ),
            html.Div(
                [
                    html.P(CONTRACT_NOTE, className="truth-line"),
                    html.P(PREPARED_NOTE, className="truth-line"),
                    html.P(MODE_NOTES[trace.mode], className="truth-mode"),
                ],
                className="exchange-truth",
            ),
            actors_row(),
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [connection_tab(stage) for stage in trace.stages],
                        className="exchange-connections",
                        **{"aria-label": "Interacciones entre Prisma, ECON y Startrack"},
                    ),
                    html.P(STATE_CAPTION, className="exchange-caption"),
                    *[
                        dmc.TabsPanel(
                            [
                                contract_block(stage),
                                dmc.Text(stage_note(trace, stage.key), size="sm", mt="sm"),
                                stage_section(position, stage, context),
                                section("Cuerpo preparado para Startrack", prepared_payload(trace))
                                if stage.key == "startrack_request"
                                else None,
                            ],
                            value=stage.key,
                            pt="lg",
                        )
                        for position, stage in enumerate(trace.stages, start=1)
                    ],
                ],
                value="prisma",
                keepMounted=False,
                className="exchange-tabs",
            ),
            html.P(RECEIPT_NOTE, className="exchange-closing"),
        ],
        className="exchange-view",
    )


def stage_section(position: int, stage: TraceStage, context: QueryContext):
    body = [
        hint(stage.summary),
        rows_table({entry.label: entry_view(entry) for entry in stage.entries})
        if stage.entries
        else empty("Sin campos que mostrar en esta etapa", stage.summary),
        [
            eyebrow("Pendientes y reglas de esta etapa"),
            dmc.List([dmc.ListItem(rule) for rule in stage.rules], size="sm"),
        ]
        if stage.rules
        else None,
    ]
    if stage.provenance or stage.equipment_provenance:
        body.append(
            accordion(
                disclosure("Procedencia de la solicitud", provenance(stage.provenance))
                if stage.provenance
                else None,
                disclosure("Procedencia de la unidad", provenance(stage.equipment_provenance))
                if stage.equipment_provenance
                else None,
                mt="sm",
            )
        )
    return section(
        f"Etapa {position} · {stage.title}",
        dmc.Group(
            [
                eyebrow("Estado de la evidencia"),
                state_text(STAGE_STATES[stage.state][1], STAGE_STATES[stage.state][0]),
            ],
            gap="xs",
            mb="xs",
        ),
        *body,
    )


def duration_text(seconds: float) -> str:
    minutes, remainder = divmod(int(abs(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = [
        f"{value} {unit}" for value, unit in [(days, "d"), (hours, "h"), (minutes, "min")] if value
    ] or [f"{remainder} s"]
    return ("−" if seconds < 0 else "") + " ".join(parts)


def times_section(trace: IntegrationTrace):
    timeline = trace.timeline
    expected = timeline.expected_duration_seconds
    return section(
        "Tiempos del traslado",
        eyebrow("Instantes registrados"),
        simple_table(
            ["Instante", "Momento registrado", "De dónde sale"],
            [
                [
                    moment.label,
                    instant(moment.at) if moment.at else "Sin registro",
                    moment.source,
                ]
                for moment in timeline.instants
            ],
            caption="Instantes registrados por las fuentes para este traslado",
        ),
        eyebrow("Duraciones calculadas", "eyebrow spaced"),
        simple_table(
            ["Duración", "Valor", "Lectura"],
            [
                *(
                    [
                        duration.label,
                        duration_text(duration.seconds),
                        duration.detail,
                    ]
                    for duration in timeline.durations
                ),
                [
                    "Duración esperada (Startrack)",
                    duration_text(expected)
                    if expected is not None
                    else "Sin duración esperada informada",
                    "Campo duration del Job Data Object, en segundos.",
                ],
            ],
            caption="Duraciones calculadas solo con instantes registrados",
        ),
        hint(timeline.note),
    )


def treatment_summary(rows: list[TraceField]) -> str:
    counts = {key: sum(1 for row in rows if row.treatment == key) for key in TREATMENTS}
    detail = " · ".join(f"{counts[key]} {TREATMENTS[key].lower()}" for key in TREATMENTS)
    return f"{len(rows)} conceptos comparados: {detail}."


def map_table(rows: list[TraceField], *, caption: str):
    """Field map with a row rule on every concept that has no direct counterpart."""
    return dmc.TableScrollContainer(
        dmc.Table(
            [
                dmc.TableCaption(caption, className="sr-only"),
                dmc.TableThead(
                    dmc.TableTr(
                        [
                            dmc.TableTh(label)
                            for label in ["Concepto", "Prisma", "ECON", "Startrack", "Tratamiento"]
                        ]
                    )
                ),
                dmc.TableTbody(
                    [
                        dmc.TableTr(
                            [
                                dmc.TableTd(
                                    html.Div(
                                        [
                                            dmc.Text(row.concept, size="sm", fw=600),
                                            dmc.Text(row.note, size="xs", c="dimmed", mt=2)
                                            if row.note
                                            else None,
                                        ]
                                    )
                                ),
                                dmc.TableTd(cell_view(row.prisma)),
                                dmc.TableTd(cell_view(row.econ)),
                                dmc.TableTd(cell_view(row.startrack)),
                                dmc.TableTd(treatment_view(row.treatment)),
                            ],
                            className="fm-row fm-absent" if row.treatment == "absent" else "fm-row",
                        )
                        for row in rows
                    ]
                ),
            ],
            highlightOnHover=True,
        ),
        minWidth=760,
        type="native",
        **{"aria-label": caption},
    )


def treatment_legend():
    return html.Dl(
        [
            item
            for key in TREATMENTS
            for item in (
                html.Dt(TREATMENTS[key]),
                html.Dd(TREATMENT_MEANINGS[key]),
            )
        ],
        className="treatment-legend",
    )


def field_map_section(trace: IntegrationTrace):
    """Two audited groups: what ECON maps across platforms and what it never sends."""
    sent = [row for row in trace.field_map if row.prisma.field or row.econ.field]
    provider_only = [row for row in trace.field_map if not (row.prisma.field or row.econ.field)]
    return section(
        "Mapeo campo a campo",
        html.P(treatment_summary(trace.field_map), className="map-summary"),
        html.P(
            "Las filas con una regla al margen no tienen mapeo directo: el dato no viaja o "
            "depende de una decisión del operador.",
            className="map-rule-note",
        ),
        html.Div(
            [
                eyebrow("Campos que ECON toma de Prisma y prepara para Startrack"),
                map_table(sent, caption="Correspondencia de campos entre Prisma, ECON y Startrack"),
                eyebrow("Campos del formulario de Startrack que ECON no envía", "eyebrow spaced"),
                map_table(
                    provider_only,
                    caption="Campos del formulario de Startrack sin origen en Prisma ni en ECON",
                )
                if provider_only
                else hint("La lectura no registra campos exclusivos del formulario de Startrack."),
            ],
            className="field-map",
        ),
        eyebrow("Cómo leer el tratamiento", "eyebrow spaced"),
        treatment_legend(),
    )


def trace_panel(hub: HubResponse, context: QueryContext, workflow, request_id: str | None):
    if request_id is None:
        return empty(
            "Sin solicitudes en esta consulta",
            "Cambia el origen de datos o revisa la cobertura de la lectura.",
        )
    trace = build_trace(hub, request_id, workflow)
    if trace is None:
        return empty(
            "Solicitud fuera de la consulta",
            "Comprueba el origen seleccionado y el identificador de la solicitud.",
        )
    current = next((stage for stage in trace.stages if stage.state != "done"), None)
    api_href = f"/api/v1/integration/{quote(trace.request_id, safe='')}?mode={trace.mode}"
    return [
        facts(
            [
                ("Solicitud", link(trace.request_label, context.request_href(trace.request_id))),
                ("Unidad asignada", trace.equipment_label or "Sin unidad asignada"),
                (
                    "Movimiento guardado",
                    link(trace.movement_reference, context.movement_href(trace.movement_id))
                    if trace.movement_id
                    else trace.message,
                ),
            ]
        ),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Recorrido", value="overview"),
                        dmc.TabsTab("Tiempos", value="times"),
                        dmc.TabsTab("Mapa de campos", value="fields"),
                        dmc.TabsTab("Respuesta de nuestra API", value="api"),
                    ]
                ),
                dmc.TabsPanel(
                    [
                        exchange_view(trace, context),
                        html.Div(
                            [
                                dmc.Title("Qué falta resolver", order=2, size="h4"),
                                dmc.List(
                                    [dmc.ListItem(rule) for rule in current.rules],
                                    size="sm",
                                    mt="sm",
                                )
                                if current and current.rules
                                else hint(
                                    current.summary
                                    if current
                                    else "Las cuatro etapas tienen evidencia. "
                                    "Revisa llegada y recepción por separado."
                                ),
                                link(
                                    "Revisar solicitud y asignación",
                                    context.request_href(trace.request_id),
                                    mt="md",
                                    display="block",
                                ),
                            ],
                            className="trace-next",
                        ),
                    ],
                    value="overview",
                ),
                dmc.TabsPanel(times_section(trace), value="times"),
                dmc.TabsPanel(
                    [
                        field_map_section(trace),
                        link(
                            "Consultar contrato JSON",
                            api_href,
                        ),
                    ],
                    value="fields",
                ),
                dmc.TabsPanel(
                    [
                        dmc.Title("Lo que expone nuestra API", order=2, size="h4"),
                        hint(
                            "Esta es la misma proyección que entrega el endpoint de ECON: "
                            "origen, transformación, preparación y evidencia de retorno. "
                            "No es una captura de tráfico HTTP entre proveedores."
                        ),
                        link(
                            "Abrir respuesta JSON de ECON",
                            api_href,
                            display="block",
                            mb="md",
                        ),
                        json_block(
                            kind="Respuesta de nuestra API",
                            contract=f"GET {api_href}",
                            body=trace.model_dump_json(indent=2),
                            label="Respuesta JSON de la API de ECON",
                            note="Un HTTP 200 de ECON puede describir evidencia faltante; no "
                            "certifica conexión ni envío a Startrack.",
                        ),
                    ],
                    value="api",
                ),
            ],
            id={"type": "integration-stage", "request": trace.request_id},
            value="overview",
            persistence=trace.mode,
            persistence_type="session",
            keepMounted=False,
            className="analysis-tabs",
            mt="md",
        ),
    ]


def integration_page(hub: HubResponse, context: QueryContext, workflow=None):
    selected = default_request_id(hub)
    return [
        heading("Integración", INTRO),
        dmc.Select(
            id=SELECT_ID,
            label="Solicitud a seguir",
            description="Cambiar la solicitud solo vuelve a leer lo que ya está en memoria.",
            value=selected,
            persistence=context.mode,
            persistence_type="session",
            data=request_options(hub),
            allowDeselect=False,
            searchable=True,
            nothingFoundMessage="Sin solicitudes en esta consulta",
            w={"base": "100%", "sm": 520},
            mb="md",
        ),
        html.Div(trace_panel(hub, context, workflow, selected), id=PANEL_ID),
    ]


def integration_controls():
    """Declare the page ids for the validation layout without building a whole trace."""
    return [dmc.Select(id=SELECT_ID, data=[], label="Solicitud a seguir"), html.Div(id=PANEL_ID)]
