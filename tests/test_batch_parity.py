"""Batch calculations must agree with the per-entity reference implementations.

The Trends and Scorecard tabs are powered by ``batch_*`` functions that
reimplement the logic of ``calc_acv_pct`` and ``calc_tdp`` as single grouped
passes. Nothing compared the two, so a one-character change to a batch function
could collapse every retailer's ACV% to zero after the first quarter with the
whole suite still green — the per-entity functions have no callers left in the
app, so their own tests cannot catch it.

These tests pin both halves: parity against the reference, and a small set of
absolute values so the two cannot drift together.
"""

import pytest
from cinderhaven_store_universe.constants import PRODUCT_LINES, RETAILERS

from app.calculations import (
    batch_acv_by_product_line,
    batch_acv_by_retailer,
    batch_tdp_by_retailer,
    calc_acv_pct,
    calc_penetration_rate,
    calc_tdp,
)

QUARTERS = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
RETAILER_IDS = list(RETAILERS.keys())
PL_PREFIXES = list(PRODUCT_LINES.keys())

TOL = 1e-9


@pytest.mark.parametrize("ret_id", RETAILER_IDS)
def test_batch_acv_by_retailer_matches_reference(ret_id):
    """Every (retailer, quarter) ACV% equals calc_acv_pct for the same slice."""
    batch = batch_acv_by_retailer(QUARTERS, RETAILER_IDS)
    for q in QUARTERS:
        expected = calc_acv_pct(q, retailers=[ret_id])
        actual = batch[ret_id][q]
        assert actual == pytest.approx(expected, abs=TOL), (
            f"ACV% mismatch for {ret_id} {q}: batch={actual!r} reference={expected!r}"
        )


@pytest.mark.parametrize("ret_id", RETAILER_IDS)
def test_batch_tdp_by_retailer_matches_reference(ret_id):
    """Every (retailer, quarter) TDP equals calc_tdp for the same slice."""
    batch = batch_tdp_by_retailer(QUARTERS, RETAILER_IDS)
    for q in QUARTERS:
        expected = calc_tdp(q, retailers=[ret_id])
        actual = batch[ret_id][q]
        assert actual == pytest.approx(expected, abs=TOL), (
            f"TDP mismatch for {ret_id} {q}: batch={actual!r} reference={expected!r}"
        )


@pytest.mark.parametrize("pl", PL_PREFIXES)
def test_batch_acv_by_product_line_matches_reference(pl):
    """Every (product line, quarter) ACV% equals calc_acv_pct for the same slice."""
    batch = batch_acv_by_product_line(QUARTERS, PL_PREFIXES)
    for q in QUARTERS:
        expected = calc_acv_pct(q, product_lines=[pl])
        actual = batch[pl][q]
        assert actual == pytest.approx(expected, abs=TOL), (
            f"ACV% mismatch for {pl} {q}: batch={actual!r} reference={expected!r}"
        )


def test_batch_tdp_honours_the_sku_filter():
    """TDP over a single item equals that item's ACV%.

    Guards the defect where batch_tdp_by_retailer took no sku argument, so a
    single-item selection reported the whole product line's distribution beside
    the item's own penetration and ACV%.
    """
    sku = "CHP-AS-001"
    batch = batch_tdp_by_retailer(["Q4 2025"], RETAILER_IDS, None, sku)
    for ret_id in RETAILER_IDS:
        acv = calc_acv_pct("Q4 2025", retailers=[ret_id], sku=sku)
        assert batch[ret_id]["Q4 2025"] == pytest.approx(acv, abs=TOL), (
            f"single-SKU TDP should equal that SKU's ACV% for {ret_id}"
        )


def test_batch_values_are_not_uniformly_zero():
    """A collapsed batch implementation returning all zeros must not pass."""
    acv = batch_acv_by_retailer(QUARTERS, RETAILER_IDS)
    tdp = batch_tdp_by_retailer(QUARTERS, RETAILER_IDS)
    acv_vals = [acv[r][q] for r in RETAILER_IDS for q in QUARTERS]
    tdp_vals = [tdp[r][q] for r in RETAILER_IDS for q in QUARTERS]

    assert any(v > 0 for v in acv_vals), "every ACV% came back zero"
    assert any(v > 0 for v in tdp_vals), "every TDP came back zero"
    # The specific regression: correct in the first quarter, zero thereafter.
    for r in RETAILER_IDS:
        later = [acv[r][q] for q in QUARTERS[1:]]
        assert any(v > 0 for v in later), f"{r} ACV% is zero in every quarter after the first"


def test_pinned_known_good_values():
    """Absolute values from the deterministic dataset.

    Parity alone cannot catch both implementations drifting together, so pin a
    few figures computed against the shipped seed.
    """
    assert calc_penetration_rate("Q4 2025") == pytest.approx(0.847, abs=5e-4)
    assert calc_acv_pct("Q4 2025", retailers=["RET-WALMART"]) == pytest.approx(0.796, abs=5e-4)
    assert calc_tdp("Q4 2025", retailers=["RET-WALMART"]) == pytest.approx(21.77, abs=5e-3)
