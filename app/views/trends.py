"""Trends view — ACV% and TDP line charts by quarter."""

from dash import html


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Trends"),
                    html.P(
                        "ACV% and TDP trends over time.",
                        style={'color': 'var(--ll-london-35)', 'fontFamily': 'var(--ll-sans)'},
                    ),
                ],
                className="lailara-container",
            ),
        ],
    )
