"""Centralized metric calculations for Door Math.

All time-relative computations use an explicit as_of_date parameter
defaulting to DEMO_AS_OF_DATE -- never wall-clock time.
"""

from app.constants import DEMO_AS_OF_DATE


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


def calc_penetration_rate(
    auth_df, scan_df, quarter, retailers=None, product_lines=None, sku=None, as_of_date=None
):
    """Calculate penetration rate: carrying doors / addressable doors for a quarter.

    Addressable = unique stores with at least one authorized item matching filters.
    Carrying = addressable stores that scanned at least once in the quarter.
    Returns float between 0 and 1.
    """
    if as_of_date is None:
        as_of_date = DEMO_AS_OF_DATE

    # Filter auth matrix to authorized items only
    auth = auth_df[auth_df["authorized"]].copy()
    if retailers:
        auth = auth[auth["retailer_id"].isin(retailers)]
    if product_lines:
        auth = auth[auth["sku_id"].str.split("-").str[1].isin(product_lines)]
    if sku:
        auth = auth[auth["sku_id"] == sku]

    # Addressable = unique stores with at least one authorized item
    addressable_stores = auth["store_id"].unique()
    if len(addressable_stores) == 0:
        return 0.0

    # Carrying = stores that scanned at least once in the quarter
    # for at least one of the authorized SKUs matching the filter
    weeks = quarter_to_weeks(quarter)
    auth_sku_ids = auth["sku_id"].unique()
    quarter_scans = scan_df[
        (scan_df["week"].isin(weeks))
        & (scan_df["scanned"])
        & (scan_df["store_id"].isin(addressable_stores))
        & (scan_df["sku_id"].isin(auth_sku_ids))
    ]

    carrying_stores = quarter_scans["store_id"].nunique()
    return carrying_stores / len(addressable_stores)


def calc_acv_pct(
    stores_df,
    auth_df,
    scan_df,
    quarter,
    retailers=None,
    product_lines=None,
    sku=None,
    as_of_date=None,
):
    """Calculate ACV% -- weighted distribution by store volume tier.

    ACV% = sum of volume weights for carrying stores / sum of volume weights
    for all addressable stores.  Volume tier weights: A=3, B=2, C=1 (proxy
    for actual ACV dollars).
    Returns float between 0 and 1.
    """
    if as_of_date is None:
        as_of_date = DEMO_AS_OF_DATE

    TIER_WEIGHTS = {"A": 3, "B": 2, "C": 1}

    # Get authorized stores
    auth = auth_df[auth_df["authorized"]].copy()
    if retailers:
        auth = auth[auth["retailer_id"].isin(retailers)]
    if product_lines:
        auth = auth[auth["sku_id"].str.split("-").str[1].isin(product_lines)]
    if sku:
        auth = auth[auth["sku_id"] == sku]

    addressable_store_ids = auth["store_id"].unique()
    if len(addressable_store_ids) == 0:
        return 0.0

    addressable = stores_df[stores_df["store_id"].isin(addressable_store_ids)]
    total_weight = addressable["volume_tier"].map(TIER_WEIGHTS).sum()
    if total_weight == 0:
        return 0.0

    # Carrying stores -- scanned at least once in the quarter
    weeks = quarter_to_weeks(quarter)
    quarter_scans = scan_df[
        (scan_df["week"].isin(weeks))
        & (scan_df["scanned"])
        & (scan_df["store_id"].isin(addressable_store_ids))
    ]
    carrying_store_ids = quarter_scans["store_id"].unique()
    carrying = stores_df[stores_df["store_id"].isin(carrying_store_ids)]
    carrying_weight = carrying["volume_tier"].map(TIER_WEIGHTS).sum()

    return carrying_weight / total_weight


def calc_tdp(
    stores_df, auth_df, scan_df, quarter, retailers=None, product_lines=None, as_of_date=None
):
    """Calculate TDP (Total Distribution Points) -- sum of ACV% across items.

    TDP = sum over all SKUs of (ACV% for that SKU in the quarter).
    Returns a float (total points, not bounded by 1).
    """
    if as_of_date is None:
        as_of_date = DEMO_AS_OF_DATE

    auth = auth_df[auth_df["authorized"]].copy()
    if retailers:
        auth = auth[auth["retailer_id"].isin(retailers)]
    if product_lines:
        auth = auth[auth["sku_id"].str.split("-").str[1].isin(product_lines)]

    skus = auth["sku_id"].unique()
    total = 0.0
    for sku in skus:
        total += calc_acv_pct(
            stores_df,
            auth_df,
            scan_df,
            quarter,
            retailers=retailers,
            product_lines=product_lines,
            sku=sku,
            as_of_date=as_of_date,
        )
    return total


def calc_period_delta(current_value, prior_value):
    """Calculate period-over-period change.

    Returns the difference (current - prior).
    """
    if prior_value is None or current_value is None:
        return 0.0
    return current_value - prior_value
