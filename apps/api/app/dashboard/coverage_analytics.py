"""Read coverage, never fleet availability inferred from row counts."""

from app.dashboard.analytics import readable
from app.dashboard.theme import MEASURE, MUTED, SURFACE, figure
from app.models.hub import HubResponse


def coverage_rows(hub: HubResponse) -> list[tuple[str, int, int | None]]:
    if not readable(hub):
        return []
    return [
        ("Solicitudes", hub.scope.requests_returned, hub.scope.requests_total),
        ("Maquinaria", hub.scope.equipment_returned, hub.scope.equipment_total),
    ]


def coverage_figure(hub: HubResponse):
    rows = coverage_rows(hub)
    if not rows:
        return None
    chart = figure(235)
    labels = [name for name, _, _ in rows]
    percentages = [
        100 * loaded / total if total is not None and total > 0 and loaded <= total else None
        for _, loaded, total in rows
    ]
    chart.add_bar(
        y=labels,
        x=percentages,
        name="En esta lectura",
        orientation="h",
        width=0.4,
        marker_color=MEASURE,
        customdata=[[loaded, total] for _, loaded, total in rows],
        hovertemplate=(
            "%{y}<br>%{customdata[0]} de %{customdata[1]} registros leídos<extra></extra>"
        ),
    )
    chart.add_bar(
        y=labels,
        x=[100 - value if value is not None else None for value in percentages],
        name="Fuera de esta lectura",
        orientation="h",
        width=0.4,
        marker={
            "color": SURFACE,
            "pattern": {"shape": "/", "fgcolor": MUTED, "solidity": 0.2},
        },
        customdata=[
            total - loaded if total is not None and total >= loaded else None
            for _, loaded, total in rows
        ],
        hovertemplate="%{y}<br>%{customdata} registros no incluidos<extra></extra>",
    )
    for (label, loaded, total), percentage in zip(rows, percentages, strict=True):
        text = f"{loaded} de {total}" if total is not None else f"{loaded} · total desconocido"
        if total is not None and total < loaded:
            text += " · total inconsistente"
        elif total == 0:
            text += " · colección vacía; sin porcentaje"
        elif percentage is not None:
            text += " · " + f"{percentage:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " %"
        chart.add_annotation(
            x=1, xref="paper", y=label, text=text, showarrow=False, xanchor="right", yshift=25
        )
    chart.update_layout(
        barmode="stack",
        meta={"kind": "coverage_percent", "denominator": "reported_collection_total"},
        showlegend=True,
        legend={
            "orientation": "h",
            "y": 1.25,
            "x": 0,
            "traceorder": "normal",
            "itemclick": False,
            "itemdoubleclick": False,
        },
    )
    chart.update_yaxes(autorange="reversed")
    chart.update_xaxes(
        title_text="Porcentaje del total informado",
        range=[0, 100],
        tick0=0,
        dtick=25,
        ticksuffix=" %",
    )
    return chart
