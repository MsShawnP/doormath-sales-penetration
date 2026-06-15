"""Scorecard view — summary metrics and PDF export."""

from dash import html


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Scorecard"),
                    html.P(
                        "Summary metrics and PDF export.",
                        style={'color': 'var(--ll-london-35)', 'fontFamily': 'var(--ll-sans)'},
                    ),
                ],
                className="lailara-container",
            ),
        ],
    )
