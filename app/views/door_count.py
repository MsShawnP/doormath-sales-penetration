"""Door Count view — hero metric, retailer bar chart, product line stacked bar,
click-to-pin callout cards, and auth gap narrative annotations."""

import json

import pandas as pd
import plotly.graph_objects as go
from cinderhaven_store_universe.constants import SKU_NAMES
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import quarters_in_range
from app.charts import CHART_CONFIG, economist_layout
from app.components import annotation_callout, dark_callout_card
from app.constants import (
    AUTH_BAR,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    INK,
    SCAN_BAR,
    TEAL_SEQUENTIAL,
    TEXT_SECONDARY,
    TREND_DOWN,
    TREND_UP,
    WHITE,
    fmt_number,
    fmt_pct,
)
from app.data import AUTH, PL_NAMES, SCAN_QUARTERLY, STORE_INFO

# ── Quarter helpers ──


def _prior_quarter(quarter_str):
    """Return the quarter string one quarter before the given quarter."""
    all_quarters = [f"Q{q} {y}" for y in [2024, 2025] for q in [1, 2, 3, 4]]
    try:
        idx = all_quarters.index(quarter_str)
    except ValueError:
        return None
    if idx == 0:
        return None
    return all_quarters[idx - 1]


# ── Data computation helpers ──


def _filter_auth(filters):
    """Filter authorized pairs by filter-state dict."""
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")

    auth = AUTH[AUTH["authorized"]]
    if retailers:
        auth = auth[auth["retailer_id"].isin(retailers)]
    if product_lines:
        auth = auth[auth["product_line"].isin(product_lines)]
    if sku:
        auth = auth[auth["sku_id"] == sku]
    return auth


def _carrying_scans(auth, quarters):
    """Return SCAN_QUARTERLY rows for authorized stores in the given quarters."""
    store_ids = set(auth["store_id"].unique())
    sku_ids = set(auth["sku_id"].unique())
    return SCAN_QUARTERLY[
        SCAN_QUARTERLY["quarter"].isin(quarters)
        & SCAN_QUARTERLY["store_id"].isin(store_ids)
        & SCAN_QUARTERLY["sku_id"].isin(sku_ids)
    ]


def _compute_penetration(auth, quarters):
    """Compute SKU-level penetration: carrying pairs / authorized pairs.

    Counts at the (sku_id, store_id) level — what fraction of authorized
    item-store slots are actually scanning in the quarter range.
    """
    auth_pairs = auth[["sku_id", "store_id"]].drop_duplicates()
    addressable = len(auth_pairs)
    if addressable == 0 or not quarters:
        return 0.0, 0, 0

    sq = _carrying_scans(auth, quarters)
    carrying_pairs = sq[["sku_id", "store_id"]].drop_duplicates()
    carrying = len(carrying_pairs)
    pct = carrying / addressable
    return pct, carrying, addressable


def _compute_retailer_bars(auth, quarters):
    """Compute per-retailer authorized vs carrying door counts."""
    ret_names = STORE_INFO[["store_id", "retailer_name"]].drop_duplicates()
    auth_ret = auth.merge(ret_names, on="store_id", how="left")
    auth_by_ret = (
        auth_ret.groupby(["retailer_id", "retailer_name"])["store_id"].nunique().reset_index()
    )
    auth_by_ret.columns = ["retailer_id", "retailer_name", "authorized_doors"]

    sq = _carrying_scans(auth, quarters)
    carry_by_ret = sq.groupby("retailer_id")["store_id"].nunique().reset_index()
    carry_by_ret.columns = ["retailer_id", "carrying_doors"]

    result = auth_by_ret.merge(carry_by_ret, on="retailer_id", how="left")
    result["carrying_doors"] = result["carrying_doors"].fillna(0).astype(int)
    result["pct"] = result["carrying_doors"] / result["authorized_doors"]
    result = result.sort_values("authorized_doors", ascending=True)
    return result.to_dict("records")


def _compute_product_line_bars(auth, quarters):
    """Compute per-product-line carrying doors broken down by retailer."""
    sq = _carrying_scans(auth, quarters)
    if sq.empty:
        return {}

    sq_named = sq.merge(
        STORE_INFO[["store_id", "retailer_name"]].drop_duplicates(),
        on="store_id",
        how="left",
    )
    grouped = (
        sq_named.groupby(["product_line", "retailer_name"])["store_id"].nunique().reset_index()
    )
    grouped.columns = ["product_line", "retailer_name", "carrying_doors"]

    result = {}
    for _, row in grouped.iterrows():
        pl_name = PL_NAMES.get(row["product_line"], row["product_line"])
        if pl_name not in result:
            result[pl_name] = {}
        result[pl_name][row["retailer_name"]] = int(row["carrying_doors"])
    return result


def _compute_auth_gaps(auth, quarters):
    """Find retailers where authorized pairs not scanning exceeds 15%."""
    ret_names = STORE_INFO[["store_id", "retailer_name"]].drop_duplicates()
    auth_ret = auth.merge(ret_names, on="store_id", how="left")

    auth_pairs = (
        auth_ret.groupby(["retailer_id", "retailer_name"])
        .apply(lambda g: len(g[["sku_id", "store_id"]].drop_duplicates()), include_groups=False)
        .reset_index(name="authorized_pairs")
    )

    sq = _carrying_scans(auth, quarters)
    if sq.empty:
        carry_pairs = pd.DataFrame(columns=["retailer_id", "carrying_pairs"])
    else:
        carry_pairs = (
            sq.groupby("retailer_id")
            .apply(lambda g: len(g[["sku_id", "store_id"]].drop_duplicates()), include_groups=False)
            .reset_index(name="carrying_pairs")
        )

    merged = auth_pairs.merge(carry_pairs, on="retailer_id", how="left")
    merged["carrying_pairs"] = merged["carrying_pairs"].fillna(0).astype(int)
    merged["gap"] = merged["authorized_pairs"] - merged["carrying_pairs"]
    merged["gap_pct"] = merged["gap"] / merged["authorized_pairs"]

    annotations = []

    if merged.empty:
        return annotations

    best = merged.loc[merged["gap_pct"].idxmin()]
    worst = merged.loc[merged["gap_pct"].idxmax()]

    if best["gap_pct"] < 0.05 and len(merged) > 1:
        best_pct = (1 - best["gap_pct"]) * 100
        annotations.append(
            f"{best['retailer_name']} leads at {best_pct:.0f}% pair coverage — "
            f"a model for what full execution looks like."
        )

    for _, row in merged[merged["gap_pct"] > 0.10].iterrows():
        gap = int(row["gap"])
        auth_ct = int(row["authorized_pairs"])
        name = row["retailer_name"]
        annotations.append(
            f"{name}: {gap} of {auth_ct} authorized item-store pairs haven't "
            f"scanned recently — the shelf says no even though the buyer said yes."
        )

    if worst["gap_pct"] > 0.20 and len(merged) > 1:
        worst_pct = worst["gap_pct"] * 100
        annotations.append(
            f"{worst['retailer_name']} has the widest distribution gap at "
            f"{worst_pct:.0f}% — prioritize field visits here."
        )

    return annotations


def _compute_click_detail(auth, quarters, retailer_name):
    """Compute detail card data for a clicked retailer."""
    ret_row = STORE_INFO[STORE_INFO["retailer_name"] == retailer_name].iloc[0]
    ret_id = ret_row["retailer_id"]

    ret_auth = auth[auth["retailer_id"] == ret_id]
    addressable = ret_auth["store_id"].nunique()

    sq = _carrying_scans(ret_auth, quarters)
    carrying_doors = sq["store_id"].nunique()

    items_auth = ret_auth["sku_id"].nunique()
    items_carried = sq["sku_id"].nunique()
    items_not_carried = items_auth - items_carried

    pct = carrying_doors / addressable if addressable > 0 else 0.0

    return {
        "retailer_name": retailer_name,
        "carrying_doors": carrying_doors,
        "addressable_doors": addressable,
        "pct": pct,
        "items_carried": items_carried,
        "items_not_carried": items_not_carried,
    }


# ── Chart builders ──


def _build_retailer_chart(bar_data, selected_retailer=None):
    """Build a horizontal grouped bar chart: authorized vs carrying by retailer."""
    retailers = [d["retailer_name"] for d in bar_data]
    auth_counts = [d["authorized_doors"] for d in bar_data]
    carry_counts = [d["carrying_doors"] for d in bar_data]

    auth_opacity = []
    carry_opacity = []
    for d in bar_data:
        if selected_retailer and d["retailer_name"] != selected_retailer:
            auth_opacity.append(0.3)
            carry_opacity.append(0.3)
        else:
            auth_opacity.append(1.0)
            carry_opacity.append(1.0)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=retailers,
            x=auth_counts,
            name="Authorized",
            orientation="h",
            marker=dict(color=AUTH_BAR, opacity=auth_opacity),
            text=[fmt_number(v) for v in auth_counts],
            textposition="outside",
            textfont=dict(family=FONT_SANS, size=12, color=INK),
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Bar(
            y=retailers,
            x=carry_counts,
            name="Carrying",
            orientation="h",
            marker=dict(color=SCAN_BAR, opacity=carry_opacity),
            text=[fmt_number(v) for v in carry_counts],
            textposition="outside",
            textfont=dict(family=FONT_SANS, size=12, color=INK),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        **economist_layout(
            barmode="group",
            title=dict(text="Authorized vs Carrying Doors by Retailer"),
            xaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                showline=True,
                linecolor=GRIDLINE,
                title="Door Count",
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            ),
            yaxis=dict(
                showgrid=False,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=120, r=60, t=100, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            height=max(300, len(retailers) * 60 + 100),
        )
    )

    return fig


def _build_product_line_chart(pl_data):
    """Build a stacked horizontal bar chart: carrying doors by product line and retailer."""
    if not pl_data:
        return go.Figure()

    product_lines = sorted(pl_data.keys())
    all_retailers = set()
    for ret_data in pl_data.values():
        all_retailers.update(ret_data.keys())
    all_retailers = sorted(all_retailers)

    fig = go.Figure()

    for i, retailer in enumerate(all_retailers):
        color = TEAL_SEQUENTIAL[i % len(TEAL_SEQUENTIAL)]
        values = [pl_data.get(pl, {}).get(retailer, 0) for pl in product_lines]
        fig.add_trace(
            go.Bar(
                y=product_lines,
                x=values,
                name=retailer,
                orientation="h",
                marker=dict(color=color),
                text=[fmt_number(v) if v > 0 else "" for v in values],
                textposition="inside",
                textfont=dict(family=FONT_SANS, size=11, color=WHITE),
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        **economist_layout(
            barmode="stack",
            title=dict(text="Carrying Doors by Product Line"),
            xaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                showline=True,
                linecolor=GRIDLINE,
                title="Carrying Doors",
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            ),
            yaxis=dict(
                showgrid=False,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=160, r=40, t=100, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            height=max(300, len(product_lines) * 50 + 120),
        )
    )

    return fig


# ── Layout ──


def layout():
    """Return the Door Count view component tree."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        id="dc-hero-pct",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "64px",
                            "fontWeight": "700",
                            "color": INK,
                            "letterSpacing": "-0.02em",
                            "lineHeight": "1",
                        },
                    ),
                    html.P(
                        "of authorized item-store pairs currently scanning",
                        id="dc-hero-subtitle",
                        style={
                            "fontFamily": FONT_SANS,
                            "fontSize": "17px",
                            "color": TEXT_SECONDARY,
                            "marginTop": "8px",
                            "marginBottom": "4px",
                        },
                    ),
                    html.Div(
                        id="dc-hero-trend",
                        style={
                            "fontFamily": FONT_SANS,
                            "fontSize": "16px",
                            "fontWeight": "600",
                        },
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "32px 0",
                    "marginBottom": "24px",
                },
            ),
            html.Div(
                dcc.Graph(
                    id="dc-retailer-chart",
                    config=CHART_CONFIG,
                ),
                **{"aria-label": "Authorized versus carrying doors by retailer"},
            ),
            html.Div(id="dc-callout-area"),
            html.Div(id="dc-auth-gap-annotations"),
            html.Div(
                dcc.Graph(
                    id="dc-product-line-chart",
                    config=CHART_CONFIG,
                ),
                style={"marginTop": "40px"},
                **{"aria-label": "Carrying doors by product line and retailer"},
            ),
            dcc.Store(id="dc-pinned-retailer", data=None),
        ],
    )


# ── Callbacks ──


@callback(
    Output("dc-hero-pct", "children"),
    Output("dc-hero-subtitle", "children"),
    Output("dc-hero-trend", "children"),
    Output("dc-hero-trend", "style"),
    Output("dc-retailer-chart", "figure"),
    Output("dc-product-line-chart", "figure"),
    Output("dc-auth-gap-annotations", "children"),
    Input("filter-state", "data"),
    Input("main-tabs", "value"),
)
def _update_door_count_view(filter_json, active_tab):
    """Recompute all door count view elements when filters change."""
    if active_tab != "door-count":
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    filters = json.loads(filter_json) if filter_json else {}

    end_q = filters.get("end_quarter", "Q4 2025")
    start_q = filters.get("start_quarter", "Q1 2025")
    prior_q = _prior_quarter(end_q)
    range_quarters = quarters_in_range(start_q, end_q)

    auth = _filter_auth(filters)

    # Hero metric — based on end quarter only
    current_pct, carrying, addressable = _compute_penetration(auth, [end_q])
    hero_text = fmt_pct(current_pct, 1)

    # Dynamic subtitle based on SKU filter
    sku = filters.get("sku")
    if sku:
        sku_label = SKU_NAMES.get(sku, sku)
        subtitle = f"of addressable doors carrying {sku_label}"
    else:
        subtitle = "of authorized item-store pairs currently scanning"

    # Trend vs prior quarter
    if prior_q:
        prior_pct, _, _ = _compute_penetration(auth, [prior_q])
        delta = current_pct - prior_pct
        if delta > 0:
            trend_text = f"↑ {abs(delta) * 100:.1f} pp from prior quarter"
            trend_style = {
                "fontFamily": FONT_SANS,
                "fontSize": "16px",
                "fontWeight": "600",
                "color": TREND_UP,
            }
        elif delta < 0:
            trend_text = f"↓ {abs(delta) * 100:.1f} pp from prior quarter"
            trend_style = {
                "fontFamily": FONT_SANS,
                "fontSize": "16px",
                "fontWeight": "600",
                "color": TREND_DOWN,
            }
        else:
            trend_text = "→ 0.0 pp from prior quarter"
            trend_style = {
                "fontFamily": FONT_SANS,
                "fontSize": "16px",
                "fontWeight": "600",
                "color": TEXT_SECONDARY,
            }
    else:
        trend_text = ""
        trend_style = {"display": "none"}

    # Retailer bar chart — full range
    bar_data = _compute_retailer_bars(auth, range_quarters)
    retailer_fig = _build_retailer_chart(bar_data)

    # Product line chart — full range
    pl_data = _compute_product_line_bars(auth, range_quarters)
    pl_fig = _build_product_line_chart(pl_data)

    # Auth gap annotations — based on end quarter
    gap_texts = _compute_auth_gaps(auth, [end_q])
    gap_children = [annotation_callout(t) for t in gap_texts] if gap_texts else []

    return hero_text, subtitle, trend_text, trend_style, retailer_fig, pl_fig, gap_children


@callback(
    Output("dc-pinned-retailer", "data"),
    Input("dc-retailer-chart", "clickData"),
    State("dc-pinned-retailer", "data"),
    prevent_initial_call=True,
)
def _toggle_pinned_retailer(click_data, current_pinned):
    """Toggle the pinned retailer on bar click."""
    if not click_data:
        return no_update

    points = click_data.get("points", [])
    if not points:
        return no_update

    clicked_retailer = points[0].get("y")
    if not clicked_retailer:
        return no_update

    if current_pinned == clicked_retailer:
        return None
    return clicked_retailer


@callback(
    Output("dc-callout-area", "children"),
    Output("dc-retailer-chart", "figure", allow_duplicate=True),
    Input("dc-pinned-retailer", "data"),
    State("filter-state", "data"),
    prevent_initial_call=True,
)
def _update_callout_and_dim(pinned_retailer, filter_json):
    """Show/hide callout card and dim non-selected retailers."""
    filters = json.loads(filter_json) if filter_json else {}
    end_q = filters.get("end_quarter", "Q4 2025")
    start_q = filters.get("start_quarter", "Q1 2025")
    range_quarters = quarters_in_range(start_q, end_q)

    auth = _filter_auth(filters)
    bar_data = _compute_retailer_bars(auth, range_quarters)

    if not pinned_retailer:
        fig = _build_retailer_chart(bar_data, selected_retailer=None)
        return [], fig

    detail = _compute_click_detail(auth, [end_q], pinned_retailer)

    card = dark_callout_card(
        title=detail["retailer_name"],
        subtitle=f"{detail['carrying_doors']} of {detail['addressable_doors']} addressable doors",
        rows=[
            {"label": "Penetration", "value": fmt_pct(detail["pct"])},
            {"label": "Items carried", "value": fmt_number(detail["items_carried"])},
            {"label": "Items not carried", "value": fmt_number(detail["items_not_carried"])},
        ],
    )

    fig = _build_retailer_chart(bar_data, selected_retailer=pinned_retailer)
    return card, fig
