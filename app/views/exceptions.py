"""Exceptions view — authorized-but-not-scanning AG Grid table with CSV export."""

import json

import dash_ag_grid as dag
import pandas as pd
from cinderhaven_store_universe.constants import SKU_NAMES
from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import filter_auth
from app.components import (
    annotation_callout,
    dark_callout_card,
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
    TOKYO_20,
    TOKYO_40,
    WHITE,
    fmt_number,
)
from app.data import DEMO_AS_OF_DATE, LAST_SCAN, PL_NAMES, STORES
from app.export import export_csv

_PL_NAMES = PL_NAMES

# ── Silence threshold: more than 4 weeks without a scan ──
SILENCE_THRESHOLD_WEEKS = 4


# ── Helpers ──


def sku_to_item_name(sku_id):
    """Look up display name from the store universe SKU_NAMES mapping."""
    return SKU_NAMES.get(sku_id, sku_id)


def sku_to_product_line(sku_id):
    """Extract the full product line name from a SKU ID."""
    line_code = sku_id.split("-")[1]
    return _PL_NAMES.get(line_code, line_code)


def _quarter_to_weeks(quarter_str):
    """Convert 'Q1 2025' to a set of week strings like {'2025-W01', ..., '2025-W13'}.

    Q1=W01-W13, Q2=W14-W26, Q3=W27-W39, Q4=W40-W52.
    """
    parts = quarter_str.split()
    q = int(parts[0][1])
    year = int(parts[1])
    boundaries = {1: (1, 13), 2: (14, 26), 3: (27, 39), 4: (40, 52)}
    start_w, end_w = boundaries[q]
    return {f"{year}-W{w:02d}" for w in range(start_w, end_w + 1)}


def _week_to_index(week_str):
    """Convert 'YYYY-Wnn' to a sortable integer (year * 100 + week_num)."""
    parts = week_str.split("-W")
    return int(parts[0]) * 100 + int(parts[1])


def _demo_as_of_week_index():
    """Return the week index for DEMO_AS_OF_DATE (2025-W52)."""
    iso = DEMO_AS_OF_DATE.isocalendar()
    return iso[0] * 100 + iso[1]


def compute_exceptions(filters):
    """Compute the exception list from filter state.

    An exception is an authorized item-store pair where the last scan
    is more than SILENCE_THRESHOLD_WEEKS before DEMO_AS_OF_DATE.

    Returns:
        tuple: (exception_rows as list of dicts, total_authorized_pairs int)
    """
    auth = filter_auth(
        retailers=filters.get("retailers"),
        product_lines=filters.get("product_lines"),
        sku=filters.get("sku"),
    )
    total_authorized = len(auth)

    if total_authorized == 0:
        return [], 0

    auth_pairs = auth[
        ["sku_id", "store_id", "retailer_id", "product_line", "authorized_date"]
    ].copy()

    merged = auth_pairs.merge(LAST_SCAN, on=["sku_id", "store_id"], how="left")

    # Compute weeks silent (vectorized)
    demo_week_idx = _demo_as_of_week_index()
    demo_year = demo_week_idx // 100
    demo_week = demo_week_idx % 100

    parts = merged["last_scan_week"].str.split("-W", expand=True)
    last_year = pd.to_numeric(parts[0], errors="coerce")
    last_week = pd.to_numeric(parts[1], errors="coerce")
    merged["weeks_silent"] = (
        ((demo_year - last_year) * 52 + (demo_week - last_week)).fillna(104).astype(int)
    )

    # Filter to exceptions: weeks_silent > threshold
    exceptions = merged[merged["weeks_silent"] > SILENCE_THRESHOLD_WEEKS].copy()

    if exceptions.empty:
        return [], total_authorized

    store_info = STORES[["store_id", "retailer_name", "region", "volume_tier"]].drop_duplicates()
    exceptions = exceptions.merge(store_info, on="store_id", how="left")

    # Generate item names and product line names
    exceptions["item_name"] = exceptions["sku_id"].apply(sku_to_item_name)
    exceptions["product_line_name"] = exceptions["sku_id"].apply(sku_to_product_line)

    # Format last_scan_date for display
    exceptions["last_scan_date"] = exceptions["last_scan_week"].fillna("Never")

    # Select and order columns for the grid
    result = exceptions[
        [
            "sku_id",
            "item_name",
            "product_line_name",
            "retailer_name",
            "store_id",
            "region",
            "authorized_date",
            "last_scan_date",
            "weeks_silent",
            "volume_tier",
        ]
    ].copy()

    result.columns = [
        "sku_id",
        "item_name",
        "product_line",
        "retailer_name",
        "store_id",
        "region",
        "authorized_date",
        "last_scan_date",
        "weeks_silent",
        "volume_tier",
    ]

    # Sort by weeks_silent descending
    result = result.sort_values("weeks_silent", ascending=False)

    return result.to_dict("records"), total_authorized


def compute_summary_stats(exception_rows, total_authorized):
    """Compute summary statistics for the exception list.

    Returns:
        dict with keys: total_exceptions, unique_stores, avg_weeks_silent,
        top_retailers (list of (name, count) tuples), exception_pct.
    """
    if not exception_rows:
        return {
            "total_exceptions": 0,
            "unique_stores": 0,
            "avg_weeks_silent": 0,
            "top_retailers": [],
            "exception_pct": 0.0,
        }

    df = pd.DataFrame(exception_rows)
    total_exceptions = len(df)
    unique_stores = df["store_id"].nunique()
    avg_weeks_silent = df["weeks_silent"].mean()

    # Top 3 retailers by exception count
    retailer_counts = df.groupby("retailer_name").size().sort_values(ascending=False).head(3)
    top_retailers = list(retailer_counts.items())

    exception_pct = total_exceptions / total_authorized if total_authorized > 0 else 0.0

    return {
        "total_exceptions": total_exceptions,
        "unique_stores": unique_stores,
        "avg_weeks_silent": round(avg_weeks_silent, 1),
        "top_retailers": top_retailers,
        "exception_pct": exception_pct,
    }


# ── AG Grid column definitions ──

_COLUMN_DEFS = [
    {
        "field": "item_name",
        "headerName": "Item",
        "flex": 2,
        "minWidth": 220,
        "tooltipField": "item_name",
    },
    {
        "field": "retailer_name",
        "headerName": "Retailer",
        "flex": 1,
        "minWidth": 140,
        "tooltipField": "retailer_name",
    },
    {
        "field": "store_id",
        "headerName": "Store",
        "width": 90,
    },
    {
        "field": "authorized_date",
        "headerName": "Authorized",
        "width": 110,
    },
    {
        "field": "last_scan_date",
        "headerName": "Last Scan",
        "width": 110,
    },
    {
        "field": "weeks_silent",
        "headerName": "Weeks Silent",
        "width": 120,
        "sort": "desc",
        "cellStyle": {
            "styleConditions": [
                {
                    "condition": "params.value > 12",
                    "style": {"color": TOKYO_40, "fontWeight": "bold"},
                },
                {
                    "condition": "params.value > 8",
                    "style": {"fontWeight": "bold"},
                },
            ],
        },
    },
]


def _build_sku_summary(exception_rows):
    """Build a summary table grouped by SKU — surfaces 'this item is a problem everywhere'."""
    if not exception_rows:
        return None

    df = pd.DataFrame(exception_rows)
    summary = (
        df.groupby("item_name")
        .agg(
            exceptions=("store_id", "size"),
            retailers=("retailer_name", "nunique"),
            avg_weeks=("weeks_silent", "mean"),
        )
        .sort_values("exceptions", ascending=False)
        .reset_index()
    )

    header = html.Thead(
        html.Tr(
            [
                html.Th("Item", style=th_style()),
                html.Th("Exceptions", style=th_style(align="right")),
                html.Th("Retailers", style=th_style(align="right")),
                html.Th("Avg Weeks Silent", style=th_style(align="right")),
            ]
        ),
    )

    body_rows = []
    for i, row in summary.iterrows():
        bg = CANVAS if i % 2 == 0 else WHITE
        weeks_color = TOKYO_40 if row["avg_weeks"] > 12 else INK
        body_rows.append(
            html.Tr(
                [
                    html.Td(
                        row["item_name"],
                        style=td_style(bg=bg),
                    ),
                    html.Td(
                        fmt_number(int(row["exceptions"])),
                        style=td_style(bg=bg, align="right"),
                    ),
                    html.Td(
                        str(int(row["retailers"])),
                        style=td_style(bg=bg, align="right"),
                    ),
                    html.Td(
                        f"{row['avg_weeks']:.0f}",
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
    """Return the Exceptions view component tree."""
    return html.Div(
        [
            # Summary stats area
            html.Div(id="ex-summary-stats"),
            # Annotation callout area
            html.Div(id="ex-annotation"),
            # SKU summary roll-up
            html.Div(
                [
                    html.H3(
                        "Exceptions by Item",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": INK,
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(id="ex-sku-summary"),
                ],
                style={"marginBottom": "40px"},
            ),
            # Download CSV button + detail grid
            html.Div(
                [
                    html.H3(
                        "Exception Detail",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": INK,
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(
                        [
                            html.Button(
                                "Download CSV",
                                id="ex-download-btn",
                                n_clicks=0,
                                style={
                                    "backgroundColor": CHICAGO_20,
                                    "color": WHITE,
                                    "border": "none",
                                    "padding": "8px 20px",
                                    "borderRadius": "2px",
                                    "fontFamily": FONT_SANS,
                                    "fontSize": "14px",
                                    "fontWeight": "600",
                                    "cursor": "pointer",
                                    "marginBottom": "12px",
                                },
                            ),
                            dcc.Download(id="ex-download"),
                        ],
                        style={"display": "flex", "justifyContent": "flex-end"},
                    ),
                ],
            ),
            # AG Grid detail table with loading overlay
            dcc.Loading(
                html.Div(
                    dag.AgGrid(
                        id="ex-grid",
                        columnDefs=_COLUMN_DEFS,
                        rowData=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        dashGridOptions={
                            "pagination": True,
                            "paginationPageSize": 50,
                            "rowSelection": {"mode": "singleRow"},
                            "animateRows": True,
                            "domLayout": "autoHeight",
                            "tooltipShowDelay": 300,
                        },
                        style={"width": "100%"},
                        className="ag-theme-alpine",
                    ),
                    **{"aria-label": "Exception detail — authorized items not scanning"},
                ),
                type="default",
                color=CHICAGO_20,
            ),
            # Inline detail card (shown on row selection)
            html.Div(id="ex-detail-card"),
            # Hidden store for exception data (avoids recomputing for CSV)
            dcc.Store(id="ex-data-store", data="[]"),
        ],
    )


# ── Callbacks ──


@callback(
    Output("ex-grid", "rowData"),
    Output("ex-summary-stats", "children"),
    Output("ex-annotation", "children"),
    Output("ex-sku-summary", "children"),
    Output("ex-data-store", "data"),
    Input("filter-state", "data"),
    Input("main-tabs", "value"),
)
def _update_exceptions_view(filter_json, active_tab):
    """Recompute exception list when filters change."""
    if active_tab != "exceptions":
        return no_update, no_update, no_update, no_update, no_update
    filters = json.loads(filter_json) if filter_json else {}

    exception_rows, total_authorized = compute_exceptions(filters)
    stats = compute_summary_stats(exception_rows, total_authorized)

    # Summary stats display
    if stats["total_exceptions"] > 0:
        top_retailers_text = ", ".join(
            f"{name} ({fmt_number(count)})" for name, count in stats["top_retailers"]
        )
        summary = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(
                                    fmt_number(stats["total_exceptions"]),
                                    style={
                                        "fontFamily": FONT_SERIF,
                                        "fontSize": "36px",
                                        "fontWeight": "700",
                                        "color": INK,
                                        "letterSpacing": "-0.02em",
                                    },
                                ),
                                html.Span(
                                    f" exceptions across {fmt_number(stats['unique_stores'])}"
                                    " stores",
                                    style={
                                        "fontFamily": FONT_SANS,
                                        "fontSize": "17px",
                                        "color": TEXT_SECONDARY,
                                        "marginLeft": "8px",
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            [
                                html.Span(
                                    f"Avg. {stats['avg_weeks_silent']} weeks silent",
                                    style={
                                        "fontFamily": FONT_SANS,
                                        "fontSize": "15px",
                                        "color": TOKYO_20,
                                        "fontWeight": "600",
                                    },
                                ),
                            ],
                            style={"marginTop": "4px"},
                        ),
                        html.Div(
                            [
                                html.Span(
                                    "Top retailers: ",
                                    style={
                                        "fontFamily": FONT_SANS,
                                        "fontSize": "14px",
                                        "color": TEXT_SECONDARY,
                                    },
                                ),
                                html.Span(
                                    top_retailers_text,
                                    style={
                                        "fontFamily": FONT_SANS,
                                        "fontSize": "14px",
                                        "color": INK,
                                        "fontWeight": "600",
                                    },
                                ),
                            ],
                            style={"marginTop": "4px"},
                        ),
                    ],
                    style={
                        "padding": "24px 0",
                        "marginBottom": "16px",
                    },
                ),
            ],
        )
    else:
        summary = html.Div(
            html.P(
                "No exceptions found for the current filters.",
                style={
                    "fontFamily": FONT_SANS,
                    "fontSize": "17px",
                    "color": TEXT_SECONDARY,
                    "padding": "24px 0",
                },
            ),
        )

    # Annotation callouts
    annotations = []
    if stats["exception_pct"] > 0.10:
        pct_display = f"{stats['exception_pct'] * 100:.1f}%"
        annotations.append(
            annotation_callout(
                f"{fmt_number(stats['total_exceptions'])} of "
                f"{fmt_number(total_authorized)} authorized item-store pairs "
                f"({pct_display}) haven't scanned recently — distribution "
                f"gaps may be widening."
            )
        )

    if exception_rows:
        never_count = sum(1 for r in exception_rows if r.get("last_scan_date") == "Never")
        if never_count > 0:
            annotations.append(
                annotation_callout(
                    f"{fmt_number(never_count)} item-store pairs have never scanned "
                    f"— these authorizations may exist on paper only."
                )
            )

        if stats["top_retailers"] and stats["total_exceptions"] > 0:
            top_name, top_count = stats["top_retailers"][0]
            top_share = top_count / stats["total_exceptions"]
            if top_share > 0.30:
                annotations.append(
                    annotation_callout(
                        f"{top_name} accounts for {top_share * 100:.0f}% of all "
                        f"exceptions — a concentrated problem worth a targeted fix."
                    )
                )

    unfiltered = unfiltered_data_callout(filters)
    if unfiltered:
        annotations.insert(0, unfiltered)

    # SKU summary roll-up
    sku_summary = _build_sku_summary(exception_rows)

    return (
        exception_rows,
        summary,
        annotations,
        sku_summary or [],
        json.dumps(exception_rows),
    )


@callback(
    Output("ex-download", "data"),
    Input("ex-download-btn", "n_clicks"),
    State("ex-data-store", "data"),
    prevent_initial_call=True,
)
def _download_csv(n_clicks, data_json):
    """Generate and trigger CSV download."""
    if not n_clicks:
        return no_update

    rows = json.loads(data_json) if data_json else []
    if not rows:
        return no_update

    csv_content = export_csv(rows)
    return dict(content=csv_content, filename="exceptions.csv", type="text/csv")


@callback(
    Output("ex-detail-card", "children"),
    Input("ex-grid", "selectedRows"),
    prevent_initial_call=True,
)
def _show_detail_card(selected_rows):
    """Show an inline detail card for the selected grid row."""
    if not selected_rows:
        return []

    row = selected_rows[0]

    return dark_callout_card(
        title=f"{row.get('sku_id', '')} — {row.get('item_name', '')}",
        subtitle=f"{row.get('retailer_name', '')} / Store {row.get('store_id', '')}",
        rows=[
            {"label": "Product Line", "value": str(row.get("product_line", ""))},
            {"label": "Region", "value": str(row.get("region", ""))},
            {"label": "Authorized Date", "value": str(row.get("authorized_date", ""))},
            {"label": "Last Scan Date", "value": str(row.get("last_scan_date", ""))},
            {"label": "Weeks Silent", "value": str(row.get("weeks_silent", ""))},
            {"label": "Store Volume Tier", "value": str(row.get("volume_tier", ""))},
        ],
    )
