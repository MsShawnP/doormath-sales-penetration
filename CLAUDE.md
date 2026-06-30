# Door Math — Distribution Penetration Tracker

## Project overview

Distribution penetration dashboard for CPG brands. Tracks door counts, ACV%, TDP trends, and the authorization-vs-scanning gap. Part of the Cinderhaven 5-tool sales analytics suite (tool #1). Portfolio piece for lailarallc.com.

## Stack

Python 3.11+ / Dash 3.x / Plotly / pandas / dash-ag-grid / WeasyPrint / Fly.io (1024MB, auto_stop="stop")

No dash-bootstrap-components — lailara-frame.css is the design system.

## Architecture

- `wsgi.py` — thin entry point (NOT `app.py` — avoids import collision with `app/` package)
- `app/` — Dash application package (app.py, layout.py, filters.py, constants.py, charts.py, components.py, calculations.py, export.py, pdf.py)
- `app/views/` — one module per tab (door_count, trends, exceptions, scorecard)
- `app/templates/scorecard.html` — Jinja2 template for PDF generation
- `packages/cinderhaven-store-universe/` — versioned data package (stores, auth matrix, scans, slow-leak)
- `assets/` — lailara-frame.css, style.css (overrides only), self-hosted woff2 fonts
- `tests/` — pytest

## Conventions

- Follow the Lailara design system for all charts and UI (see global CLAUDE.md)
- Cinderhaven canonical figures are authoritative — do not invent item or retailer data
- All hex values live in `app/constants.py` (Python side) or CSS `:root` — nowhere else
- `DEMO_AS_OF_DATE = pd.Timestamp('2025-12-29')` — never use `datetime.now()` for time-relative computations
- "Retailer" not "banner" — consistent terminology throughout
- All charts: Economist style, SVG-based, horizontal gridlines only, text labels on every data point
- Click-to-pin interactions (not hover tooltips) per Lailara design system

Never write secrets, tokens, or passwords into tracked files, READMEs, or commit messages — use environment variables and secret stores only.
