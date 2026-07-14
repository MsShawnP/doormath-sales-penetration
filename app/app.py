"""Dash application factory — no external stylesheets, no dash-bootstrap-components."""

import dash

app = dash.Dash(
    __name__,
    assets_folder="../assets",
    suppress_callback_exceptions=True,
    title="Door Math — Distribution Penetration",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

# Set page language for assistive technologies (accessibility baseline).
# Standard Dash template with <html lang="en">; all Dash placeholders preserved.
app.index_string = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
