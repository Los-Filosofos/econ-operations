"""One palette shared by Mantine, AG Grid and Plotly. Color encodes meaning, not decoration.

Brand blue is reserved for identity and primary actions. States use a small qualitative
palette validated for color-vision deficiency; magnitudes use one sequential hue and
deviations a diverging pair with a neutral center (see the dataviz skill references).

Typography and spacing follow one rule: a data console reads better with contained
headings, a comfortable body size and a 4px vertical rhythm. `assets/style.css` mirrors
the surface tokens on `:root` so pages rendered outside the shell (login) keep them.
"""

import plotly.graph_objects as go
import plotly.io as pio

BRAND = "#144f81"
INK, MUTED, LINE, SURFACE = "#1f2933", "#5c6470", "#dfe5ea", "#f1f4f7"
PAPER = "#ffffff"
# Two neutrals derived from LINE and SURFACE: a stronger hairline for structural rules
# (table heads, section dividers) and a second paper tone for inset blocks. Both keep
# body text at AA contrast.
LINE_STRONG = "#c7d0d8"
CANVAS_ALT = "#f8fafb"
# Chart gridlines sit one step below LINE so the data stays louder than the scale.
GRID_LINE = "#e8edf1"
# A measured amount is not an operational state or a brand action.
MEASURE = "#49515b"
CHART_INK = "#111820"
FONT = "Public Sans, sans-serif"
NAV_SHADES = [
    "#eef4f8", "#d2e0ea", "#aec4d4", "#8faec3", "#688fa9",
    "#477493", "#2a5878", "#204761", "#17374e", "#102a3d",
]  # fmt: skip
SHELL_VARIABLES = {
    "--econ-canvas": SURFACE,
    "--econ-canvas-alt": CANVAS_ALT,
    "--econ-paper": PAPER,
    "--econ-line": LINE,
    "--econ-line-strong": LINE_STRONG,
    "--econ-ink": INK,
    "--econ-muted": MUTED,
}

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
    "colors": {"econ": ECON_SHADES, "navigation": NAV_SHADES},
    "white": PAPER,
    "black": INK,
    "fontFamily": FONT,
    # Half-step scale: 13/14/15/17/19px. `md` is the body size, `xs` the micro-label size.
    "fontSizes": {
        "xs": "0.8125rem",
        "sm": "0.875rem",
        "md": "0.9375rem",
        "lg": "1.0625rem",
        "xl": "1.1875rem",
    },
    "lineHeights": {"xs": "1.35", "sm": "1.45", "md": "1.5", "lg": "1.5", "xl": "1.45"},
    # Every step is a multiple of 4px so Mantine spacing lands on the layout grid.
    "spacing": {
        "xs": "0.5rem",
        "sm": "0.75rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
    },
    # Radii are capped at 4px: nothing in the console should read as a rounded card.
    "radius": {
        "xs": "0.125rem",
        "sm": "0.1875rem",
        "md": "0.25rem",
        "lg": "0.25rem",
        "xl": "0.25rem",
    },
    "headings": {
        "fontFamily": FONT,
        "fontWeight": "600",
        # Contained titles: 28/24/20/17/15/13px. Page titles render at the `h2` step.
        "sizes": {
            "h1": {"fontSize": "1.75rem", "lineHeight": "1.2"},
            "h2": {"fontSize": "1.5rem", "lineHeight": "1.25"},
            "h3": {"fontSize": "1.25rem", "lineHeight": "1.3"},
            "h4": {"fontSize": "1.0625rem", "lineHeight": "1.35"},
            "h5": {"fontSize": "0.9375rem", "lineHeight": "1.4"},
            "h6": {"fontSize": "0.8125rem", "lineHeight": "1.45"},
        },
    },
    "defaultRadius": "xs",
    "focusRing": "auto",
    "components": {
        "Anchor": {"defaultProps": {"underline": "hover"}},
        "Table": {"defaultProps": {"verticalSpacing": "xs", "fz": "sm"}},
    },
}
# Quartz without its panel look: white header, hairline row rules, no column dividers.
GRID_THEME = (
    f"themeQuartz.withParams({{fontFamily:'{FONT}',fontSize:13,spacing:6,"
    f"accentColor:'{BRAND}',foregroundColor:'{INK}',backgroundColor:'{PAPER}',"
    f"borderColor:'{LINE}',wrapperBorder:true,wrapperBorderRadius:4,borderRadius:3,"
    f"headerBackgroundColor:'{PAPER}',headerTextColor:'{MUTED}',"
    f"headerFontSize:11,headerFontWeight:600,headerHeight:38,"
    f"headerRowBorder:{{color:'{LINE_STRONG}',width:1}},headerColumnBorder:false,"
    f"columnBorder:false,rowBorder:{{color:'{LINE}',width:1}},"
    f"oddRowBackgroundColor:'{PAPER}',rowHoverColor:'{ECON_SHADES[0]}',"
    f"selectedRowBackgroundColor:'{ECON_SHADES[0]}',iconSize:14}})"
)


def state_family(value: str | None) -> str:
    """Map a source state (or an explicit family name) to its color family."""
    key = (value or "").strip().upper()
    if key.lower() in FAMILY_COLORS:
        return key.lower()
    return next((family for family, values in FAMILIES.items() if key in values), "neutral")


def state_color(value: str | None) -> str:
    return FAMILY_COLORS[state_family(value)]


def state_label_color(value: str | None) -> str:
    """At least 4.5:1 against the state fill for small labels inside calendar bars."""
    return PAPER if state_family(value) in {"busy", "issue"} else CHART_INK


_AXIS = {
    "fixedrange": True,
    "zeroline": False,
    "automargin": True,
    "ticks": "",
    "tickfont": {"family": FONT, "size": 12, "color": MUTED},
    "title": {"font": {"family": FONT, "size": 12, "color": MUTED}, "standoff": 8},
}
pio.templates["econ"] = go.layout.Template(
    layout={
        "font": {"family": FONT, "size": 13, "color": MUTED},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": [FAMILY_COLORS[key] for key in ("pending", "active", "busy")],
        "colorscale": {
            "sequential": SEQUENTIAL,
            "diverging": DIVERGING,
        },
        # Tight frame; `automargin` gives labels the room they actually need.
        "margin": {"l": 4, "r": 12, "t": 12, "b": 20},
        "showlegend": False,
        "dragmode": False,
        "bargap": 0.42,
        "bargroupgap": 0.08,
        "hovermode": "closest",
        "hoverlabel": {
            "bgcolor": PAPER,
            "bordercolor": LINE_STRONG,
            "align": "left",
            "font": {"family": FONT, "size": 13, "color": INK},
        },
        # Horizontal bars: vertical gridlines carry the scale, the category axis stays bare.
        "xaxis": {**_AXIS, "gridcolor": GRID_LINE, "gridwidth": 1, "showline": False},
        "yaxis": {**_AXIS, "showgrid": False, "showline": False},
    }
)


def figure(height: int = 290) -> go.Figure:
    return go.Figure(layout={"template": "econ", "height": height})
