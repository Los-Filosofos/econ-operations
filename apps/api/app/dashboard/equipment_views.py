"""Browse every observed machine, including those without a request."""

from dash import dcc, html

from app.dashboard.analytics import equipment_label, instant, readable
from app.dashboard.context import QueryContext
from app.dashboard.views import coverage, empty, grid, heading, markdown_link, notice
from app.models.hub import HubResponse


def equipment_inventory(hub: HubResponse, context: QueryContext):
    content = [
        heading(
            "Maquinaria",
            "Consulta una unidad para comparar su estado en Prisma, el seguimiento "
            "de Startrack y la evidencia de recepción.",
        )
    ]
    if not readable(hub):
        return content + [
            notice(
                "Maquinaria no disponible",
                "No se pudo consultar la maquinaria de este origen. Revisa las fuentes "
                "o vuelve a actualizar; este resultado no significa que no haya equipos.",
                error=True,
            ),
            coverage(hub, context),
        ]

    filters = [
        ("all", "Toda la maquinaria"),
        ("active_failures", "Con falla activa registrada"),
        ("unlinked", "Vínculo con Startrack por revisar"),
    ]
    selected = context.filter if context.filter in {key for key, _ in filters} else "all"
    equipment = hub.equipment
    if selected == "active_failures":
        equipment = [item for item in equipment if item.maintenance_failure_id]
    elif selected == "unlinked":
        equipment = [item for item in equipment if item.relation_status != "confirmed"]

    content.append(
        html.Nav(
            [
                dcc.Link(
                    html.Span(label, **{"aria-current": "page"}) if key == selected else label,
                    href=context.href("/maquinaria", filter=key),
                    className="filter-link" + (" selected" if key == selected else ""),
                )
                for key, label in filters
            ],
            className="filters",
            **{"aria-label": "Filtrar maquinaria"},
        )
    )
    content.append(
        html.P(
            f"{len(equipment)} de {hub.scope.equipment_returned} unidades en esta consulta. "
            "El estado administrativo no confirma disponibilidad física. "
            "Las tareas y ubicaciones se muestran con su propia fecha en el detalle.",
            className="table-hint",
        )
    )
    if not equipment:
        content.extend(
            [
                empty(
                    "Sin maquinaria que coincida",
                    "No hay coincidencias en la lectura consultada. Su cobertura parcial "
                    "no permite descartar equipos fuera de esta ventana.",
                ),
                dcc.Link(
                    "Ver maquinaria sin búsqueda ni filtros",
                    href=QueryContext(mode=context.mode).href("/maquinaria"),
                    className="back-link",
                ),
            ]
        )
    else:
        rows = []
        for item in equipment:
            if item.maintenance_failure_id:
                maintenance = item.maintenance_status or "Falla activa registrada"
                if item.maintenance_is_stopped is True:
                    maintenance += " · Paro registrado"
            elif item.maintenance_is_stopped is True:
                maintenance = "Paro registrado; sin ID de falla"
            else:
                maintenance = "Sin falla activa registrada; disponibilidad no verificada"
            rows.append(
                {
                    "equipment": markdown_link(
                        f"{equipment_label(item)} · {item.name}",
                        context.equipment_href(item.id),
                    ),
                    "project": " · ".join(filter(None, [item.project_id, item.project_name]))
                    or "Sin proyecto registrado",
                    "administration": item.machinery_status,
                    "maintenance": maintenance,
                    "tracking": (
                        f"{len(item.transfers)} tareas vinculadas · Revisar fecha y estado"
                        if item.transfers and item.relation_status == "confirmed"
                        else "Sin evidencia vinculada en esta lectura"
                    ),
                    "location": (
                        f"{item.location.label} · {instant(item.location.observed_at)}"
                        if item.location
                        else "Sin ubicación fechada de la maquinaria"
                    ),
                }
            )
        content.append(
            grid(
                "equipment-table",
                rows,
                [
                    ("equipment", "Maquinaria"),
                    ("project", "Proyecto en Prisma"),
                    ("administration", "Estado administrativo"),
                    ("maintenance", "Mantenimiento"),
                    ("tracking", "Seguimiento Startrack"),
                    ("location", "Ubicación de maquinaria"),
                ],
                link_field="equipment",
            )
        )
    return content + [coverage(hub, context)]
