"""Generate the SKU x store authorization matrix."""

import numpy as np
import pandas as pd

from .constants import ALL_SKUS, AUTH_RATES, SEED
from .stores import get_stores

_cache: pd.DataFrame | None = None


def _sku_prefix(sku_id: str) -> str:
    """Extract the product line prefix from a SKU ID (e.g. 'CHP-AS-001' -> 'AS')."""
    return sku_id.split("-")[1]


def get_auth_matrix() -> pd.DataFrame:
    """Return the authorization matrix for all SKU x store pairs.

    Columns: sku_id, store_id, retailer_id, authorized (bool), authorized_date (str 'YYYY-Wnn').
    Not every item is authorized at every door — rates vary by retailer and product line.
    Deterministic (SEED=42).
    """
    global _cache
    if _cache is not None:
        return _cache.copy()

    rng = np.random.default_rng(SEED)
    stores = get_stores()

    # Build all SKU x store combinations using vectorized operations
    n_skus = len(ALL_SKUS)
    n_stores = len(stores)
    total_pairs = n_skus * n_stores

    # Repeat each SKU for all stores, tile stores for all SKUs
    sku_ids = np.repeat(ALL_SKUS, n_stores)
    store_ids = np.tile(stores["store_id"].values, n_skus)
    retailer_ids = np.tile(stores["retailer_id"].values, n_skus)

    # Compute authorization probability for each pair
    auth_probs = np.empty(total_pairs, dtype=np.float64)
    for i, sku_id in enumerate(ALL_SKUS):
        prefix = _sku_prefix(sku_id)
        start = i * n_stores
        for j in range(n_stores):
            ret_id = retailer_ids[start + j]
            auth_probs[start + j] = AUTH_RATES[ret_id][prefix]

    # Draw authorization flags
    authorized = rng.random(total_pairs) < auth_probs

    # Generate authorized_date for authorized items: random week in Q1-Q2 2024 (W01-W26)
    week_nums = rng.integers(1, 27, size=total_pairs)  # 1 through 26 inclusive
    auth_dates = np.where(
        authorized,
        np.array([f"2024-W{w:02d}" for w in week_nums]),
        None,
    )

    _cache = pd.DataFrame(
        {
            "sku_id": sku_ids,
            "store_id": store_ids,
            "retailer_id": retailer_ids,
            "authorized": authorized,
            "authorized_date": auth_dates,
        }
    )
    return _cache.copy()
