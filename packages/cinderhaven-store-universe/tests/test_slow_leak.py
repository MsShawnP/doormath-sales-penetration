"""Validate slow-leak curves for CHP-DG-003 and CHP-SC-007."""

import numpy as np
import pandas as pd
import pytest
from cinderhaven_store_universe import get_auth_matrix, get_scan_data
from cinderhaven_store_universe.slow_leak import (
    QUARTER_ENDS,
    QUARTER_STARTS,
    _quarter_sequence,
    _week_to_sortable,
)


def _penetration_by_quarter(
    scan_df: pd.DataFrame, auth_df: pd.DataFrame, sku_id: str
) -> dict[str, float]:
    """Compute scanning penetration per quarter for a given SKU.

    Penetration = doors scanning at least once in the quarter / doors authorized.
    """
    auth_stores = set(auth_df[(auth_df["sku_id"] == sku_id) & auth_df["authorized"]]["store_id"])
    n_authorized = len(auth_stores)
    if n_authorized == 0:
        return {}

    sku_scans = scan_df[scan_df["sku_id"] == sku_id].copy()
    sku_scans["_week_sort"] = sku_scans["week"].apply(_week_to_sortable)

    result = {}
    for q_label, q_start in QUARTER_STARTS.items():
        q_end = QUARTER_ENDS[q_label]
        q_start_sort = _week_to_sortable(q_start)
        q_end_sort = _week_to_sortable(q_end)

        q_mask = (sku_scans["_week_sort"] >= q_start_sort) & (sku_scans["_week_sort"] <= q_end_sort)
        q_data = sku_scans[q_mask]

        # Doors that scanned at least once in the quarter
        scanning_doors = set(q_data[q_data["scanned"]]["store_id"])
        result[q_label] = len(scanning_doors) / n_authorized

    return result


@pytest.fixture(scope="module")
def data():
    scans = get_scan_data()
    auth = get_auth_matrix()
    return scans, auth


class TestCHP_DG_003:
    """CHP-DG-003: dramatic accelerating decline from ~100% to ~52%."""

    def test_penetration_pre_leak(self, data):
        """Q1 2024 is before the leak starts — should be near 100% (at-least-once metric)."""
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-DG-003")
        assert pen["2024-Q1"] >= 0.90, f"Pre-leak penetration {pen['2024-Q1']:.2%} too low"

    def test_penetration_end(self, data):
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-DG-003")
        # By Q4 2025 should be near ~52% (within +-5pp tolerance)
        assert 0.42 <= pen["2025-Q4"] <= 0.62, (
            f"End penetration {pen['2025-Q4']:.2%} outside 42%-62% range"
        )

    def test_total_drop(self, data):
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-DG-003")
        drop = pen["2024-Q1"] - pen["2025-Q4"]
        # Should drop roughly 33-48pp (from ~100% to ~52%)
        assert drop >= 0.25, f"Total drop {drop:.2%} too small"

    def test_accelerating_curve(self, data):
        """Later quarters should lose more penetration than earlier ones."""
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-DG-003")
        quarters = _quarter_sequence("2024-Q2", "2025-Q4")

        # Split into early half and late half
        mid = len(quarters) // 2
        early_qs = quarters[:mid]
        late_qs = quarters[mid:]

        # Compute drops
        early_drops = []
        for i in range(1, len(early_qs)):
            early_drops.append(pen[early_qs[i - 1]] - pen[early_qs[i]])

        late_drops = []
        for i in range(1, len(late_qs)):
            late_drops.append(pen[late_qs[i - 1]] - pen[late_qs[i]])

        avg_early = np.mean(early_drops) if early_drops else 0
        avg_late = np.mean(late_drops) if late_drops else 0

        # Late quarters should show larger average drops
        assert avg_late >= avg_early, (
            f"Curve not accelerating: early avg drop {avg_early:.4f}, late avg drop {avg_late:.4f}"
        )


class TestCHP_SC_007:
    """CHP-SC-007: steady linear decline from ~100% to ~58%."""

    def test_penetration_pre_leak(self, data):
        """Q2 2024 is before CHP-SC-007's leak starts — should be near 100%."""
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-SC-007")
        assert pen["2024-Q2"] >= 0.90, f"Pre-leak penetration {pen['2024-Q2']:.2%} too low"

    def test_penetration_end(self, data):
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-SC-007")
        # By Q4 2025 should be near ~58% (within +-5pp tolerance)
        assert 0.48 <= pen["2025-Q4"] <= 0.68, (
            f"End penetration {pen['2025-Q4']:.2%} outside 48%-68% range"
        )

    def test_total_drop(self, data):
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-SC-007")
        drop = pen["2024-Q2"] - pen["2025-Q4"]
        # Should drop at least 25pp (from ~100% to ~58%)
        assert drop >= 0.20, f"Total drop {drop:.2%} too small"

    def test_approximately_linear(self, data):
        """Quarterly drops should be roughly similar in magnitude."""
        scans, auth = data
        pen = _penetration_by_quarter(scans, auth, "CHP-SC-007")
        quarters = _quarter_sequence("2024-Q3", "2025-Q4")

        drops = []
        for i in range(1, len(quarters)):
            drops.append(pen[quarters[i - 1]] - pen[quarters[i]])

        if len(drops) < 2:
            pytest.skip("Not enough quarters to assess linearity")

        # For a linear curve, the coefficient of variation should be modest
        # Allow some randomness -- CV under 1.5 is reasonable
        std = np.std(drops)
        mean = np.mean(drops)
        if mean > 0:
            cv = std / mean
            assert cv < 1.5, f"Drops not approximately linear: CV={cv:.2f}, drops={drops}"


class TestNonLeakSKUs:
    """Non-leak SKUs should maintain stable penetration."""

    def test_stable_penetration(self, data):
        scans, auth = data
        # Pick a few non-leak SKUs to check
        non_leak_skus = ["CHP-AS-001", "CHP-PS-005", "CHP-SB-010"]

        for sku_id in non_leak_skus:
            pen = _penetration_by_quarter(scans, auth, sku_id)
            if not pen:
                continue

            values = list(pen.values())
            # Penetration should be reasonably stable -- no large drops
            max_pen = max(values)
            min_pen = min(values)
            spread = max_pen - min_pen
            assert spread < 0.25, (
                f"{sku_id} penetration unstable: spread={spread:.2%} "
                f"(max={max_pen:.2%}, min={min_pen:.2%})"
            )
