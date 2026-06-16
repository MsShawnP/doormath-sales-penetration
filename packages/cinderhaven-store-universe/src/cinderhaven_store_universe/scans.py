"""Generate weekly POS scan data for authorized item-store pairs."""

import numpy as np
import pandas as pd

from .authorization import get_auth_matrix
from .constants import ALL_SKUS, LATE_LAUNCH, NEVER_SCAN_RATES, SCAN_RATES, SEED
from .slow_leak import SLOW_LEAK_CONFIG, apply_slow_leak
from .stores import get_stores

_cache: pd.DataFrame | None = None

# Per-SKU shelf velocity — modulates never-scan rate to create item-level variance.
# Higher velocity = lower effective never-scan rate = higher penetration ceiling.
# Slow-leak and late-launch SKUs are set to 1.0 so pre-leak penetration stays high.
_vel_rng = np.random.default_rng(SEED + 200)
_SKU_VELOCITY = {sku: float(_vel_rng.beta(4, 2)) for sku in ALL_SKUS}
for _sku in list(SLOW_LEAK_CONFIG.keys()) + list(LATE_LAUNCH.keys()):
    _SKU_VELOCITY[_sku] = 1.00


def _generate_weeks() -> list[str]:
    """Return ISO week strings from 2024-W01 through 2025-W52."""
    weeks = []
    for year in (2024, 2025):
        for w in range(1, 53):
            weeks.append(f"{year}-W{w:02d}")
    return weeks


def get_scan_data() -> pd.DataFrame:
    """Return weekly POS scan flags for all authorized item-store pairs.

    Columns: sku_id, store_id, week (str 'YYYY-Wnn'), scanned (bool).
    Scan probability varies by store volume tier.
    Slow-leak patterns are applied after base generation.
    Deterministic (SEED=42).
    """
    global _cache
    if _cache is not None:
        return _cache.copy()

    rng = np.random.default_rng(SEED)

    # Get authorized pairs only
    auth = get_auth_matrix()
    auth_pairs = auth[auth["authorized"]].copy()

    # Merge volume tier from stores
    stores = get_stores()[["store_id", "volume_tier"]]
    auth_pairs = auth_pairs.merge(stores, on="store_id", how="left")

    weeks = _generate_weeks()
    n_weeks = len(weeks)
    n_pairs = len(auth_pairs)

    # Build scan probabilities per pair based on volume tier
    tier_probs = auth_pairs["volume_tier"].map(SCAN_RATES).values  # shape (n_pairs,)

    # Vectorized: generate all random draws at once
    # Shape: (n_pairs, n_weeks) — each row is one auth pair across all weeks
    random_draws = rng.random((n_pairs, n_weeks))
    scanned_matrix = random_draws < tier_probs[:, np.newaxis]

    # Never-scan pairs: authorized but never carried.
    # One-time per-pair designation — a store that never carries an item
    # stays consistently absent across all 104 weeks, not flickering.
    retailer_base = auth_pairs["retailer_id"].map(NEVER_SCAN_RATES).values
    sku_vel = np.array([_SKU_VELOCITY[s] for s in auth_pairs["sku_id"].values])
    effective_never_scan = np.clip(retailer_base / sku_vel, 0.02, 0.50)
    never_rng = np.random.default_rng(SEED + 300)
    never_scan_flags = never_rng.random(n_pairs) < effective_never_scan
    scanned_matrix[never_scan_flags] = False

    # Late-launch SKUs: suppress all scans before their market entry week
    for late_sku, launch_week in LATE_LAUNCH.items():
        if launch_week in weeks:
            launch_idx = weeks.index(launch_week)
            sku_mask = auth_pairs["sku_id"].values == late_sku
            scanned_matrix[sku_mask, :launch_idx] = False

    # Build the DataFrame using numpy repeat/tile for efficiency
    sku_ids = np.repeat(auth_pairs["sku_id"].values, n_weeks)
    store_ids = np.repeat(auth_pairs["store_id"].values, n_weeks)
    week_arr = np.tile(weeks, n_pairs)
    scanned_flat = scanned_matrix.ravel()

    scan_df = pd.DataFrame(
        {
            "sku_id": sku_ids,
            "store_id": store_ids,
            "week": week_arr,
            "scanned": scanned_flat,
        }
    )

    # Apply slow-leak patterns
    scan_df = apply_slow_leak(scan_df)

    _cache = scan_df
    return _cache.copy()
