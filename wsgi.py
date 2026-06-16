"""Thin entry point — named wsgi.py to avoid import collision with app/ package."""

import os

from flask import jsonify

from app.app import server
from app.layout import register_layout

register_layout()


@server.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    from app.app import app

    debug = os.environ.get("DASH_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=debug, use_reloader=False, port=port)
