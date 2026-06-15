# Door Math — Distribution Penetration Tracker

## Project overview

Distribution penetration dashboard for CPG brands. Tracks door counts, ACV%, TDP trends, and the authorization-vs-scanning gap. Part of the Cinderhaven 5-tool sales analytics suite (tool #1).

## Stack

Python 3.11+ / Dash 3.x / Plotly / pandas / dash-ag-grid / dash-bootstrap-components / Fly.io

## Architecture

- `app.py` — multi-page Dash app entry point
- `pages/` — one module per dashboard page (door_count, trends, exceptions, scorecard)
- `data/synthetic.py` — synthetic store universe, authorization matrix, and POS scan generators
- `assets/style.css` — Lailara design system tokens
- `tests/` — pytest

## Conventions

- Follow the Lailara design system for all charts and UI (see global CLAUDE.md)
- Cinderhaven canonical figures are authoritative — do not invent item or retailer data
- Store universe data stays in this repo for now (may extract to shared package later)
- All charts: Economist style, SVG-based, horizontal gridlines only, text labels on every data point
