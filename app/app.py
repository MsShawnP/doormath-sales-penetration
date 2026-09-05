"""Dash application factory — no external stylesheets, no dash-bootstrap-components."""

import dash

app = dash.Dash(
    __name__,
    assets_folder="../assets",
    suppress_callback_exceptions=True,
    title="Door Math — Distribution Penetration",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "Which stores actually carry a brand versus which were authorized: the gap where revenue quietly dies."},
        {"property": "og:title", "content": "Door Math: Distribution Penetration"},
        {"property": "og:description", "content": "Which stores actually carry a brand versus which were authorized: the gap where revenue quietly dies."},
        {"property": "og:type", "content": "website"},
        {"property": "og:url", "content": "https://doormath.lailarallc.com/"},
        {"property": "og:image", "content": "https://lailarallc.com/og/s/doormath.png"},
        {"property": "og:image:secure_url", "content": "https://lailarallc.com/og/s/doormath.png"},
        {"property": "og:image:type", "content": "image/png"},
        {"property": "og:image:width", "content": "1200"},
        {"property": "og:image:height", "content": "630"},
        {"property": "og:image:alt", "content": "Door Math: Distribution Penetration"},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:image", "content": "https://lailarallc.com/og/s/doormath.png"},
    ],
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
