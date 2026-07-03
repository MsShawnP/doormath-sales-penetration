"""Shared Economist-style chart defaults and SVG config for Plotly figures."""

from app.constants import (
    CANVAS,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    INK,
    TEXT_SECONDARY,
)


def economist_layout(**overrides):
    """Return a Plotly layout dict with Lailara/Economist-style defaults.

    Apply to any figure: fig.update_layout(**economist_layout())
    Overrides replace individual keys, not nested dicts—pass full sub-dicts
    when overriding xaxis, yaxis, etc.
    """
    defaults = dict(
        paper_bgcolor=CANVAS,
        plot_bgcolor=CANVAS,
        font=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        title=dict(
            font=dict(family=FONT_SERIF, size=22, color=INK),
            y=0.98,
            yanchor="top",
            x=0.0,
            xanchor="left",
            pad=dict(l=60),
        ),
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            tickfont=dict(family=FONT_SANS, size=11, color=TEXT_SECONDARY),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            showline=False,
            zeroline=False,
            tickfont=dict(family=FONT_SANS, size=11, color=TEXT_SECONDARY),
        ),
        margin=dict(l=60, r=20, t=100, b=50),
        hoverlabel=dict(
            bgcolor=CANVAS,
            font=dict(family=FONT_SANS, size=13, color=INK),
            bordercolor=GRIDLINE,
        ),
        dragmode=False,
        showlegend=True,
        legend=dict(
            font=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
    )
    for key, val in overrides.items():
        if key in defaults and isinstance(defaults[key], dict) and isinstance(val, dict):
            defaults[key] = {**defaults[key], **val}
        else:
            defaults[key] = val
    return defaults


# SVG-based chart config — disable mode bar, render as SVG for print
CHART_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "svg"},
}
