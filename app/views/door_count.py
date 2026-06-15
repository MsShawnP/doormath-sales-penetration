"""Door Count view — hero metric, retailer bar chart, product line stacked bar,
click-to-pin callout cards, and auth gap narrative annotations."""

import json

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update

from cinderhaven_store_universe import get_stores, get_auth_matrix, get_scan_data
from cinderhaven_store_universe.constants import PRODUCT_LINES

from app.constants import (
    AUTH_BAR, SCAN_BAR, TEAL_SEQUENTIAL,
    TREND_UP, TREND_DOWN, INK, TEXT_SECONDARY,
    FONT_SANS, FONT_SERIF,
    fmt_pct, fmt_number,
)
from app.charts import economist_layout, CHART_CONFIG
from app.components import dark_callout_card, annotation_callout


# ── Data loading (cached at module level) ──

_stores = get_stores()
_auth = get_auth_matrix()
_scans = get_scan_data()

# Pre-extract product line prefix from sku_id for filtering
_auth = _auth.copy()
_auth['product_line'] = _auth['sku_id'].str.split('-').str[1]

_scans = _scans.copy()
_scans['product_line'] = _scans['sku_id'].str.split('-').str[1]

# Product line name lookup
_PL_NAMES = {prefix: info['name'] for prefix, info in PRODUCT_LINES.items()}


# ── Quarter / week helpers ──

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


def _quarter_range_weeks(start_q, end_q):
    """Return all weeks covered by the quarter range [start_q, end_q]."""
    all_quarters = [
        f"Q{q} {y}" for y in [2024, 2025] for q in [1, 2, 3, 4]
    ]
    # Find indices
    try:
        si = all_quarters.index(start_q)
        ei = all_quarters.index(end_q)
    except ValueError:
        return set()
    weeks = set()
    for q in all_quarters[si:ei + 1]:
        weeks |= _quarter_to_weeks(q)
    return weeks


def _prior_quarter(quarter_str):
    """Return the quarter string one quarter before the given quarter."""
    all_quarters = [
        f"Q{q} {y}" for y in [2024, 2025] for q in [1, 2, 3, 4]
    ]
    try:
        idx = all_quarters.index(quarter_str)
    except ValueError:
        return None
    if idx == 0:
        return None
    return all_quarters[idx - 1]


# ── Data computation helpers ──

def _filter_data(filters):
    """Apply filter-state dict to auth and scan DataFrames. Return filtered copies."""
    retailers = filters.get('retailers', [])
    product_lines = filters.get('product_lines', [])
    sku = filters.get('sku')

    auth = _auth.copy()
    scans = _scans.copy()

    if retailers:
        auth = auth[auth['retailer_id'].isin(retailers)]
        scans = scans[scans['store_id'].isin(auth['store_id'].unique())]

    if product_lines:
        auth = auth[auth['product_line'].isin(product_lines)]
        scans = scans[scans['product_line'].isin(product_lines)]

    if sku:
        auth = auth[auth['sku_id'] == sku]
        scans = scans[scans['sku_id'] == sku]

    return auth, scans


def _compute_penetration(auth, scans, weeks):
    """Compute penetration: carrying_doors / addressable_doors.

    addressable_doors: unique stores with at least one authorized item.
    carrying_doors: addressable stores that scanned at least once in the given weeks.
    """
    auth_only = auth[auth['authorized']]
    addressable_stores = set(auth_only['store_id'].unique())

    if not addressable_stores or not weeks:
        return 0.0, 0, len(addressable_stores)

    # Scans in the specified weeks for authorized item-store pairs
    auth_pairs = set(zip(auth_only['sku_id'], auth_only['store_id']))
    period_scans = scans[scans['week'].isin(weeks) & scans['scanned']]
    scan_pairs = set(zip(period_scans['sku_id'], period_scans['store_id']))
    # Intersect with authorized pairs
    carrying_pairs = auth_pairs & scan_pairs
    carrying_stores = {pair[1] for pair in carrying_pairs}
    carrying_doors = len(carrying_stores & addressable_stores)
    addressable = len(addressable_stores)

    pct = carrying_doors / addressable if addressable > 0 else 0.0
    return pct, carrying_doors, addressable


def _compute_retailer_bars(auth, scans, weeks):
    """Compute per-retailer authorized vs carrying door counts.

    Returns a list of dicts: retailer_name, authorized_doors, carrying_doors, pct.
    """
    auth_only = auth[auth['authorized']]
    retailers = auth_only[['retailer_id', 'store_id']].drop_duplicates()

    # Map retailer_id to name via stores
    ret_names = _stores[['retailer_id', 'retailer_name']].drop_duplicates()
    retailers = retailers.merge(ret_names, on='retailer_id', how='left')

    # Authorized doors per retailer
    auth_by_ret = retailers.groupby(['retailer_id', 'retailer_name'])['store_id'].nunique().reset_index()
    auth_by_ret.columns = ['retailer_id', 'retailer_name', 'authorized_doors']

    # Carrying doors per retailer
    period_scans = scans[scans['week'].isin(weeks) & scans['scanned']]
    # Only count scans for authorized pairs
    auth_pairs = auth_only[['sku_id', 'store_id', 'retailer_id']].drop_duplicates()
    carrying = period_scans.merge(auth_pairs, on=['sku_id', 'store_id'], how='inner')
    carry_by_ret = carrying.groupby('retailer_id')['store_id'].nunique().reset_index()
    carry_by_ret.columns = ['retailer_id', 'carrying_doors']

    result = auth_by_ret.merge(carry_by_ret, on='retailer_id', how='left')
    result['carrying_doors'] = result['carrying_doors'].fillna(0).astype(int)
    result['pct'] = result['carrying_doors'] / result['authorized_doors']
    result = result.sort_values('authorized_doors', ascending=True)

    return result.to_dict('records')


def _compute_product_line_bars(auth, scans, weeks):
    """Compute per-product-line carrying doors broken down by retailer.

    Returns a dict: {product_line_name: {retailer_name: carrying_doors}}.
    """
    auth_only = auth[auth['authorized']]
    period_scans = scans[scans['week'].isin(weeks) & scans['scanned']]

    # Join auth and scans to identify carrying
    auth_pairs = auth_only[['sku_id', 'store_id', 'retailer_id', 'product_line']].drop_duplicates()
    # Drop product_line from scans before merge to avoid suffixed duplicates
    scan_cols = period_scans[['sku_id', 'store_id']].drop_duplicates()
    carrying = scan_cols.merge(auth_pairs, on=['sku_id', 'store_id'], how='inner')

    if carrying.empty:
        return {}

    ret_names = _stores[['retailer_id', 'retailer_name']].drop_duplicates()
    carrying = carrying.merge(ret_names, on='retailer_id', how='left')

    # Count unique carrying doors per product line per retailer
    grouped = carrying.groupby(['product_line', 'retailer_name'])['store_id'].nunique().reset_index()
    grouped.columns = ['product_line', 'retailer_name', 'carrying_doors']

    result = {}
    for _, row in grouped.iterrows():
        pl_name = _PL_NAMES.get(row['product_line'], row['product_line'])
        if pl_name not in result:
            result[pl_name] = {}
        result[pl_name][row['retailer_name']] = int(row['carrying_doors'])

    return result


def _compute_auth_gaps(auth, scans, weeks):
    """Find retailers where the auth gap exceeds 15% of authorized doors.

    Returns list of annotation strings.
    """
    auth_only = auth[auth['authorized']]
    retailers = auth_only[['retailer_id', 'store_id']].drop_duplicates()
    ret_names = _stores[['retailer_id', 'retailer_name']].drop_duplicates()
    retailers = retailers.merge(ret_names, on='retailer_id', how='left')

    auth_by_ret = retailers.groupby(['retailer_id', 'retailer_name'])['store_id'].nunique().reset_index()
    auth_by_ret.columns = ['retailer_id', 'retailer_name', 'authorized_doors']

    period_scans = scans[scans['week'].isin(weeks) & scans['scanned']]
    auth_pairs = auth_only[['sku_id', 'store_id', 'retailer_id']].drop_duplicates()
    carrying = period_scans.merge(auth_pairs, on=['sku_id', 'store_id'], how='inner')
    carry_by_ret = carrying.groupby('retailer_id')['store_id'].nunique().reset_index()
    carry_by_ret.columns = ['retailer_id', 'carrying_doors']

    merged = auth_by_ret.merge(carry_by_ret, on='retailer_id', how='left')
    merged['carrying_doors'] = merged['carrying_doors'].fillna(0).astype(int)
    merged['gap'] = merged['authorized_doors'] - merged['carrying_doors']
    merged['gap_pct'] = merged['gap'] / merged['authorized_doors']

    # Compute weeks of silence — how many weeks since last scan in the period
    annotations = []
    for _, row in merged[merged['gap_pct'] > 0.15].iterrows():
        gap = int(row['gap'])
        auth_doors = int(row['authorized_doors'])
        name = row['retailer_name']
        # Approximate weeks since last scan: use the total weeks in the period
        n_weeks = len(weeks)
        annotations.append(
            f"{name}: {gap} of {auth_doors} authorized stores haven't scanned "
            f"in {n_weeks}+ weeks — the shelf says no even though the "
            f"retailer said yes."
        )

    return annotations


def _compute_click_detail(auth, scans, weeks, retailer_name):
    """Compute detail card data for a clicked retailer."""
    ret_id_row = _stores[_stores['retailer_name'] == retailer_name].iloc[0]
    ret_id = ret_id_row['retailer_id']

    ret_auth = auth[(auth['retailer_id'] == ret_id) & auth['authorized']]
    addressable = ret_auth['store_id'].nunique()

    auth_pairs = set(zip(ret_auth['sku_id'], ret_auth['store_id']))
    period_scans = scans[scans['week'].isin(weeks) & scans['scanned']]
    scan_pairs = set(zip(period_scans['sku_id'], period_scans['store_id']))
    carrying_pairs = auth_pairs & scan_pairs
    carrying_doors = len({p[1] for p in carrying_pairs})

    items_auth = ret_auth['sku_id'].nunique()
    carrying_items_set = {p[0] for p in carrying_pairs}
    items_carried = len(carrying_items_set)
    items_not_carried = items_auth - items_carried

    pct = carrying_doors / addressable if addressable > 0 else 0.0

    return {
        'retailer_name': retailer_name,
        'carrying_doors': carrying_doors,
        'addressable_doors': addressable,
        'pct': pct,
        'items_carried': items_carried,
        'items_not_carried': items_not_carried,
    }


# ── Chart builders ──

def _build_retailer_chart(bar_data, selected_retailer=None):
    """Build a horizontal grouped bar chart: authorized vs carrying by retailer."""
    retailers = [d['retailer_name'] for d in bar_data]
    auth_counts = [d['authorized_doors'] for d in bar_data]
    carry_counts = [d['carrying_doors'] for d in bar_data]

    # Opacity per bar: dim non-selected when a retailer is pinned
    auth_opacity = []
    carry_opacity = []
    for d in bar_data:
        if selected_retailer and d['retailer_name'] != selected_retailer:
            auth_opacity.append(0.3)
            carry_opacity.append(0.3)
        else:
            auth_opacity.append(1.0)
            carry_opacity.append(1.0)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=retailers,
        x=auth_counts,
        name='Authorized',
        orientation='h',
        marker=dict(color=AUTH_BAR, opacity=auth_opacity),
        text=[fmt_number(v) for v in auth_counts],
        textposition='outside',
        textfont=dict(family=FONT_SANS, size=12, color=INK),
        hoverinfo='skip',
    ))

    fig.add_trace(go.Bar(
        y=retailers,
        x=carry_counts,
        name='Carrying',
        orientation='h',
        marker=dict(color=SCAN_BAR, opacity=carry_opacity),
        text=[fmt_number(v) for v in carry_counts],
        textposition='outside',
        textfont=dict(family=FONT_SANS, size=12, color=INK),
        hoverinfo='skip',
    ))

    fig.update_layout(
        **economist_layout(
            barmode='group',
            title=dict(text='Authorized vs Carrying Doors by Retailer'),
            xaxis=dict(
                showgrid=True,
                gridcolor='#d9d9d9',
                showline=True,
                linecolor='#d9d9d9',
                title='Door Count',
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            ),
            yaxis=dict(
                showgrid=False,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=120, r=60, t=60, b=40),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='left',
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
    # Collect all retailer names across product lines
    all_retailers = set()
    for ret_data in pl_data.values():
        all_retailers.update(ret_data.keys())
    all_retailers = sorted(all_retailers)

    fig = go.Figure()

    for i, retailer in enumerate(all_retailers):
        color = TEAL_SEQUENTIAL[i % len(TEAL_SEQUENTIAL)]
        values = [pl_data.get(pl, {}).get(retailer, 0) for pl in product_lines]
        fig.add_trace(go.Bar(
            y=product_lines,
            x=values,
            name=retailer,
            orientation='h',
            marker=dict(color=color),
            text=[fmt_number(v) if v > 0 else '' for v in values],
            textposition='inside',
            textfont=dict(family=FONT_SANS, size=11, color='white'),
            hoverinfo='skip',
        ))

    fig.update_layout(
        **economist_layout(
            barmode='stack',
            title=dict(text='Carrying Doors by Product Line'),
            xaxis=dict(
                showgrid=True,
                gridcolor='#d9d9d9',
                showline=True,
                linecolor='#d9d9d9',
                title='Carrying Doors',
                tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            ),
            yaxis=dict(
                showgrid=False,
                showline=False,
                tickfont=dict(family=FONT_SANS, size=13, color=INK),
                automargin=True,
            ),
            margin=dict(l=160, r=40, t=60, b=40),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='left',
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
            # Hero metric
            html.Div(
                [
                    html.Div(
                        id='dc-hero-pct',
                        style={
                            'fontFamily': FONT_SERIF,
                            'fontSize': '64px',
                            'fontWeight': '700',
                            'color': INK,
                            'letterSpacing': '-0.02em',
                            'lineHeight': '1',
                        },
                    ),
                    html.P(
                        'of addressable doors carrying at least one Cinderhaven item',
                        style={
                            'fontFamily': FONT_SANS,
                            'fontSize': '17px',
                            'color': TEXT_SECONDARY,
                            'marginTop': '8px',
                            'marginBottom': '4px',
                        },
                    ),
                    html.Div(
                        id='dc-hero-trend',
                        style={
                            'fontFamily': FONT_SANS,
                            'fontSize': '16px',
                            'fontWeight': '600',
                        },
                    ),
                ],
                style={
                    'textAlign': 'center',
                    'padding': '32px 0',
                    'marginBottom': '24px',
                },
            ),

            # Retailer bar chart
            html.Div(
                dcc.Graph(
                    id='dc-retailer-chart',
                    config=CHART_CONFIG,
                ),
                **{'aria-label': 'Authorized versus carrying doors by retailer'},
            ),

            # Click-to-pin callout card area
            html.Div(id='dc-callout-area'),

            # Auth gap annotations
            html.Div(id='dc-auth-gap-annotations'),

            # Product line stacked bar chart
            html.Div(
                dcc.Graph(
                    id='dc-product-line-chart',
                    config=CHART_CONFIG,
                ),
                style={'marginTop': '40px'},
                **{'aria-label': 'Carrying doors by product line and retailer'},
            ),

            # Hidden store for tracking the pinned retailer
            dcc.Store(id='dc-pinned-retailer', data=None),
        ],
    )


# ── Callbacks ──

@callback(
    Output('dc-hero-pct', 'children'),
    Output('dc-hero-trend', 'children'),
    Output('dc-hero-trend', 'style'),
    Output('dc-retailer-chart', 'figure'),
    Output('dc-product-line-chart', 'figure'),
    Output('dc-auth-gap-annotations', 'children'),
    Input('filter-state', 'data'),
)
def _update_door_count_view(filter_json):
    """Recompute all door count view elements when filters change."""
    filters = json.loads(filter_json) if filter_json else {}

    end_q = filters.get('end_quarter', 'Q4 2025')
    start_q = filters.get('start_quarter', 'Q1 2025')

    # Determine weeks for the end quarter (current) and prior quarter
    current_weeks = _quarter_to_weeks(end_q)
    prior_q = _prior_quarter(end_q)
    prior_weeks = _quarter_to_weeks(prior_q) if prior_q else set()

    # Full range weeks for the bar charts
    range_weeks = _quarter_range_weeks(start_q, end_q)

    auth, scans = _filter_data(filters)

    # Hero metric — based on end quarter only
    current_pct, carrying, addressable = _compute_penetration(
        auth, scans, current_weeks
    )
    hero_text = fmt_pct(current_pct, 1)

    # Trend vs prior quarter
    if prior_weeks:
        prior_pct, _, _ = _compute_penetration(auth, scans, prior_weeks)
        delta = current_pct - prior_pct
        if delta > 0:
            trend_text = f"↑ {abs(delta) * 100:.1f} pp from prior quarter"
            trend_style = {
                'fontFamily': FONT_SANS, 'fontSize': '16px', 'fontWeight': '600',
                'color': TREND_UP,
            }
        elif delta < 0:
            trend_text = f"↓ {abs(delta) * 100:.1f} pp from prior quarter"
            trend_style = {
                'fontFamily': FONT_SANS, 'fontSize': '16px', 'fontWeight': '600',
                'color': TREND_DOWN,
            }
        else:
            trend_text = "→ 0.0 pp from prior quarter"
            trend_style = {
                'fontFamily': FONT_SANS, 'fontSize': '16px', 'fontWeight': '600',
                'color': TEXT_SECONDARY,
            }
    else:
        trend_text = ''
        trend_style = {'display': 'none'}

    # Retailer bar chart — uses full range
    bar_data = _compute_retailer_bars(auth, scans, range_weeks)
    retailer_fig = _build_retailer_chart(bar_data)

    # Product line chart — uses full range
    pl_data = _compute_product_line_bars(auth, scans, range_weeks)
    pl_fig = _build_product_line_chart(pl_data)

    # Auth gap annotations — based on end quarter
    gap_texts = _compute_auth_gaps(auth, scans, current_weeks)
    gap_children = [annotation_callout(t) for t in gap_texts] if gap_texts else []

    return hero_text, trend_text, trend_style, retailer_fig, pl_fig, gap_children


@callback(
    Output('dc-pinned-retailer', 'data'),
    Input('dc-retailer-chart', 'clickData'),
    State('dc-pinned-retailer', 'data'),
    prevent_initial_call=True,
)
def _toggle_pinned_retailer(click_data, current_pinned):
    """Toggle the pinned retailer on bar click."""
    if not click_data:
        return no_update

    points = click_data.get('points', [])
    if not points:
        return no_update

    clicked_retailer = points[0].get('y')
    if not clicked_retailer:
        return no_update

    # Toggle: click same retailer to dismiss
    if current_pinned == clicked_retailer:
        return None
    return clicked_retailer


@callback(
    Output('dc-callout-area', 'children'),
    Output('dc-retailer-chart', 'figure', allow_duplicate=True),
    Input('dc-pinned-retailer', 'data'),
    State('filter-state', 'data'),
    prevent_initial_call=True,
)
def _update_callout_and_dim(pinned_retailer, filter_json):
    """Show/hide callout card and dim non-selected retailers."""
    filters = json.loads(filter_json) if filter_json else {}
    end_q = filters.get('end_quarter', 'Q4 2025')
    start_q = filters.get('start_quarter', 'Q1 2025')
    range_weeks = _quarter_range_weeks(start_q, end_q)

    auth, scans = _filter_data(filters)
    bar_data = _compute_retailer_bars(auth, scans, range_weeks)

    if not pinned_retailer:
        # Clear callout, reset opacity
        fig = _build_retailer_chart(bar_data, selected_retailer=None)
        return [], fig

    # Build callout card
    current_weeks = _quarter_to_weeks(end_q)
    detail = _compute_click_detail(auth, scans, current_weeks, pinned_retailer)

    card = dark_callout_card(
        title=detail['retailer_name'],
        subtitle=f"{detail['carrying_doors']} of {detail['addressable_doors']} addressable doors",
        rows=[
            {'label': 'Penetration', 'value': fmt_pct(detail['pct'])},
            {'label': 'Items carried', 'value': fmt_number(detail['items_carried'])},
            {'label': 'Items not carried', 'value': fmt_number(detail['items_not_carried'])},
        ],
    )

    # Rebuild chart with dimming
    fig = _build_retailer_chart(bar_data, selected_retailer=pinned_retailer)

    return card, fig
