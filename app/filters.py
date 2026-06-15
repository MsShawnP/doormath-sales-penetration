"""Shared filter bar component and callbacks."""

import json

from cinderhaven_store_universe.constants import PRODUCT_LINES, RETAILERS
from dash import Input, Output, State, callback, dcc, html, no_update

# ── Option lists derived from store universe constants ──

RETAILER_OPTIONS = [{"label": info["name"], "value": ret_id} for ret_id, info in RETAILERS.items()]
ALL_RETAILER_IDS = [opt["value"] for opt in RETAILER_OPTIONS]

PRODUCT_LINE_OPTIONS = [
    {"label": info["name"], "value": prefix} for prefix, info in PRODUCT_LINES.items()
]
ALL_PRODUCT_LINE_PREFIXES = [opt["value"] for opt in PRODUCT_LINE_OPTIONS]

# ── Quarter options: Q1 2024 through Q4 2025 (8 quarters) ──
QUARTER_OPTIONS = [
    {"label": f"Q{q} {y}", "value": f"Q{q} {y}"} for y in [2024, 2025] for q in [1, 2, 3, 4]
]

DEFAULT_START_QUARTER = "Q1 2025"
DEFAULT_END_QUARTER = "Q4 2025"

# ── Default filter state ──
DEFAULT_FILTER_STATE = {
    "retailers": ALL_RETAILER_IDS,
    "product_lines": ALL_PRODUCT_LINE_PREFIXES,
    "sku": None,
    "start_quarter": DEFAULT_START_QUARTER,
    "end_quarter": DEFAULT_END_QUARTER,
}


def _sku_options_for_lines(product_lines):
    """Build SKU dropdown options for the given product line prefixes."""
    options = []
    for prefix in product_lines:
        if prefix in PRODUCT_LINES:
            for sku in PRODUCT_LINES[prefix]["skus"]:
                options.append({"label": sku, "value": sku})
    return options


def build_filter_bar():
    """Return the filter bar component."""
    return html.Div(
        [
            html.Div(
                [
                    html.Label("Retailer"),
                    dcc.Dropdown(
                        id="filter-retailer",
                        options=RETAILER_OPTIONS,
                        value=ALL_RETAILER_IDS,
                        multi=True,
                        placeholder="Select retailers...",
                        clearable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "220px", "flex": "1"},
            ),
            html.Div(
                [
                    html.Label("Product Line"),
                    dcc.Dropdown(
                        id="filter-product-line",
                        options=PRODUCT_LINE_OPTIONS,
                        value=ALL_PRODUCT_LINE_PREFIXES,
                        multi=True,
                        placeholder="Select product lines...",
                        clearable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "220px", "flex": "1"},
            ),
            html.Div(
                [
                    html.Label("SKU (optional)"),
                    dcc.Dropdown(
                        id="filter-sku",
                        options=[],
                        value=None,
                        multi=False,
                        placeholder="All SKUs",
                        searchable=True,
                        clearable=True,
                    ),
                ],
                id="filter-sku-group",
                className="filter-group",
                style={"minWidth": "180px", "flex": "1", "display": "none"},
            ),
            html.Div(
                [
                    html.Label("Start Quarter"),
                    dcc.Dropdown(
                        id="filter-start-quarter",
                        options=QUARTER_OPTIONS,
                        value=DEFAULT_START_QUARTER,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "140px"},
            ),
            html.Div(
                [
                    html.Label("End Quarter"),
                    dcc.Dropdown(
                        id="filter-end-quarter",
                        options=QUARTER_OPTIONS,
                        value=DEFAULT_END_QUARTER,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "140px"},
            ),
        ],
        className="filter-bar",
    )


def build_empty_state():
    """Return the empty-state placeholder shown when no data matches filters."""
    return html.Div(
        [
            html.P("No data matches the current filters."),
            html.Button("Reset filters", id="reset-filters-btn", n_clicks=0),
        ],
        id="empty-state",
        className="empty-state",
        style={"display": "none"},
    )


def register_filter_callbacks():
    """Register all filter-related callbacks."""

    @callback(
        Output("filter-sku-group", "style"),
        Output("filter-sku", "options"),
        Output("filter-sku", "value"),
        Input("filter-product-line", "value"),
        State("filter-sku", "value"),
    )
    def _update_sku_visibility(product_lines, current_sku):
        """Show SKU dropdown only when exactly 1 product line is selected."""
        if product_lines and len(product_lines) == 1:
            options = _sku_options_for_lines(product_lines)
            sku_ids = [o["value"] for o in options]
            # Keep current selection if it still belongs to the selected product line
            kept_sku = current_sku if current_sku in sku_ids else None
            return (
                {
                    "minWidth": "180px",
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "var(--ll-space-xs)",
                },
                options,
                kept_sku,
            )
        # Hide and reset
        return (
            {"minWidth": "180px", "flex": "1", "display": "none"},
            [],
            None,
        )

    @callback(
        Output("filter-state", "data"),
        Input("filter-retailer", "value"),
        Input("filter-product-line", "value"),
        Input("filter-sku", "value"),
        Input("filter-start-quarter", "value"),
        Input("filter-end-quarter", "value"),
    )
    def _sync_filter_state(retailers, product_lines, sku, start_q, end_q):
        """Write current filter selections to the shared store."""
        return json.dumps(
            {
                "retailers": retailers or [],
                "product_lines": product_lines or [],
                "sku": sku,
                "start_quarter": start_q,
                "end_quarter": end_q,
            }
        )

    @callback(
        Output("filter-retailer", "value"),
        Output("filter-product-line", "value"),
        Output("filter-start-quarter", "value"),
        Output("filter-end-quarter", "value"),
        Input("reset-filters-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _reset_filters(n_clicks):
        """Reset all filters to defaults."""
        if not n_clicks:
            return no_update, no_update, no_update, no_update
        return (
            ALL_RETAILER_IDS,
            ALL_PRODUCT_LINE_PREFIXES,
            DEFAULT_START_QUARTER,
            DEFAULT_END_QUARTER,
        )
