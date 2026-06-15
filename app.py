import os

import dash
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

load_dotenv()

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Door Math — Distribution Penetration",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

app.layout = dbc.Container(
    [
        dbc.NavbarSimple(
            brand="Door Math",
            brand_href="/",
            color="dark",
            dark=True,
            className="mb-4",
            children=[
                dbc.NavItem(dbc.NavLink("Door Count", href="/")),
                dbc.NavItem(dbc.NavLink("Trends", href="/trends")),
                dbc.NavItem(dbc.NavLink("Exceptions", href="/exceptions")),
                dbc.NavItem(dbc.NavLink("Scorecard", href="/scorecard")),
            ],
        ),
        dash.page_container,
    ],
    fluid=True,
    className="px-4",
)

if __name__ == "__main__":
    debug = os.getenv("DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 8050))
    app.run(debug=debug, port=port)
