"""
Visual design tokens for the Saul Stitch House dashboard.

Values are the validated default palette from Anthropic's dataviz skill
(references/palette.md) -- categorical hues are CVD-safe in the documented
order, the sequential ramp is a single blue hue light->dark, and the
diverging pair is blue<->red with a neutral gray midpoint. Swap these hexes
for a brand palette later; keep the *order* and *roles* unchanged so the
CVD-safety properties still hold (re-run the skill's validator on any swap).
"""

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Categorical (identity) -- fixed order, never cycled/reordered per-chart.
# ---------------------------------------------------------------------------
CATEGORICAL = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark":  ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}

# Fixed channel -> categorical slot mapping so a channel's color never shifts
# when a filter changes which channels are on screen.
CHANNEL_COLOR_SLOT = {
    "Shopify": 0,   # blue
    "Etsy": 1,      # orange
    "QuickBooks": 2,  # aqua
}

# ---------------------------------------------------------------------------
# Sequential (magnitude) -- one hue, light -> dark.
# ---------------------------------------------------------------------------
SEQUENTIAL_BLUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]

# ---------------------------------------------------------------------------
# Diverging (polarity) -- blue <-> red, neutral gray midpoint.
# ---------------------------------------------------------------------------
DIVERGING = {
    "light": {"neg": "#e34948", "mid": "#f0efec", "pos": "#2a78d6"},
    "dark":  {"neg": "#e66767", "mid": "#383835", "pos": "#3987e5"},
}

# ---------------------------------------------------------------------------
# Status (fixed, never themed / never reused for a series).
# ---------------------------------------------------------------------------
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

# ---------------------------------------------------------------------------
# Chart chrome & ink.
# ---------------------------------------------------------------------------
CHROME = {
    "light": {
        "surface": "#fcfcfb",
        "page": "#f9f9f7",
        "primary_ink": "#0b0b0b",
        "secondary_ink": "#52514e",
        "muted": "#898781",
        "gridline": "#e1e0d9",
        "baseline": "#c3c2b7",
    },
    "dark": {
        "surface": "#1a1a19",
        "page": "#0d0d0d",
        "primary_ink": "#ffffff",
        "secondary_ink": "#c3c2b7",
        "muted": "#898781",
        "gridline": "#2c2c2a",
        "baseline": "#383835",
    },
}


def plotly_template(mode: str = "light") -> go.layout.Template:
    """Build a Plotly template that follows the dataviz tokens: thin marks,
    recessive gridlines/axes, no chart title bloat, categorical colorway in
    fixed order."""
    c = CHROME[mode]
    colorway = CATEGORICAL[mode]
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=c["primary_ink"], size=13),
            paper_bgcolor=c["surface"],
            plot_bgcolor=c["surface"],
            colorway=colorway,
            xaxis=dict(
                gridcolor=c["gridline"], linecolor=c["baseline"], zerolinecolor=c["baseline"],
                tickfont=dict(color=c["muted"]), title_font=dict(color=c["secondary_ink"]),
            ),
            yaxis=dict(
                gridcolor=c["gridline"], linecolor=c["baseline"], zerolinecolor=c["baseline"],
                tickfont=dict(color=c["muted"]), title_font=dict(color=c["secondary_ink"]),
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=c["secondary_ink"])),
            margin=dict(l=10, r=10, t=40, b=10),
            hoverlabel=dict(bgcolor=c["surface"], font=dict(color=c["primary_ink"])),
        )
    )


def channel_color(channel: str, mode: str = "light") -> str:
    """Stable color for a sales channel -- identity never shifts with filters."""
    slot = CHANNEL_COLOR_SLOT.get(channel)
    palette = CATEGORICAL[mode]
    if slot is None:
        return CHROME[mode]["muted"]
    return palette[slot % len(palette)]
