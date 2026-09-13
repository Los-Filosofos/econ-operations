"""Candidate units for a pending request, derived from the bounded read; nothing is assigned.

Pure function in the ``build_trace`` pattern: it reads a ``HubResponse`` and an optional
``WorkflowOverview`` and calls no provider. Every rule quotes the source field it uses and a
fact the bounded read did not cover stays in ``missing`` as «no verificable». Prisma remains
the authority of the assignment. GPS presence and geofence visits are never used as evidence
of where a unit is: the tracked device may belong to the carrier, and entering a geofence
proves neither unloading nor availability. Similar class spellings are reported, never
merged, and never change a candidate's tier.
"""

from app.models.hub import EquipmentRecord, HubResponse, RequestRecord
from app.models.operations import MovementRecord
from app.models.suggestions import AssignmentSuggestion, CandidateUnit, SuggestionEvidence
from app.models.workflow import WorkflowOverview
from app.services.hub import APPROVED, PENDING
from app.services.intervals import (
    DayInterval,
    assignment_window_of,
    compare,
    parse_day,
    scheduled_day,
    usage_period_of,
)
from app.services.transfers import compatible_evidence

TIER_ORDER = {"eligible": 0, "review_required": 1, "excluded": 2}
# unknown: the POST outcome is uncertain, so a task may exist; it is treated as open.
OPEN_MOVEMENT_STATES = {"draft", "queued", "sending", "unknown"}
LOCATION_NOT_VERIFIABLE = (
    "Ubicación física de la unidad: no verificable. ECON no usa presencia GPS ni visitas a "
    "geocercas como evidencia de ubicación (el dispositivo puede ser del transportador)."
)
RULES = [
    "R0 Evidencia compatible: solo unidades de Prisma con la misma clase de evidencia, entorno "
    "y carácter sintético que la solicitud; fixture y live nunca se mezclan.",
    "R1 Clase exacta: request.machinery_type y equipment.equipment_class se comparan tal cual "
    "(solo strip). Las grafías cercanas se informan en similar_classes sin unir registros ni "
    "cambiar el nivel de ninguna candidata.",
    "R2 Estado administrativo: solo DISPONIBLE es candidatable; OCUPADA, OBSOLETA y valores no "
    "reconocidos se listan como excluidos con su motivo. DISPONIBLE no acredita disponibilidad "
    "física.",
    "R3 Paro: active_failure_is_paro=true excluye; null queda «no verificable».",
    "R4 Falla activa: active_failure_id requiere revisión de Mantenimiento; no equivale por sí "
    "sola a indisponibilidad.",
    "R5 Asignación vigente: fecha_inicio_uso/fecha_fin_uso frente al período solicitado, "
    "inclusivo por días. DISPONIBLE con proyecto o fechas informados es una contradicción "
    "administrativa a revisar; fechas ausentes o sin zona quedan «no verificable».",
    "R6 Otras solicitudes PENDIENTE/APROBADA con la misma maquinaria_id y período que se cruza "
    "requieren revisión; fechas ausentes quedan «no verificable».",
    "R7 Movimientos locales de la misma unidad (draft, queued, sending, unknown o sent sin "
    "recepción) programados dentro o antes del período requieren revisión; registro sin "
    "consultar o parcial queda «no verificable».",
    "R8 Mismo proyecto: solo project_id igual en Prisma con asignación que termina antes del "
    "período solicitado. Es continuidad administrativa, no ubicación observada.",
    "La presencia GPS y las visitas a geocercas no se usan: el dispositivo puede ser del "
    "transportador y entrar en una geocerca no prueba ubicación ni disponibilidad.",
    "Orden determinista por nivel (eligible, review_required, excluded), evidencia de mismo "
    "proyecto e ID de unidad; sin puntajes, distancias ni ETA.",
]


def _find_request(hub: HubResponse, request_id: str) -> RequestRecord | None:
    return next(
        (r for r in hub.requests if r.id == request_id or r.provenance.source_id == request_id),
        None,
    )


def _singular(word: str) -> str:
    for suffix in ("es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)]
    return word


def _similar(requested: str, actual: str) -> bool:
    """Case or plural variants only; the records are still never merged."""
    left, right = requested.casefold(), actual.casefold()
    return left == right or _singular(left) == _singular(right)


def _open_movement_of(movement: MovementRecord, hub: HubResponse, item: EquipmentRecord) -> bool:
    return (
        movement.mode == hub.mode
        and movement.environment == item.provenance.environment
        and item.provenance.source_id is not None
        and movement.machinery_source_id == item.provenance.source_id
        and (
            movement.state in OPEN_MOVEMENT_STATES
            or (movement.state == "sent" and movement.receipt is None)
        )
    )


def _movement_notes(
    hub: HubResponse,
    item: EquipmentRecord,
    usage: DayInterval,
    workflow: WorkflowOverview | None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """R7: reasons, review reasons, missing facts and conflicting movement IDs."""
    reasons: list[str] = []
    review: list[str] = []
    missing: list[str] = []
    conflicting: list[str] = []
    if workflow is None or not workflow.available:
        missing.append(
            "Registro de movimientos: sin consultar; no se puede descartar un traslado "
            "programado para la unidad."
        )
        return reasons, review, missing, conflicting
    if not workflow.complete:
        missing.append(
            "Registro de movimientos parcial: puede existir un traslado de la unidad fuera "
            "de la ventana leída."
        )
    for movement in workflow.movements:
        if not _open_movement_of(movement, hub, item):
            continue
        value = movement.mapping.get("scheduled_date")
        day = parse_day(value) if isinstance(value, str) else None
        scheduled = scheduled_day(day, f"Movimiento {movement.id}: mapping.scheduled_date")
        relation = compare(scheduled, usage)
        label = f"Movimiento {movement.movement_reference} ({movement.state})"
        if relation.status == "not_verifiable":
            missing.append(
                f"{label}: relación programación/período no verificable; falta "
                f"{', '.join(relation.missing)}."
            )
        elif relation.status == "overlap" or day < usage.start:
            conflicting.append(movement.id)
            position = "dentro del" if relation.status == "overlap" else "antes del"
            review.append(
                f"{label} programado el {day.isoformat()} {position} período solicitado "
                f"({usage.span()}); la unidad tendría un traslado sin cerrar."
            )
        else:
            reasons.append(
                f"{label} programado el {day.isoformat()}, después del período solicitado."
            )
    return reasons, review, missing, conflicting


def _candidate(
    hub: HubResponse,
    request: RequestRecord,
    item: EquipmentRecord,
    usage: DayInterval,
    workflow: WorkflowOverview | None,
) -> CandidateUnit:
    reasons: list[str] = []
    review: list[str] = []
    excluded: list[str] = []
    missing: list[str] = []
    overlapping_requests: list[str] = []

    # R1: exact class, both strings kept as compared.
    requested = (request.machinery_type or "").strip()
    actual = (item.equipment_class or "").strip()
    class_match = bool(requested) and requested == actual
    if class_match:
        reasons.append(f"Clase exacta: solicitud «{requested}» = unidad «{actual}».")
    else:
        excluded.append(
            f"Clase distinta: solicitud «{request.machinery_type or 'ausente'}» vs unidad "
            f"«{item.equipment_class or 'ausente'}»."
        )

    # R2: administrative state.
    status = item.machinery_status.strip().upper()
    if status == "DISPONIBLE":
        reasons.append(
            "Estado administrativo DISPONIBLE en Prisma; no acredita disponibilidad física."
        )
    elif status == "OCUPADA":
        excluded.append("OCUPADA administrativamente en Prisma.")
    elif status == "OBSOLETA":
        excluded.append("OBSOLETA: revisar con Mantenimiento; el estado no afirma avería ni paro.")
    else:
        excluded.append(f"Estado administrativo no reconocido: {item.machinery_status}.")

    # R3: explicit stop; unknown stays unknown.
    if item.maintenance_is_stopped is True:
        excluded.append("Paro de mantenimiento explícito (active_failure_is_paro=true).")
    elif item.maintenance_is_stopped is None:
        missing.append(
            "Paro de mantenimiento: no verificable (active_failure_is_paro ausente en la lectura)."
        )
    else:
        reasons.append("Sin paro de mantenimiento registrado (active_failure_is_paro=false).")

    # R4: active failure.
    if item.maintenance_failure_id:
        review.append(
            f"Falla activa {item.maintenance_failure_id} "
            f"(estado: {item.maintenance_status or 'sin dato'}); revisar con Mantenimiento."
        )
    else:
        reasons.append("Sin falla activa registrada.")

    # R5: current assignment window vs usage period.
    window = assignment_window_of(item)
    if item.project_id or item.assignment_starts_on or item.assignment_ends_on:
        relation = compare(usage, window)
        if relation.status == "not_verifiable":
            missing.append(
                "Solapamiento con la asignación vigente: no verificable; falta "
                f"{', '.join(relation.missing)}."
            )
        elif relation.status == "overlap":
            review.append(relation.reason)
        else:
            reasons.append(relation.reason)
        if status == "DISPONIBLE":
            review.append(
                "Contradicción administrativa: DISPONIBLE con proyecto o fechas de asignación "
                "informados; revisar la vigencia en Prisma."
            )
    else:
        reasons.append("Prisma no informa proyecto ni fechas de asignación vigente para la unidad.")

    # R6: other requests on the same unit, by exact maquinaria_id.
    for other in hub.requests:
        if (
            other.id == request.id
            or other.machinery_id != item.id
            or other.status.upper() not in PENDING | APPROVED
            or not compatible_evidence(request.provenance, other.provenance)
        ):
            continue
        relation = compare(usage, usage_period_of(other))
        label = f"Solicitud {other.id} ({other.status}) sobre la misma unidad"
        if relation.status == "overlap":
            overlapping_requests.append(other.id)
            review.append(f"{label}: {relation.reason}")
        elif relation.status == "not_verifiable":
            missing.append(
                f"{label}: solapamiento no verificable; falta {', '.join(relation.missing)}."
            )
        else:
            reasons.append(f"{label} no se cruza con el período solicitado.")

    # R7: open local movements of this unit.
    movement_reasons, movement_review, movement_missing, overlapping_movements = _movement_notes(
        hub, item, usage, workflow
    )
    reasons += movement_reasons
    review += movement_review
    missing += movement_missing

    # R8: same project in Prisma, ending before the requested period. Administrative only.
    evidence = None
    if (
        item.project_id
        and item.project_id == request.project_id
        and window.end is not None
        and usage.start is not None
        and window.end < usage.start
    ):
        evidence = SuggestionEvidence(
            fact=(
                f"Asignada administrativamente al mismo proyecto {item.project_id} hasta "
                f"{window.end.isoformat()}, antes del período solicitado. Continuidad "
                "administrativa registrada en Prisma (administrativo, no observado)."
            ),
            source="nexus",
            field="project_id, fecha_fin_uso",
            observed_at=item.provenance.observed_at,
            observed_on=item.provenance.observed_on,
            reference=f"updated_at={item.updated_at.isoformat()}" if item.updated_at else None,
        )

    missing.append(LOCATION_NOT_VERIFIABLE)
    operators_known = item.operators is not None
    if not operators_known:
        missing.append(
            "Operadores asociados: no verificable en la lectura acotada de lista "
            "(solo el detalle de Prisma los documenta)."
        )
    if item.project_rate is None:
        missing.append(
            "Tarifa por proyecto: no verificable en la lectura de lista; es un dato de "
            "entrada de la asignación en Prisma, no un criterio."
        )

    return CandidateUnit(
        equipment_id=item.id,
        equipment_source_id=item.provenance.source_id,
        label=item.asset_number or item.code or item.name,
        requested_class=request.machinery_type,
        equipment_class=item.equipment_class,
        class_match=class_match,
        machinery_status=item.machinery_status,
        project_id=item.project_id,
        project_name=item.project_name,
        assignment_starts_on=item.assignment_starts_on,
        assignment_ends_on=item.assignment_ends_on,
        maintenance_failure_id=item.maintenance_failure_id,
        maintenance_status=item.maintenance_status,
        maintenance_is_stopped=item.maintenance_is_stopped,
        eligibility=("excluded" if excluded else "review_required" if review else "eligible"),
        reasons=reasons,
        review_reasons=review,
        exclusion_reasons=excluded,
        missing=missing,
        overlapping_requests=overlapping_requests,
        overlapping_movements=overlapping_movements,
        same_project_evidence=evidence,
        operators_known=operators_known,
        provenance=item.provenance.model_copy(deep=True),
    )


def _sort_key(candidate: CandidateUnit) -> tuple[int, bool, str]:
    return (
        TIER_ORDER[candidate.eligibility],
        candidate.same_project_evidence is None,
        candidate.equipment_id,
    )


def suggest_assignment(
    hub: HubResponse, request_id: str, workflow: WorkflowOverview | None = None
) -> AssignmentSuggestion | None:
    """Candidates for one request; None when the request is outside the bounded read."""
    request = _find_request(hub, request_id)
    if request is None:
        return None
    base = {
        "mode": hub.mode,
        "generated_at": hub.generated_at,
        "data_as_of": hub.data_as_of,
        "request_id": request.id,
        "request_source_id": request.provenance.source_id,
        "request_status": request.status,
        "project_id": request.project_id,
        "project_label": request.project_name or request.project_id or "Proyecto sin nombre",
        "requested_class": request.machinery_type,
        "requested_starts_on": request.starts_on,
        "requested_ends_on": request.ends_on,
        "rules": list(RULES),
        "scope": hub.scope,
        "registry": hub.operation_evidence,
    }
    if request.status.upper() not in PENDING:
        message = (
            f"No aplica: la solicitud está en estado {request.status}. Solo se sugieren "
            "unidades para solicitudes pendientes sin unidad vinculada."
        )
    elif request.machinery_id:
        message = (
            "No aplica: la solicitud ya tiene una unidad vinculada (maquinaria_id); "
            "la asignación se revisa en Prisma."
        )
    elif request.provenance.source != "nexus":
        message = "No aplica: la solicitud no procede de Prisma."
    else:
        message = ""
    if message:
        return AssignmentSuggestion(
            **base, applicable=False, message=message, candidates=[], similar_classes=[]
        )

    usage = usage_period_of(request)
    units = [
        item
        for item in hub.equipment
        if item.provenance.source == "nexus"
        and compatible_evidence(request.provenance, item.provenance)
    ]
    candidates = sorted(
        (_candidate(hub, request, item, usage, workflow) for item in units), key=_sort_key
    )
    requested = (request.machinery_type or "").strip()
    similar_classes = sorted(
        {
            candidate.equipment_class.strip()
            for candidate in candidates
            if not candidate.class_match
            and requested
            and candidate.equipment_class
            and candidate.equipment_class.strip()
            and _similar(requested, candidate.equipment_class.strip())
        }
    )
    eligible = sum(candidate.eligibility == "eligible" for candidate in candidates)
    review = sum(candidate.eligibility == "review_required" for candidate in candidates)
    total = hub.scope.equipment_total
    coverage = f"{len(units)} de {total if total is not None else 'total desconocido'}"
    message = (
        f"{eligible} unidad(es) elegible(s) y {review} por revisar dentro de la lectura "
        f"acotada ({coverage} unidades). La cobertura parcial no permite afirmar que no "
        "existan otras candidatas; la asignación se registra en Prisma."
    )
    if not requested:
        message = (
            "La solicitud no informa tipo de maquinaria; ninguna unidad cumple la clase "
            f"exacta. {message}"
        )
    elif similar_classes:
        message += (
            " Hay clases con grafía cercana en la lectura (similar_classes); no se unen ni "
            "cambian el nivel de las candidatas."
        )
    return AssignmentSuggestion(
        **base,
        applicable=True,
        message=message,
        candidates=candidates,
        similar_classes=similar_classes,
    )
