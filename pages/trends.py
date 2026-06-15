import dash
from dash import html

dash.register_page(__name__, path="/trends", name="Trends")

layout = html.Div(
    [
        html.H2("Distribution Trends"),
        html.P("ACV% and TDP trend lines — is distribution building or bleeding?"),
    ]
)
