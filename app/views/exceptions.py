"""Exceptions view — void finder AG Grid table."""

from dash import html


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Exceptions"),
                    html.P(
                        "Authorization gaps and scanning exceptions.",
                        style={'color': 'var(--ll-london-35)', 'fontFamily': 'var(--ll-sans)'},
                    ),
                ],
                className="lailara-container",
            ),
        ],
    )
