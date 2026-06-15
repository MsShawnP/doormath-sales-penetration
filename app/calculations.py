"""Centralized metric calculations for Door Math.

Uses pre-aggregated quarterly scan data from app.data for performance.
All time-relative computations use DEMO_AS_OF_DATE -- never wall-clock time.
"""

from app.data import AUTH, SCAN_QUARTERLY, STORE_INFO


def quarter_to_weeks(quarter_str):
    """Convert 'Q1 2024' to list of week strings ['2024-W01', ..., '2024-W13'].

    Quarter boundaries: Q1=W01-W13, Q2=W14-W26, Q3=W27-W39, Q4=W40-W52.
    """
    q, year = quarter_str.split()
    q_num = int(q[1])
    year = int(year)
    start_week = (q_num - 1) * 13 + 1
    end_week = q_num * 13
    return [f"{year}-W{w:02d}" for w in range(start_week, end_week + 1)]


def quarters_in_range(start_quarter, end_quarter):
    """Return list of quarter strings from start to end inclusive.

    Covers the 2024-2025 range (8 quarters total).
    """
    all_quarters = [f"Q{q} {y}" for y in [2024, 2025] for q in [1, 2, 3, 4]]
    try:
        start_idx = all_quarters.index(start_quarter)
        end_idx = all_quarters.index(end_quarter)
    except ValueError:
        return []
    return all_quarters[start_idx : end_idx + 1]


def filter_auth(retailers=None, product_lines=None, sku=None):
    """Return authorized pairs filtered by retailer, product line, and/or SKU."""
    auth = AUTH[AUTH["authorized"]]
    if retailers:
        auth = auth[auth["retailer_id"].isin(retailers)]
    if product_lines:
        auth = auth[auth["product_line"].isin(product_lines)]
    if sku:
        auth = auth[auth["sku_id"] == sku]
    return auth


def carrying_in_quarter(quarter, auth_store_ids, auth_sku_ids=None):
    """Return SCAN_QUARTERLY rows for carrying stores in the given quarter."""
    mask = (SCAN_QUARTERLY["quarter"] == quarter) & SCAN_QUARTERLY["store_id"].isin(auth_store_ids)
    if auth_sku_ids is not None:
        mask = mask & SCAN_QUARTERLY["sku_id"].isin(auth_sku_ids)
    return SCAN_QUARTERLY[mask]


def calc_penetration_rate(quarter, retailers=None, product_lines=None, sku=None):
    """Calculate penetration rate: carrying doors / addressable doors for a quarter.

    Addressable = unique stores with at least one authorized item matching filters.
    Carrying = addressable stores that scanned at least once in the quarter.
    Returns float between 0 and 1.
    """
    auth = filter_auth(retailers, product_lines, sku)
    addressable_ids = set(auth["store_id"].unique())
    if not addressable_ids:
        return 0.0

    sq = carrying_in_quarter(quarter, addressable_ids, set(auth["sku_id"].unique()))
    carrying = sq["store_id"].nunique()
    return carrying / len(addressable_ids)


def calc_acv_pct(quarter, retailers=None, product_lines=None, sku=None):
    """Calculate ACV% -- weighted distribution by store volume tier.

    ACV% = sum of volume weights for carrying stores / sum of volume weights
    for all addressable stores.  Volume tier weights: A=3, B=2, C=1 (proxy
    for actual ACV dollars).
    Returns float between 0 and 1.
    """
    auth = filter_auth(retailers, product_lines, sku)
    addressable_ids = set(auth["store_id"].unique())
    if not addressable_ids:
        return 0.0

    total_weight = STORE_INFO.loc[STORE_INFO["store_id"].isin(addressable_ids), "weight"].sum()
    if total_weight == 0:
        return 0.0

    auth_sku_ids = set(auth["sku_id"].unique())
    sq = carrying_in_quarter(quarter, addressable_ids, auth_sku_ids)
    carrying_ids = set(sq["store_id"].unique())
    carrying_weight = STORE_INFO.loc[STORE_INFO["store_id"].isin(carrying_ids), "weight"].sum()

    return carrying_weight / total_weight


def calc_tdp(quarter, retailers=None, product_lines=None):
    """Calculate TDP (Total Distribution Points) -- sum of ACV% across items.

    Vectorized: computes per-SKU ACV% in a single groupby instead of looping.
    Returns a float (total points, not bounded by 1).
    """
    auth = filter_auth(retailers, product_lines)
    addressable_ids = set(auth["store_id"].unique())
    if not addressable_ids:
        return 0.0

    total_weight = STORE_INFO.loc[STORE_INFO["store_id"].isin(addressable_ids), "weight"].sum()
    if total_weight == 0:
        return 0.0

    auth_sku_ids = set(auth["sku_id"].unique())
    sq = carrying_in_quarter(quarter, addressable_ids, auth_sku_ids)

    per_sku = (
        sq.drop_duplicates(subset=["sku_id", "store_id"]).groupby("sku_id")["weight"].sum()
    )
    return per_sku.sum() / total_weight


def calc_period_delta(current_value, prior_value):
    """Calculate period-over-period change.

    Returns the difference (current - prior).
    """
    if prior_value is None or current_value is None:
        return 0.0
    return current_value - prior_value
