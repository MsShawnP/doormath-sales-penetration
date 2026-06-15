"""
Synthetic store universe, authorization matrix, and POS scan data
for Cinderhaven's ~$25M specialty food brand.
"""

import pandas as pd


def build_store_universe() -> pd.DataFrame:
    """600 doors across 3 banners with volume tiers."""
    raise NotImplementedError


def build_authorization_matrix() -> pd.DataFrame:
    """Item x door authorization matrix with deliberate gaps."""
    raise NotImplementedError


def build_scan_data() -> pd.DataFrame:
    """Weekly POS scan data with a slow-leak distribution story."""
    raise NotImplementedError
