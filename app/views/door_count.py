"""Door Count view — hero metric, retailer bar chart, product line stacked bar,
click-to-pin callout cards, and auth gap narrative annotations."""

import json

import pandas as pd
import plotly.graph_objects as go
from cinderhaven_store_universe.constants import SKU_NAMES
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import filter_auth, prior_quarter, quarters_in_range
from app.charts import CHART_CONFIG, economist_layout
from app.components import (
    chart_footnote,
    dark_callout_card,
    term_disclosure,
    unfiltered_data_callout,
)
from app.constants import (
    CATEGORICAL_6,
    FONT_SANS,
    GAP_BAR,
    GRIDLINE,
    INK,
    SCAN_BAR,
    TEXT_SECONDARY,
    TREND_DOWN,
    TREND_UP,
    WHITE,
    fmt_number,
    fmt_pct,
)
from app.data import PL_NAMES, SCAN_QUARTERLY, STORE_INFO

# ── Data computation helpers ──


def _filter_auth_from_dict(filters):
    """Unpack a filter-state dict and delegate to calculations.filter_auth."""
    return filter_auth(
        retailers=filters.get("retailers"),
        product_lines=filters.get("product_lines"),
        sku=filters.get("sku"),
    )


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
    """Compute per-retailer authorized vs scanning pair counts."""
    ret_names = STORE_INFO[["store_id", "retailer_name"]].drop_duplicates()
    auth_ret = auth.merge(ret_names, on="store_id", how="left")

    auth_pairs = (
        auth_ret.groupby(["retailer_id", "retailer_name"])
        .apply(lambda g: len(g[["sku_id", "store_id"]].drop_duplicates()), include_groups=False)
        .reset_index(name="authorized_pairs")
    )

    sq = _carrying_scans(auth, quarters)
    if sq.empty:
        carry_pairs = pd.DataFrame(columns=["retailer_id", "scanning_pairs"])
    else:
        carry_pairs = (
            sq.groupby("retailer_id")
            .apply(lambda g: len(g[["sku_id", "store_id"]].drop_duplicates()), include_groups=False)
            .reset_index(name="scanning_pairs")
        )

    result = auth_pairs.merge(carry_pairs, on="retailer_id", how="left")
    result["scanning_pairs"] = result["scanning_pairs"].fillna(0).astype(int)
    result["pct"] = result["scanning_pairs"] / result["authorized_pairs"]
    result = result.sort_values("authorized_pairs", ascending=True)
    return result.to_dict("records")


def _compute_product_line_bars(auth, quarters):
    """Compute per-product-line scanning pairs broken down by retailer."""
    sq = _carrying_scans(auth, quarters)
    if sq.empty:
        return {}

    sq_named = sq.merge(
        STORE_INFO[["store_id", "retailer_name"]].drop_duplicates(),
        on="store_id",
        how="left",
    )
    scanning = (
        sq_named.groupby(["product_line", "retailer_name"])
        .apply(lambda g: len(g[["sku_id", "store_id"]].drop_duplicates()), include_groups=False)
        .reset_index(name="scanning_pairs")
    )

    result = {}
    for _, row in scanning.iterrows():
        pl_name = PL_NAMES.get(row["product_line"], row["product_line"])
        if pl_name not in result:
            result[pl_name] = {}
        result[pl_name][row["retailer_name"]] = int(row["scanning_pairs"])
    return result


def _compute_retailer_gaps(auth, quarters):
    """Compute per-retailer gap data — one entry per retailer, sorted by gap descending."""
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
    merged = merged.sort_values("gap", ascending=False)

    if merged.empty:
        return []

    worst_idx = merged["gap_pct"].idxmax()

    cards = []
    for idx, row in merged.iterrows():
        cards.append(
            {
                "value": fmt_number(int(row["gap"])),
                "label": f"pairs not scanning — {row['retailer_name']}",
                "is_worst": idx == worst_idx,
                "gap_pct": row["gap_pct"],
            }
        )

    return cards


def _gap_card(data):
    """Render a single retailer gap card — design system Level 1 card."""
    children = [
        html.Div(
            data["value"],
            className="ll-benchmark-value",
            style={
                "color": INK,
            },
        ),
        html.P(
            data["label"],
            style={
                "fontFamily": FONT_SANS,
                "fontSize": "14px",
                "color": TEXT_SECONDARY,
                "marginTop": "8px",
                "lineHeight": "1.4",
                "margin": "8px 0 0 0",
            },
        ),
    ]

    if data.get("is_worst"):
        children.append(
            html.Span(
                "widest gap",
                style={
                    "fontFamily": FONT_SANS,
                    "fontSize": "11px",
                    "fontWeight": "600",
                    "color": TREND_DOWN,
                    "textTransform": "uppercase",
                    "letterSpacing": "0.04em",
                    "marginTop": "8px",
                    "display": "inline-block",
                },
            )
        )

    return html.Div(
        children,
        style={
            "padding": "24px",
            "border": f"1px solid {GRIDLINE}",
            "borderRadius": "2px",
        },
    )


def _gap_card_grid(cards_data):
    """Render retailer gap cards in a 3-column CSS grid."""
    return html.Div(
        [_gap_card(c) for c in cards_data],
        className="gap-card-grid",
    )


def _compute_click_detail(auth, quarters, retailer_name):
    """Compute detail card data for a clicked retailer (pair-level)."""
    matching = STORE_INFO[STORE_INFO["retailer_name"] == retailer_name]
    if matching.empty:
        return None
    ret_row = matching.iloc[0]
    ret_id = ret_row["retailer_id"]

    ret_auth = auth[auth["retailer_id"] == ret_id]
    auth_pairs = ret_auth[["sku_id", "store_id"]].drop_duplicates()
    addressable = len(auth_pairs)

    sq = _carrying_scans(ret_auth, quarters)
    scanning = len(sq[["sku_id", "store_id"]].drop_duplicates())

    items_auth = ret_auth["sku_id"].nunique()
    items_carried = sq["sku_id"].nunique()
    items_not_carried = items_auth - items_carried

    pct = scanning / addressable if addressable > 0 else 0.0

    return {
        "retailer_name": retailer_name,
        "scanning_pairs": scanning,
        "authorized_pairs": addressable,
        "pct": pct,
        "items_carried": items_carried,
        "items_not_carried": items_not_carried,
    }


# ── Chart builders ──


def _build_retailer_chart(bar_data, selected_retailer=None):
    """Build a stacked horizontal bar chart showing scanning pairs + gap per retailer.

    The scanning portion (teal) and gap portion (light grey) stack to show
    total authorized.  Gap percentage is annotated to the right of each bar
    so the authorization-to-scan gap is immediately visible.
    """
    retailers = [d["retailer_name"] for d in bar_data]
    scan_counts = [d["scanning_pairs"] for d in bar_data]
    gap_counts = [d["authorized_pairs"] - d["scanning_pairs"] for d in bar_data]
    gap_pcts = [1 - d["pct"] if d["pct"] > 0 else 1.0 for d in bar_data]

    scan_opacity = []
    gap_opacity = []
    for d in bar_data:
        if selected_retailer and d["retailer_name"] != selected_retailer:
            scan_opacity.append(0.25)
            gap_opacity.append(0.15)
        else:
            scan_opacity.append(1.0)
            gap_opacity.append(1.0)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=retailers,
            x=scan_counts,
            name="Scanning",
            orientation="h",
            marker=dict(color=SCAN_BAR, opacity=scan_opacity),
            text=[fmt_number(v) for v in scan_counts],
            textposition="inside",
            textfont=dict(family=FONT_SANS, size=12, color=WHITE, weight="bold"),
            hoverinfo="skip",
        )
    )

    max_total = max((d["authorized_pairs"] for d in bar_data), default=1)

    fig.add_trace(
        go.Bar(
            y=retailers,
            x=gap_counts,
            name="Not scanning (gap)",
            orientation="h",
            marker=dict(color=GAP_BAR, opacity=gap_opacity),
            hoverinfo="skip",
        )
    )

    for i, (gap, gap_pct) in enumerate(zip(gap_counts, gap_pcts)):
        if gap <= 0:
            continue
        label = f"{gap:,.0f} ({gap_pct:.0%} gap)"
        total = scan_counts[i] + gap
        if gap >= 0.15 * max_total:
            fig.add_annotation(
                x=scan_counts[i] + gap / 2,
                y=retailers[i],
                text=label,
                showarrow=False,
                font=dict(family=FONT_SANS, size=12, color=WHITE, weight="bold"),
                xanchor="center",
                yanchor="middle",
            )
        else:
            fig.add_annotation(
                x=total,
                y=retailers[i],
                text=f"  {label}",
                showarrow=False,
                font=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY, weight="bold"),
                xanchor="left",
                yanchor="middle",
            )

    fig.update_layout(
        **economist_layout(
            barmode="stack",
            title=dict(text="Authorization-to-Scan Gap by Retailer"),
            xaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                title=None,
                range=[0, max_total * 1.08],
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=120, r=100, t=100, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.12,
                xanchor="left",
                x=0,
                font=dict(family=FONT_SANS, size=12),
                entrywidthmode="fraction",
                entrywidth=0.3,
            ),
            height=max(320, len(retailers) * 55 + 120),
        )
    )

    return fig


def _build_product_line_chart(pl_data):
    """Build a grouped horizontal bar chart: scanning pairs by product line and retailer."""
    if not pl_data:
        return go.Figure()

    product_lines = sorted(pl_data.keys())
    all_retailers = set()
    for ret_data in pl_data.values():
        all_retailers.update(ret_data.keys())
    all_retailers = sorted(all_retailers)

    fig = go.Figure()

    for i, retailer in enumerate(all_retailers):
        color = CATEGORICAL_6[i % len(CATEGORICAL_6)]
        values = [pl_data.get(pl, {}).get(retailer, 0) for pl in product_lines]
        fig.add_trace(
            go.Bar(
                y=product_lines,
                x=values,
                name=retailer,
                orientation="h",
                marker=dict(color=color),
                text=[fmt_number(v) if v > 0 else "" for v in values],
                textposition="outside",
                textfont=dict(family=FONT_SANS, size=11, color=INK),
                cliponaxis=False,
                constraintext="none",
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        **economist_layout(
            barmode="group",
            title=dict(text="Scanning Pairs by Product Line"),
            xaxis=dict(
                showgrid=True,
                gridcolor=GRIDLINE,
                title=None,
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=160, r=80, t=100, b=60),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.10,
                xanchor="left",
                x=0,
                font=dict(family=FONT_SANS, size=12),
                entrywidthmode="fraction",
                entrywidth=0.16,
            ),
            height=max(420, len(product_lines) * 120 + 160),
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
                        className="hero-number",
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
                    html.Div(
                        [
                            term_disclosure("scanning", inline=True),
                            term_disclosure("authorized", inline=True),
                        ],
                        style={"marginTop": "12px"},
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "40px 0 32px",
                    "marginBottom": "32px",
                },
            ),
            html.Div(
                dcc.Graph(
                    id="dc-retailer-chart",
                    config=CHART_CONFIG,
                ),
                **{"aria-label": "Authorized versus carrying doors by retailer"},
            ),
            chart_footnote(
                "Source: Cinderhaven synthetic store universe. Scanning = authorized "
                "item-store pairs with a recorded scan in the selected end quarter. "
                "Gap = authorized pairs with no scan that quarter."
            ),
            term_disclosure("gap", inline=True),
            html.Div(id="dc-callout-area"),
            html.Div(id="dc-auth-gap-annotations"),
            html.Div(
                dcc.Graph(
                    id="dc-product-line-chart",
                    config=CHART_CONFIG,
                ),
                style={"marginTop": "56px"},
                **{"aria-label": "Carrying doors by product line and retailer"},
            ),
            chart_footnote(
                "Source: Cinderhaven synthetic store universe. Counts reflect authorized "
                "item-store pairs with at least one recorded scan across the selected "
                "quarter range, grouped by product line and retailer."
            ),
            term_disclosure("door_count", inline=True),
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
    prior_q = prior_quarter(end_q)
    range_quarters = quarters_in_range(start_q, end_q)

    auth = _filter_auth_from_dict(filters)

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

    # Retailer bar chart — end quarter only (must match hero + gap cards)
    bar_data = _compute_retailer_bars(auth, [end_q])
    retailer_fig = _build_retailer_chart(bar_data)

    # Product line chart — full range
    pl_data = _compute_product_line_bars(auth, range_quarters)
    pl_fig = _build_product_line_chart(pl_data)

    # Per-retailer gap cards — one per retailer, 3×2 grid
    gap_cards = _compute_retailer_gaps(auth, [end_q])
    gap_children = []
    unfiltered = unfiltered_data_callout(filters)
    if unfiltered:
        gap_children.append(unfiltered)
    if gap_cards:
        gap_children.append(_gap_card_grid(gap_cards))

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

    auth = _filter_auth_from_dict(filters)
    bar_data = _compute_retailer_bars(auth, [end_q])

    if not pinned_retailer:
        fig = _build_retailer_chart(bar_data, selected_retailer=None)
        return [], fig

    detail = _compute_click_detail(auth, [end_q], pinned_retailer)

    card = dark_callout_card(
        title=detail["retailer_name"],
        subtitle=(
            f"{fmt_number(detail['scanning_pairs'])} of "
            f"{fmt_number(detail['authorized_pairs'])} authorized pairs scanning"
        ),
        rows=[
            {"label": "Pair penetration", "value": fmt_pct(detail["pct"])},
            {"label": "Items carried", "value": fmt_number(detail["items_carried"])},
            {"label": "Items not carried", "value": fmt_number(detail["items_not_carried"])},
        ],
    )

    fig = _build_retailer_chart(bar_data, selected_retailer=pinned_retailer)
    return card, fig
