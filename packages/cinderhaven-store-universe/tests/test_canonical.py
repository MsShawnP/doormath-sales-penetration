"""Validate store universe data against canonical constraints."""

import re

import pandas as pd
import pytest

from cinderhaven_store_universe import (
    DEMO_AS_OF_DATE,
    get_auth_matrix,
    get_scan_data,
    get_stores,
)
from cinderhaven_store_universe.constants import ALL_SKUS, PRODUCT_LINES, RETAILERS


class TestStores:
    def test_total_door_count(self):
        stores = get_stores()
        assert len(stores) == 640

    def test_doors_per_retailer(self):
        stores = get_stores()
        expected = {
            "RET-WALMART": 180,
            "RET-COSTCO": 60,
            "RET-WHOLEFOODS": 120,
            "RET-SPROUTS": 90,
            "RET-KROGER": 150,
            "RET-REGIONAL": 40,
        }
        actual = stores.groupby("retailer_id").size().to_dict()
        assert actual == expected

    def test_store_id_format(self):
        stores = get_stores()
        pattern = re.compile(r"^RET-[A-Z]+-\d{3}$")
        for sid in stores["store_id"]:
            assert pattern.match(sid), f"Invalid store_id format: {sid}"

    def test_all_regions_present(self):
        stores = get_stores()
        assert set(stores["region"]) == {"Northeast", "Southeast", "Midwest", "West"}

    def test_all_volume_tiers_present(self):
        stores = get_stores()
        assert set(stores["volume_tier"]) == {"A", "B", "C"}

    def test_reproducibility(self):
        s1 = get_stores()
        s2 = get_stores()
        pd.testing.assert_frame_equal(s1, s2)


class TestSKUs:
    def test_total_sku_count(self):
        assert len(ALL_SKUS) == 50

    def test_five_product_lines(self):
        assert len(PRODUCT_LINES) == 5

    def test_ten_skus_per_line(self):
        for prefix, info in PRODUCT_LINES.items():
            assert len(info["skus"]) == 10, f"{prefix} has {len(info['skus'])} SKUs"

    def test_sku_id_format(self):
        pattern = re.compile(r"^CHP-(AS|PS|SC|DG|SB)-\d{3}$")
        for sku in ALL_SKUS:
            assert pattern.match(sku), f"Invalid SKU format: {sku}"

    def test_sku_prefixes(self):
        expected_prefixes = {"AS", "PS", "SC", "DG", "SB"}
        actual_prefixes = set(PRODUCT_LINES.keys())
        assert actual_prefixes == expected_prefixes


class TestAuthMatrix:
    def test_has_deliberate_gaps(self):
        auth = get_auth_matrix()
        auth_rate = auth["authorized"].mean()
        # Overall auth rate should be well below 100%
        assert auth_rate < 0.80, f"Auth rate {auth_rate:.2%} is too high — should have gaps"
        assert auth_rate > 0.40, f"Auth rate {auth_rate:.2%} is too low"

    def test_all_skus_present(self):
        auth = get_auth_matrix()
        assert set(auth["sku_id"].unique()) == set(ALL_SKUS)

    def test_all_stores_present(self):
        auth = get_auth_matrix()
        stores = get_stores()
        assert set(auth["store_id"].unique()) == set(stores["store_id"].unique())

    def test_authorized_date_format(self):
        auth = get_auth_matrix()
        authorized = auth[auth["authorized"]]
        pattern = re.compile(r"^2024-W\d{2}$")
        for date_str in authorized["authorized_date"].dropna():
            assert pattern.match(date_str), f"Invalid auth date: {date_str}"


class TestScanData:
    def test_week_range(self):
        scans = get_scan_data()
        weeks = sorted(scans["week"].unique())
        assert weeks[0] == "2024-W01"
        assert weeks[-1] == "2025-W52"

    def test_only_authorized_pairs_scanned(self):
        """Scan data should only contain rows for authorized item-store pairs."""
        scans = get_scan_data()
        auth = get_auth_matrix()
        authorized_pairs = set(
            zip(
                auth[auth["authorized"]]["sku_id"],
                auth[auth["authorized"]]["store_id"],
            )
        )
        scan_pairs = set(zip(scans["sku_id"], scans["store_id"]))
        assert scan_pairs.issubset(authorized_pairs)

    def test_week_count(self):
        """Should have ~104 weeks (52 per year x 2 years)."""
        scans = get_scan_data()
        n_weeks = scans["week"].nunique()
        assert n_weeks == 104


class TestDemoDate:
    def test_demo_as_of_date(self):
        assert DEMO_AS_OF_DATE == pd.Timestamp("2025-12-29")
