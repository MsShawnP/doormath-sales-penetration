import dash
from dash import html

dash.register_page(__name__, path="/", name="Door Count")

layout = html.Div(
    [
        html.H2("Door Count Dashboard"),
        html.P("Distribution penetration by item, banner, and region."),
    ]
)
