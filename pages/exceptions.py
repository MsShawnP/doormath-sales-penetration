import dash
from dash import html

dash.register_page(__name__, path="/exceptions", name="Exceptions")

layout = html.Div(
    [
        html.H2("Authorization Exceptions"),
        html.P("Authorized-but-not-scanning items — the gap where money dies."),
    ]
)
