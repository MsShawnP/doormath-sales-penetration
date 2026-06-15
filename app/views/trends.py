"""Trends view -- ACV% and TDP line charts by quarter with slow-leak annotations."""

import json
import statistics

import plotly.graph_objects as go
from cinderhaven_store_universe import (
    get_auth_matrix,
    get_scan_data,
    get_slow_leak_config,
    get_stores,
)
from cinderhaven_store_universe.constants import RETAILERS
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import (
    calc_acv_pct,
    calc_penetration_rate,
    calc_period_delta,
    calc_tdp,
    quarters_in_range,
)
from app.charts import CHART_CONFIG, economist_layout
from app.components import annotation_callout, dark_callout_card
from app.constants import (
    FONT_SANS,
    GRIDLINE,
    INK,
    REFERENCE,
    TEAL_SEQUENTIAL,
    TEXT_SECONDARY,
    fmt_delta,
    fmt_pct,
)

# -- Data loading (cached at module level) --

_stores = get_stores()
_auth = get_auth_matrix()
_scans = get_scan_data()
_slow_leak = get_slow_leak_config()

# Retailer ID-to-name lookup
_RETAILER_NAMES = {ret_id: info["name"] for ret_id, info in RETAILERS.items()}
_RETAILER_IDS_SORTED = sorted(RETAILERS.keys())

# Assign one teal color per retailer, evenly spaced across the 8-shade palette.
# 6 retailers, 8 teal shades -- pick indices [0, 1, 2, 4, 5, 7] for contrast.
_RETAILER_COLOR_INDICES = [0, 1, 2, 4, 5, 7]
RETAILER_COLORS = {}
for i, ret_id in enumerate(_RETAILER_IDS_SORTED):
    idx = (
        _RETAILER_COLOR_INDICES[i] if i < len(_RETAILER_COLOR_INDICES) else i % len(TEAL_SEQUENTIAL)
    )
    RETAILER_COLORS[ret_id] = TEAL_SEQUENTIAL[idx]


# -- Computation helpers --


def _compute_acv_by_retailer(filters, quarters):
    """Compute ACV% per retailer per quarter.

    Returns dict: {retailer_id: {quarter_str: acv_pct_float}}.
    """
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")

    result = {}
    for ret_id in retailers:
        result[ret_id] = {}
        for q in quarters:
            result[ret_id][q] = calc_acv_pct(
                _stores,
                _auth,
                _scans,
                q,
                retailers=[ret_id],
                product_lines=product_lines if product_lines else None,
                sku=sku,
            )
    return result


def _compute_tdp_by_retailer(filters, quarters):
    """Compute TDP per retailer per quarter.

    Returns dict: {retailer_id: {quarter_str: tdp_float}}.
    """
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])

    result = {}
    for ret_id in retailers:
        result[ret_id] = {}
        for q in quarters:
            result[ret_id][q] = calc_tdp(
                _stores,
                _auth,
                _scans,
                q,
                retailers=[ret_id],
                product_lines=product_lines if product_lines else None,
            )
    return result


def _compute_slow_leak_annotations(filters, quarters):
    """Check slow-leak SKUs and return annotation strings for significant drops.

    A significant drop is >20 percentage points from peak penetration.
    """
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")
    retailers = filters.get("retailers", [])

    annotations = []

    for sku_id, config in _slow_leak.items():
        # Extract product line prefix from sku_id (e.g. CHP-DG-003 -> DG)
        sku_prefix = sku_id.split("-")[1]

        # Only annotate if the product line is visible in current filters
        if product_lines and sku_prefix not in product_lines:
            continue
        # If a specific SKU is selected and it's not this one, skip
        if sku and sku != sku_id:
            continue

        # Compute penetration trend across quarters for this SKU
        penetration_by_q = {}
        for q in quarters:
            penetration_by_q[q] = calc_penetration_rate(
                _auth,
                _scans,
                q,
                retailers=retailers if retailers else None,
                product_lines=[sku_prefix],
                sku=sku_id,
            )

        if not penetration_by_q:
            continue

        peak_pct = max(penetration_by_q.values())
        current_pct = penetration_by_q[quarters[-1]] if quarters else 0.0
        drop_pp = peak_pct - current_pct

        # Significant drop: >20 percentage points from peak
        if drop_pp > 0.20:
            peak_q = [q for q, v in penetration_by_q.items() if v == peak_pct][0]
            # Count quarters from peak to current
            try:
                peak_idx = quarters.index(peak_q)
                n_quarters = len(quarters) - 1 - peak_idx
            except ValueError:
                n_quarters = 0

            # Estimate doors lost: use addressable stores for this SKU
            auth_for_sku = _auth[(_auth["authorized"]) & (_auth["sku_id"] == sku_id)]
            if retailers:
                auth_for_sku = auth_for_sku[auth_for_sku["retailer_id"].isin(retailers)]
            addressable = auth_for_sku["store_id"].nunique()
            doors_lost = int(addressable * drop_pp)

            annotations.append(
                f"{sku_id} has lost ~{doors_lost} doors across "
                f"{n_quarters} quarter{'s' if n_quarters != 1 else ''} "
                f"-- penetration down from {fmt_pct(peak_pct)} to "
                f"{fmt_pct(current_pct)}"
            )

    return annotations


# -- Chart builders --


def _build_acv_chart(acv_data, quarters, selected_point=None):
    """Build ACV% trend line chart with one line per retailer plus a median reference.

    Args:
        acv_data: {retailer_id: {quarter: acv_pct}}.
        quarters: Ordered list of quarter strings.
        selected_point: Optional dict with 'retailer_id' and 'quarter' for dimming.
    """
    fig = go.Figure()

    # Compute median ACV% across retailers per quarter
    medians = []
    for q in quarters:
        vals = [acv_data[r][q] for r in acv_data if q in acv_data[r]]
        medians.append(statistics.median(vals) if vals else 0.0)

    # Add median reference line
    fig.add_trace(
        go.Scatter(
            x=quarters,
            y=[v * 100 for v in medians],
            mode="lines",
            name="Median",
            line=dict(color=REFERENCE, dash="dash", width=2),
            hoverinfo="skip",
        )
    )

    # Add one line per retailer
    for ret_id in sorted(acv_data.keys()):
        color = RETAILER_COLORS.get(ret_id, TEAL_SEQUENTIAL[0])
        name = _RETAILER_NAMES.get(ret_id, ret_id)
        values = [acv_data[ret_id].get(q, 0.0) for q in quarters]

        # Dim non-selected retailers when a point is pinned
        opacity = 1.0
        if selected_point and selected_point.get("retailer_id") != ret_id:
            opacity = 0.25

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=[v * 100 for v in values],
                mode="lines+markers+text",
                name=name,
                line=dict(color=color, width=2.5),
                marker=dict(color=color, size=7),
                text=[f"{v * 100:.1f}%" for v in values],
                textposition="top center",
                textfont=dict(family=FONT_SANS, size=11, color=INK),
                opacity=opacity,
                customdata=[ret_id] * len(quarters),
            )
        )

    fig.update_layout(
        **economist_layout(
            title=dict(text="ACV% by Retailer"),
            xaxis=dict(
                showgrid=False,
                showline=True,
                linecolor=GRIDLINE,
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
                title=None,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                gridwidth=1,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
                ticksuffix="%",
                rangemode="tozero",
                title=None,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            height=420,
        )
    )

    return fig


def _build_tdp_chart(tdp_data, quarters, selected_point=None):
    """Build TDP trend line chart with one line per retailer plus a median reference.

    Args:
        tdp_data: {retailer_id: {quarter: tdp_value}}.
        quarters: Ordered list of quarter strings.
        selected_point: Optional dict with 'retailer_id' and 'quarter' for dimming.
    """
    fig = go.Figure()

    # Compute median TDP across retailers per quarter
    medians = []
    for q in quarters:
        vals = [tdp_data[r][q] for r in tdp_data if q in tdp_data[r]]
        medians.append(statistics.median(vals) if vals else 0.0)

    # Add median reference line
    fig.add_trace(
        go.Scatter(
            x=quarters,
            y=[round(v, 1) for v in medians],
            mode="lines",
            name="Median",
            line=dict(color=REFERENCE, dash="dash", width=2),
            hoverinfo="skip",
        )
    )

    # Add one line per retailer
    for ret_id in sorted(tdp_data.keys()):
        color = RETAILER_COLORS.get(ret_id, TEAL_SEQUENTIAL[0])
        name = _RETAILER_NAMES.get(ret_id, ret_id)
        values = [tdp_data[ret_id].get(q, 0.0) for q in quarters]

        # Dim non-selected retailers when a point is pinned
        opacity = 1.0
        if selected_point and selected_point.get("retailer_id") != ret_id:
            opacity = 0.25

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=[round(v, 1) for v in values],
                mode="lines+markers+text",
                name=name,
                line=dict(color=color, width=2.5),
                marker=dict(color=color, size=7),
                text=[f"{v:.1f}" for v in values],
                textposition="top center",
                textfont=dict(family=FONT_SANS, size=11, color=INK),
                opacity=opacity,
                customdata=[ret_id] * len(quarters),
            )
        )

    fig.update_layout(
        **economist_layout(
            title=dict(text="TDP by Retailer"),
            xaxis=dict(
                showgrid=False,
                showline=True,
                linecolor=GRIDLINE,
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
                title=None,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                gridwidth=1,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
                rangemode="tozero",
                title="TDP points",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            height=420,
        )
    )

    return fig


# -- Layout --


def layout():
    """Return the Trends view component tree."""
    return html.Div(
        [
            # Side-by-side chart row
            html.Div(
                [
                    html.Div(
                        dcc.Graph(
                            id="tr-acv-chart",
                            config=CHART_CONFIG,
                        ),
                        style={"flex": "1", "minWidth": "0"},
                        **{"aria-label": "ACV percent trend by retailer over time"},
                    ),
                    html.Div(
                        dcc.Graph(
                            id="tr-tdp-chart",
                            config=CHART_CONFIG,
                        ),
                        style={"flex": "1", "minWidth": "0"},
                        **{"aria-label": "TDP trend by retailer over time"},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "24px",
                    "flexWrap": "wrap",
                },
            ),
            # Click-to-pin callout card area
            html.Div(id="tr-callout-area"),
            # Slow-leak annotation area
            html.Div(id="tr-slow-leak-annotations"),
            # Hidden stores for click-to-pin state
            dcc.Store(id="tr-pinned-acv", data=None),
            dcc.Store(id="tr-pinned-tdp", data=None),
        ],
    )


# -- Callbacks --


@callback(
    Output("tr-acv-chart", "figure"),
    Output("tr-tdp-chart", "figure"),
    Output("tr-slow-leak-annotations", "children"),
    Input("filter-state", "data"),
)
def _update_trends_charts(filter_json):
    """Recompute ACV% and TDP charts when filters change."""
    filters = json.loads(filter_json) if filter_json else {}

    start_q = filters.get("start_quarter", "Q1 2025")
    end_q = filters.get("end_quarter", "Q4 2025")
    quarters = quarters_in_range(start_q, end_q)

    if not quarters or not filters.get("retailers"):
        empty = go.Figure()
        empty.update_layout(**economist_layout())
        return empty, empty, []

    # Compute per-retailer metrics across quarters
    acv_data = _compute_acv_by_retailer(filters, quarters)
    tdp_data = _compute_tdp_by_retailer(filters, quarters)

    acv_fig = _build_acv_chart(acv_data, quarters)
    tdp_fig = _build_tdp_chart(tdp_data, quarters)

    # Slow-leak annotations
    leak_texts = _compute_slow_leak_annotations(filters, quarters)
    leak_children = [annotation_callout(t) for t in leak_texts] if leak_texts else []

    return acv_fig, tdp_fig, leak_children


@callback(
    Output("tr-pinned-acv", "data"),
    Input("tr-acv-chart", "clickData"),
    State("tr-pinned-acv", "data"),
    prevent_initial_call=True,
)
def _toggle_acv_pin(click_data, current_pinned):
    """Toggle pinned point on ACV% chart click."""
    if not click_data:
        return no_update

    points = click_data.get("points", [])
    if not points:
        return no_update

    point = points[0]
    quarter = point.get("x")
    retailer_id = point.get("customdata")

    if not quarter or not retailer_id:
        return no_update

    # Toggle: click same point to dismiss
    if (
        current_pinned
        and current_pinned.get("retailer_id") == retailer_id
        and current_pinned.get("quarter") == quarter
    ):
        return None

    return {"retailer_id": retailer_id, "quarter": quarter}


@callback(
    Output("tr-pinned-tdp", "data"),
    Input("tr-tdp-chart", "clickData"),
    State("tr-pinned-tdp", "data"),
    prevent_initial_call=True,
)
def _toggle_tdp_pin(click_data, current_pinned):
    """Toggle pinned point on TDP chart click."""
    if not click_data:
        return no_update

    points = click_data.get("points", [])
    if not points:
        return no_update

    point = points[0]
    quarter = point.get("x")
    retailer_id = point.get("customdata")

    if not quarter or not retailer_id:
        return no_update

    # Toggle: click same point to dismiss
    if (
        current_pinned
        and current_pinned.get("retailer_id") == retailer_id
        and current_pinned.get("quarter") == quarter
    ):
        return None

    return {"retailer_id": retailer_id, "quarter": quarter}


@callback(
    Output("tr-callout-area", "children"),
    Output("tr-acv-chart", "figure", allow_duplicate=True),
    Output("tr-tdp-chart", "figure", allow_duplicate=True),
    Input("tr-pinned-acv", "data"),
    Input("tr-pinned-tdp", "data"),
    State("filter-state", "data"),
    prevent_initial_call=True,
)
def _update_callout_and_dim(acv_pin, tdp_pin, filter_json):
    """Show callout card and dim non-selected retailers on pin."""
    filters = json.loads(filter_json) if filter_json else {}

    start_q = filters.get("start_quarter", "Q1 2025")
    end_q = filters.get("end_quarter", "Q4 2025")
    quarters = quarters_in_range(start_q, end_q)

    if not quarters or not filters.get("retailers"):
        empty = go.Figure()
        empty.update_layout(**economist_layout())
        return [], empty, empty

    acv_data = _compute_acv_by_retailer(filters, quarters)
    tdp_data = _compute_tdp_by_retailer(filters, quarters)

    # Use whichever pin was set most recently (prefer ACV if both set)
    active_pin = acv_pin or tdp_pin

    acv_fig = _build_acv_chart(acv_data, quarters, selected_point=active_pin)
    tdp_fig = _build_tdp_chart(tdp_data, quarters, selected_point=active_pin)

    if not active_pin:
        return [], acv_fig, tdp_fig

    ret_id = active_pin["retailer_id"]
    quarter = active_pin["quarter"]
    ret_name = _RETAILER_NAMES.get(ret_id, ret_id)

    # Get current values
    acv_val = acv_data.get(ret_id, {}).get(quarter, 0.0)
    tdp_val = tdp_data.get(ret_id, {}).get(quarter, 0.0)

    # Compute period-over-period delta
    q_idx = quarters.index(quarter) if quarter in quarters else -1
    if q_idx > 0:
        prior_q = quarters[q_idx - 1]
        prior_acv = acv_data.get(ret_id, {}).get(prior_q, 0.0)
        prior_tdp = tdp_data.get(ret_id, {}).get(prior_q, 0.0)
        acv_delta = calc_period_delta(acv_val, prior_acv)
        tdp_delta = calc_period_delta(tdp_val, prior_tdp)
    else:
        acv_delta = 0.0
        tdp_delta = 0.0

    card = dark_callout_card(
        title=ret_name,
        subtitle=quarter,
        rows=[
            {"label": "ACV%", "value": fmt_pct(acv_val)},
            {"label": "ACV% change", "value": fmt_delta(acv_delta)},
            {"label": "TDP", "value": f"{tdp_val:.1f}"},
            {"label": "TDP change", "value": f"{tdp_delta:+.1f} pts"},
        ],
    )

    return card, acv_fig, tdp_fig
