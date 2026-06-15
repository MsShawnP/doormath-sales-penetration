"""Scorecard view — one-page distribution summary with PDF export.

Shows a hero penetration metric, retailer summary table, product line summary
table, and top 10 exceptions.  The "Download PDF" button triggers WeasyPrint
generation via ``app.pdf``.
"""

import json

from cinderhaven_store_universe import get_auth_matrix, get_scan_data, get_stores
from cinderhaven_store_universe.constants import PRODUCT_LINES, RETAILERS
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import (
    calc_acv_pct,
    calc_penetration_rate,
    calc_period_delta,
    calc_tdp,
    quarter_to_weeks,
)
from app.components import annotation_callout, error_banner
from app.constants import (
    CANVAS,
    CHICAGO_20,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    INK,
    TEXT_SECONDARY,
    TOKYO_40,
    TREND_DOWN,
    TREND_UP,
    WHITE,
    fmt_number,
    fmt_pct,
)
from app.views.exceptions import compute_exceptions, sku_to_item_name

# ── Data loading (cached at module level) ──

_stores = get_stores()
_auth = get_auth_matrix()
_scans = get_scan_data()

# Retailer name lookup
_RET_NAMES = {ret_id: info["name"] for ret_id, info in RETAILERS.items()}

# Product line name lookup
_PL_NAMES = {prefix: info["name"] for prefix, info in PRODUCT_LINES.items()}
_PL_PREFIXES = list(PRODUCT_LINES.keys())


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


# ── Core data computation ──


def _compute_scorecard_data(filters):
    """Compute all data needed for both the screen scorecard and the PDF.

    Returns a dict with keys:
        hero_pct, hero_delta, retailer_rows, product_line_rows,
        top_exceptions, quarter_label, generation_date
    """
    retailers = filters.get("retailers", [])
    product_lines = filters.get("product_lines", [])
    sku = filters.get("sku")
    end_q = filters.get("end_quarter", "Q4 2025")
    prior_q = _prior_quarter(end_q)

    # ── Hero metric ──
    hero_pct = calc_penetration_rate(
        _auth,
        _scans,
        end_q,
        retailers=retailers or None,
        product_lines=product_lines or None,
        sku=sku,
    )
    if prior_q:
        prior_pct = calc_penetration_rate(
            _auth,
            _scans,
            prior_q,
            retailers=retailers or None,
            product_lines=product_lines or None,
            sku=sku,
        )
        hero_delta = calc_period_delta(hero_pct, prior_pct)
    else:
        hero_delta = 0.0

    # ── Retailer summary rows ──
    retailer_rows = []
    active_retailers = retailers if retailers else list(RETAILERS.keys())
    for ret_id in active_retailers:
        ret_name = _RET_NAMES.get(ret_id, ret_id)
        ret_filter = [ret_id]

        pen = calc_penetration_rate(
            _auth,
            _scans,
            end_q,
            retailers=ret_filter,
            product_lines=product_lines or None,
            sku=sku,
        )
        acv = calc_acv_pct(
            _stores,
            _auth,
            _scans,
            end_q,
            retailers=ret_filter,
            product_lines=product_lines or None,
            sku=sku,
        )
        tdp = calc_tdp(
            _stores,
            _auth,
            _scans,
            end_q,
            retailers=ret_filter,
            product_lines=product_lines or None,
        )

        # Compute carrying / addressable counts
        auth_filtered = _auth[_auth["authorized"] & _auth["retailer_id"].isin(ret_filter)]
        if product_lines:
            auth_filtered = auth_filtered[
                auth_filtered["sku_id"].str.split("-").str[1].isin(product_lines)
            ]
        if sku:
            auth_filtered = auth_filtered[auth_filtered["sku_id"] == sku]
        addressable = auth_filtered["store_id"].nunique()

        weeks = quarter_to_weeks(end_q)
        auth_store_ids = auth_filtered["store_id"].unique()
        auth_sku_ids = auth_filtered["sku_id"].unique()
        quarter_scans = _scans[
            (_scans["week"].isin(weeks))
            & _scans["scanned"]
            & _scans["store_id"].isin(auth_store_ids)
            & _scans["sku_id"].isin(auth_sku_ids)
        ]
        carrying = quarter_scans["store_id"].nunique()

        # Prior quarter delta
        if prior_q:
            prior_pen = calc_penetration_rate(
                _auth,
                _scans,
                prior_q,
                retailers=ret_filter,
                product_lines=product_lines or None,
                sku=sku,
            )
            delta = calc_period_delta(pen, prior_pen)
        else:
            delta = 0.0

        retailer_rows.append(
            {
                "name": ret_name,
                "carrying": carrying,
                "addressable": addressable,
                "penetration": pen,
                "acv_pct": acv,
                "tdp": tdp,
                "delta": delta,
            }
        )

    # Sort by addressable descending
    retailer_rows.sort(key=lambda r: r["addressable"], reverse=True)

    # ── Product line summary rows ──
    product_line_rows = []
    active_pls = product_lines if product_lines else _PL_PREFIXES
    for pl_prefix in active_pls:
        pl_name = _PL_NAMES.get(pl_prefix, pl_prefix)
        pl_filter = [pl_prefix]

        pen = calc_penetration_rate(
            _auth,
            _scans,
            end_q,
            retailers=retailers or None,
            product_lines=pl_filter,
            sku=sku,
        )
        acv = calc_acv_pct(
            _stores,
            _auth,
            _scans,
            end_q,
            retailers=retailers or None,
            product_lines=pl_filter,
            sku=sku,
        )

        # Carrying / addressable for this product line
        auth_filtered = _auth[_auth["authorized"]].copy()
        if retailers:
            auth_filtered = auth_filtered[auth_filtered["retailer_id"].isin(retailers)]
        auth_filtered = auth_filtered[auth_filtered["sku_id"].str.split("-").str[1].isin(pl_filter)]
        if sku:
            auth_filtered = auth_filtered[auth_filtered["sku_id"] == sku]
        addressable = auth_filtered["store_id"].nunique()

        weeks = quarter_to_weeks(end_q)
        auth_store_ids = auth_filtered["store_id"].unique()
        auth_sku_ids = auth_filtered["sku_id"].unique()
        quarter_scans = _scans[
            (_scans["week"].isin(weeks))
            & _scans["scanned"]
            & _scans["store_id"].isin(auth_store_ids)
            & _scans["sku_id"].isin(auth_sku_ids)
        ]
        carrying = quarter_scans["store_id"].nunique()

        # Prior quarter delta
        if prior_q:
            prior_pen = calc_penetration_rate(
                _auth,
                _scans,
                prior_q,
                retailers=retailers or None,
                product_lines=pl_filter,
                sku=sku,
            )
            delta = calc_period_delta(pen, prior_pen)
        else:
            delta = 0.0

        product_line_rows.append(
            {
                "name": pl_name,
                "carrying": carrying,
                "addressable": addressable,
                "penetration": pen,
                "acv_pct": acv,
                "delta": delta,
            }
        )

    # Sort by addressable descending
    product_line_rows.sort(key=lambda r: r["addressable"], reverse=True)

    # ── Top exceptions ──
    exception_rows, _ = compute_exceptions(filters)
    top_exceptions = []
    for row in exception_rows[:10]:
        top_exceptions.append(
            {
                "sku_id": row["sku_id"],
                "item_name": row.get("item_name", sku_to_item_name(row["sku_id"])),
                "retailer": row.get("retailer_name", ""),
                "weeks_silent": row.get("weeks_silent", 0),
            }
        )

    from app.constants import DEMO_AS_OF_DATE

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
                html.Th("Retailer", style=_th_style()),
                html.Th("Doors Carrying / Addressable", style=_th_style()),
                html.Th("Penetration %", style=_th_style(align="right")),
                html.Th("ACV%", style=_th_style(align="right")),
                html.Th("TDP", style=_th_style(align="right")),
                html.Th("Δ vs Prior Qtr", style=_th_style(align="right")),
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
                    html.Td(row["name"], style=_td_style(bg=bg)),
                    html.Td(
                        f"{fmt_number(row['carrying'])} / {fmt_number(row['addressable'])}",
                        style=_td_style(bg=bg),
                    ),
                    html.Td(fmt_pct(row["penetration"]), style=_td_style(bg=bg, align="right")),
                    html.Td(fmt_pct(row["acv_pct"]), style=_td_style(bg=bg, align="right")),
                    html.Td(f"{row['tdp']:.1f}", style=_td_style(bg=bg, align="right")),
                    html.Td(
                        delta_text,
                        style=_td_style(bg=bg, align="right", color=delta_color),
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
                html.Th("Product Line", style=_th_style()),
                html.Th("Doors Carrying / Addressable", style=_th_style()),
                html.Th("Penetration %", style=_th_style(align="right")),
                html.Th("ACV%", style=_th_style(align="right")),
                html.Th("Δ vs Prior Qtr", style=_th_style(align="right")),
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
                    html.Td(row["name"], style=_td_style(bg=bg)),
                    html.Td(
                        f"{fmt_number(row['carrying'])} / {fmt_number(row['addressable'])}",
                        style=_td_style(bg=bg),
                    ),
                    html.Td(fmt_pct(row["penetration"]), style=_td_style(bg=bg, align="right")),
                    html.Td(fmt_pct(row["acv_pct"]), style=_td_style(bg=bg, align="right")),
                    html.Td(
                        delta_text,
                        style=_td_style(bg=bg, align="right", color=delta_color),
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
                html.Th("SKU ID", style=_th_style()),
                html.Th("Item Name", style=_th_style()),
                html.Th("Retailer", style=_th_style()),
                html.Th("Weeks Silent", style=_th_style(align="right")),
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
                    html.Td(exc["sku_id"], style=_td_style(bg=bg)),
                    html.Td(exc["item_name"], style=_td_style(bg=bg)),
                    html.Td(exc["retailer"], style=_td_style(bg=bg)),
                    html.Td(
                        str(exc["weeks_silent"]),
                        style=_td_style(bg=bg, align="right", color=weeks_color),
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


# ── Style helpers ──


def _th_style(align="left"):
    """Return inline style dict for table header cells."""
    return {
        "textAlign": align,
        "padding": "8px 12px",
        "borderBottom": f"2px solid {INK}",
        "fontFamily": FONT_SANS,
        "fontSize": "13px",
        "fontWeight": "600",
        "color": INK,
        "whiteSpace": "nowrap",
    }


def _td_style(bg=WHITE, align="left", color=None):
    """Return inline style dict for table data cells."""
    style = {
        "textAlign": align,
        "padding": "6px 12px",
        "borderBottom": f"1px solid {GRIDLINE}",
        "fontFamily": FONT_SANS,
        "fontSize": "14px",
        "color": color or INK,
        "backgroundColor": bg,
    }
    return style


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
                        "of addressable doors carrying at least one Cinderhaven item",
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
            # Download PDF button
            html.Div(
                [
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
    Output("sc-retailer-table", "children"),
    Output("sc-product-line-table", "children"),
    Output("sc-exceptions-list", "children"),
    Output("sc-annotation", "children"),
    Input("filter-state", "data"),
)
def _update_scorecard(filter_json):
    """Recompute all scorecard elements when filters change."""
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

    # Annotation
    annotation = []
    if data["top_exceptions"]:
        worst = data["top_exceptions"][0]
        annotation = annotation_callout(
            f"Longest silence: {worst['item_name']} at {worst['retailer']} "
            f"({worst['weeks_silent']} weeks) — authorized but not scanning."
        )

    return (
        hero_text,
        trend_text,
        trend_style,
        retailer_table,
        product_line_table,
        exceptions_list,
        annotation,
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
