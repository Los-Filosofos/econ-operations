"""One palette shared by Mantine, AG Grid and Plotly. Color encodes meaning, not decoration.

Brand blue is reserved for identity and primary actions. States use a small qualitative
palette validated for color-vision deficiency; magnitudes use one sequential hue and
deviations a diverging pair with a neutral center (see the dataviz skill references).
"""

import plotly.graph_objects as go
import plotly.io as pio

BRAND = "#144f81"
INK, MUTED, LINE, SURFACE = "#1f2933", "#5c6470", "#e3e7eb", "#f6f8fa"
FONT = "Inter, system-ui, sans-serif"

# Qualitative state families: orange, green and violet pass the CVD validator on all pairs.
# `issue` is a reserved status color (always paired with an icon and label); `neutral` is gray.
FAMILY_COLORS = {
    "pending": "#eb6834",
    "active": "#199e70",
    "busy": "#4a3aa7",
    "issue": "#d03b3b",
    "neutral": "#868e96",
}
FAMILIES = {
    "pending": {"PENDIENTE", "PENDING", "DRAFT", "QUEUED", "SENDING", "EN CURSO"},
    "active": {
        "APROBADA",
        "APPROVED",
        "DISPONIBLE",
        "AVAILABLE",
        "SENT",
        "COMPLETADA",
        "COMPLETED",
    },
    "busy": {"OCUPADA", "OCCUPIED", "ASIGNADA", "ASSIGNED"},
    "issue": {"FAILED", "BLOCKED", "UNKNOWN", "RECHAZADA", "REJECTED"},
}
SEQUENTIAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
DIVERGING = ["#0d366b", "#5598e7", "#f0efec", "#ec835a", "#b3261e"]

ECON_SHADES = [
    "#e8f0f7", "#cddef0", "#a9c6e2", "#7fa9d0", "#5a8dbc",
    "#3c74a6", "#265f92", BRAND, "#0f406a", "#0a3154",
]  # fmt: skip
MANTINE_THEME = {
    "primaryColor": "econ",
    "primaryShade": 7,
    "colors": {"econ": ECON_SHADES},
    "fontFamily": FONT,
    "headings": {"fontFamily": FONT, "fontWeight": "600"},
    "defaultRadius": "sm",
    "focusRing": "auto",
    "components": {
        "Anchor": {"defaultProps": {"underline": "hover"}},
        "Table": {"defaultProps": {"verticalSpacing": "sm", "fz": "sm"}},
    },
}
GRID_THEME = (
    f"themeQuartz.withParams({{fontFamily:'{FONT}',fontSize:13,accentColor:'{BRAND}',"
    f"foregroundColor:'{INK}',headerTextColor:'{MUTED}',headerBackgroundColor:'{SURFACE}',"
    f"borderColor:'{LINE}',wrapperBorderRadius:4,borderRadius:4,rowHoverColor:'#f0f4f8'}})"
)


def state_family(value: str | None) -> str:
    """Map a source state (or an explicit family name) to its color family."""
    key = (value or "").strip().upper()
    if key.lower() in FAMILY_COLORS:
        return key.lower()
    return next((family for family, values in FAMILIES.items() if key in values), "neutral")


def state_color(value: str | None) -> str:
    return FAMILY_COLORS[state_family(value)]


pio.templates["econ"] = go.layout.Template(
    layout={
        "font": {"family": FONT, "size": 12, "color": MUTED},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": [FAMILY_COLORS[key] for key in ("pending", "active", "busy")],
        "colorscale": {
            "sequential": SEQUENTIAL,
            "diverging": DIVERGING,
        },
        "margin": {"l": 8, "r": 24, "t": 12, "b": 26},
        "showlegend": False,
        "dragmode": False,
        "bargap": 0.55,
        "hoverlabel": {"bgcolor": "white", "font": {"size": 12, "color": INK}},
        "xaxis": {"fixedrange": True, "zeroline": False, "gridcolor": LINE, "automargin": True},
        "yaxis": {"fixedrange": True, "zeroline": False, "showgrid": False, "automargin": True},
    }
)


def figure(height: int = 290) -> go.Figure:
    return go.Figure(layout={"template": "econ", "height": height})
