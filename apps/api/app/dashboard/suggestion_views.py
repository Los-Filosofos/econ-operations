"""Candidate units and date conflicts shown where the decision is made; nothing is assigned.

Both sections read the projections the page already has (`HubResponse`, `WorkflowOverview`)
through the rule services (`services.suggestions`, `services.intervals`): they call no
provider and duplicate no rule. Suggestions carry no distance, ETA or GPS presence, because
the tracked device may belong to the carrier. A missing or unzoned date stays «no
verificable»; it is never reported as «sin conflicto».
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

import dash_mantine_components as dmc

from app.dashboard.analytics import equipment_label
from app.dashboard.components import (
    accordion,
    disclosure,
    facts,
    hint,
    icon,
    link,
    section,
    simple_table,
    state_text,
)
from app.dashboard.context import QueryContext
from app.dashboard.workflow_views import STATES, matching_movements
from app.models.hub import AlertRecord, EquipmentRecord, HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.suggestions import CandidateUnit
from app.models.workflow import WorkflowOverview
from app.services.hub import APPROVED, BUSINESS_TIMEZONE, PENDING
from app.services.intervals import (
    DayInterval,
    assignment_window_of,
    compare,
    covers,
    parse_day,
    usage_period_of,
)
from app.services.suggestions import OPEN_MOVEMENT_STATES, suggest_assignment
from app.services.transfers import compatible_evidence

AUTHORITY = "Recomendar no es asignar: la asignación se hace en Prisma."
NO_GEOMETRY = "Sin distancias ni tiempos estimados: la ubicación física no se verifica por GPS."
TIERS = {
    "eligible": ("Elegible según la lectura", "active"),
    "review_required": ("Por revisar", "pending"),
    "excluded": ("Descartada", "neutral"),
}
VERDICTS = {
    "conflict": ("Cruce", "issue"),
    "discrepancy": ("Discrepancia", "pending"),
    "not_verifiable": ("No verificable", "neutral"),
    "clear": ("Sin cruce", "active"),
}
INTERVAL_ALERTS = {
    "overlapping_approved_requests",
    "overlap_not_verifiable",
    "assignment_window_differs_from_request",
}
# A failed movement no longer schedules anything; every other state still can.
SCHEDULED_STATES = OPEN_MOVEMENT_STATES | {"blocked", "sent"}


def _title(icon_name: str, text: str):
    return dmc.Group([icon(icon_name, 20), text], gap=8, wrap="nowrap")


def _open(request: RequestRecord) -> bool:
    return request.status.upper() in PENDING | APPROVED


def request_label(request: RequestRecord) -> str:
    return f"{request.project_name or 'Solicitud sin proyecto'} · {request.status}"


# --- Suggestions -------------------------------------------------------------------------


def unit_review_reasons(unit: EquipmentRecord) -> list[str]:
    """Administrative facts of Prisma that put a linked unit under review; nothing inferred."""
    reasons = []
    if unit.machinery_status.strip().upper() == "OBSOLETA":
        reasons.append("OBSOLETA en Prisma")
    if unit.maintenance_is_stopped is True:
        reasons.append("paro de mantenimiento registrado")
    if unit.maintenance_failure_id:
        reasons.append(f"falla activa {unit.maintenance_failure_id}")
    return reasons


def recommendation(candidate: CandidateUnit) -> str | None:
    """Only what the service backs: the tier and the same-project administrative evidence."""
    if candidate.eligibility == "excluded":
        return None
    status = candidate.machinery_status.strip().upper() or "sin estado"
    if candidate.same_project_evidence is not None:
        pending = " tras revisar los puntos indicados" if candidate.review_reasons else ""
        return (
            f"Ya está asignada al mismo proyecto hasta "
            f"{candidate.assignment_ends_on or 'fecha ausente'} y está {status}: valorar "
            f"usarla{pending}. Hecho administrativo registrado en Prisma, no ubicación observada."
        )
    if candidate.eligibility == "eligible":
        return (
            f"Cumple la clase exacta y está {status} en Prisma: valorar usarla. El estado "
            "administrativo no acredita disponibilidad física."
        )
    return "Cumple la clase; valorarla solo después de revisar los puntos indicados."


def candidate_card(candidate: CandidateUnit, context: QueryContext):
    label, family = TIERS[candidate.eligibility]
    project = " · ".join(filter(None, [candidate.project_id, candidate.project_name]))
    if candidate.project_id or candidate.assignment_starts_on or candidate.assignment_ends_on:
        project = (
            f"{project or 'Proyecto sin ID'} ({candidate.assignment_starts_on or 'ausente'} → "
            f"{candidate.assignment_ends_on or 'ausente'})"
        )
    advice = recommendation(candidate)
    return dmc.Paper(
        [
            dmc.Group(
                [
                    link(candidate.label, context.equipment_href(candidate.equipment_id), fw=600),
                    state_text(label, family),
                ],
                justify="space-between",
                gap="md",
            ),
            facts(
                [
                    (
                        "Clase comparada",
                        f"solicitud «{candidate.requested_class or 'ausente'}» · unidad "
                        f"«{candidate.equipment_class or 'ausente'}» · "
                        + ("coincide" if candidate.class_match else "distinta"),
                    ),
                    ("Estado administrativo", state_text(candidate.machinery_status)),
                    ("Proyecto vigente en Prisma", project or "Sin proyecto vigente informado"),
                ]
            ),
            dmc.Text(advice, size="sm", fw=500) if advice else None,
            [
                dmc.Text("Puntos a revisar", size="xs", c="dimmed", mt="xs"),
                dmc.List([dmc.ListItem(reason) for reason in candidate.review_reasons], size="sm"),
            ]
            if candidate.review_reasons
            else None,
            accordion(
                disclosure(
                    f"Motivos ({len(candidate.reasons)})",
                    dmc.List([dmc.ListItem(reason) for reason in candidate.reasons], size="sm"),
                ),
                disclosure(
                    f"No verificable en esta lectura ({len(candidate.missing)})",
                    dmc.List([dmc.ListItem(item) for item in candidate.missing], size="sm"),
                )
                if candidate.missing
                else None,
                mt="sm",
            ),
        ],
        withBorder=True,
        p="md",
        mb="sm",
        className="candidate-card",
    )


def excluded_table(candidates: list[CandidateUnit], context: QueryContext):
    return simple_table(
        ["Unidad", "Clase comparada", "Estado", "Motivos de descarte"],
        [
            [
                link(candidate.label, context.equipment_href(candidate.equipment_id)),
                f"«{candidate.requested_class or 'ausente'}» vs "
                f"«{candidate.equipment_class or 'ausente'}»",
                state_text(candidate.machinery_status),
                " ".join(candidate.exclusion_reasons),
            ]
            for candidate in candidates
        ],
        caption="Unidades descartadas y sus motivos",
    )


def linked_unit_note(hub: HubResponse, request: RequestRecord, message: str, context):
    """A linked unit under review: say why nothing is proposed and where the path continues."""
    unit = next((item for item in hub.equipment if item.id == request.machinery_id), None)
    reasons = unit_review_reasons(unit) if unit else []
    if not reasons:
        return None
    return [
        hint(
            f"La solicitud tiene vinculada la unidad {equipment_label(unit)} y su estado "
            f"requiere revisión ({', '.join(reasons)}). {message}"
        ),
        hint(
            "Mientras Prisma mantenga la vinculación, ECON no propone sustitutas; si la "
            f"desvincula, aquí aparecerán las candidatas de clase "
            f"«{request.machinery_type or 'ausente'}». {AUTHORITY}"
        ),
        link("Abrir la unidad", context.equipment_href(unit.id)),
    ]


def suggestions_section(
    hub: HubResponse,
    request: RequestRecord,
    workflow: WorkflowOverview | None,
    context: QueryContext,
):
    """Candidates for a pending request without a unit; a linked unit under review gets a note.

    Returns None when the request is outside the read or when the service has nothing to say.
    """
    suggestion = suggest_assignment(hub, request.id, workflow)
    if suggestion is None:
        return None
    heading = _title("bulb", "Unidades que podrían cubrir esta solicitud")
    if not suggestion.applicable:
        note = linked_unit_note(hub, request, suggestion.message, context)
        return section(heading, note) if note else None
    listed = [item for item in suggestion.candidates if item.eligibility != "excluded"]
    excluded = [item for item in suggestion.candidates if item.eligibility == "excluded"]
    return section(
        heading,
        hint(
            f"Clase solicitada «{suggestion.requested_class or 'ausente'}» · período "
            f"{usage_period_of(request).span()}. {suggestion.message}"
        ),
        [candidate_card(item, context) for item in listed]
        or hint(
            "Ninguna unidad de la lectura cumple clase y estado administrativo; revisa las "
            "descartadas y la cobertura de la consulta."
        ),
        hint(
            f"Clases con grafía cercana en la lectura: {', '.join(suggestion.similar_classes)}. "
            "No se unen registros ni cambia el nivel de ninguna candidata."
        )
        if suggestion.similar_classes
        else None,
        accordion(
            disclosure(
                f"Descartadas y por qué ({len(excluded)})", excluded_table(excluded, context)
            )
        )
        if excluded
        else None,
        hint(f"{AUTHORITY} {NO_GEOMETRY}", fw=500),
    )


# --- Conflicts ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One documented comparison: which interval, against which, with exact dates."""

    verdict: str
    left: str
    right: str
    detail: str
    parties: tuple[tuple[str, str], ...] = ()


def _span(interval: DayInterval, owner: str) -> str:
    return f"{interval.label.capitalize()} · {owner} · {interval.span()}"


def _day_of(instant: datetime | None) -> date | None:
    """Only a zoned instant yields a business day; an unzoned one stays unknown."""
    if instant is None or instant.tzinfo is None:
        return None
    return instant.astimezone(BUSINESS_TIMEZONE).date()


def _scheduled_day(movement: MovementRecord) -> date | None:
    value = movement.mapping.get("scheduled_date")
    return parse_day(value) if isinstance(value, str) else None


def window_finding(request: RequestRecord, unit: EquipmentRecord, context) -> Finding | None:
    """Usage period against the unit's current administrative assignment window."""
    if not (unit.project_id or unit.assignment_starts_on or unit.assignment_ends_on):
        return None
    usage, window = usage_period_of(request), assignment_window_of(unit)
    relation = compare(usage, window)
    same_project = bool(request.project_id) and unit.project_id == request.project_id
    other = " · ".join(filter(None, [unit.project_id, unit.project_name])) or "otro proyecto"
    if relation.status == "not_verifiable":
        verdict, detail = "not_verifiable", relation.reason
    elif relation.status == "overlap":
        if same_project and (usage.start, usage.end) == (window.start, window.end):
            verdict = "clear"
            detail = "La asignación vigente coincide con el período solicitado."
        elif same_project:
            verdict = "discrepancy"
            detail = (
                f"{relation.reason} La ventana registrada para el mismo proyecto difiere del "
                "período aprobado; revisar la vigencia en Prisma."
            )
        else:
            verdict = "conflict"
            detail = (
                f"{relation.reason} La unidad figura asignada a {other} durante el período; "
                "Prisma admite ambos hechos y ECON solo lo señala."
            )
    elif same_project:
        verdict = "discrepancy"
        detail = (
            f"{relation.reason} La asignación vigente no cubre el período solicitado; revisar "
            "la vigencia en Prisma."
        )
    else:
        verdict, detail = "clear", relation.reason
    return Finding(
        verdict,
        _span(usage, request_label(request)),
        _span(window, equipment_label(unit)),
        detail,
        ((equipment_label(unit), context.equipment_href(unit.id)),),
    )


def pair_finding(first: RequestRecord, second: RequestRecord, context, *, both: bool) -> Finding:
    """Two open requests on the same unit; Prisma admits both and ECON only points at them."""
    relation = compare(usage_period_of(first), usage_period_of(second))
    verdict = {"overlap": "conflict", "disjoint": "clear", "not_verifiable": "not_verifiable"}[
        relation.status
    ]
    detail = relation.reason
    if verdict == "conflict":
        detail += " Prisma admite ambas; ECON solo lo señala y no modifica la asignación."
    parties = [(request_label(second), context.request_href(second.id))]
    if both:
        parties.insert(0, (request_label(first), context.request_href(first.id)))
    return Finding(
        verdict,
        _span(usage_period_of(first), request_label(first)),
        _span(usage_period_of(second), request_label(second)),
        detail,
        tuple(parties),
    )


def schedule_finding(
    request: RequestRecord, movement: MovementRecord, context, *, own: bool
) -> Finding:
    """A transfer day against the usage period; the period is never a delivery window."""
    usage = usage_period_of(request)
    day = _scheduled_day(movement)
    placement = covers(usage, day, "la fecha programada")
    right = (
        f"Programación del traslado · {movement.movement_reference} "
        f"({STATES[movement.state]}) · {day.isoformat() if day else 'ausente'}"
    )
    if placement.status == "not_verifiable":
        verdict, detail = "not_verifiable", placement.reason
    elif own:
        if placement.status == "overlap":
            verdict, detail = "clear", placement.reason
        elif day > usage.end:
            verdict = "discrepancy"
            detail = f"{placement.reason} Programado después del fin del período solicitado."
        else:
            verdict = "clear"
            detail = f"{placement.reason} Precede al período; el período no es ventana de entrega."
    elif placement.status == "overlap":
        verdict = "conflict"
        detail = (
            f"{placement.reason} Es un traslado sin cerrar de la misma unidad para otra "
            f"solicitud ({movement.request_source_id})."
        )
    else:
        verdict, detail = "clear", placement.reason
    return Finding(
        verdict,
        _span(usage, request_label(request)),
        right,
        detail,
        ((movement.movement_reference, context.movement_href(movement.id)),),
    )


def observed_findings(request: RequestRecord, movement: MovementRecord, context) -> list[Finding]:
    """Recorded instants (arrivals, receipt) placed on the usage period, one per fact."""
    usage = usage_period_of(request)
    instants = [
        ("la llegada observada", event.event_time)
        for event in movement.events
        if event.kind == "arrival"
    ]
    if movement.receipt:
        instants.append(("la recepción declarada", movement.receipt.received_at))
    findings = []
    for what, instant in instants:
        day = _day_of(instant)
        placement = covers(usage, day, what)
        if placement.status == "not_verifiable":
            verdict, detail = "not_verifiable", placement.reason
        elif placement.status == "overlap":
            verdict, detail = "clear", placement.reason
        else:
            verdict = "discrepancy"
            detail = f"{placement.reason} Fuera del período de uso; el período no es ventana."
        findings.append(
            Finding(
                verdict,
                _span(usage, request_label(request)),
                f"Intervalo observado · {what} · {day.isoformat() if day else 'ausente'} · "
                f"{movement.movement_reference}",
                detail,
                ((movement.movement_reference, context.movement_href(movement.id)),),
            )
        )
    return findings


def unit_movements(
    hub: HubResponse, unit: EquipmentRecord, workflow: WorkflowOverview | None
) -> list[MovementRecord]:
    """Movements that still schedule the unit, matched by exact source id and evidence."""
    if workflow is None or not workflow.available or not unit.provenance.source_id:
        return []
    return [
        movement
        for movement in workflow.movements
        if movement.mode == hub.mode
        and movement.environment == unit.provenance.environment
        and movement.machinery_source_id == unit.provenance.source_id
        and (
            movement.state in OPEN_MOVEMENT_STATES
            or (movement.state == "sent" and movement.receipt is None)
        )
    ]


def _own_movements(workflow, request: RequestRecord) -> list[MovementRecord]:
    return [m for m in matching_movements(workflow, request) if m.state in SCHEDULED_STATES]


def request_findings(
    hub: HubResponse, request: RequestRecord, workflow: WorkflowOverview | None, context
) -> list[Finding]:
    unit = next((item for item in hub.equipment if item.id == request.machinery_id), None)
    findings: list[Finding] = []
    if unit is not None:
        if (finding := window_finding(request, unit, context)) is not None:
            findings.append(finding)
        findings.extend(
            pair_finding(request, other, context, both=False)
            for other in sorted(hub.requests, key=lambda item: item.id)
            if other.id != request.id
            and other.machinery_id == unit.id
            and _open(other)
            and compatible_evidence(request.provenance, other.provenance)
        )
    for movement in _own_movements(workflow, request):
        findings.append(schedule_finding(request, movement, context, own=True))
        findings.extend(observed_findings(request, movement, context))
    if unit is not None:
        findings.extend(
            schedule_finding(request, movement, context, own=False)
            for movement in unit_movements(hub, unit, workflow)
            if movement.request_source_id != request.provenance.source_id
        )
    return findings


def equipment_findings(
    hub: HubResponse, unit: EquipmentRecord, workflow: WorkflowOverview | None, context
) -> list[Finding]:
    related = sorted(
        (
            request
            for request in hub.requests
            if request.machinery_id == unit.id
            and _open(request)
            and compatible_evidence(unit.provenance, request.provenance)
        ),
        key=lambda item: item.id,
    )
    findings: list[Finding] = []
    for request in related:
        if (finding := window_finding(request, unit, context)) is not None:
            findings.append(finding)
        for movement in _own_movements(workflow, request):
            findings.append(schedule_finding(request, movement, context, own=True))
            findings.extend(observed_findings(request, movement, context))
    findings.extend(
        pair_finding(first, second, context, both=True)
        for index, first in enumerate(related)
        for second in related[index + 1 :]
    )
    scheduled = unit_movements(hub, unit, workflow)
    findings.extend(
        schedule_finding(request, movement, context, own=False)
        for request in related
        for movement in scheduled
        if movement.request_source_id != request.provenance.source_id
    )
    return findings


def hub_signals(
    hub: HubResponse, *, request: RequestRecord | None = None, unit: EquipmentRecord | None = None
) -> list[AlertRecord]:
    """Interval alerts the shared read already raised for the subject, quoted by code."""
    return [
        alert
        for alert in hub.alerts
        if alert.code in INTERVAL_ALERTS
        and (
            (
                request is not None
                and (
                    alert.request_id == request.id
                    or any(f"solicitud={request.id}" in item for item in alert.evidence)
                )
            )
            or (unit is not None and alert.equipment_id == unit.id)
        )
    ]


def findings_table(findings: list[Finding]):
    return simple_table(
        ["Resultado", "Intervalo", "Contrastado con", "Detalle", "Implicado"],
        [
            [
                state_text(*VERDICTS[finding.verdict]),
                finding.left,
                finding.right,
                finding.detail,
                dmc.Stack([link(label, href) for label, href in finding.parties], gap=2)
                if finding.parties
                else "—",
            ]
            for finding in findings
        ],
        caption="Comparaciones de intervalos documentados",
    )


def conflicts_section(
    hub: HubResponse,
    subject: RequestRecord | EquipmentRecord,
    workflow: WorkflowOverview | None,
    context: QueryContext,
):
    """Date overlaps and discrepancies for a request or a unit; None when nothing compares."""
    if isinstance(subject, RequestRecord):
        findings = request_findings(hub, subject, workflow, context)
        signals, owner = hub_signals(hub, request=subject), "esta solicitud"
    else:
        findings = equipment_findings(hub, subject, workflow, context)
        signals, owner = hub_signals(hub, unit=subject), "esta unidad"
    if not findings and not signals:
        return None
    flagged = [finding for finding in findings if finding.verdict != "clear"]
    clear = [finding for finding in findings if finding.verdict == "clear"]
    counts = Counter(finding.verdict for finding in findings)
    return section(
        _title("alert-triangle", "Cruces de fechas y discrepancias"),
        hint(
            f"{counts['conflict']} cruce(s), {counts['discrepancy']} discrepancia(s) y "
            f"{counts['not_verifiable']} no verificable(s) en {len(findings)} comparaciones de "
            f"fechas documentadas para {owner}.",
            role="status",
        ),
        findings_table(flagged)
        if flagged
        else hint("Sin cruces ni discrepancias en las fechas documentadas."),
        accordion(disclosure(f"Comparaciones sin cruce ({len(clear)})", findings_table(clear)))
        if clear
        else None,
        [
            dmc.Text("Señales de la lectura del hub", size="xs", c="dimmed", mt="sm"),
            dmc.List(
                [
                    dmc.ListItem(f"{alert.title} ({alert.code}) · {alert.owner}")
                    for alert in signals
                ],
                size="sm",
            ),
        ]
        if signals
        else None,
        hint(
            "Comparación inclusiva por días de las fechas documentadas: período de uso, "
            "asignación vigente, programación del traslado e instantes observados en lecturas "
            "acotadas. Una fecha ausente o sin zona queda «no verificable», nunca «sin "
            "conflicto». ECON señala; la asignación se revisa en Prisma."
        ),
    )
