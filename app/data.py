"""Centralized data loading and pre-aggregation.

Loads the store universe once and pre-aggregates ~2M weekly scan rows into
~150K quarterly carrying records for fast callback computation.

Pre-aggregated frames are cached to .cache/ as parquet files; subsequent
startups skip the expensive raw-scan processing entirely.
"""

import hashlib
from pathlib import Path

import pandas as pd
from cinderhaven_store_universe import (
    get_auth_matrix,
    get_scan_data,
    get_slow_leak_config,
    get_stores,
)
from cinderhaven_store_universe.constants import DEMO_AS_OF_DATE, PRODUCT_LINES, RETAILERS

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"

STORES = get_stores()
AUTH = get_auth_matrix()
SLOW_LEAK = get_slow_leak_config()

AUTH["product_line"] = AUTH["sku_id"].str.split("-").str[1]

PL_NAMES = {prefix: info["name"] for prefix, info in PRODUCT_LINES.items()}
RETAILER_NAMES = {ret_id: info["name"] for ret_id, info in RETAILERS.items()}

STORE_INFO = STORES[["store_id", "retailer_id", "retailer_name", "volume_tier"]].copy()
STORE_INFO["weight"] = STORE_INFO["volume_tier"].map({"A": 3, "B": 2, "C": 1})


def _cache_key():
    """Hash AUTH + store count to detect data changes."""
    sig = f"{len(AUTH)}-{len(STORES)}-{DEMO_AS_OF_DATE}"
    return hashlib.md5(sig.encode()).hexdigest()[:12]


def _load_or_build_aggregates():
    _CACHE_DIR.mkdir(exist_ok=True)
    key = _cache_key()
    sq_path = _CACHE_DIR / f"scan_quarterly_{key}.parquet"
    ls_path = _CACHE_DIR / f"last_scan_{key}.parquet"

    if sq_path.exists() and ls_path.exists():
        sq = pd.read_parquet(sq_path)
        ls = pd.read_parquet(ls_path)
        return sq, ls

    raw = get_scan_data()
    year = raw["week"].str[:4]
    wnum = raw["week"].str.split("-W").str[1].astype(int)
    qnum = ((wnum - 1) // 13) + 1
    raw["quarter"] = "Q" + qnum.astype(str) + " " + year
    raw["product_line"] = raw["sku_id"].str.split("-").str[1]

    sq = (
        raw.loc[raw["scanned"], ["sku_id", "store_id", "quarter", "product_line"]]
        .drop_duplicates()
        .copy()
    )
    sq = sq.merge(STORE_INFO[["store_id", "retailer_id", "weight"]], on="store_id", how="left")

    ls = (
        raw.loc[raw["scanned"]]
        .groupby(["sku_id", "store_id"])["week"]
        .max()
        .reset_index()
        .rename(columns={"week": "last_scan_week"})
    )

    sq.to_parquet(sq_path, index=False)
    ls.to_parquet(ls_path, index=False)
    return sq, ls


SCAN_QUARTERLY, LAST_SCAN = _load_or_build_aggregates()

ALL_QUARTERS = [f"Q{q} {y}" for y in (2024, 2025) for q in range(1, 5)]
