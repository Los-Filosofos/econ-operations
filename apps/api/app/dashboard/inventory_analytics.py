"""Administrative inventory counts from the visible read, never fleet availability."""

from collections import Counter
from html import escape
from math import ceil

import plotly.graph_objects as go

from app.dashboard.components import accordion, disclosure, hint, section, simple_table
from app.dashboard.decision_analytics import graph
from app.dashboard.theme import figure, state_color
from app.models.hub import EquipmentRecord


def inventory_status_panel(
    equipment: list[EquipmentRecord], *, read_total: int, source_total: int | None = None
):
    """Render the visible units, using the entire read as the count-axis reference.

    `equipment` may be narrowed by the list's display filter. `read_total` is the
    number of units returned before that filter, not the total reported by Prisma.
    Unknown administrative states retain their labels and the neutral palette.
    """
    if not equipment:
        return None
    counts = Counter(unit.machinery_status or "Sin estado informado" for unit in equipment)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    axis_total = max(read_total, len(equipment))
    chart = figure(height=max(180, 48 * len(ordered) + 80))
    chart.add_trace(
        go.Bar(
            x=[count for _, count in ordered],
            y=[escape(state) for state, _ in ordered],
            orientation="h",
            marker_color=[state_color(state) for state, _ in ordered],
            text=[str(count) for _, count in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x} equipos de esta vista<extra></extra>",
        )
    )
    chart.update_xaxes(
        title_text="Equipos de la lectura",
        range=[0, axis_total],
        tick0=0,
        dtick=max(1, ceil(axis_total / 6)),
        fixedrange=True,
    )
    chart.update_yaxes(autorange="reversed", title_text=None, fixedrange=True)
    chart.update_layout(showlegend=False, margin={"l": 8, "r": 36, "t": 12, "b": 42})
    scope = (
        f"Lectura: {read_total} de {source_total} equipos reportados."
        if source_total is not None
        else f"{read_total} equipos leídos; el origen no informa total."
    )
    if len(equipment) != read_total:
        scope = f"Vista filtrada: {len(equipment)} equipos. {scope}"
    return section(
        "Estado administrativo de la maquinaria",
        hint(f"{scope} El estado administrativo no confirma disponibilidad física."),
        graph("inventory-status-chart", chart),
        accordion(
            disclosure(
                "Ver conteos por estado",
                simple_table(
                    ["Estado en Prisma", "Equipos en esta vista"],
                    [[state, count] for state, count in ordered],
                    caption="Distribución de los equipos visibles por estado administrativo",
                ),
            )
        ),
    )
