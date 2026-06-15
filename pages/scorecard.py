import dash
from dash import html

dash.register_page(__name__, path="/scorecard", name="Scorecard")

layout = html.Div(
    [
        html.H2("Distribution Scorecard"),
        html.P("One-page summary for buyer meetings."),
    ]
)
