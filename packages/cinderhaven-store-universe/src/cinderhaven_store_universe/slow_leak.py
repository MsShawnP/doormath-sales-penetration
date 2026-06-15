"""Slow-leak story configuration and data generation.

Two SKUs exhibit declining scan penetration over time:
- CHP-DG-003: dramatic accelerating decline (85% -> 52%)
- CHP-SC-007: steady linear decline (72% -> 58%)
"""

import numpy as np
import pandas as pd

from .constants import SEED

# Quarter boundaries as ISO week strings
QUARTER_STARTS = {
    "2024-Q1": "2024-W01",
    "2024-Q2": "2024-W14",
    "2024-Q3": "2024-W27",
    "2024-Q4": "2024-W40",
    "2025-Q1": "2025-W01",
    "2025-Q2": "2025-W14",
    "2025-Q3": "2025-W27",
    "2025-Q4": "2025-W40",
}

QUARTER_ENDS = {
    "2024-Q1": "2024-W13",
    "2024-Q2": "2024-W26",
    "2024-Q3": "2024-W39",
    "2024-Q4": "2024-W52",
    "2025-Q1": "2025-W13",
    "2025-Q2": "2025-W26",
    "2025-Q3": "2025-W39",
    "2025-Q4": "2025-W52",
}

SLOW_LEAK_CONFIG = {
    "CHP-DG-003": {
        "description": "Dramatic accelerating decline — dried goods item losing doors",
        "start_quarter": "2024-Q2",
        "end_quarter": "2025-Q4",
        "start_penetration": 0.85,
        "end_penetration": 0.52,
        "curve": "accelerating",
        "retailers_affected_order": [
            "RET-REGIONAL",
            "RET-SPROUTS",
            "RET-KROGER",
        ],
        "retailers_stable": ["RET-WALMART", "RET-COSTCO"],
    },
    "CHP-SC-007": {
        "description": "Steady linear decline — specialty condiment losing traction",
        "start_quarter": "2024-Q3",
        "end_quarter": "2025-Q4",
        "start_penetration": 0.72,
        "end_penetration": 0.58,
        "curve": "linear",
        "retailers_affected_order": "all",
        "retailers_stable": [],
    },
}


def get_slow_leak_config() -> dict:
    """Return the slow-leak story configuration dict."""
    return SLOW_LEAK_CONFIG.copy()


def _week_to_sortable(week_str: str) -> int:
    """Convert 'YYYY-Wnn' to an integer for sorting/comparison."""
    year, w = week_str.split("-W")
    return int(year) * 100 + int(w)


def _get_quarter_weeks(quarter: str) -> tuple[int, int]:
    """Return (start_sortable, end_sortable) for a quarter label like '2024-Q2'."""
    return (
        _week_to_sortable(QUARTER_STARTS[quarter]),
        _week_to_sortable(QUARTER_ENDS[quarter]),
    )


def _quarter_sequence(start_q: str, end_q: str) -> list[str]:
    """Return ordered list of quarter labels from start to end inclusive."""
    all_quarters = list(QUARTER_STARTS.keys())
    si = all_quarters.index(start_q)
    ei = all_quarters.index(end_q)
    return all_quarters[si : ei + 1]


def apply_slow_leak(scan_df: pd.DataFrame) -> pd.DataFrame:
    """Apply slow-leak patterns to the scan DataFrame.

    For each configured leak SKU, progressively suppress scans at selected
    stores. Once a store stops scanning an item, it stays stopped.

    The penetration targets (start_penetration, end_penetration) are expressed
    as fractions of ALL authorized stores for the SKU, not just the affected
    retailers' stores.

    Args:
        scan_df: Base scan DataFrame with columns sku_id, store_id, week, scanned.

    Returns:
        Modified scan DataFrame with leak patterns applied.
    """
    rng = np.random.default_rng(SEED + 1)  # Offset seed to avoid correlation with base scans
    df = scan_df.copy()

    # Pre-compute sortable week values for the entire DataFrame
    df["_week_sort"] = df["week"].apply(_week_to_sortable)

    for sku_id, config in SLOW_LEAK_CONFIG.items():
        sku_mask = df["sku_id"] == sku_id
        if not sku_mask.any():
            continue

        # Count ALL authorized stores for this SKU (the denominator for penetration)
        all_sku_stores = df.loc[sku_mask, "store_id"].unique()
        n_total_authorized = len(all_sku_stores)

        # Get the set of stores scanning in the first quarter of the leak
        start_q = config["start_quarter"]
        start_sort, first_q_end = _get_quarter_weeks(start_q)
        first_q_mask = sku_mask & (df["_week_sort"] >= start_sort) & (df["_week_sort"] <= first_q_end)
        scanning_stores = list(df.loc[first_q_mask & df["scanned"], "store_id"].unique())

        # Filter to affected retailers only
        if config["retailers_affected_order"] == "all":
            affected_stores = list(scanning_stores)
        else:
            affected_retailer_ids = set(config["retailers_affected_order"])
            # Order stores by retailer priority (Regional first, then Sprouts, then Kroger)
            affected_stores = []
            for retailer_id in config["retailers_affected_order"]:
                retailer_stores = [
                    s for s in scanning_stores
                    if "-".join(s.split("-")[:2]) == retailer_id
                ]
                rng.shuffle(retailer_stores)
                affected_stores.extend(retailer_stores)

        if len(affected_stores) == 0:
            continue

        # Compute how many stores to silence in total.
        # Target: penetration drops from start_penetration to end_penetration
        # relative to ALL authorized stores.
        target_scanning_end = int(n_total_authorized * config["end_penetration"])
        current_scanning = len(scanning_stores)
        total_to_drop = current_scanning - target_scanning_end
        total_to_drop = min(total_to_drop, len(affected_stores))
        total_to_drop = max(total_to_drop, 0)

        quarters = _quarter_sequence(config["start_quarter"], config["end_quarter"])
        n_quarters = len(quarters)

        if config["curve"] == "accelerating":
            # Accelerating: fewer drops early, more later
            weights = np.array([(i + 1) ** 2 for i in range(n_quarters)], dtype=float)
            weights /= weights.sum()
            drops_per_quarter = np.round(weights * total_to_drop).astype(int)
            # Adjust rounding to match total
            diff = total_to_drop - drops_per_quarter.sum()
            if diff > 0:
                drops_per_quarter[-1] += diff
            elif diff < 0:
                for i in range(len(drops_per_quarter) - 1, -1, -1):
                    can_remove = min(-diff, drops_per_quarter[i])
                    drops_per_quarter[i] -= can_remove
                    diff += can_remove
                    if diff == 0:
                        break
        else:
            # Linear: roughly equal drops per quarter
            base = total_to_drop // n_quarters
            remainder = total_to_drop % n_quarters
            drops_per_quarter = np.full(n_quarters, base, dtype=int)
            for i in range(remainder):
                drops_per_quarter[i] += 1

        # Progressively silence stores
        silenced_stores: set[str] = set()
        drop_idx = 0

        for qi, quarter in enumerate(quarters):
            q_start_sort, _ = _get_quarter_weeks(quarter)
            n_drop = drops_per_quarter[qi]

            # Pick stores to silence this quarter
            new_silenced = []
            while len(new_silenced) < n_drop and drop_idx < len(affected_stores):
                store = affected_stores[drop_idx]
                drop_idx += 1
                if store not in silenced_stores:
                    new_silenced.append(store)
                    silenced_stores.add(store)

        # After computing all silenced stores per quarter, apply suppression
        # in one pass: for each store, suppress from the quarter it was silenced onward
        # Rebuild the suppression by tracking when each store was silenced
        silenced_stores_reset: set[str] = set()
        drop_idx = 0

        for qi, quarter in enumerate(quarters):
            q_start_sort, _ = _get_quarter_weeks(quarter)
            n_drop = drops_per_quarter[qi]

            newly_silenced = []
            while len(newly_silenced) < n_drop and drop_idx < len(affected_stores):
                store = affected_stores[drop_idx]
                drop_idx += 1
                if store not in silenced_stores_reset:
                    newly_silenced.append(store)
                    silenced_stores_reset.add(store)

            # For newly silenced stores, suppress ALL scans from this quarter onward
            if newly_silenced:
                silence_mask = (
                    sku_mask
                    & df["store_id"].isin(newly_silenced)
                    & (df["_week_sort"] >= q_start_sort)
                )
                df.loc[silence_mask, "scanned"] = False

    df = df.drop(columns=["_week_sort"])
    return df
