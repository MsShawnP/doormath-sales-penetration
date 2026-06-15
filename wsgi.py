"""Thin entry point — named wsgi.py to avoid import collision with app/ package."""

from app.app import server
from app.layout import register_layout
from flask import jsonify

register_layout()


@server.route('/health')
def health():
    return jsonify(status='ok')


if __name__ == '__main__':
    from app.app import app
    app.run(debug=True, port=8050)
