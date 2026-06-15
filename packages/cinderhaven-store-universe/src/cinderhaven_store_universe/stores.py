"""Generate the 640-door store universe."""

import numpy as np
import pandas as pd

from .constants import REGIONS, RETAILERS, SEED, VOLUME_TIER_WEIGHTS, VOLUME_TIERS

_cache: pd.DataFrame | None = None


def get_stores() -> pd.DataFrame:
    """Return a DataFrame of 640 stores across 6 retailers.

    Columns: store_id, retailer_id, retailer_name, region, volume_tier.
    Deterministic (SEED=42).
    """
    global _cache
    if _cache is not None:
        return _cache.copy()

    rng = np.random.default_rng(SEED)
    rows: list[dict] = []

    for retailer_id, info in RETAILERS.items():
        n = info["door_count"]
        tier_weights = VOLUME_TIER_WEIGHTS[retailer_id]

        # Assign regions — roughly even with small random variation
        regions = rng.choice(REGIONS, size=n)

        # Assign volume tiers according to retailer-specific weights
        tiers = rng.choice(VOLUME_TIERS, size=n, p=tier_weights)

        for i in range(n):
            rows.append(
                {
                    "store_id": f"{retailer_id}-{i + 1:03d}",
                    "retailer_id": retailer_id,
                    "retailer_name": info["name"],
                    "region": regions[i],
                    "volume_tier": tiers[i],
                }
            )

    _cache = pd.DataFrame(rows)
    return _cache.copy()
