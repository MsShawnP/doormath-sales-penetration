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
    """Calculate penetration rate at the pair level for a quarter.

    Addressable = unique (sku_id, store_id) authorized pairs matching filters.
    Carrying = authorized pairs that scanned at least once in the quarter.
    Returns float between 0 and 1.
    """
    auth = filter_auth(retailers, product_lines, sku)
    auth_pairs = auth[["sku_id", "store_id"]].drop_duplicates()
    addressable = len(auth_pairs)
    if addressable == 0:
        return 0.0

    sq = carrying_in_quarter(quarter, set(auth["store_id"].unique()), set(auth["sku_id"].unique()))
    carrying = len(sq[["sku_id", "store_id"]].drop_duplicates())
    return carrying / addressable


def calc_acv_pct(quarter, retailers=None, product_lines=None, sku=None):
    """Calculate ACV% at the pair level, weighted by store volume tier.

    Each authorized (sku_id, store_id) pair contributes its store's weight
    to the denominator.  Scanning pairs contribute to the numerator.
    A store with 50 authorized items but only 30 scanning contributes 60%
    of its potential weight, not 100%.
    Volume tier weights: A=3, B=2, C=1 (proxy for actual ACV dollars).
    Returns float between 0 and 1.
    """
    auth = filter_auth(retailers, product_lines, sku)
    if auth.empty:
        return 0.0

    auth_pairs = auth[["sku_id", "store_id"]].drop_duplicates()
    store_weights = STORE_INFO[["store_id", "weight"]].drop_duplicates()

    pairs_per_store = auth_pairs.groupby("store_id").size().reset_index(name="n_auth")
    pairs_per_store = pairs_per_store.merge(store_weights, on="store_id", how="left")
    total_weight = (pairs_per_store["n_auth"] * pairs_per_store["weight"]).sum()
    if total_weight == 0:
        return 0.0

    addressable_ids = set(auth["store_id"].unique())
    auth_sku_ids = set(auth["sku_id"].unique())
    sq = carrying_in_quarter(quarter, addressable_ids, auth_sku_ids)
    scanning_pairs = sq[["sku_id", "store_id"]].drop_duplicates()

    scan_per_store = scanning_pairs.groupby("store_id").size().reset_index(name="n_scan")
    scan_per_store = scan_per_store.merge(store_weights, on="store_id", how="left")
    carrying_weight = (scan_per_store["n_scan"] * scan_per_store["weight"]).sum()

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

    per_sku = sq.drop_duplicates(subset=["sku_id", "store_id"]).groupby("sku_id")["weight"].sum()
    return per_sku.sum() / total_weight


def batch_acv_by_retailer(quarters, retailers, product_lines=None, sku=None):
    """Compute ACV% for every (retailer, quarter) pair in one pass.

    Returns dict: {retailer_id: {quarter_str: float}}.
    """
    auth = filter_auth(retailers=retailers, product_lines=product_lines, sku=sku)
    if auth.empty:
        return {r: {q: 0.0 for q in quarters} for r in retailers}

    store_weights = STORE_INFO[["store_id", "weight", "retailer_id"]].drop_duplicates(
        subset=["store_id"]
    )
    auth_pairs = auth[["sku_id", "store_id"]].drop_duplicates()
    auth_w = auth_pairs.merge(store_weights, on="store_id", how="left")

    denom = auth_w.groupby("retailer_id")["weight"].sum()

    store_ids = set(auth["store_id"].unique())
    sku_ids = set(auth["sku_id"].unique())
    sq = SCAN_QUARTERLY[
        SCAN_QUARTERLY["quarter"].isin(quarters)
        & SCAN_QUARTERLY["store_id"].isin(store_ids)
        & SCAN_QUARTERLY["sku_id"].isin(sku_ids)
    ].drop_duplicates(subset=["sku_id", "store_id", "quarter"])

    numer = sq.groupby(["retailer_id", "quarter"])["weight"].sum()

    result = {}
    for r in retailers:
        result[r] = {}
        d = denom.get(r, 0)
        for q in quarters:
            n = numer.get((r, q), 0)
            result[r][q] = (n / d) if d > 0 else 0.0
    return result


def batch_tdp_by_retailer(quarters, retailers, product_lines=None):
    """Compute TDP for every (retailer, quarter) pair in one pass.

    Returns dict: {retailer_id: {quarter_str: float}}.
    """
    auth = filter_auth(retailers=retailers, product_lines=product_lines)
    if auth.empty:
        return {r: {q: 0.0 for q in quarters} for r in retailers}

    store_weights = STORE_INFO[["store_id", "weight", "retailer_id"]].drop_duplicates(
        subset=["store_id"]
    )
    addressable_ids = set(auth["store_id"].unique())

    denom = store_weights.loc[
        store_weights["store_id"].isin(addressable_ids)
    ].groupby("retailer_id")["weight"].sum()

    sku_ids = set(auth["sku_id"].unique())
    sq = SCAN_QUARTERLY[
        SCAN_QUARTERLY["quarter"].isin(quarters)
        & SCAN_QUARTERLY["store_id"].isin(addressable_ids)
        & SCAN_QUARTERLY["sku_id"].isin(sku_ids)
    ].drop_duplicates(subset=["sku_id", "store_id", "quarter"])

    per_sku_ret_q = sq.groupby(["retailer_id", "quarter", "sku_id"])["weight"].sum()
    tdp_by_ret_q = per_sku_ret_q.groupby(level=["retailer_id", "quarter"]).sum()

    result = {}
    for r in retailers:
        result[r] = {}
        d = denom.get(r, 0)
        for q in quarters:
            n = tdp_by_ret_q.get((r, q), 0)
            result[r][q] = (n / d) if d > 0 else 0.0
    return result


def calc_period_delta(current_value, prior_value):
    """Calculate period-over-period change.

    Returns the difference (current - prior).
    """
    if prior_value is None or current_value is None:
        return 0.0
    return current_value - prior_value
