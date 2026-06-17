"""Trends view -- ACV% and TDP line charts by quarter with slow-leak annotations."""

import json
import statistics

import plotly.graph_objects as go
from cinderhaven_store_universe.constants import SKU_NAMES
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import (
    batch_acv_by_retailer,
    batch_tdp_by_retailer,
    calc_penetration_rate,
    calc_period_delta,
    quarters_in_range,
)
from app.charts import CHART_CONFIG, economist_layout
from app.components import (
    dark_callout_card,
    stat_card,
    stat_card_row,
    unfiltered_data_callout,
)
from app.constants import (
    FONT_SANS,
    GRIDLINE,
    REFERENCE,
    TEAL_SEQUENTIAL,
    TEXT_SECONDARY,
    fmt_delta,
    fmt_pct,
)
from app.data import AUTH, RETAILER_NAMES, SLOW_LEAK

_RETAILER_NAMES = RETAILER_NAMES
_RETAILER_IDS_SORTED = sorted(RETAILER_NAMES.keys())

# Assign one teal color per retailer, evenly spaced across the 8-shade palette.
# 6 retailers, 8 teal shades -- pick indices [0, 1, 2, 4, 5, 7] for contrast.
_RETAILER_COLOR_INDICES = [0, 1, 2, 4, 5, 6]
RETAILER_COLORS = {}
for i, ret_id in enumerate(_RETAILER_IDS_SORTED):
    idx = (
        _RETAILER_COLOR_INDICES[i] if i < len(_RETAILER_COLOR_INDICES) else i % len(TEAL_SEQUENTIAL)
    )
    RETAILER_COLORS[ret_id] = TEAL_SEQUENTIAL[idx]

_LINE_DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
_MARKER_SYMBOLS = ["circle", "square", "diamond", "triangle-up", "cross", "star"]
RETAILER_LINE_STYLES = {}
RETAILER_MARKERS = {}
for i, ret_id in enumerate(_RETAILER_IDS_SORTED):
    RETAILER_LINE_STYLES[ret_id] = _LINE_DASHES[i % len(_LINE_DASHES)]
    RETAILER_MARKERS[ret_id] = _MARKER_SYMBOLS[i % len(_MARKER_SYMBOLS)]


# -- Computation helpers --


def _compute_acv_by_retailer(filters, quarters):
    """Compute ACV% per retailer per quarter in a single batch pass."""
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")
    return batch_acv_by_retailer(
        quarters,
        retailers,
        product_lines=product_lines if product_lines else None,
        sku=sku,
    )


def _compute_tdp_by_retailer(filters, quarters):
    """Compute TDP per retailer per quarter in a single batch pass."""
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    return batch_tdp_by_retailer(
        quarters,
        retailers,
        product_lines=product_lines if product_lines else None,
    )


def _compute_slow_leak_annotations(filters, quarters):
    """Check slow-leak SKUs and return stat card data for significant drops.

    A significant drop is >20 percentage points from peak penetration.
    Returns list of dicts with 'value' and 'label' keys.
    """
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")
    retailers = filters.get("retailers", [])

    cards = []

    for sku_id, config in SLOW_LEAK.items():
        sku_prefix = sku_id.split("-")[1]

        if product_lines and sku_prefix not in product_lines:
            continue
        if sku and sku != sku_id:
            continue

        penetration_by_q = {}
        for q in quarters:
            penetration_by_q[q] = calc_penetration_rate(
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

        if drop_pp > 0.20:
            peak_q = [q for q, v in penetration_by_q.items() if v == peak_pct][0]
            try:
                peak_idx = quarters.index(peak_q)
                n_quarters = len(quarters) - 1 - peak_idx
            except ValueError:
                n_quarters = 0

            auth_for_sku = AUTH[(AUTH["authorized"]) & (AUTH["sku_id"] == sku_id)]
            if retailers:
                auth_for_sku = auth_for_sku[auth_for_sku["retailer_id"].isin(retailers)]
            addressable = auth_for_sku["store_id"].nunique()
            doors_lost = int(addressable * drop_pp)

            sku_label = SKU_NAMES.get(sku_id, sku_id)
            cards.append(
                {
                    "value": f"~{doors_lost}",
                    "label": (
                        f"doors lost — {sku_label} over "
                        f"{n_quarters} quarter{'s' if n_quarters != 1 else ''}. "
                        f"Down from {fmt_pct(peak_pct)} to {fmt_pct(current_pct)}."
                    ),
                }
            )

    return cards


# -- Chart builders --


def _auto_y_range(all_values, suffix_pct=False):
    """Compute a Y-axis range with ~10% padding around the data extremes."""
    if not all_values:
        return None
    data_min = min(all_values)
    data_max = max(all_values)
    span = data_max - data_min
    padding = max(span * 0.15, 2.0)
    y_min = max(0, data_min - padding)
    y_max = data_max + padding
    if suffix_pct:
        y_max = min(100, y_max)
    return [round(y_min, 1), round(y_max, 1)]


def _build_acv_chart(acv_data, quarters, selected_point=None):
    """Build ACV% trend line chart with one line per retailer plus a median reference.

    Each retailer gets a unique color, line dash, and marker symbol so all 6
    lines are visually distinguishable even when values cluster tightly.
    Y-axis auto-scales to the data range instead of starting at 0%.
    """
    fig = go.Figure()

    # Collect all values for auto-range
    all_pct_values = []

    # Compute median ACV% across retailers per quarter
    medians = []
    for q in quarters:
        vals = [acv_data[r][q] for r in acv_data if q in acv_data[r]]
        med = statistics.median(vals) if vals else 0.0
        medians.append(med)
    median_pcts = [v * 100 for v in medians]
    all_pct_values.extend(median_pcts)

    fig.add_trace(
        go.Scatter(
            x=quarters,
            y=median_pcts,
            mode="lines",
            name="Median",
            line=dict(color=REFERENCE, dash="dash", width=2),
            showlegend=True,
            hovertemplate="Median: %{y:.1f}%<extra></extra>",
        )
    )

    for ret_id in sorted(acv_data.keys()):
        color = RETAILER_COLORS.get(ret_id, TEAL_SEQUENTIAL[0])
        dash = RETAILER_LINE_STYLES.get(ret_id, "solid")
        symbol = RETAILER_MARKERS.get(ret_id, "circle")
        name = _RETAILER_NAMES.get(ret_id, ret_id)
        values = [acv_data[ret_id].get(q, 0.0) for q in quarters]
        pct_values = [v * 100 for v in values]
        all_pct_values.extend(pct_values)

        opacity = 1.0
        if selected_point and selected_point.get("retailer_id") != ret_id:
            opacity = 0.25

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=pct_values,
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2.5, dash=dash),
                marker=dict(color=color, size=8, symbol=symbol),
                opacity=opacity,
                customdata=[ret_id] * len(quarters),
            )
        )

    y_range = _auto_y_range(all_pct_values, suffix_pct=True)

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
                range=y_range,
                title=None,
            ),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="left",
                x=0,
                font=dict(family=FONT_SANS, size=12),
                entrywidthmode="fraction",
                entrywidth=0.14,
            ),
            height=480,
        )
    )

    return fig


def _dodge_overlapping(tdp_data, quarters, threshold=1.0, min_gap=1.0):
    """Nudge overlapping TDP values apart at each quarter for visual clarity."""
    nudged = {ret_id: dict(vals) for ret_id, vals in tdp_data.items()}

    # Sort cluster members by mean value across all quarters so the same
    # retailer always gets the same lane — prevents artificial line crossings.
    means = {}
    for ret_id in tdp_data:
        vals = [tdp_data[ret_id].get(q, 0.0) for q in quarters]
        means[ret_id] = sum(vals) / len(vals) if vals else 0.0

    for q in quarters:
        points = [(ret_id, tdp_data[ret_id].get(q, 0.0)) for ret_id in tdp_data]
        points.sort(key=lambda p: p[1])

        if len(points) < 2:
            continue

        clusters = []
        current = [points[0]]
        for i in range(1, len(points)):
            if points[i][1] - current[-1][1] <= threshold:
                current.append(points[i])
            else:
                if len(current) > 1:
                    clusters.append(current)
                current = [points[i]]
        if len(current) > 1:
            clusters.append(current)

        for cluster in clusters:
            cluster.sort(key=lambda p: means[p[0]])
            center = sum(p[1] for p in cluster) / len(cluster)
            n = len(cluster)
            total_span = (n - 1) * min_gap
            start = center - total_span / 2
            for j, (ret_id, _) in enumerate(cluster):
                nudged[ret_id][q] = round(start + j * min_gap, 2)

    return nudged


def _build_tdp_chart(tdp_data, quarters, selected_point=None):
    """Build TDP trend line chart with one line per retailer plus a median reference.

    Each retailer gets a unique color, line dash, and marker symbol.
    Y-axis auto-scales to the data range.
    """
    fig = go.Figure()

    nudged = _dodge_overlapping(tdp_data, quarters)
    all_values = []

    medians = []
    for q in quarters:
        vals = [tdp_data[r][q] for r in tdp_data if q in tdp_data[r]]
        med = statistics.median(vals) if vals else 0.0
        medians.append(med)
    median_vals = [round(v, 1) for v in medians]
    all_values.extend(median_vals)

    fig.add_trace(
        go.Scatter(
            x=quarters,
            y=median_vals,
            mode="lines",
            name="Median",
            line=dict(color=REFERENCE, dash="dash", width=2),
            showlegend=True,
            hovertemplate="Median: %{y:.1f} pts<extra></extra>",
        )
    )

    for ret_id in sorted(tdp_data.keys()):
        color = RETAILER_COLORS.get(ret_id, TEAL_SEQUENTIAL[0])
        dash = RETAILER_LINE_STYLES.get(ret_id, "solid")
        symbol = RETAILER_MARKERS.get(ret_id, "circle")
        name = _RETAILER_NAMES.get(ret_id, ret_id)
        true_values = [tdp_data[ret_id].get(q, 0.0) for q in quarters]
        plot_values = [nudged[ret_id].get(q, 0.0) for q in quarters]
        all_values.extend(plot_values)

        opacity = 1.0
        if selected_point and selected_point.get("retailer_id") != ret_id:
            opacity = 0.25

        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=[round(v, 1) for v in plot_values],
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2.5, dash=dash),
                marker=dict(color=color, size=8, symbol=symbol),
                opacity=opacity,
                customdata=[ret_id] * len(quarters),
                text=[f"{v:.1f}" for v in true_values],
                hovertemplate="%{x}<br>TDP: %{text}<extra>%{fullData.name}</extra>",
            )
        )

    y_range = _auto_y_range(all_values)

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
                title="TDP points",
                range=y_range,
            ),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="left",
                x=0,
                font=dict(family=FONT_SANS, size=12),
                entrywidthmode="fraction",
                entrywidth=0.14,
            ),
            height=480,
        )
    )

    return fig


# -- Layout --


def layout():
    """Return the Trends view component tree."""
    return html.Div(
        [
            html.Div(
                dcc.Graph(
                    id="tr-acv-chart",
                    config=CHART_CONFIG,
                ),
                **{"aria-label": "ACV percent trend by retailer over time"},
            ),
            html.Div(
                dcc.Graph(
                    id="tr-tdp-chart",
                    config=CHART_CONFIG,
                ),
                style={"marginTop": "40px"},
                **{"aria-label": "TDP trend by retailer over time"},
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
    Input("main-tabs", "value"),
)
def _update_trends_charts(filter_json, active_tab):
    """Recompute ACV% and TDP charts when filters change."""
    if active_tab != "trends":
        return no_update, no_update, no_update
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

    # Slow-leak stat cards
    leak_cards = _compute_slow_leak_annotations(filters, quarters)
    leak_children = []
    unfiltered = unfiltered_data_callout(filters)
    if unfiltered:
        leak_children.append(unfiltered)
    if leak_cards:
        leak_children.append(stat_card_row([stat_card(c["value"], c["label"]) for c in leak_cards]))

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
