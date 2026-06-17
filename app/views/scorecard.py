"""Scorecard view — one-page distribution summary with PDF export.

Shows a hero penetration metric, retailer summary table, product line summary
table, and top 10 exceptions.  The "Download PDF" button triggers WeasyPrint
generation via ``app.pdf``.
"""

import json

from cinderhaven_store_universe.constants import PRODUCT_LINES, RETAILERS
from dash import Input, Output, State, callback, clientside_callback, dcc, html, no_update

from app.calculations import (
    batch_acv_by_product_line,
    batch_acv_by_retailer,
    batch_tdp_by_retailer,
    calc_penetration_rate,
    calc_period_delta,
    carrying_in_quarter,
    filter_auth,
    prior_quarter,
)
from app.components import (
    error_banner,
    stat_card,
    stat_card_row,
    td_style,
    th_style,
    unfiltered_data_callout,
)
from app.constants import (
    CANVAS,
    CHICAGO_20,
    FONT_SANS,
    FONT_SERIF,
    INK,
    TEXT_SECONDARY,
    TOKYO_40,
    TREND_DOWN,
    TREND_UP,
    WHITE,
    fmt_number,
    fmt_pct,
)
from app.data import DEMO_AS_OF_DATE, PL_NAMES, RETAILER_NAMES
from app.views.exceptions import compute_exceptions

_RET_NAMES = RETAILER_NAMES
_PL_NAMES = PL_NAMES
_PL_PREFIXES = list(PRODUCT_LINES.keys())


# ── Core data computation ──


def _compute_scorecard_data(filters):
    """Compute all data needed for both the screen scorecard and the PDF.

    Uses batch queries instead of per-entity loops — ~5 queries total
    instead of ~30+.

    Returns a dict with keys:
        hero_pct, hero_delta, retailer_rows, product_line_rows,
        top_exceptions, quarter_label, generation_date
    """
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")
    end_q = filters.get("end_quarter", "Q4 2025")
    prior_q = prior_quarter(end_q)

    # ── Hero metric ──
    hero_pct = calc_penetration_rate(
        end_q,
        retailers=retailers or None,
        product_lines=product_lines or None,
        sku=sku,
    )
    if prior_q:
        prior_pct = calc_penetration_rate(
            prior_q,
            retailers=retailers or None,
            product_lines=product_lines or None,
            sku=sku,
        )
        hero_delta = calc_period_delta(hero_pct, prior_pct)
    else:
        hero_delta = 0.0

    # ── Retailer summary rows (batched) ──
    active_retailers = retailers if retailers else list(RETAILERS.keys())
    quarters_batch = [end_q] + ([prior_q] if prior_q else [])

    acv_by_ret = batch_acv_by_retailer(quarters_batch, active_retailers, product_lines or None, sku)
    tdp_by_ret = batch_tdp_by_retailer(quarters_batch, active_retailers, product_lines or None)

    auth_all = filter_auth(retailers=active_retailers, product_lines=product_lines or None, sku=sku)
    auth_pairs = auth_all[["sku_id", "store_id", "retailer_id"]].drop_duplicates()
    addr_by_ret = auth_pairs.groupby("retailer_id").size()

    store_ids = set(auth_all["store_id"].unique())
    sku_ids = set(auth_all["sku_id"].unique())
    sq_end = carrying_in_quarter(end_q, store_ids, sku_ids)
    carry_end = sq_end[["sku_id", "store_id", "retailer_id"]].drop_duplicates()
    carry_by_ret = carry_end.groupby("retailer_id").size()

    carry_prior_by_ret = None
    if prior_q:
        sq_prior = carrying_in_quarter(prior_q, store_ids, sku_ids)
        carry_prior = sq_prior[["sku_id", "store_id", "retailer_id"]].drop_duplicates()
        carry_prior_by_ret = carry_prior.groupby("retailer_id").size()

    retailer_rows = []
    for ret_id in active_retailers:
        addr = int(addr_by_ret.get(ret_id, 0))
        carry = int(carry_by_ret.get(ret_id, 0))
        pen = carry / addr if addr > 0 else 0.0

        if prior_q and carry_prior_by_ret is not None:
            prior_carry = int(carry_prior_by_ret.get(ret_id, 0))
            prior_pen = prior_carry / addr if addr > 0 else 0.0
            delta = calc_period_delta(pen, prior_pen)
        else:
            delta = 0.0

        retailer_rows.append(
            {
                "name": _RET_NAMES.get(ret_id, ret_id),
                "carrying": carry,
                "addressable": addr,
                "penetration": pen,
                "acv_pct": acv_by_ret.get(ret_id, {}).get(end_q, 0.0),
                "tdp": tdp_by_ret.get(ret_id, {}).get(end_q, 0.0),
                "delta": delta,
            }
        )

    retailer_rows.sort(key=lambda r: r["addressable"], reverse=True)

    # ── Product line summary rows (batched) ──
    active_pls = product_lines if product_lines else _PL_PREFIXES

    acv_by_pl = batch_acv_by_product_line(quarters_batch, active_pls, retailers or None, sku)

    pl_auth = filter_auth(retailers=retailers or None, product_lines=active_pls, sku=sku)
    pl_pairs = pl_auth[["sku_id", "store_id", "product_line"]].drop_duplicates()
    pl_addr = pl_pairs.groupby("product_line").size()

    pl_store_ids = set(pl_auth["store_id"].unique())
    pl_sku_ids = set(pl_auth["sku_id"].unique())
    pl_sq = carrying_in_quarter(end_q, pl_store_ids, pl_sku_ids)
    pl_carry = pl_sq[["sku_id", "store_id", "product_line"]].drop_duplicates()
    pl_carry_by = pl_carry.groupby("product_line").size()

    pl_carry_prior_by = None
    if prior_q:
        pl_sq_prior = carrying_in_quarter(prior_q, pl_store_ids, pl_sku_ids)
        pl_carry_p = pl_sq_prior[["sku_id", "store_id", "product_line"]].drop_duplicates()
        pl_carry_prior_by = pl_carry_p.groupby("product_line").size()

    product_line_rows = []
    for pl_prefix in active_pls:
        addr = int(pl_addr.get(pl_prefix, 0))
        carry = int(pl_carry_by.get(pl_prefix, 0))
        pen = carry / addr if addr > 0 else 0.0

        if prior_q and pl_carry_prior_by is not None:
            prior_carry = int(pl_carry_prior_by.get(pl_prefix, 0))
            prior_pen = prior_carry / addr if addr > 0 else 0.0
            delta = calc_period_delta(pen, prior_pen)
        else:
            delta = 0.0

        product_line_rows.append(
            {
                "name": _PL_NAMES.get(pl_prefix, pl_prefix),
                "carrying": carry,
                "addressable": addr,
                "penetration": pen,
                "acv_pct": acv_by_pl.get(pl_prefix, {}).get(end_q, 0.0),
                "delta": delta,
            }
        )

    product_line_rows.sort(key=lambda r: r["addressable"], reverse=True)

    # ── Top exceptions (one row per SKU, aggregated across stores) ──
    exception_rows, _ = compute_exceptions(filters)
    top_exceptions = []
    if exception_rows:
        import pandas as pd

        ex_df = pd.DataFrame(exception_rows)
        total_retailers = ex_df["retailer_name"].nunique()
        sku_agg = (
            ex_df.groupby("sku_id")
            .agg(
                item_name=("item_name", "first"),
                stores=("store_id", "nunique"),
                retailers=(
                    "retailer_name",
                    lambda x: (
                        "All retailers"
                        if x.nunique() == total_retailers
                        else ", ".join(sorted(x.unique()))
                    ),
                ),
                max_weeks=("weeks_silent", "max"),
            )
            .sort_values("max_weeks", ascending=False)
            .head(10)
            .reset_index()
        )
        for _, row in sku_agg.iterrows():
            top_exceptions.append(
                {
                    "sku_id": row["sku_id"],
                    "item_name": row["item_name"],
                    "retailer": row["retailers"],
                    "stores": int(row["stores"]),
                    "weeks_silent": int(row["max_weeks"]),
                }
            )

    generation_date = DEMO_AS_OF_DATE.strftime("%Y-%m-%d")

    return {
        "hero_pct": hero_pct,
        "hero_delta": hero_delta,
        "retailer_rows": retailer_rows,
        "product_line_rows": product_line_rows,
        "top_exceptions": top_exceptions,
        "quarter_label": end_q,
        "generation_date": generation_date,
    }


# ── Table builders (Dash HTML) ──


def _build_retailer_table(rows):
    """Build the retailer summary table as a Dash html.Table."""
    header = html.Thead(
        html.Tr(
            [
                html.Th("Retailer", style=th_style()),
                html.Th("Scanning / Authorized", style=th_style()),
                html.Th("Penetration %", style=th_style(align="right")),
                html.Th("ACV%", style=th_style(align="right")),
                html.Th("TDP", style=th_style(align="right")),
                html.Th("Δ vs Prior Qtr", style=th_style(align="right")),
            ]
        ),
    )

    body_rows = []
    for i, row in enumerate(rows):
        bg = CANVAS if i % 2 == 0 else WHITE
        delta_color = (
            TREND_UP if row["delta"] > 0 else TREND_DOWN if row["delta"] < 0 else TEXT_SECONDARY
        )
        delta_arrow = "↑" if row["delta"] > 0 else "↓" if row["delta"] < 0 else "→"
        delta_text = f"{delta_arrow} {abs(row['delta']) * 100:.1f} pp"

        body_rows.append(
            html.Tr(
                [
                    html.Td(row["name"], style=td_style(bg=bg)),
                    html.Td(
                        f"{fmt_number(row['carrying'])} / {fmt_number(row['addressable'])}",
                        style=td_style(bg=bg),
                    ),
                    html.Td(fmt_pct(row["penetration"]), style=td_style(bg=bg, align="right")),
                    html.Td(fmt_pct(row["acv_pct"]), style=td_style(bg=bg, align="right")),
                    html.Td(f"{row['tdp']:.1f}", style=td_style(bg=bg, align="right")),
                    html.Td(
                        delta_text,
                        style=td_style(bg=bg, align="right", color=delta_color),
                    ),
                ]
            )
        )

    body = html.Tbody(body_rows)
    return html.Table(
        [header, body],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontFamily": FONT_SANS,
            "fontSize": "14px",
        },
    )


def _build_product_line_table(rows):
    """Build the product line summary table as a Dash html.Table."""
    header = html.Thead(
        html.Tr(
            [
                html.Th("Product Line", style=th_style()),
                html.Th("Scanning / Authorized", style=th_style()),
                html.Th("Penetration %", style=th_style(align="right")),
                html.Th("ACV%", style=th_style(align="right")),
                html.Th("Δ vs Prior Qtr", style=th_style(align="right")),
            ]
        ),
    )

    body_rows = []
    for i, row in enumerate(rows):
        bg = CANVAS if i % 2 == 0 else WHITE
        delta_color = (
            TREND_UP if row["delta"] > 0 else TREND_DOWN if row["delta"] < 0 else TEXT_SECONDARY
        )
        delta_arrow = "↑" if row["delta"] > 0 else "↓" if row["delta"] < 0 else "→"
        delta_text = f"{delta_arrow} {abs(row['delta']) * 100:.1f} pp"

        body_rows.append(
            html.Tr(
                [
                    html.Td(row["name"], style=td_style(bg=bg)),
                    html.Td(
                        f"{fmt_number(row['carrying'])} / {fmt_number(row['addressable'])}",
                        style=td_style(bg=bg),
                    ),
                    html.Td(fmt_pct(row["penetration"]), style=td_style(bg=bg, align="right")),
                    html.Td(fmt_pct(row["acv_pct"]), style=td_style(bg=bg, align="right")),
                    html.Td(
                        delta_text,
                        style=td_style(bg=bg, align="right", color=delta_color),
                    ),
                ]
            )
        )

    body = html.Tbody(body_rows)
    return html.Table(
        [header, body],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontFamily": FONT_SANS,
            "fontSize": "14px",
        },
    )


def _build_exceptions_list(exceptions):
    """Build a compact top-exceptions table as a Dash html.Table."""
    if not exceptions:
        return html.P(
            "No exceptions for the current filters.",
            style={
                "fontFamily": FONT_SANS,
                "fontSize": "14px",
                "color": TEXT_SECONDARY,
                "padding": "12px 0",
            },
        )

    header = html.Thead(
        html.Tr(
            [
                html.Th("Item Name", style=th_style()),
                html.Th("Retailers", style=th_style()),
                html.Th("Stores", style=th_style(align="right")),
                html.Th("Max Weeks Silent", style=th_style(align="right")),
            ]
        ),
    )

    body_rows = []
    for i, exc in enumerate(exceptions):
        bg = CANVAS if i % 2 == 0 else WHITE
        weeks_color = TOKYO_40 if exc["weeks_silent"] > 12 else INK
        body_rows.append(
            html.Tr(
                [
                    html.Td(exc["item_name"], style=td_style(bg=bg)),
                    html.Td(exc.get("retailer", ""), style=td_style(bg=bg)),
                    html.Td(
                        fmt_number(exc.get("stores", 0)),
                        style=td_style(bg=bg, align="right"),
                    ),
                    html.Td(
                        str(exc["weeks_silent"]),
                        style=td_style(bg=bg, align="right", color=weeks_color),
                    ),
                ]
            )
        )

    body = html.Tbody(body_rows)
    return html.Table(
        [header, body],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontFamily": FONT_SANS,
            "fontSize": "14px",
        },
    )


# ── Layout ──


def layout():
    """Return the Scorecard view component tree."""
    return html.Div(
        [
            # Hero metric
            html.Div(
                [
                    html.Div(
                        id="sc-hero-pct",
                        className="hero-number",
                    ),
                    html.P(
                        "of authorized item-store pairs currently scanning",
                        style={
                            "fontFamily": FONT_SANS,
                            "fontSize": "17px",
                            "color": TEXT_SECONDARY,
                            "marginTop": "8px",
                            "marginBottom": "4px",
                        },
                    ),
                    html.Div(
                        id="sc-hero-trend",
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
            # Headline insight cards (visible without scrolling)
            html.Div(id="sc-headline-cards"),
            # Retailer summary table
            html.Div(
                [
                    html.H3(
                        "Retailer Summary",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": INK,
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(id="sc-retailer-table"),
                ],
                style={"marginBottom": "40px"},
            ),
            # Product line summary table
            html.Div(
                [
                    html.H3(
                        "Product Line Summary",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": INK,
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(id="sc-product-line-table"),
                ],
                style={"marginBottom": "40px"},
            ),
            # Top exceptions
            html.Div(
                [
                    html.H3(
                        "Top Exceptions",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": INK,
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(id="sc-exceptions-list"),
                ],
                style={"marginBottom": "40px"},
            ),
            # Annotation callout
            html.Div(id="sc-annotation"),
            # Export buttons
            html.Div(
                [
                    html.Button(
                        "Print",
                        id="sc-print-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": "transparent",
                            "color": CHICAGO_20,
                            "border": f"1px solid {CHICAGO_20}",
                            "padding": "10px 24px",
                            "borderRadius": "2px",
                            "fontFamily": FONT_SANS,
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "marginRight": "12px",
                        },
                    ),
                    html.Button(
                        "Download PDF",
                        id="sc-download-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": CHICAGO_20,
                            "color": WHITE,
                            "border": "none",
                            "padding": "10px 24px",
                            "borderRadius": "2px",
                            "fontFamily": FONT_SANS,
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                        },
                    ),
                    dcc.Download(id="sc-pdf-download"),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "flex-end",
                    "marginTop": "24px",
                },
            ),
            # Error area for PDF generation failures
            html.Div(id="sc-pdf-error"),
        ],
    )


# ── Callbacks ──


@callback(
    Output("sc-hero-pct", "children"),
    Output("sc-hero-trend", "children"),
    Output("sc-hero-trend", "style"),
    Output("sc-headline-cards", "children"),
    Output("sc-retailer-table", "children"),
    Output("sc-product-line-table", "children"),
    Output("sc-exceptions-list", "children"),
    Output("sc-annotation", "children"),
    Input("filter-state", "data"),
    Input("main-tabs", "value"),
)
def _update_scorecard(filter_json, active_tab):
    """Recompute all scorecard elements when filters change."""
    if active_tab != "scorecard":
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )
    filters = json.loads(filter_json) if filter_json else {}
    data = _compute_scorecard_data(filters)

    # Hero
    hero_text = fmt_pct(data["hero_pct"], 1)

    delta = data["hero_delta"]
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

    # Tables
    retailer_table = _build_retailer_table(data["retailer_rows"])
    product_line_table = _build_product_line_table(data["product_line_rows"])
    exceptions_list = _build_exceptions_list(data["top_exceptions"])

    # Headline insight cards (above tables, no scroll needed)
    headline_cards = []
    if data["retailer_rows"]:
        widest = max(data["retailer_rows"], key=lambda r: r["addressable"] - r["carrying"])
        gap = widest["addressable"] - widest["carrying"]
        if gap > 0:
            gap_pct = 1 - widest["penetration"]
            headline_cards.append(
                stat_card(
                    f"{gap_pct * 100:.0f}%",
                    f"widest gap — {widest['name']}. {fmt_number(gap)} pairs not scanning.",
                )
            )
    if data["product_line_rows"]:
        weakest = min(data["product_line_rows"], key=lambda r: r["penetration"])
        if weakest["penetration"] < 0.95:
            headline_cards.append(
                stat_card(
                    fmt_pct(weakest["penetration"]),
                    f"lowest penetration — {weakest['name']}",
                )
            )
    headline = stat_card_row(headline_cards) if headline_cards else []

    # Bottom annotations as stat cards
    annotations = []
    unfiltered = unfiltered_data_callout(filters)
    if unfiltered:
        annotations.append(unfiltered)

    bottom_cards = []
    if data["retailer_rows"]:
        declining = [r for r in data["retailer_rows"] if r["delta"] < -0.02]
        if declining:
            names = ", ".join(r["name"] for r in declining[:3])
            bottom_cards.append(
                stat_card(
                    str(len(declining)),
                    f"retailers declining QoQ — {names}",
                )
            )

    if data["top_exceptions"]:
        worst = data["top_exceptions"][0]
        bottom_cards.append(
            stat_card(
                f"{worst['weeks_silent']} wks",
                f"longest silence — {worst['item_name']} at {worst['retailer']}",
            )
        )

    if bottom_cards:
        annotations.append(stat_card_row(bottom_cards))

    return (
        hero_text,
        trend_text,
        trend_style,
        headline,
        retailer_table,
        product_line_table,
        exceptions_list,
        annotations,
    )


@callback(
    Output("sc-pdf-download", "data"),
    Output("sc-pdf-error", "children"),
    Input("sc-download-btn", "n_clicks"),
    State("filter-state", "data"),
    prevent_initial_call=True,
)
def _download_pdf(n_clicks, filter_json):
    """Generate and trigger PDF download."""
    if not n_clicks:
        return no_update, no_update

    filters = json.loads(filter_json) if filter_json else {}
    data = _compute_scorecard_data(filters)

    try:
        from app.pdf import generate_scorecard_pdf

        pdf_bytes = generate_scorecard_pdf(data)
        return dcc.send_bytes(pdf_bytes, "distribution-scorecard.pdf"), []
    except RuntimeError as exc:
        return no_update, error_banner(str(exc))
    except Exception as exc:
        return no_update, error_banner(f"PDF generation failed: {exc}")


clientside_callback(
    "function(n) { if (n) { window.print(); } return ''; }",
    Output("sc-print-btn", "title"),
    Input("sc-print-btn", "n_clicks"),
    prevent_initial_call=True,
)
