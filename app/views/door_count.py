"""Door Count view — distribution penetration by item, retailer, and region."""

from dash import html


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Door Count"),
                    html.P(
                        "Distribution penetration by item, retailer, and region.",
                        style={'color': 'var(--ll-london-35)', 'fontFamily': 'var(--ll-sans)'},
                    ),
                ],
                className="lailara-container",
            ),
        ],
    )
